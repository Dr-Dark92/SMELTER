"""Background version probes must not create Windows console windows."""
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'setup'))
import check_requirements


class RequirementProcessTests(unittest.TestCase):
    def test_version_probes_request_no_window_and_no_shell(self):
        with patch.object(check_requirements, 'find_executable', return_value='powershell.exe'), \
                patch.object(subprocess, 'CREATE_NO_WINDOW', 0x08000000, create=True), \
                patch.object(check_requirements.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '7.5', '')) as run:
            result = check_requirements.probe('powershell', ['powershell', '-NoProfile', '-NonInteractive', '-Command', '$PSVersionTable.PSVersion.ToString()'], 'optional')
        self.assertEqual(result['status'], 'installed')
        self.assertEqual(run.call_args.kwargs['creationflags'], 0x08000000)
        self.assertFalse(run.call_args.kwargs['shell'])
        self.assertEqual(run.call_args.kwargs['timeout'], 5)

