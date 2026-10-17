"""Run a single local inference worker and always clean up its request."""
import json
from pathlib import Path
import os
import subprocess
import time

def run_worker(app, job_id, details, script, python, update):
    requests = app / 'data' / 'jobs'
    requests.mkdir(exist_ok=True)
    request = requests / f'{job_id}.json'
    request.write_text(json.dumps(details, ensure_ascii=False), encoding='utf-8')
    log = app / 'data' / 'generations' / f'{job_id}.worker.log'
    try:
        with log.open('w', encoding='utf-8') as stream:
            process = subprocess.Popen([str(python), '-u', str(app / script), str(request)],
                cwd=str(app), stdout=stream, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW,
                env=dict(os.environ, PYTHONIOENCODING='utf-8'))
            deadline = time.monotonic() + 1200
            while process.poll() is None and time.monotonic() < deadline:
                time.sleep(1)
                lines = log.read_text(encoding='utf-8', errors='replace').splitlines()
                progress = [line for line in lines if line.startswith(('STUDIO:', 'Creative voice model loaded', 'Creating creative passage'))]
                if progress:
                    update(progress[-1].removeprefix('STUDIO:'))
            if process.poll() is None:
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True,
                               creationflags=subprocess.CREATE_NO_WINDOW)
                process.wait()
                raise RuntimeError('This audio took too long to process. Try a shorter clip.')
        if process.returncode or not Path(details['output']).is_file():
            detail = log.read_text(encoding='utf-8', errors='replace').lower()
            if '1455' in detail or 'paging file' in detail:
                raise RuntimeError('Windows virtual memory is too full to load this voice. Close memory-heavy apps or restart this PC, then try again.')
            if 'out of memory' in detail:
                raise RuntimeError('GPU memory is full. Close other GPU apps, then try again.')
            raise RuntimeError(f'The voice engine stopped (code {process.returncode}). The studio is still available. Details are in the local worker log.')
    finally:
        request.unlink(missing_ok=True)
