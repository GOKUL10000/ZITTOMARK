import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from output_storage import OutputStorage, local_directory

class OutputStorageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='voice-storage-test-',dir=Path(__file__).resolve().parent)
        self.root = Path(self.temporary.name).resolve()
        assert self.root.is_relative_to(Path(__file__).resolve().parent)
        self.default = self.root/'original'
        self.default.mkdir()
        self.settings = self.root/'settings.json'
        self.store = OutputStorage(self.settings,self.default)
    def tearDown(self):
        assert self.root.is_relative_to(Path(__file__).resolve().parent) and self.root.name.startswith('voice-storage-test-')
        self.temporary.cleanup()
    def recording(self, folder):
        folder.mkdir(exist_ok=True,parents=True)
        job_id = str(uuid.uuid4())
        (folder/(job_id+'.wav')).write_bytes(b'RIFF-test-output')
        metadata = dict(id=job_id,text='Storage test.',voice='Test',seconds=1,sample_rate=24000,
            created='2026-10-18T00:00:00Z',audio_url='/audio/'+job_id+'.wav')
        (folder/(job_id+'.json')).write_text(json.dumps(metadata),encoding='utf-8')
        return job_id
    def test_changed_folder_persists_and_old_recordings_remain_available(self):
        old_id = self.recording(self.default)
        destination = self.root/'New audio தமிழ்'
        self.store.change(str(destination))
        new_id = self.recording(destination)
        reopened = OutputStorage(self.settings,self.default)
        self.assertEqual(reopened.current,destination)
        self.assertEqual(reopened.find_audio(old_id),self.default/(old_id+'.wav'))
        self.assertEqual(reopened.find_audio(new_id),destination/(new_id+'.wav'))
        self.assertEqual({item['id'] for item in reopened.history()},{old_id,new_id})
        self.assertTrue(all('saved_path' in item for item in reopened.history()))
        self.assertEqual(reopened.output_path(str(uuid.uuid4())).parent,destination)
        self.assertFalse(list(destination.glob('.voice-studio-write-check-*')))
    def test_relative_network_and_device_paths_are_rejected(self):
        for value in ('',None,'relative/folder',r'\\server\share',r'\\?\C:\output',r'\\.\pipe\output','//server/share','C:\\bad\npath'):
            with self.subTest(path=value),self.assertRaises(ValueError): self.store.change(value)
        self.assertEqual(self.store.current,self.default)
    def test_unwritable_destination_preserves_previous_setting(self):
        file = self.root/'existing-file'
        file.write_text('Keep this file.',encoding='utf-8')
        with self.assertRaises(ValueError): self.store.change(str(file))
        self.assertEqual(file.read_text(encoding='utf-8'),'Keep this file.')
        self.assertEqual(self.store.current,self.default)
    def test_failed_settings_write_does_not_activate_new_folder(self):
        with patch.object(Path,'replace',side_effect=PermissionError('blocked')):
            with self.assertRaises(ValueError): self.store.change(str(self.root/'new-folder'))
        self.assertEqual(self.store.current,self.default)
        self.assertFalse(self.settings.with_suffix('.tmp').exists())
    def test_history_ignores_foreign_broken_and_unpaired_metadata(self):
        good = self.recording(self.default)
        (self.default/'personal.json').write_text('{"private":"unrelated"}',encoding='utf-8')
        broken = str(uuid.uuid4())
        (self.default/(broken+'.json')).write_text('broken',encoding='utf-8')
        (self.default/(broken+'.wav')).write_bytes(b'test')
        no_audio = str(uuid.uuid4())
        (self.default/(no_audio+'.json')).write_text('{}',encoding='utf-8')
        self.assertEqual([item['id'] for item in self.store.history()],[good])
        with self.assertRaises(ValueError): self.store.find_audio('../personal')
    def test_corrupt_settings_show_a_recovery_message(self):
        self.settings.write_text('broken',encoding='utf-8')
        reopened = OutputStorage(self.settings,self.default)
        self.assertEqual(reopened.current,self.default)
        self.assertTrue(reopened.describe()['warning'])
    def test_saved_voice_folder_cannot_be_used_for_output(self):
        references = self.root/'voices'
        store = OutputStorage(self.settings,self.default,protected_directories=(references,))
        with self.assertRaises(ValueError): store.change(str(references))
        self.assertEqual(store.current,self.default)

if __name__=='__main__': unittest.main()
