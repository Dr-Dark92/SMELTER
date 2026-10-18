import tempfile
import unittest
from pathlib import Path
from database import select_database
from config_store import load_config, save_config

class ConfigStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.root = base / "checkout"
        (self.root / ".smelter").mkdir(parents=True)
        (self.root / ".smelter" / "extensions.json").write_text('{"schema_version":1,"enabled":[]}')
        select_database(self.root, str(base / "data"))
    def test_imported_extensions(self):
        self.assertEqual(load_config(self.root, "extensions.json")["enabled"], [])
    def test_persists_without_legacy_changes(self):
        save_config(self.root, "extensions.json", {"schema_version":1,"enabled":["blender"]})
        self.assertEqual(load_config(self.root, "extensions.json")["enabled"], ["blender"])
        self.assertIn('"enabled":[]', (self.root / ".smelter" / "extensions.json").read_text())
    def test_model_preferences_roundtrip(self):
        save_config(self.root, "model_preferences.json", {"schema_version":1,"models":{"reasoning":"qwen3.5:9b"}})
        self.assertEqual(load_config(self.root, "model_preferences.json")["models"]["reasoning"], "qwen3.5:9b")
    def test_invalid_config_rejected(self):
        with self.assertRaises(ValueError):
            save_config(self.root, "extensions.json", {"schema_version":1,"enabled":["unknown"]})
    def test_unknown_name_rejected(self):
        with self.assertRaises(ValueError):
            load_config(self.root, "arbitrary.json")

if __name__ == "__main__":
    unittest.main()
