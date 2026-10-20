"""Standard-library client for the private, loopback-only studio API."""
import json
import os
from pathlib import Path
import re
import subprocess
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from runtime_paths import APP, RUNTIME


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Studio redirects are not allowed.')


class StudioClient:
    def __init__(self, url=None):
        url = url or os.environ.get('OVS_URL') or ('http://127.0.0.1:' + os.environ.get('OVS_PORT', '7865'))
        parsed = urlsplit(url)
        if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or parsed.username or
                parsed.password or parsed.path not in ('', '/') or parsed.query or parsed.fragment or
                not parsed.port or not 1024 <= parsed.port <= 65535):
            raise ValueError('Use http://127.0.0.1:PORT with a port between 1024 and 65535.')
        self.url = url.rstrip('/')
        self.opener = build_opener(ProxyHandler({}), NoRedirect())
        self.token = None

    def _read(self, route, payload=None):
        headers = {}
        data = None
        if payload is not None:
            if not self.token:
                self._token()
            headers = {'Content-Type': 'application/json', 'X-Studio-Token': self.token}
            data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        request = Request(self.url + route, data=data, headers=headers)
        try:
            with self.opener.open(request, timeout=45) as response:
                return response.read()
        except HTTPError as error:
            try:
                message = json.loads(error.read()).get('error', str(error))
            except (ValueError, AttributeError):
                message = str(error)
            raise RuntimeError(f'Studio HTTP {error.code}: {message}') from error
        except URLError as error:
            raise RuntimeError('The studio is unavailable. Start-Local-Voice.cmd or start_studio first.') from error

    def _token(self):
        page = self._read('/').decode('utf-8')
        match = re.search(r'<meta name="studio-token" content="([A-Za-z0-9_-]+)"', page)
        if not match:
            raise RuntimeError('This server is not a compatible Local Voice Studio.')
        self.token = match.group(1)

    def request(self, route, payload=None):
        if not route.startswith('/api/') or '?' in route or '#' in route or '..' in route:
            raise ValueError('Invalid studio API route.')
        try:
            return json.loads(self._read(route, payload))
        except RuntimeError as error:
            # A rejected token means no operation ran. Refresh once after a restart.
            if payload is None or not str(error).startswith('Studio HTTP 403: Reload'):
                raise
            self._token()
            return json.loads(self._read(route, payload))

    def status(self):
        health = self.request('/api/health')
        state = self.request('/api/state')
        return dict(health, creative_ready=state['creative_ready'], conversion_ready=state['conversion_ready'])

    def voices(self):
        state = self.request('/api/state')
        return {key: state[key] for key in ('voices', 'feelings', 'creative_presets', 'conversion_targets', 'creative_ready')}

    def job(self, job_id):
        return self.request('/api/jobs/' + str(uuid.UUID(job_id)))

    def generate(self, text, language='en', voice='english_default', feeling='neutral',
                 strength=0.7, mode='classic', description='', seed=42):
        return self.request('/api/generate', dict(text=text, language=language, voice=voice,
            feeling=feeling, expression=strength, mode=mode, description=description, seed=seed))

    def history(self, limit=10):
        return {'generations': self.request('/api/state')['history'][:max(1, min(100, int(limit)))]}

    def audio_payload(self, input_path, reference=False):
        source = Path(input_path).expanduser().resolve(strict=True)
        if not source.is_file() or source.stat().st_size > 128 * 1024 * 1024:
            raise ValueError('Choose an audio file up to 128 MB.')
        python = RUNTIME / '.venv' / 'Scripts' / 'python.exe'
        if not python.is_file():
            raise RuntimeError('Run Setup.cmd first to install the audio runtime.')
        result = subprocess.run([str(python), str(APP / 'normalize_audio.py'), str(source),
            '--reference' if reference else '--conversion'], capture_output=True, text=True,
            encoding='utf-8', timeout=120, cwd=APP)
        if result.returncode:
            raise ValueError(result.stderr.strip()[-1500:] or 'The audio file could not be decoded. Try WAV or FLAC.')
        return json.loads(result.stdout)

    def convert(self, input_path, target_voice):
        audio = self.audio_payload(input_path)
        return self.request('/api/convert', dict(audio=audio['audio'], name=Path(input_path).name, target=target_voice))

    def add_voice(self, name, input_path):
        audio = self.audio_payload(input_path, reference=True)
        return self.request('/api/voices', dict(name=name, audio=audio['audio']))

    def start(self):
        if os.name != 'nt':
            raise RuntimeError('Automatic startup requires Windows. Run the server manually on other systems.')
        # Never run a user-provided command. Launch only this checkout's fixed script.
        environment = dict(os.environ, OVS_PORT=str(urlsplit(self.url).port))
        log = APP / 'data' / 'logs' / 'agent-start.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        # Windows descendants can retain inherited pipe handles after a launcher exits.
        # Use a file and detached stdin so completion never waits on a server-held pipe.
        with log.open('w', encoding='utf-8') as stream:
            result = subprocess.run([str(RUNTIME / '.venv' / 'Scripts' / 'python.exe'),
                str(APP / 'launcher.py'), 'start', '--no-browser'],
                stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
                timeout=45, cwd=APP, env=environment, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise RuntimeError(log.read_text(encoding='utf-8', errors='replace').strip()[-1500:] or 'Studio startup failed.')
        return self.status()
