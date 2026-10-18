import subprocess
import unittest
from unittest.mock import Mock
from blender import inspect_blender

class BlenderTests(unittest.TestCase):
    def invoke(self, approval="CHECK BLENDER", state=None, status=None, runner=None, finder=None):
        return inspect_blender(
            approval, {"enabled": ["blender"]} if state is None else state,
            {"blender": "installed"} if status is None else status,
            runner=runner or Mock(return_value=subprocess.CompletedProcess([], 0, "Blender 5.2.2\n", "")),
            finder=finder or (lambda name: "C:/Program Files/Blender Foundation/Blender 5.2/blender.exe"))
    def test_approved_version_only(self):
        runner = Mock(return_value=subprocess.CompletedProcess([], 0, "Blender 5.2.2\n", ""))
        result = self.invoke(runner=runner)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(runner.call_args.args[0][-1], "--version")
        self.assertEqual(len(runner.call_args.args[0]), 2)
        self.assertFalse(runner.call_args.kwargs["shell"])
    def test_missing_approval(self):
        with self.assertRaisesRegex(ValueError, "approval"):
            self.invoke(approval="")
    def test_disabled_extension(self):
        with self.assertRaisesRegex(ValueError, "disabled"):
            self.invoke(state={"enabled": []})
    def test_missing_dependency(self):
        with self.assertRaisesRegex(ValueError, "not verified"):
            self.invoke(status={"blender": "missing"})
    def test_reject_non_exe(self):
        with self.assertRaisesRegex(ValueError, "unavailable"):
            self.invoke(finder=lambda name: "blender.cmd")
    def test_bad_version_output(self):
        runner = Mock(return_value=subprocess.CompletedProcess([], 0, "unexpected", ""))
        self.assertEqual(self.invoke(runner=runner)["status"], "failed")
    def test_timeout(self):
        runner = Mock(side_effect=subprocess.TimeoutExpired(["blender"], 20))
        self.assertEqual(self.invoke(runner=runner)["status"], "timeout")

if __name__ == "__main__":
    unittest.main()
