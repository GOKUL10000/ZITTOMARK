import base64
import io
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
import soundfile as sf
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from normalize_audio import normalize


class NormalizeAudioTests(unittest.TestCase):
    def test_agent_audio_is_24k_mono_and_reference_duration_is_bounded(self):
        with tempfile.TemporaryDirectory(prefix='voice-storage-test-normalize-', dir=Path(__file__).resolve().parent) as folder:
            path = Path(folder) / 'chosen.wav'
            t = np.arange(44100*2) / 44100
            sf.write(path, np.column_stack([0.2*np.sin(t*880), 0.2*np.sin(t*880)]), 44100)
            result = normalize(path)
            decoded, rate = sf.read(io.BytesIO(base64.b64decode(result['audio'])))
            self.assertEqual(rate, 24000)
            self.assertEqual(decoded.shape, (48000,))
            with self.assertRaisesRegex(ValueError, '3–30'): normalize(path, reference=True)
