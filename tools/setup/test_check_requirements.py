#!/usr/bin/env python3
"""Deterministic tests for the read-only V1 requirements scanner."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import subprocess

PATH = Path(__file__).with_name("check_requirements.py")
spec = importlib.util.spec_from_file_location("check_requirements", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class RequirementsTests(unittest.TestCase):
    def test_missing_optional_is_not_failure(self):
        with patch.object(module.shutil, "which", return_value=None):
            result = module.probe("blender", ["blender", "--version"], "optional")
        self.assertEqual(result["status"], "missing")

    def test_successful_version(self):
        completed = subprocess.CompletedProcess(["git", "--version"], 0, "git version 2.0\n", "")
        with patch.object(module.shutil, "which", return_value="/usr/bin/git"):
            with patch.object(module.subprocess, "run", return_value=completed) as runner:
                result = module.probe("git", ["git", "--version"], "recommended")
        self.assertEqual(result["status"], "installed")
        self.assertEqual(result["version"], "git version 2.0")
        self.assertFalse(runner.call_args.kwargs.get("shell", False))

    def test_timeout(self):
        with patch.object(module.shutil, "which", return_value="/usr/bin/java"):
            with patch.object(module.subprocess, "run", side_effect=subprocess.TimeoutExpired("java", 5)):
                result = module.probe("java", ["java", "-version"], "optional")
        self.assertEqual(result["status"], "detected_unverified")

    def test_failed_version_command(self):
        completed = subprocess.CompletedProcess(["java", "-version"], 1, "", "error")
        with patch.object(module.shutil, "which", return_value="/usr/bin/java"):
            with patch.object(module.subprocess, "run", return_value=completed):
                result = module.probe("java", ["java", "-version"], "optional")
        self.assertEqual(result["status"], "detected_unverified")

    def test_scan_schema_and_no_paths(self):
        with patch.object(module, "probe", side_effect=lambda n, a, p: {"name": n, "status": "missing", "policy": p, "version": None}):
            result = module.scan()
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(len(result["tools"]), len(module.TOOLS))
        self.assertNotIn("path", json.dumps(result).lower())

    def test_python_version_gate(self):
        with patch.object(module.sys, "version_info", (3, 11, 0)):
            with patch.object(module, "probe", return_value={"status": "missing"}):
                self.assertFalse(module.scan()["vanilla_ready"])

if __name__ == "__main__":
    unittest.main()
