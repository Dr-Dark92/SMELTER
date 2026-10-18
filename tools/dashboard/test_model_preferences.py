import json
import tempfile
import unittest
from pathlib import Path
from model_preferences import load_preferences, configure_model, configured_status

DISCOVERY = {"status": "connected", "models": [{"name": "qwen3.5:9b"}, {"name": "qwen3.5:4b"}]}

class ModelPreferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "models.json"
    def test_default_empty(self):
        self.assertEqual(load_preferences(self.path)["models"], {})
    def test_save_and_reload(self):
        configure_model(self.path, "reasoning", "qwen3.5:9b", DISCOVERY)
        configure_model(self.path, "lightweight", "qwen3.5:4b", DISCOVERY)
        self.assertEqual(load_preferences(self.path)["models"], {"reasoning": "qwen3.5:9b", "lightweight": "qwen3.5:4b"})
    def test_reject_unknown_role(self):
        with self.assertRaisesRegex(ValueError, "role"):
            configure_model(self.path, "shell", "qwen3.5:9b", DISCOVERY)
    def test_reject_uninstalled(self):
        with self.assertRaisesRegex(ValueError, "installed"):
            configure_model(self.path, "reasoning", "other", DISCOVERY)
        self.assertFalse(self.path.exists())
    def test_reject_offline(self):
        with self.assertRaisesRegex(ValueError, "connected"):
            configure_model(self.path, "reasoning", "qwen3.5:9b", {"status": "unavailable", "models": []})
    def test_availability(self):
        configured = {"schema_version": 1, "models": {"reasoning": "qwen3.5:9b"}}
        self.assertEqual(configured_status(configured, DISCOVERY)["availability"]["reasoning"], "available")
        self.assertEqual(configured_status(configured, {"status": "unavailable"})["availability"]["reasoning"], "unavailable")
    def test_corrupt_preferences(self):
        self.path.write_text(json.dumps({"schema_version": 1, "models": {"reasoning": 3}}))
        with self.assertRaisesRegex(ValueError, "Invalid"):
            load_preferences(self.path)

if __name__ == "__main__":
    unittest.main()
