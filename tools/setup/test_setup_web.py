"""Unit tests for the SMELTER Vanilla setup wizard's safety gates."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import setup_web

class SetupWebTests(unittest.TestCase):
    def test_plan_contains_no_optional_installs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = root / "requirements.txt"
            scanner = root / "check_requirements.py"
            req.write_text("# stdlib only\n", encoding="utf-8")
            scanner.write_text("", encoding="utf-8")
            with patch.object(setup_web, "REQ", req), patch.object(setup_web, "SCANNER", scanner):
                plan = setup_web.Engine().plan()
            self.assertEqual(plan["optional_installations"], [])
            self.assertFalse(plan["downloads"])
            self.assertFalse(plan["system_package_changes"])

    def test_reject_unreviewed_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = root / "requirements.txt"
            scanner = root / "check_requirements.py"
            req.write_text("requests==2.0\n", encoding="utf-8")
            scanner.write_text("", encoding="utf-8")
            with patch.object(setup_web, "REQ", req), patch.object(setup_web, "SCANNER", scanner):
                with self.assertRaisesRegex(ValueError, "refuses third-party"):
                    setup_web.Engine().plan()

    def test_apply_requires_valid_plan_and_approval(self):
        engine = setup_web.Engine()
        with self.assertRaisesRegex(ValueError, "Explicit approval"):
            engine.apply("invalid", True)
        with self.assertRaisesRegex(ValueError, "Explicit approval"):
            engine.apply("invalid", False)

if __name__ == "__main__":
    unittest.main()
