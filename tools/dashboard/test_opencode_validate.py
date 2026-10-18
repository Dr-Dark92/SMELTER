import json
import tempfile
import unittest
from pathlib import Path
from opencode_validate import validate_staged_config

PREFS = {"models": {"reasoning": "qwen3.5:9b", "lightweight": "qwen3.5:4b"}}
DISCOVERY = {"status": "connected", "models": [{"name": "qwen3.5:9b"}, {"name": "qwen3.5:4b"}]}
CONFIG = {"provider": {"smelter_ollama": {"npm": "@ai-sdk/openai-compatible",
           "options": {"baseURL": "http://127.0.0.1:11434/v1"},
           "models": {"qwen3.5:9b": {}, "qwen3.5:4b": {}}}}}

class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / ".smelter" / "opencode-isolated"
        self.root.mkdir(parents=True)
        self.target = self.root / "opencode.json"
        self.target.write_text(json.dumps(CONFIG), encoding="utf-8")
    def test_valid(self):
        report = validate_staged_config(self.root, PREFS, DISCOVERY)
        self.assertEqual(report["status"], "valid")
        self.assertFalse(report["executed"])
    def test_stale_preferences(self):
        report = validate_staged_config(self.root, {"models": {"reasoning": "qwen3.5:9b"}}, DISCOVERY)
        self.assertTrue(report["preferences_stale"])
    def test_wrong_endpoint(self):
        altered = json.loads(self.target.read_text())
        altered["provider"]["smelter_ollama"]["options"]["baseURL"] = "https://remote.example/v1"
        self.target.write_text(json.dumps(altered))
        with self.assertRaisesRegex(ValueError, "endpoint"):
            validate_staged_config(self.root, PREFS, DISCOVERY)
    def test_offline(self):
        with self.assertRaisesRegex(ValueError, "disconnected"):
            validate_staged_config(self.root, PREFS, {"status": "unavailable", "models": []})
    def test_missing_file(self):
        self.target.unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            validate_staged_config(self.root, PREFS, DISCOVERY)
    def test_unavailable_model(self):
        with self.assertRaisesRegex(ValueError, "unavailable"):
            validate_staged_config(self.root, PREFS, {"status": "connected", "models": [{"name": "qwen3.5:9b"}]})

if __name__ == "__main__":
    unittest.main()
