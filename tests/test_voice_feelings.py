import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from feelings import parse_script, settings

class DeliveryTests(unittest.TestCase):
    def test_switching_and_reset_never_passes_tags_as_speech(self):
        plan = parse_script("Start. [happy] Hello! [pause=0.8] [sad] Goodbye. [reset] End.", "calm")
        spoken = [part for part in plan if part["kind"] == "speech"]
        self.assertEqual([part["feeling"] for part in spoken], ["calm", "happy", "sad", "calm"])
        self.assertEqual([part["text"] for part in spoken], ["Start.", "Hello!", "Goodbye.", "End."])
        self.assertEqual(plan[2], {"kind": "pause", "seconds": 0.8})

    def test_tamil_words_are_preserved(self):
        self.assertEqual(parse_script("[happy] வணக்கம்! [neutral] இன்று நல்ல நாள்.")[0]["text"], "வணக்கம்!")

    def test_invalid_tags_and_nonfinite_values_are_rejected(self):
        for text in ("[laugh] Hello", "[happy", "[pause=nan] Hello", "[pause=-1] Hello", "[pause=30] Hello", "[happy]"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_script(text)
        with self.assertRaises(ValueError):
            settings("happy", float("nan"))
        with self.assertRaises(ValueError):
            parse_script("Hello", "unknown")

    def test_pause_budget_is_bounded(self):
        with self.assertRaises(ValueError):
            parse_script("Hello " + "[pause=3]" * 6)

    def test_zero_strength_is_neutral_and_opposite_styles_differ(self):
        self.assertEqual(settings("happy", 0), settings("neutral", 1))
        self.assertGreater(settings("happy", 1)["pitch"], 0)
        self.assertGreater(settings("happy", 1)["rate"], 1)
        self.assertLess(settings("sad", 1)["pitch"], 0)
        self.assertLess(settings("sad", 1)["rate"], 1)

    def test_tamil_uses_baseline_native_conditioning_and_gentler_effects(self):
        self.assertEqual(settings("happy", 1, "ta")["exaggeration"], 0.5)
        self.assertLess(settings("happy", 1, "ta")["pitch"], settings("happy", 1, "en")["pitch"])

if __name__ == "__main__":
    unittest.main()
