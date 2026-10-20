import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import installer
from launcher import own_app


class InstallerIntegrityTests(unittest.TestCase):
    def test_bootstrap_checksum_must_match_before_helper_can_be_used(self):
        with tempfile.TemporaryDirectory(prefix='voice-storage-test-installer-',dir=Path(__file__).resolve().parent) as folder:
            root=Path(folder).resolve()
            helper=root/'helper.exe';helper.write_bytes(b'approved-test-artifact')
            (root/'bootstrap-lock.json').write_text(json.dumps({'uv':{'executable_sha256':hashlib.sha256(helper.read_bytes()).hexdigest()}}))
            with patch.object(installer,'APP',root):
                self.assertEqual(installer.verified_uv(helper),helper)
                helper.write_bytes(b'modified-artifact')
                with self.assertRaisesRegex(ValueError,'checksum'):installer.verified_uv(helper)

    def test_all_package_artifacts_and_bootstrap_are_hash_pinned(self):
        root=Path(__file__).resolve().parents[1]
        for lock in root.glob('requirements-*.lock'):
            for line in lock.read_text().splitlines():
                if not line.strip() or line.startswith('#'):continue
                self.assertRegex(line,r'--hash=sha256:[a-f0-9]{64}',str(lock))
                requirement=line.split(' --hash=')[0]
                if ' @ ' in requirement:
                    self.assertIn(' @ https://',requirement)
                    self.assertNotIn('git+',requirement)
                    if 'github.com/' in requirement:self.assertRegex(requirement,r'/[a-f0-9]{40}\.zip$')
                else:self.assertRegex(requirement,r'^[a-zA-Z0-9_.-]+==[^ ]+$')
        lock=json.loads((root/'bootstrap-lock.json').read_text())
        script=(root/'Install.cmd').read_text()
        self.assertIn(lock['uv']['archive_sha256'],script)
        self.assertIn(lock['uv']['executable_sha256'],script)
        self.assertIn(lock['uv']['url'],script)
        self.assertIn('--no-bin --no-registry',script)

    def test_user_index_overrides_do_not_change_installation_sources(self):
        with patch.dict(os.environ,{'UV_INDEX_URL':'https://untrusted.invalid','PIP_EXTRA_INDEX_URL':'https://untrusted.invalid'}):
            environment=installer.clean_environment()
        self.assertNotIn('UV_INDEX_URL',environment)
        self.assertNotIn('PIP_EXTRA_INDEX_URL',environment)

    def test_launcher_rejects_missing_or_foreign_app_identity(self):
        self.assertTrue(own_app({'app':'offline-voice-studio','app_root':str(installer.APP)}))
        for root in (None,'','.',str(installer.APP/'other-copy')):
            self.assertFalse(own_app({'app':'offline-voice-studio','app_root':root}))
        self.assertFalse(own_app({'app':'other','app_root':str(installer.APP)}))


if __name__=='__main__':unittest.main()
