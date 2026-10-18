import unittest
from workflows import definitions, plan

SCAN = {"tools": [{"name": "7z", "status": "installed"}, {"name": "blender", "status": "installed"}, {"name": "ffmpeg", "status": "installed"}]}

class WorkflowTests(unittest.TestCase):
    def test_definitions(self):
        self.assertGreaterEqual(len(definitions()), 2)
    def test_all_enabled_ready(self):
        report = plan("asset_preflight", SCAN, {"enabled": ["7z", "blender", "ffmpeg"]})
        self.assertEqual(report["status"], "ready")
        self.assertEqual(len(report["steps"]), 3)
        self.assertFalse(report["executed"])
        self.assertFalse(report["permissions_granted"])
    def test_disabled_blocks(self):
        report = plan("media_preflight", SCAN, {"enabled": []})
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["steps"][0]["reason"], "extension disabled")
    def test_missing_tool_blocks(self):
        report = plan("media_preflight", {"tools": []}, {"enabled": ["ffmpeg"]})
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["steps"][0]["reason"], "dependency not verified")
    def test_unknown_workflow_rejected(self):
        with self.assertRaises(ValueError):
            plan("../projects", SCAN, {"enabled": []})
    def test_no_executable_commands_in_report(self):
        report = plan("asset_preflight", SCAN, {"enabled": ["7z", "blender", "ffmpeg"]})
        self.assertTrue(all("command" not in step for step in report["steps"]))
        self.assertEqual(report["mode"], "dry_run")

if __name__ == "__main__":
    unittest.main()
