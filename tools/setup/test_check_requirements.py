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
        with patch.object(module, "find_executable", return_value=None):
            result = module.probe("blender", ["blender", "--version"], "optional")
        self.assertEqual(result["status"], "missing")

    def test_registered_path_detects_new_ffmpeg(self):
        def which(name, path=None):
            return r"C:\Winget\ffmpeg\bin\ffmpeg.exe" if name == "ffmpeg" and path == r"C:\Winget\ffmpeg\bin" else None
        with patch.object(module.os, "name", "nt"):
            with patch.object(module, "windows_path_entries", return_value=[r"C:\Winget\ffmpeg\bin"]):
                with patch.object(module.shutil, "which", side_effect=which):
                    self.assertEqual(module.find_executable("ffmpeg"), r"C:\Winget\ffmpeg\bin\ffmpeg.exe")

    def test_7zip_windows_program_files_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            seven = Path(tmp) / "7-Zip" / "7z.exe"
            seven.parent.mkdir()
            seven.write_bytes(b"")
            with patch.object(module.os, "name", "nt"), patch.dict(module.os.environ, {"ProgramFiles": tmp}, clear=True):
                with patch.object(module.shutil, "which", return_value=None):
                    self.assertEqual(module.find_executable("7z"), str(seven))

    def test_npm_cmd_uses_node_not_shim(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cli = root / "node_modules" / "npm" / "bin" / "npm-cli.js"
            cli.parent.mkdir(parents=True)
            cli.write_text("// mock", encoding="utf-8")
            npm = root / "npm.cmd"
            npm.write_text("@echo off", encoding="utf-8")
            with patch.object(module.os, "name", "nt"):
                with patch.object(module, "find_executable", side_effect=lambda name: str(npm) if name == "npm" else str(root / "node.exe")):
                    with patch.object(module.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "11.0.0\\n", "")) as runner:
                        result = module.probe("npm", ["npm", "--version"], "optional")
            self.assertEqual(result["status"], "installed")
            self.assertEqual(runner.call_args.args[0][1:], [str(cli), "--version"])

    def test_npm_missing_cli_is_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            npm = Path(tmp) / "npm.cmd"
            npm.write_text("@echo off", encoding="utf-8")
            with patch.object(module.os, "name", "nt"):
                with patch.object(module, "find_executable", side_effect=lambda name: str(npm) if name == "npm" else "node.exe"):
                    with patch.object(module.subprocess, "run") as runner:
                        result = module.probe("npm", ["npm", "--version"], "optional")
            self.assertEqual(result["status"], "detected_unverified")
            runner.assert_not_called()

    def test_7zip_info_command(self):
        self.assertEqual(module.TOOLS["7z"][0], ["7z", "i"])

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
