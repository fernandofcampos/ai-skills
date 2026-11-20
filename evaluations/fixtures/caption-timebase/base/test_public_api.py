import unittest
from public_api import label_at

class CaptionTests(unittest.TestCase):
    def test_first_frame_has_title(self):
        self.assertEqual(label_at([{'start_ms': 0, 'end_ms': 10, 'text': 'Intro'}], 0), 'Intro')
