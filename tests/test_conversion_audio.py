import base64
import io
from pathlib import Path
import sys
import unittest
import numpy as np
import soundfile as sf

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from conversion_audio import decode_source, source_label

def encode(samples, rate=24000):
    buffer=io.BytesIO(); sf.write(buffer,samples,rate,format='WAV',subtype='PCM_16')
    return base64.b64encode(buffer.getvalue()).decode()

class SourceAudioTests(unittest.TestCase):
    def test_stereo_is_resampled_and_normalized(self):
        tone=np.sin(np.arange(48000)*2*np.pi*220/48000).astype('float32')*.2
        audio,rate=decode_source(encode(np.column_stack([tone,tone]),48000))
        self.assertEqual(rate,24000); self.assertEqual(len(audio),24000)
        self.assertTrue(np.isfinite(audio).all()); self.assertGreater(np.std(audio),.1)
    def test_silent_short_long_and_malformed_inputs_are_rejected(self):
        for value in ('!!!', None, base64.b64encode(b'not a wave file').decode(),
                      encode(np.zeros(24000)),encode(np.ones(12000)*.1),encode(np.ones(301*24000)*.1)):
            with self.subTest(value_type=type(value).__name__),self.assertRaises(ValueError): decode_source(value)
    def test_input_labels_never_become_paths(self):
        self.assertEqual(source_label(r'..\..\sample.wav'),'sample.wav')
        self.assertEqual(source_label('/tmp/voice.wav'),'voice.wav')
    def test_five_minute_boundary_is_accepted_without_truncation(self):
        source = np.full(300 * 24000, .1, dtype='float32')
        audio, rate = decode_source(encode(source))
        self.assertEqual(rate, 24000)
        self.assertEqual(len(audio), len(source))

if __name__=='__main__': unittest.main()
