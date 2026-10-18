import io
import json
import unittest
from unittest.mock import Mock
from urllib.error import URLError
from ollama import list_models

STATE = {"enabled": ["ollama"]}
STATUS = {"ollama": "installed"}

class Response:
    def __init__(self, data):
        self.stream = io.BytesIO(data)
    def __enter__(self):
        return self.stream
    def __exit__(self, *args):
        return False

class OllamaTests(unittest.TestCase):
    def test_models(self):
        payload = {"models": [{"name": "qwen2.5-coder:7b", "size": 4000, "modified_at": "2026-10-18"}]}
        opener = Mock(return_value=Response(json.dumps(payload).encode()))
        result = list_models(STATE, STATUS, opener)
        self.assertEqual(result["status"], "connected")
        self.assertEqual(result["models"][0]["name"], "qwen2.5-coder:7b")
        self.assertEqual(opener.call_args.args[0].get_method(), "GET")
        self.assertEqual(opener.call_args.kwargs["timeout"], 3)
        self.assertFalse(result["executed"])
    def test_disabled(self):
        with self.assertRaisesRegex(ValueError, "disabled"):
            list_models({"enabled": []}, STATUS)
    def test_unverified(self):
        with self.assertRaisesRegex(ValueError, "not verified"):
            list_models(STATE, {"ollama": "missing"})
    def test_offline(self):
        result = list_models(STATE, STATUS, Mock(side_effect=URLError("offline")))
        self.assertEqual(result["status"], "unavailable")
    def test_bad_schema(self):
        with self.assertRaisesRegex(ValueError, "Invalid"):
            list_models(STATE, STATUS, lambda *a, **k: Response(b'{"models":{}}'))
    def test_bounded_response(self):
        with self.assertRaisesRegex(ValueError, "size limit"):
            list_models(STATE, STATUS, lambda *a, **k: Response(b"x" * (256 * 1024 + 1)))

if __name__ == "__main__":
    unittest.main()
