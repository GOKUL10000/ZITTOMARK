import contextlib
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from shard_creative_model import repack


class ModelShardingTests(unittest.TestCase):
    def test_shards_preserve_every_tensor_byte_and_reject_changed_source(self):
        with tempfile.TemporaryDirectory(prefix='voice-storage-test-shards-', dir=Path(__file__).resolve().parent) as folder:
            root = Path(folder)
            tensors = {'a': b'abcdefghijklmnop', 'b': b'qrstuvwxyz012345'}
            header = {'a':{'dtype':'F32','shape':[4],'data_offsets':[0,16]},
                      'b':{'dtype':'F32','shape':[4],'data_offsets':[16,32]}}
            encoded = json.dumps(header).encode(); encoded += b' ' * (-len(encoded) % 8)
            original = root / 'source.safetensors'
            original.write_bytes(struct.pack('<Q', len(encoded)) + encoded + b''.join(tensors.values()))
            expected = hashlib.sha256(original.read_bytes()).hexdigest()
            with contextlib.redirect_stdout(io.StringIO()):
                report = repack(original, root/'shards', expected, max_bytes=16)
            index = json.loads((root/'shards'/'model.safetensors.index.json').read_text())
            self.assertEqual(report['tensor_count'], 2)
            self.assertEqual(len(report['shards']), 2)
            for name, filename in index['weight_map'].items():
                data = (root/'shards'/filename).read_bytes()
                length = struct.unpack('<Q', data[:8])[0]
                tensor_header = json.loads(data[8:8+length])
                begin, end = tensor_header[name]['data_offsets']
                self.assertEqual(data[8+length+begin:8+length+end], tensors[name])
            original.write_bytes(original.read_bytes() + b'bad')
            with self.assertRaisesRegex(ValueError, 'checksum'): repack(original, root/'bad', expected)
