"""Single-user, loopback-only offline speech studio."""
import base64
from datetime import datetime, timezone
import io
import json
import mimetypes
import os
from pathlib import Path
import secrets
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
import uuid
from feelings import FEELINGS, catalog as feeling_catalog, parse_script, settings as feeling_settings
from creative import PRESETS, parse_creative
from conversion_audio import decode_source, source_label
from worker_runner import run_worker
from runtime_paths import RUNTIME
from output_storage import OutputStorage

os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", DO_NOT_TRACK="1")
from offline_network import enforce_local_network
enforce_local_network()

APP = Path(__file__).resolve().parent
DATA = APP / "data"
GENERATIONS = DATA / "generations"
VOICES = DATA / "voices"
CONVERSION_INPUTS = DATA / 'conversion-inputs'
for directory in (GENERATIONS, VOICES, CONVERSION_INPUTS):
    directory.mkdir(parents=True, exist_ok=True)
OUTPUTS = OutputStorage(DATA / 'output-settings.json', GENERATIONS, protected_directories=(VOICES,))
PORT = int(os.environ.get("OVS_PORT", "7865"))
ORIGIN = f"http://127.0.0.1:{PORT}"
TOKEN = secrets.token_urlsafe(32)
JOBS = {}
ACTIVE = threading.Lock()
CLASSIC_CPU_COMPAT = False
STARTED = time.time()
CREATIVE_PYTHON = RUNTIME / 'qwen-venv' / 'Scripts' / 'python.exe'
CREATIVE_MODEL = RUNTIME / 'models' / 'qwen-design-sharded' / 'model.safetensors.index.json'
MODEL_ROOT = RUNTIME / 'models'
DESIGNED_REFERENCES = {'soft_hypnotic': 'Soft-Hypnotic-Demo.wav', 'shadow_spirit': 'Shadow-Spirit-Demo.wav'}

def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path, content):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)

def voice_list():
    result = [
        {"id": "english_default", "name": "English · Original", "language": "en", "custom": False},
        {"id": "ta_female", "name": "Tamil · Female", "language": "ta", "custom": False},
        {"id": "ta_male", "name": "Tamil · Male", "language": "ta", "custom": False},
    ]
    for metadata in VOICES.glob("*.json"):
        voice = read_json(metadata)
        if (VOICES / f'{voice["id"]}.wav').is_file():
            result.append(voice)
    return result

def history():
    return OUTPUTS.history()

def conversion_targets():
    targets = [dict(id=v['id'], name=v['name'], kind='Saved voice' if v['custom'] else 'Built-in voice') for v in voice_list()]
    for key, filename in DESIGNED_REFERENCES.items():
        if (APP / filename).is_file():
            targets.append(dict(id='design:' + key, name=PRESETS[key]['label'], kind='Designed character'))
    return targets

def conversion_reference(target_id):
    if target_id == 'english_default':
        return dict(conditioning=str(MODEL_ROOT / 'base' / 'conds.pt'))
    if target_id in ('ta_female', 'ta_male'):
        return dict(conditioning=str(MODEL_ROOT / 'indic' / 'conds' / (target_id + '.pt')))
    if target_id.startswith('design:'):
        key = target_id.removeprefix('design:')
        return dict(reference=str(APP / DESIGNED_REFERENCES[key]))
    return dict(reference=str(VOICES / (target_id + '.wav')))

