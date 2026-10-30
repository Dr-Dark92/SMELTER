"""Exercise generic probe gates in a reviewed fixture executable, without RPH/GTA.

This runs only the fixture compiled below; build_managed_mod never runs plugins.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import build_managed_mod as managed

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(os.name == 'nt', 'Windows Framework fixture compiler required')
class RuntimeProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='smelter-read-probe-test-')
        cls.base = Path(cls.temp.name)
        cls.exe = cls.base / 'RuntimeProbeFixture.exe'
        compiler, refs, _ = managed.compiler()
        flags = [x for x in managed.FLAGS if x != '/target:library']
        command = [str(compiler), *flags, '/target:exe', '/out:' + str(cls.exe),
                   *['/reference:' + str(p) for p in refs],
                   str(ROOT / 'mods/gta-ark/common/managed/RuntimeProbeHarness.cs'),
                   str(ROOT / 'tools/setup/fixtures/RuntimeProbeFixture.cs')]
        result = subprocess.run(command, capture_output=True, timeout=30,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            cls.temp.cleanup()
            raise AssertionError((result.stdout + result.stderr).decode(errors='replace'))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_probe(self, scenario):
        output = self.base / scenario
        result = subprocess.run([str(self.exe), scenario, str(output)], capture_output=True,
                                timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        lines = result.stdout.decode().strip().splitlines()
        receipt = Path(lines[0])
        self.assertTrue(receipt.resolve().is_relative_to(output.resolve()))
        report = json.loads(receipt.read_text(encoding='utf-8-sig'))
        counters = tuple(map(int, lines[1].split(',')))
        self.assertFalse(report['game_runtime_verified'])
        self.assertEqual(report['probe_mutating_calls'], 0)
        self.assertEqual(report['network_session_checks'], counters[1])
        self.assertEqual(report['runtime_assembly'], 'fake-runtime-no-game')
        return report, counters

    def test_success_records_all_samples_without_claiming_gameplay(self):
        report, counters = self.run_probe('ok')
        self.assertEqual(counters, (4, 4, 3))
        self.assertEqual(report['stage'], 'native_reads_observed')
        self.assertTrue(report['native_reads_completed'])
        self.assertEqual(len(report['samples']), 4)
        self.assertEqual(len(report['plugin_sha256']), 64)
        self.assertTrue(all(s['utc'] and s['handle'] == 'fake-ped-1' for s in report['samples']))

    def test_every_executable_identity_field_is_checked_before_callbacks(self):
        for scenario in ('wrong_hash', 'wrong_name', 'wrong_version'):
            with self.subTest(scenario=scenario):
                report, counters = self.run_probe(scenario)
                self.assertEqual(counters, (0, 0, 0))
                self.assertFalse(report['native_reads_completed'])
                self.assertIn('unsupported_executable_identity', report['error'])

    def test_active_or_unknown_network_session_stops_before_capture(self):
        for scenario, error in [('network_active', 'network_session_active'),
                                ('network_throws', 'network_unknown')]:
            with self.subTest(scenario=scenario):
                report, counters = self.run_probe(scenario)
                self.assertEqual(counters, (0, 1, 0))
                self.assertFalse(report['native_reads_completed'])
                self.assertEqual(report['samples'], [])
                self.assertIn(error, report['error'])

    def test_session_is_rechecked_between_reads(self):
        report, counters = self.run_probe('network_changes')
        self.assertEqual(counters, (1, 2, 1))
        self.assertEqual(len(report['samples']), 1)
        self.assertFalse(report['native_reads_completed'])

    def test_invalid_samples_and_capture_errors_do_not_become_success(self):
        for scenario in ('invalid_sample', 'nan_position', 'infinite_position',
                         'missing_sample', 'capture_throws'):
            with self.subTest(scenario=scenario):
                report, counters = self.run_probe(scenario)
                self.assertEqual(counters, (1, 1, 0))
                self.assertEqual(report['stage'], 'probe_failed')
                self.assertFalse(report['native_reads_completed'])
                self.assertEqual(report['samples'], [])
                self.assertTrue(report['error'])

    def test_scheduler_failure_preserves_partial_evidence(self):
        report, counters = self.run_probe('pause_throws')
        self.assertEqual(counters, (1, 1, 1))
        self.assertEqual(len(report['samples']), 1)
        self.assertFalse(report['native_reads_completed'])
        self.assertIn('scheduler_failed', report['error'])

    def test_profile_limits_and_path_escape_reject_before_callbacks(self):
        for scenario in ('sample_limit', 'delay_limit', 'channel_escape'):
            with self.subTest(scenario=scenario):
                report, counters = self.run_probe(scenario)
                self.assertEqual(counters, (0, 0, 0))
                self.assertEqual(report['stage'], 'probe_failed')
                self.assertTrue(report['error'])
        self.assertFalse((self.base / 'escape').exists())


if __name__ == '__main__':
    unittest.main()
