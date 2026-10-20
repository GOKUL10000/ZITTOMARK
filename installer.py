"""Private Windows installation. Downloaded dependencies are pinned and hash checked."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from runtime_paths import APP, RUNTIME


def plan(basic=False, agents_only=False):
    environments = ['agent-venv'] if agents_only else ['.venv', 'agent-venv']
    if not basic and not agents_only: environments.append('qwen-venv')
    return dict(runtime=str(RUNTIME), environments=environments,
        models=[] if agents_only else ['English / Tamil / voice conversion'] + ([] if basic else ['Creative English']),
        requires_nvidia=not agents_only, recommended_free_gb=2 if agents_only else 20 if basic else 40,
        sources=['github.com/astral-sh', 'pypi.org', 'files.pythonhosted.org', 'download.pytorch.org',
                 'codeload.github.com', 'huggingface.co (and its model download CDN)'],
        global_python_changes=False, powershell_policy_changes=False, firewall_changes=False)


def verified_uv(path):
    lock = json.loads((APP/'bootstrap-lock.json').read_text())
    path = Path(path).resolve(strict=True)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != lock['uv']['executable_sha256']:
        raise ValueError('The installer helper checksum does not match. Run Install.cmd to fetch the verified copy.')
    return path


def clean_environment():
    # Local package-index overrides must not silently change where this installer looks.
    environment = {key:value for key,value in os.environ.items()
                   if not key.startswith(('PIP_', 'UV_')) and key not in ('PYTHONHOME','PYTHONPATH')}
    environment.update(UV_CACHE_DIR=str(RUNTIME/'uv-cache'), UV_PYTHON_INSTALL_DIR=str(RUNTIME/'python'),
        PYTHONIOENCODING='utf-8', PYTHONUTF8='1', UV_NO_PROGRESS='1')
    return environment


class Installer:
    def __init__(self, uv, selected):
        self.uv, self.selected = str(uv), selected
        self.log = APP/'data'/'logs'/'install.log'
        self.report = APP/'data'/'installation.json'
        self.environment = clean_environment()
        self.step = ''

    def run(self, title, *command):
        self.step = title
        print('\n' + title, flush=True)
        self.log.parent.mkdir(parents=True, exist_ok=True)
        with self.log.open('a', encoding='utf-8') as stream:
            stream.write('\n[' + datetime.now(timezone.utc).isoformat() + '] ' + title + '\n'); stream.flush()
            result = subprocess.run([str(arg) for arg in command], cwd=APP, env=self.environment,
                stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT)
        if result.returncode:
            detail = self.log.read_text(encoding='utf-8', errors='replace')[-3500:]
            raise RuntimeError(title + ' failed. Details: ' + str(self.log) + '\n' + detail)

    def packages(self, python, lock, source_builds=False):
        command = [self.uv, '--no-config', 'pip', 'install', '--python', python,
            '--default-index', 'https://pypi.org/simple', '--no-deps', '--require-hashes',
            '--no-build-isolation', '-r', APP/lock]
        if not source_builds: command.append('--only-binary=:all:')
        self.run('Install verified packages: ' + lock, *command)

    def write_report(self, status, error=None):
        self.report.parent.mkdir(parents=True, exist_ok=True)
        record = dict(self.selected, status=status, updated=datetime.now(timezone.utc).isoformat(), last_step=self.step)
        if error: record['error'] = str(error)[-3500:]
        self.report.write_text(json.dumps(record, indent=2), encoding='utf-8')

    def install(self):
        try:
            for name in self.selected['environments']:
                location = RUNTIME/name
                python = location/'Scripts'/'python.exe'
                if not python.is_file():
                    self.run('Create private environment: ' + name, self.uv, '--no-config', 'venv',
                        '--python', sys.executable, location)
                else:
                    self.run('Check existing environment: ' + name, python, '-c',
                        'import sys; assert sys.version_info[:2] == (3, 11)')
                if name != 'agent-venv': self.packages(python, 'requirements-build.lock')
                lock = {'agent-venv':'requirements-agent.lock','.venv':'requirements-classic.lock',
                        'qwen-venv':'requirements-creative.lock'}[name]
                self.packages(python, lock, source_builds=name != 'agent-venv')
                self.run('Check installed dependencies: ' + name, self.uv, '--no-config', 'pip', 'check', '--python', python)
            classic = RUNTIME/'.venv'/'Scripts'/'python.exe'
            if self.selected['models']:
                creative = 'qwen-venv' in self.selected['environments']
                self.run('Download and verify speech models (may take a while)', classic, APP/'download_models.py',
                    *(['--creative'] if creative else []))
                if creative:
                    self.run('Prepare and verify creative model shards', classic, APP/'shard_creative_model.py')
                self.run('Check local models and NVIDIA GPU', classic, APP/'doctor.py',
                    *(['--require-creative'] if creative else []))
            agent = RUNTIME/'agent-venv'/'Scripts'/'python.exe'
            self.run('Create local AI-tool connection examples', agent, APP/'agent_config.py')
            self.write_report('complete')
        except Exception as error:
            self.write_report('failed', error)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--basic', action='store_true', help='English/Tamil and MCP; omit optional creative model')
    group.add_argument('--agents-only', action='store_true', help='Install MCP support only; no speech models')
    parser.add_argument('--creative', action='store_true', help='Full installation (the default)')
    parser.add_argument('--yes', action='store_true', help='Accept the displayed download/install plan')
    parser.add_argument('--check-only', action='store_true', help='Display prerequisites and plan without installing')
    args = parser.parse_args()
    selected = plan(args.basic, args.agents_only)
    print('ZITTOMARK installation plan\n' + json.dumps(selected, indent=2), flush=True)
    if args.check_only: return 0
    if os.name != 'nt' or platform.machine().lower() not in ('amd64', 'x86_64'):
        raise RuntimeError('The packaged installer requires 64-bit x86 Windows 10/11.')
    if sys.version_info[:2] != (3, 11): raise RuntimeError('Use Install.cmd to obtain the private Python 3.11 runtime.')
    if not args.yes and os.environ.get('OVS_BOOTSTRAP_APPROVED') != '1':
        if input('Download and execute the listed third-party packages? [y/N] ').strip().lower() != 'y':
            print('Installation cancelled.'); return 0
    uv = verified_uv(os.environ.get('OVS_UV', str(RUNTIME/'bootstrap'/'uv-0.11.7'/'uv.exe')))
    if selected['requires_nvidia']:
        driver = shutil.which('nvidia-smi.exe')
        if not driver: raise RuntimeError('NVIDIA driver not found. Install/update it from nvidia.com, then retry. No GPU driver is installed automatically.')
        result = subprocess.run([driver,'--query-gpu=name','--format=csv,noheader'], capture_output=True, text=True)
        if result.returncode: raise RuntimeError('NVIDIA driver is unavailable. Update it and retry.')
        print('Detected GPU: ' + result.stdout.strip(), flush=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    free = shutil.disk_usage(RUNTIME).free / 1024**3
    if free < selected['recommended_free_gb']:
        raise RuntimeError(f'Only {free:.1f} GB is free. Allow {selected["recommended_free_gb"]} GB for this installation profile.')
    Installer(uv, selected).install()
    print('\nInstallation complete. Double-click Start-Local-Voice.cmd.\nAI tool connection examples: data/agent-config', flush=True)
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    try: sys.exit(main())
    except Exception as error:
        print('\nInstallation stopped: ' + str(error) + '\nCorrect the issue and rerun Install.cmd; verified downloads are reused.', file=sys.stderr)
        sys.exit(1)
