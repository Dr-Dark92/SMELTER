import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from media import inspect_media

class MediaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.file = Path(self.temp.name) / "test.mp4"
        self.file.write_bytes(b"fixture")
        self.state = {"enabled": ["ffmpeg"]}
        self.status = {"ffmpeg": "installed"}
    def run_probe(self, approval="PROBE MEDIA", state=None, status=None, runner=None, resolver=None):
        return inspect_media(str(self.file), approval, self.state if state is None else state,
                             self.status if status is None else status,
                             runner=runner or Mock(return_value=subprocess.CompletedProcess([], 0, json.dumps({"streams": [], "format": {}}), "")),
                             resolver=resolver or (lambda: "C:/FFmpeg/bin/ffprobe.exe"))
    def test_approved_probe(self):
        runner = Mock(return_value=subprocess.CompletedProcess([], 0, '{"streams":[],"format":{}}', ""))
        result = self.run_probe(runner=runner)
        self.assertEqual(result["status"], "completed")
        args = runner.call_args.args[0]
        self.assertEqual(args[1:5], ["-v", "error", "-show_format", "-show_streams"])
        self.assertFalse(runner.call_args.kwargs["shell"])
        self.assertFalse(any(x in args for x in ("-y", "-c:v", "-f")))
    def test_approval_required(self):
        with self.assertRaisesRegex(ValueError, "approval"):
            self.run_probe(approval="")
    def test_disabled(self):
        with self.assertRaisesRegex(ValueError, "disabled"):
            self.run_probe(state={"enabled": []})
    def test_unverified(self):
        with self.assertRaisesRegex(ValueError, "not verified"):
            self.run_probe(status={"ffmpeg": "missing"})
    def test_bad_metadata(self):
        runner = Mock(return_value=subprocess.CompletedProcess([], 0, "not json", ""))
        self.assertEqual(self.run_probe(runner=runner)["status"], "failed")
    def test_timeout(self):
        runner = Mock(side_effect=subprocess.TimeoutExpired(["ffprobe"], 20))
        self.assertEqual(self.run_probe(runner=runner)["status"], "timeout")
    def test_directory_rejected(self):
        with self.assertRaisesRegex(ValueError, "regular file"):
            inspect_media(self.temp.name, "PROBE MEDIA", self.state, self.status)
    def test_missing_probe_rejected(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            self.run_probe(resolver=lambda: None)

if __name__ == "__main__":
    unittest.main()
