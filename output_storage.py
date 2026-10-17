"""Persistent local output folders, including access to earlier generations."""
import json
import os
from pathlib import Path
import uuid


def local_directory(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Enter the full path of a local folder.')
    value = os.path.expandvars(value.strip().strip('"'))
    if any(ord(char) < 32 for char in value) or value.startswith(('\\\\', '//')):
        raise ValueError('Use a local folder, for example C:\\Voice recordings.')
    path = Path(value).expanduser()
    if not path.is_absolute() or (os.name == 'nt' and (len(path.drive) != 2 or path.drive[1] != ':')):
        raise ValueError('Enter a full local folder path, for example C:\\Voice recordings.')
    path = path.resolve()
    if str(path).startswith(('\\\\', '//')):
        raise ValueError('Choose a local folder rather than a network share.')
    return path


class OutputStorage:
    def __init__(self, settings_file, default_directory, protected_directories=()):
        self.settings_file = Path(settings_file)
        self.protected = {Path(folder).resolve() for folder in protected_directories}
        self.default = Path(default_directory).resolve()
        self.current = self.default
        self.folders = [self.default]
        self.warning = ''
        if self.settings_file.exists():
            try:
                settings = json.loads(self.settings_file.read_text(encoding='utf-8'))
                current = local_directory(settings['generation_directory'])
                if current in self.protected:
                    raise ValueError('Reserved application folder.')
                folders = [local_directory(value) for value in settings.get('previous_directories', [])]
                self.current = current
                self.folders = list(dict.fromkeys([current, self.default, *folders]))
            except (OSError, ValueError, KeyError, TypeError):
                self.warning = 'The saved folder setting could not be read. Choose your save folder again.'

    def describe(self):
        return dict(generation_directory=str(self.current), default_directory=str(self.default), warning=self.warning)

    @staticmethod
    def check_writable(folder):
        probe = folder / ('.voice-studio-write-check-' + str(uuid.uuid4()))
        try:
            folder.mkdir(parents=True, exist_ok=True)
            with probe.open('xb') as file:
                file.write(b'Voice Studio folder check')
        except OSError as error:
            raise ValueError('This folder is unavailable or cannot be written to. Choose another local folder.') from error
        finally:
            try:
                probe.unlink(missing_ok=True)
            except OSError:
                pass

    def change(self, value):
        folder = local_directory(value)
        if folder in self.protected:
            raise ValueError('This folder is used for saved voice references. Choose another folder for generated audio.')
        self.check_writable(folder)
        folders = list(dict.fromkeys([folder, *self.folders]))
        settings = dict(generation_directory=str(folder), previous_directories=[str(item) for item in folders])
        temporary = self.settings_file.with_suffix('.tmp')
        try:
            temporary.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(self.settings_file)
        except OSError as error:
            raise ValueError('The app could not remember this folder. The previous setting is still active.') from error
        finally:
            temporary.unlink(missing_ok=True)
        self.current, self.folders, self.warning = folder, folders, ''
        return self.describe()

    def output_path(self, job_id):
        name = str(uuid.UUID(job_id)) + '.wav'
        self.check_writable(self.current)
        return self.current / name

    def find_audio(self, job_id):
        name = str(uuid.UUID(job_id)) + '.wav'
        for folder in self.folders:
            file = folder / name
            try:
                if file.is_file() and file.resolve().parent == folder:
                    return file
            except OSError:
                continue
        return None

    def history(self, limit=30):
        records = {}
        for folder in self.folders:
            try:
                files = list(folder.glob('*.json'))
            except OSError:
                continue
            for file in files:
                try:
                    # Only studio UUID metadata with its matching audio is history.
                    job_id = str(uuid.UUID(file.stem))
                    if file.resolve().parent != folder or file.stat().st_size > 128 * 1024:
                        continue
                    audio = folder / (job_id + '.wav')
                    if not audio.is_file() or audio.resolve().parent != folder:
                        continue
                    item = json.loads(file.read_text(encoding='utf-8'))
                    if item.get('id') != job_id or not all(key in item for key in ('text','voice','seconds','sample_rate','created','audio_url')):
                        continue
                    item['saved_path'] = str(audio)
                    item['audio_url'] = '/audio/' + job_id + '.wav'
                    modified = file.stat().st_mtime
                    if job_id not in records or modified > records[job_id][0]:
                        records[job_id] = (modified, item)
                except (OSError, ValueError, TypeError, AttributeError):
                    continue
        return [item for _, item in sorted(records.values(), key=lambda pair:pair[0], reverse=True)[:limit]]
