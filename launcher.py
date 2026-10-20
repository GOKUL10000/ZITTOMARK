"""Start or stop only this app copy. No PowerShell policy changes or public listener."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
import webbrowser
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener
from runtime_paths import APP, RUNTIME
from studio_client import NoRedirect


def health(url):
    try:
        with build_opener(ProxyHandler({}), NoRedirect()).open(url+'/api/health', timeout=2) as response:
            return json.load(response)
    except (OSError, ValueError, URLError): return None


def own_app(status):
    root = status.get('app_root')
    return (status.get('app') == 'offline-voice-studio' and
            isinstance(root, str) and bool(root) and Path(root).is_absolute() and Path(root).resolve() == APP)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('start','stop'))
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    port = int(os.environ.get('OVS_PORT','7865'))
    if not 1024 <= port <= 65535: raise ValueError('Choose OVS_PORT between 1024 and 65535.')
    url = f'http://127.0.0.1:{port}'
    log = APP/'data'/'logs'
    pid_file = log/f'studio-{port}.pid'
    status = health(url)
    if status and not own_app(status): raise RuntimeError('Another app copy uses this port. It was left running; choose OVS_PORT or stop that copy.')
    if args.action == 'stop':
        if not status: print('This studio is already stopped.'); return 0
        if not pid_file.is_file() or int(pid_file.read_text().strip()) != int(status['pid']):
            raise RuntimeError('The process record does not match. No process was stopped.')
        if os.name != 'nt': raise RuntimeError('This launcher targets Windows.')
        subprocess.run(['taskkill.exe','/PID',str(int(status['pid'])),'/T','/F'], check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW)
        for path in (APP/'data'/'conversion-inputs').glob('*.wav'):
            try: uuid.UUID(path.stem)
            except ValueError: continue
            path.unlink(missing_ok=True)
        print('Local Voice Studio stopped.'); return 0
    python = RUNTIME/'.venv'/'Scripts'/'python.exe'
    if not python.is_file(): raise RuntimeError('Run Install.cmd first. The private speech runtime is not installed.')
    if not status:
        log.mkdir(parents=True, exist_ok=True)
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
        with (log/f'studio-{port}.log').open('ab') as output, (log/f'studio-{port}-error.log').open('ab') as errors:
            process = subprocess.Popen([str(python),'-u',str(APP/'server.py')], cwd=APP,
                stdin=subprocess.DEVNULL, stdout=output, stderr=errors, close_fds=True, creationflags=flags)
        deadline = time.monotonic()+25
        while time.monotonic()<deadline:
            status = health(url)
            if status:
                if not own_app(status): raise RuntimeError('Another app won this port. Choose a different OVS_PORT.')
                break
            if process.poll() is not None: raise RuntimeError('Startup failed. Check the error log in data/logs.')
            time.sleep(0.25)
        else: raise RuntimeError('Startup timed out. Check the error log in data/logs.')
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    pid_file.write_text(str(int(status['pid'])), encoding='ascii')
    print('Local Voice Studio is ready at ' + url)
    if not args.no_browser: webbrowser.open(url)
    return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except Exception as error:
        print(str(error), file=sys.stderr); sys.exit(1)