def conversion_job(job_id, source, label, source_seconds, target):
    job = JOBS[job_id]
    def update(message):
        job.update(status='working', message=message)
    try:
        import numpy as np
        import soundfile as sf
        output = OUTPUTS.output_path(job_id)
        details = dict(source=str(source), output=str(output), **conversion_reference(target['id']))
        update('Preparing offline voice conversion…')
        run_worker(APP, job_id, details, 'conversion_worker.py', Path(os.sys.executable), update)
        audio, rate = sf.read(output, dtype='float32')
        result = dict(id=job_id, created=datetime.now(timezone.utc).isoformat(),
                      text='Voice conversion · ' + label, source_name=label, source_seconds=round(source_seconds, 2),
                      language='source', voice=target['name'], target_voice=target['id'], mode='conversion',
                      seconds=round(len(audio) / rate, 2), sample_rate=rate,
                      elapsed=round(time.time() - job['started'], 2), audio_url=f'/audio/{job_id}.wav',
                      rms=float(np.sqrt(np.mean(audio ** 2))), engine='ChatterboxVC', saved_path=str(output))
        save_json(output.with_suffix('.json'), result)
        source.unlink(missing_ok=True)
        job.update(status='done', message='Your converted audio is ready', result=result)
    except Exception as error:
        traceback.print_exc()
        job.update(status='error', message=str(error))
    finally:
        try:
            source.unlink(missing_ok=True)
        finally:
            ACTIVE.release()

