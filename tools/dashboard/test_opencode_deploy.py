import json
import tempfile
import unittest
from pathlib import Path
from opencode_deploy import deploy_isolated_config

PREVIEW = {"status": "preview_ready", "written": False, "executed": False,
           "config": {"provider": {"smelter_ollama": {"models": {"qwen3.5:9b": {}}}}}}

class IsolatedDeployTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / ".smelter" / "opencode-isolated"
    def test_deploy(self):
        result = deploy_isolated_config(self.root, PREVIEW, "DEPLOY ISOLATED CONFIG")
        self.assertEqual(result["status"], "deployed")
        self.assertFalse(result["executed"])
        self.assertEqual(json.loads((self.root / "opencode.json").read_text()), PREVIEW["config"])
    def test_approval(self):
        with self.assertRaisesRegex(ValueError, "approval"):
            deploy_isolated_config(self.root, PREVIEW, "")
        self.assertFalse(self.root.exists())
    def test_no_overwrite(self):
        deploy_isolated_config(self.root, PREVIEW, "DEPLOY ISOLATED CONFIG")
        with self.assertRaisesRegex(ValueError, "already exists"):
            deploy_isolated_config(self.root, PREVIEW, "DEPLOY ISOLATED CONFIG")
    def test_wrong_destination(self):
        with self.assertRaisesRegex(ValueError, "Destination"):
            deploy_isolated_config(Path(self.tmp.name) / "projects", PREVIEW, "DEPLOY ISOLATED CONFIG")
    def test_invalid_preview(self):
        with self.assertRaisesRegex(ValueError, "preview"):
            deploy_isolated_config(self.root, {"status": "failed"}, "DEPLOY ISOLATED CONFIG")
    def test_no_external_settings(self):
        deploy_isolated_config(self.root, PREVIEW, "DEPLOY ISOLATED CONFIG")
        self.assertEqual(list(Path(self.tmp.name).rglob("opencode.json")), [self.root / "opencode.json"])

if __name__ == "__main__":
    unittest.main()
