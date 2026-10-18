import unittest
from chat_inference import ask

class InferenceTests(unittest.TestCase):
    def test_empty_prompt_rejected(self):
        with self.assertRaises(ValueError):
            ask(None, None, '')
    def test_long_prompt_rejected(self):
        with self.assertRaises(ValueError):
            ask(None, None, 'x' * 1801)

if __name__ == '__main__':
    unittest.main()