def generate_job(job_id, payload, voice):
    global CLASSIC_CPU_COMPAT
    job = JOBS[job_id]
    def update(message):
        job.update(status="working", message=message)
    try:
        update("Starting the voice engine…")
        import numpy as np
        import soundfile as sf
        file = OUTPUTS.output_path(job_id)
        creative = payload['mode'] == 'creative'
        details = dict(payload, output=str(file), voice_id=voice['id'],
                       reference=str(VOICES / f"{voice['id']}.wav") if voice['custom'] else None)
        details['cpu_only'] = CLASSIC_CPU_COMPAT and not creative
        update('Loading the creative voice model…' if creative else 'Loading your saved voice model…')
        try:
            run_worker(APP, job_id, details, 'creative_worker.py' if creative else 'classic_worker.py',
                       CREATIVE_PYTHON if creative else Path(os.sys.executable), update)
        except RuntimeError:
            log = (GENERATIONS / f'{job_id}.worker.log').read_text(encoding='utf-8', errors='replace').lower()
            if creative or details['cpu_only'] or not any(value in log for value in ('cuda error', 'out of memory', 'paging file', 'memory allocation failure')):
                raise
            CLASSIC_CPU_COMPAT = True
            details['cpu_only'] = True
            update('Using a lower-memory compatibility mode. Speech may take longer…')
            run_worker(APP, job_id + '-compat', details, 'classic_worker.py', Path(os.sys.executable), update)
        audio, rate = sf.read(file, dtype='float32')
        result = {"id": job_id, "created": datetime.now(timezone.utc).isoformat(), "text": payload["text"],
                  "language": payload["language"], "voice": voice["name"], "seconds": round(len(audio) / rate, 2),
                  "elapsed": round(time.time() - job["started"], 2), "sample_rate": rate,
                  "feeling": payload["feeling"], "feeling_strength": payload["expression"],
                  "mode": payload['mode'], "voice_description": payload.get('description', ''),
                  "delivery_sections": payload["sections"],
                  "audio_url": f"/audio/{job_id}.wav", "rms": float(np.sqrt(np.mean(audio ** 2))), 'saved_path':str(file)}
        save_json(file.with_suffix(".json"), result)
        job.update(status="done", message="Your audio is ready", result=result)
    except Exception as error:
        traceback.print_exc()
        message = str(error)
        if "out of memory" in message.lower():
            message = "GPU memory is full. Close other GPU apps, restart the studio, and try a shorter sentence."
        job.update(status="error", message=message)
    finally:
        ACTIVE.release()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, template, *args):
        print(f"{self.command} {urlparse(self.path).path} {args[1] if len(args)>1 else ''}", flush=True)

    def send(self, content, code=200, kind="application/json; charset=utf-8"):
        if isinstance(content, (dict, list)):
            content = json.dumps(content, ensure_ascii=False).encode("utf-8")
        elif isinstance(content, str):
            content = content.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; media-src 'self' blob:; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(content)

    def valid_host(self):
        return self.headers.get("Host") in (f"127.0.0.1:{PORT}", f"localhost:{PORT}")

    def do_GET(self):
        if not self.valid_host():
            return self.send({"error": "Local connections only"}, 403)
        route = urlparse(self.path).path
        if route == "/api/health":
            return self.send({"app": "offline-voice-studio", "offline": True, "pid": os.getpid(), "app_root": str(APP), "busy": ACTIVE.locked(), "inference": "isolated workers"})
        if route == '/api/openapi.json':
            return self.send((APP / 'docs' / 'openapi.json').read_bytes())
        if route == "/api/state":
            return self.send({"voices": voice_list(), "history": history(), "feelings": feeling_catalog(), "ready": True,
                              "creative_ready": CREATIVE_PYTHON.is_file() and CREATIVE_MODEL.is_file(), "creative_presets": PRESETS,
                              'conversion_targets': conversion_targets(), 'conversion_ready': (MODEL_ROOT / 'base' / 's3gen.pt').is_file(), 'storage':OUTPUTS.describe()})
        if route.startswith("/api/jobs/"):
            job = JOBS.get(route.rsplit("/", 1)[-1])
            return self.send(job or {"error": "Job not found"}, 200 if job else 404)
        if route in ("/", "/index.html"):
            content = (APP / "web" / "index.html").read_text(encoding="utf-8").replace("__SESSION_TOKEN__", TOKEN)
            return self.send(content, kind="text/html; charset=utf-8")
        if route in ("/app.js", "/conversion.js", "/audio-wav.js", "/file-entry.js", "/style.css"):
            file = APP / "web" / route[1:]
            return self.send(file.read_bytes(), kind="application/javascript" if route.endswith(".js") else "text/css")
        if route.startswith("/audio/"):
            name = route.rsplit("/", 1)[-1]
            try:
                if not name.endswith('.wav'):
                    raise ValueError('Not audio')
                job_id = str(uuid.UUID(name.removesuffix(".wav")))
            except ValueError:
                return self.send({"error": "Invalid audio ID"}, 404)
            file = OUTPUTS.find_audio(job_id)
            if file:
                return self.send(file.read_bytes(), kind="audio/wav")
        return self.send({"error": "Not found"}, 404)

    def do_POST(self):
        if not self.valid_host() or self.headers.get("X-Studio-Token") != TOKEN:
            return self.send({"error": "Reload the studio page to continue"}, 403)
        origin = self.headers.get("Origin")
        if origin and origin not in (ORIGIN, f"http://localhost:{PORT}"):
            return self.send({"error": "Local studio requests only"}, 403)
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= 35 * 1024 * 1024:
                raise ValueError("The recording is too large. Use a short WAV or FLAC clip.")
            body = json.loads(self.rfile.read(length))
            route = urlparse(self.path).path
            if route == '/api/storage':
                if not ACTIVE.acquire(blocking=False):
                    return self.send({'error':'Wait for the current audio to finish before changing the save folder.'},409)
                try:
                    return self.send({'storage':OUTPUTS.change(body.get('directory'))})
                finally:
                    ACTIVE.release()
            if route == '/api/storage/open':
                if not OUTPUTS.current.is_dir():
                    raise ValueError('The saved folder is unavailable. Choose another folder.')
                try:
                    os.startfile(str(OUTPUTS.current))
                except OSError as error:
                    raise ValueError('Windows could not open this folder. Check that the drive is available.') from error
                return self.send({'opened':True})
            if route == "/api/voices":
                return self.add_voice(body)
            if route == '/api/convert':
                return self.convert_voice(body)
            if route != "/api/generate":
                return self.send({"error": "Not found"}, 404)
            text = str(body.get("text", "")).strip()
            if not text or len(text) > 2000:
                raise ValueError("Enter between 1 and 2,000 characters.")
            language = body.get("language")
            if language not in ("en", "ta"):
                raise ValueError("Choose English or Tamil.")
            mode = body.get('mode', 'classic')
            if mode not in ('classic', 'creative'):
                raise ValueError('Choose a voice mode.')
            feeling = body.get("feeling", "neutral")
            strength = float(body.get("expression", 0.7))
            feeling_settings(feeling, strength)
            description = str(body.get('description', '')).strip()
            if mode == 'creative':
                if language != 'en':
                    raise ValueError('Creative voice design currently supports English. Use Saved voice mode for Tamil.')
                if not CREATIVE_PYTHON.is_file() or not CREATIVE_MODEL.is_file():
                    raise ValueError('The creative voice model is not installed yet.')
                sections = parse_creative(text, description)
                voice = dict(id='creative', name='Creative · Designed voice', custom=False)
            else:
                voice = next((v for v in voice_list() if v['id'] == body.get('voice')), None)
                if voice is None or (not voice['custom'] and voice['language'] != language):
                    raise ValueError('Choose a voice for the selected language.')
                sections = parse_script(text, feeling)
            payload = {"text": text, "language": language, "feeling": feeling, "expression": strength,
                       "sections": sections, "seed": int(body.get("seed", 42)) % 2147483647,
                       'mode': mode, 'description': description}
            if not ACTIVE.acquire(blocking=False):
                return self.send({"error": "A voice is already generating. Please wait."}, 409)
            job_id = str(uuid.uuid4())
            JOBS[job_id] = {"id": job_id, "status": "queued", "message": "Preparing your audio…", "started": time.time()}
            threading.Thread(target=generate_job, args=(job_id, payload, voice), daemon=True).start()
            return self.send({"id": job_id}, 202)
        except (ValueError, KeyError, TypeError) as error:
            return self.send({"error": str(error)}, 400)
        except Exception:
            traceback.print_exc()
            return self.send({"error": "Could not process this request. Try a WAV recording."}, 500)

    def convert_voice(self, body):
        import soundfile as sf
        target = next((v for v in conversion_targets() if v['id'] == body.get('target')), None)
        if target is None:
            raise ValueError('Choose an available target voice.')
        audio, rate = decode_source(body.get('audio'))
        if not ACTIVE.acquire(blocking=False):
            return self.send({'error': 'Audio is already processing. Please wait.'}, 409)
        job_id = str(uuid.uuid4())
        source = CONVERSION_INPUTS / (job_id + '.wav')
        try:
            sf.write(source, audio, rate, subtype='PCM_16')
            JOBS[job_id] = dict(id=job_id, status='queued', message='Preparing voice conversion…', started=time.time())
            threading.Thread(target=conversion_job,
                args=(job_id, source, source_label(body.get('name', 'Audio recording')), len(audio) / rate, target), daemon=True).start()
        except Exception:
            source.unlink(missing_ok=True)
            ACTIVE.release()
            raise
        return self.send({'id': job_id}, 202)

    def add_voice(self, body):
        import numpy as np
        import soundfile as sf
        from scipy.signal import resample_poly
        import math
        name = str(body.get("name", "")).strip()[:60]
        if not name:
            raise ValueError("Give this voice a name.")
        recording = base64.b64decode(body["audio"], validate=True)
        audio, rate = sf.read(io.BytesIO(recording), dtype="float32", always_2d=True)
        if not 3 <= len(audio) / rate <= 30:
            raise ValueError("Use a clear recording between 3 and 30 seconds long.")
        audio = np.mean(audio, axis=1)
        if not np.isfinite(audio).all() or float(np.sqrt(np.mean(audio ** 2))) < 0.002:
            raise ValueError("This recording is too quiet or invalid. Try a clearer clip.")
        divisor = math.gcd(rate, 24000)
        audio = resample_poly(audio, 24000 // divisor, rate // divisor)
        audio = audio[:24000 * 15]
        voice_id = str(uuid.uuid4())
        sf.write(VOICES / f"{voice_id}.wav", audio, 24000, subtype="PCM_16")
        voice = {"id": voice_id, "name": name, "language": "both", "custom": True}
        save_json(VOICES / f"{voice_id}.json", voice)
        return self.send(voice, 201)

if __name__ == "__main__":
    print(f"Local Voice Studio: {ORIGIN} (offline; this PC only)", flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
