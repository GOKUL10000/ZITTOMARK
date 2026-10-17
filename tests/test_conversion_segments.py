from pathlib import Path
import sys
import unittest
from math import ceil
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from conversion_segments import encoding_windows, TOKEN_HOP

class EncodingWindowTests(unittest.TestCase):
    def test_boundaries_cover_every_source_token_once_with_context(self):
        for frames in (16000, 24*16000, 24*16000+1, 30*16000, 300*16000, 300*16000+1):
            covered = []
            for begin,end,first,count in encoding_windows(frames):
                self.assertLessEqual(end-begin, 25*16000)
                self.assertLessEqual(first, 12)
                covered.extend(range(begin // TOKEN_HOP + first, begin // TOKEN_HOP + first + count))
            self.assertEqual(covered, list(range(ceil(frames / TOKEN_HOP))))
    def test_empty_source_is_rejected(self):
        with self.assertRaises(ValueError): list(encoding_windows(0))

if __name__ == '__main__': unittest.main()
