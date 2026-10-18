import tempfile
import unittest
from pathlib import Path
from extensions import catalog, load_state, save_state, set_enabled

SCAN = {"tools": [{"name": "blender", "status": "installed"}, {"name": "ffmpeg", "status": "missing"}, {"name": "7z", "status": "installed"}]}

class ExtensionTests(unittest.TestCase):
    def test_default_disabled(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(load_state(Path(folder) / "extensions.json")["enabled"], [])
    def test_enable_verified(self):
        result = set_enabled({"schema_version": 1, "enabled": []}, "blender", True, SCAN)
        self.assertEqual(result["enabled"], ["blender"])
    def test_missing_cannot_enable(self):
        with self.assertRaisesRegex(ValueError, "not verified"):
            set_enabled({"schema_version": 1, "enabled": []}, "ffmpeg", True, SCAN)
    def test_unknown_rejected(self):
        with self.assertRaises(ValueError):
            set_enabled({"schema_version": 1, "enabled": []}, "invalid", True, SCAN)
    def test_state_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "extensions.json"
            save_state(path, {"schema_version": 1, "enabled": ["7z"]})
            self.assertEqual(load_state(path)["enabled"], ["7z"])
    def test_health_ready_but_permissions_not_granted(self):
        items = catalog(SCAN, {"schema_version": 1, "enabled": ["blender"]})
        blender = next(x for x in items if x["id"] == "blender")
        self.assertEqual(blender["health"], "ready")
        self.assertFalse(blender["permission_granted"])

    def test_health_disabled(self):
        items = catalog(SCAN, {"schema_version": 1, "enabled": []})
        blender = next(x for x in items if x["id"] == "blender")
        self.assertEqual(blender["health"], "available_disabled")

    def test_health_detects_lost_dependency(self):
        items = catalog(SCAN, {"schema_version": 1, "enabled": ["ffmpeg"]})
        ffmpeg = next(x for x in items if x["id"] == "ffmpeg")
        self.assertEqual(ffmpeg["health"], "dependency_unavailable")
        self.assertTrue(ffmpeg["enabled"])

    def test_catalog_status(self):
        items = catalog(SCAN, {"schema_version": 1, "enabled": ["blender"]})
        self.assertTrue(next(x for x in items if x["id"] == "blender")["enabled"])
        self.assertEqual(next(x for x in items if x["id"] == "ffmpeg")["status"], "missing")

if __name__ == "__main__":
    unittest.main()
