from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch,Mock,call

from reload_dashboard import _url,reload,_launch


class ReloadDashboardTests(unittest.TestCase):
    @unittest.skipUnless(os.name=='nt','Windows-only console reload')
    def test_replacement_does_not_inherit_the_helpers_ignored_interrupts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.smelter').mkdir();kernel=Mock();sequence=Mock()
            sequence.attach_mock(kernel.SetConsoleCtrlHandler,'reset')
            with patch('reload_dashboard.subprocess.Popen') as start:
                sequence.attach_mock(start,'start');_launch(root,8769,kernel)
                self.assertEqual(sequence.mock_calls[0],call.reset(None,False))
                self.assertEqual(sequence.mock_calls[1][0],'start')
                self.assertEqual(start.call_args.kwargs['stdin'],-3)

    def test_launch_log_must_identify_the_requested_session_port(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'launch.log';token='a'*43;path.write_text('SMELTER dashboard: http://127.0.0.1:8768/#token='+token)
            self.assertEqual(_url(path,8768),token)
            with self.assertRaises(ValueError):_url(path,8769)

    @unittest.skipUnless(os.name=='nt','Windows-only console reload')
    def test_a_failed_project_identity_check_sends_no_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'.smelter').mkdir();path=root/'.smelter/launch.log';path.write_text('http://127.0.0.1:8768/#token='+'a'*43)
            with patch('reload_dashboard._verify',side_effect=ValueError('Wrong project')),patch('reload_dashboard.ctypes.WinDLL') as kernel,patch('reload_dashboard.subprocess.Popen') as start:
                with self.assertRaisesRegex(ValueError,'Wrong project'):reload(root,123,path)
                kernel.assert_not_called();start.assert_not_called()


if __name__=='__main__':unittest.main()
