import unittest
from opencode import inspect_opencode
from extensions import set_enabled

class OpenCodeTests(unittest.TestCase):
    def test_verified(self):
        report = inspect_opencode({"enabled": ["opencode"]},
                                  {"opencode": {"status": "installed", "version": "1.0.0"}},
                                  finder=lambda _: "C:/bin/opencode.exe")
        self.assertEqual(report["status"], "installed")
        self.assertFalse(report["execution_enabled"])
        self.assertFalse(report["project_access"])
    def test_windows_shim(self):
        report = inspect_opencode({"enabled": ["opencode"]},
                                  {"opencode": {"status": "detected_unverified", "version": None}},
                                  finder=lambda _: "C:/npm/opencode.cmd")
        self.assertEqual(report["entry_type"], ".cmd")
        self.assertIsNone(report["version"])
    def test_disabled(self):
        with self.assertRaisesRegex(ValueError, "disabled"):
            inspect_opencode({"enabled": []}, {"opencode": {"status": "installed"}})
    def test_missing_scanner(self):
        with self.assertRaisesRegex(ValueError, "missing"):
            inspect_opencode({"enabled": ["opencode"]}, {})
    def test_enable_detected_shim(self):
        state = set_enabled({"enabled": []}, "opencode", True,
                            {"tools": [{"name": "opencode", "status": "detected_unverified"}]})
        self.assertIn("opencode", state["enabled"])
    def test_reject_missing(self):
        with self.assertRaisesRegex(ValueError, "not verified"):
            set_enabled({"enabled": []}, "opencode", True,
                        {"tools": [{"name": "opencode", "status": "missing"}]})

if __name__ == "__main__":
    unittest.main()
