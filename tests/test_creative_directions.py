import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from creative import parse_creative

class CreativeDirections(unittest.TestCase):
    def test_custom_tags_go_to_instructions_never_spoken_text(self):
        plan = parse_creative('[whispery][sly, playful] A secret. [sad, neutral] Goodbye. [reset] Home.', 'Adult narrator')
        self.assertEqual([s['text'] for s in plan], ['A secret.', 'Goodbye.', 'Home.'])
        self.assertIn('whispery, sly, playful', plan[0]['direction'])
        self.assertNotIn('whispery', plan[1]['direction'])
        self.assertEqual(plan[2]['direction'], 'Adult narrator')

    def test_pauses_keep_the_direction(self):
        plan = parse_creative('[gentle] Relax. [pause=0.8] Listen.', 'Adult voice')
        self.assertEqual(plan[1], {'kind': 'pause', 'seconds': .8})
        self.assertEqual(plan[0]['direction'], plan[2]['direction'])

    def test_invalid_or_unbounded_plans_are_rejected(self):
        for text in ('[whispery', '[whispery]', '[pause=nan] Hello.', '[pause=12] Hello.', 'a' * 801):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_creative(text, 'Adult narrator')

if __name__ == '__main__':
    unittest.main()
