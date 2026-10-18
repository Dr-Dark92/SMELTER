import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "setup"))

from execution import inspect_archive

class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.archive = Path(self.tmp.name) / "sample.zip"
        self.archive.write_bytes(b"test")
        self.state = {"enabled": ["7z"]}
        self.status = {"7z": "installed"}
    def invoke(self, approval="LIST ARCHIVE", state=None, status=None, runner=None):
        return inspect_archive(str(self.archive), approval, self.state if state is None else state,
                               self.status if status is None else status,
                               runner=runner or Mock(return_value=subprocess.CompletedProcess([], 0, "archive listing", "")),
                               finder=lambda name: "C:/Program Files/7-Zip/7z.exe")
    def test_approved_read_only_command(self):
        runner = Mock(return_value=subprocess.CompletedProcess([], 0, "archive listing", ""))
        result = self.invoke(runner=runner)
        self.assertEqual(result["status"], "completed")
        args = runner.call_args.args[0]
        self.assertEqual(args[1:5], ["l", "-slt", "-bd", "--"])
        self.assertFalse(runner.call_args.kwargs["shell"])
        self.assertEqual(result["stdout"], "archive listing")
    def test_missing_approval(self):
        with self.assertRaisesRegex(ValueError, "approval"):
            self.invoke(approval="")
    def test_disabled_extension(self):
        with self.assertRaisesRegex(ValueError, "disabled"):
            self.invoke(state={"enabled": []})
    def test_unverified_tool(self):
        with self.assertRaisesRegex(ValueError, "not verified"):
            self.invoke(status={"7z": "missing"})
    def test_directory_rejected(self):
        with self.assertRaisesRegex(ValueError, "regular file"):
            inspect_archive(self.tmp.name, "LIST ARCHIVE", self.state, self.status)
    def test_timeout_report(self):
        runner = Mock(side_effect=subprocess.TimeoutExpired(["7z"], 20))
        self.assertEqual(self.invoke(runner=runner)["status"], "timeout")

if __name__ == "__main__":
    unittest.main()
