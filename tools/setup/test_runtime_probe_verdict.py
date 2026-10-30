"""Verdicts for native read-probe reports and runtime inventories, without a game or loader."""
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
import zipfile

import inspect_loader_runtime as runtime
import verify_runtime_probe as probe

ROOT = Path(__file__).resolve().parents[2]


class VerdictTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='smelter-probe-verdict-')
        self.base = Path(self.temp.name)
        self.exe = self.base / 'Game.exe'
        self.exe.write_bytes(b'MZ fixture executable')
        self.plugin = self.base / 'Plugins/SmelterNativeProbe.dll'
        self.plugin.parent.mkdir(); self.plugin.write_bytes(b'MZ fixture plugin')
        self.plugin_hash = probe.sha256(self.plugin)
        self.profile = json.loads((ROOT / 'mods/gta-ark/gta/rph/read_probe_expectations.json').read_text(encoding='utf-8'))
        self.profile['executable'] = {'name': 'Game.exe', 'file_version': '1.2.3.4', 'sha256': hashlib.sha256(self.exe.read_bytes()).hexdigest()}
        self.profile['plugin']['sha256'] = self.plugin_hash
        self.log = self.base / 'RagePluginHook.log'
        self.log.write_text('[INFO] Loading plugin SmelterNativeProbe.dll\n[INFO] SmelterNativeProbe finished\n', encoding='utf-8')

    def tearDown(self):
        self.temp.cleanup()

    def report(self, run_id='run1', **changes):
        value = {'schema_version': 1, 'stage': 'native_reads_observed', 'scope': 'read_only_native_probe_not_gameplay',
                 'run_id': run_id, 'process_id': 7, 'executable': str(self.exe), 'file_version': '1.2.3.4',
                 'executable_sha256': self.profile['executable']['sha256'], 'plugin_sha256': self.plugin_hash,
                 'runtime_assembly': 'Rage, Version=1.0', 'network_session_checks': 4, 'native_reads_completed': True,
                 'game_runtime_verified': False, 'probe_mutating_calls': 0, 'started_utc': '2026-10-28T10:00:00Z',
                 'elapsed_ms': 800, 'error': None,
                 'samples': [{'handle': '12', 'valid': True, 'human': True, 'alive': True, 'x': 1.5 + i, 'y': -2.0, 'z': 30.25,
                              'utc': '2026-10-28T10:00:0%dZ' % i} for i in range(4)]}
        value.update(changes)
        folder = self.base / 'runtime-probes' / self.profile['channel'] / run_id
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / 'probe.json'
        path.write_text(json.dumps(value), encoding='utf-8')
        prefix = self.profile['loader_log'].get('receipt_prefix')
        if prefix:
            with self.log.open('a', encoding='utf-8') as out:
                out.write('[INFO] ' + prefix + ' ' + str(path.resolve()) + '\n')
        return path

    def judge(self, path, log='default'):
        return probe.judge(path, self.profile, self.log if log == 'default' else log)

    def test_a_complete_report_with_matching_hashes_and_log_is_verified(self):
        verdict, reasons, evidence = self.judge(self.report())
        self.assertEqual((verdict, reasons), ('native_reads_verified', []))
        self.assertEqual(len(evidence['loader_log']['plugin_lines']), 2)
        self.assertEqual(evidence['executable_on_disk_sha256'], self.profile['executable']['sha256'])

    def test_every_failed_gate_is_named(self):
        bad_sample = {'handle': '12', 'valid': True, 'x': None, 'y': 0, 'z': 0, 'utc': '2026-10-28T10:00:09Z'}
        cases = {
            'stage_not_native_reads_observed': {'stage': 'probe_failed', 'error': 'InvalidOperationException:network_session_active'},
            'report_error:InvalidOperationException:x': {'error': 'InvalidOperationException:x'},
            'report_overclaims_game_runtime': {'game_runtime_verified': True},
            'mutating_calls_reported': {'probe_mutating_calls': 1},
            'network_checks_not_4': {'network_session_checks': 3},
            'samples_not_4': {'samples': []},
            'plugin_hash_mismatch': {'plugin_sha256': 'cd' * 32},
            'executable_version_mismatch': {'file_version': '1.2.3.5'},
            'reported_executable_hash_mismatch': {'executable_sha256': 'ef' * 32},
        }
        for reason, change in cases.items():
            with self.subTest(reason):
                verdict, reasons, _ = self.judge(self.report(**change))
                self.assertEqual(verdict, 'rejected'); self.assertIn(reason, reasons)
        path = self.report()
        value = json.loads(path.read_text()); value['samples'][3] = bad_sample; path.write_text(json.dumps(value))
        self.assertIn('sample_3_invalid', self.judge(path)[1])

    def test_the_executable_on_disk_is_rehashed_and_the_run_folder_must_match(self):
        path = self.report()
        self.exe.write_bytes(b'MZ updated by a game patch')
        self.assertIn('executable_on_disk_mismatch', self.judge(path)[1])
        self.exe.unlink()
        self.assertIn('executable_on_disk_unavailable', self.judge(path)[1])
        moved = self.report(run_id='other')
        value = json.loads(moved.read_text()); value['run_id'] = 'run1'; moved.write_text(json.dumps(value))
        self.assertIn('run_id_folder_mismatch', self.judge(moved)[1])

    def test_deployed_plugin_is_independently_rehashed(self):
        path = self.report()
        self.plugin.write_bytes(b'different deployed plugin')
        self.assertIn('deployed_plugin_hash_mismatch', self.judge(path)[1])
        self.plugin.unlink()
        self.assertIn('deployed_plugin_unavailable', self.judge(path)[1])

    def test_loader_must_link_the_exact_report_not_a_different_run(self):
        path = self.report()
        self.log.write_text('[INFO] Loaded plugin SmelterNativeProbe.dll\n' +
                            '[SMELTER] Native read-probe receipt: ' + str(path.parent.parent/'other/probe.json') + '\n')
        self.assertIn('loader_log_report_path_mismatch', self.judge(path)[1])
        with self.log.open('a') as out:
            out.write('[SMELTER] Native read-probe receipt: ' + str(path).replace('\\', '/').upper() + '\n')
        self.assertEqual(self.judge(path)[:2], ('native_reads_verified', []))

    def test_deployment_profile_cannot_escape_the_executable_folder(self):
        path = self.report()
        for relative in ('../outside.dll', r'C:\outside.dll', r'Plugins\..\outside.dll'):
            with self.subTest(relative=relative):
                self.profile['plugin']['deployed_relative_path'] = relative
                with self.assertRaisesRegex(ValueError, 'stay under'):
                    self.judge(path)

    def test_the_loader_log_is_required_and_a_plugin_exception_rejects(self):
        self.assertIn('loader_log_required', self.judge(self.report(), log=None)[1])
        self.log.write_text('[INFO] nothing relevant\n', encoding='utf-8')
        self.assertIn('loader_log_never_mentions_plugin', self.judge(self.report())[1])
        self.log.write_text('[ERROR] SmelterNativeProbe threw NullReferenceException\n', encoding='utf-8')
        self.assertIn('loader_log_plugin_exception', self.judge(self.report())[1])

    def test_latest_report_and_receipt_are_recorded_without_overwrite(self):
        old = self.report(run_id='a'); new = self.report(run_id='b')
        os.utime(old, (1, 1))
        self.assertEqual(probe.latest_report(self.profile['channel'], self.base / 'runtime-probes'), new)
        profile_path = self.base / 'profile.json'; profile_path.write_text(json.dumps(self.profile))
        verdict, reasons, evidence = self.judge(new)
        path, receipt = probe.record(self.base, verdict, reasons, evidence, profile_path)
        self.assertEqual(receipt['claims'], {'self_reported_report': True, 'game_runtime_verified': False, 'gameplay_verified': False})
        self.assertEqual(json.loads(path.read_text())['report_sha256'], hashlib.sha256(new.read_bytes()).hexdigest())

    def test_rejected_run_ids_cannot_choose_a_receipt_path(self):
        profile_path = self.base / 'profile.json'; profile_path.write_text(json.dumps(self.profile))
        for run in ('../../outside', r'C:\outside', 'x'*1000, {'unexpected':'object'}):
            with self.subTest(run=repr(run)[:40]):
                path, receipt = probe.record(self.base, 'rejected', ['run_id_folder_mismatch'],
                                             {'run_id':run}, profile_path)
                self.assertEqual(path.parent, self.base/'.smelter/runtime-probe-verdicts')
                self.assertTrue(path.name.startswith('invalid-run-'))
                self.assertEqual(receipt['verdict'], 'rejected')

    def test_the_gta_profile_pins_the_staged_plugin(self):
        manifest = ROOT / '.smelter/mod-packages/gta-native-read-probe-20261028/manifest.json'
        if not manifest.is_file(): self.skipTest('Staged probe package not present on this machine')
        profile = json.loads((ROOT / 'mods/gta-ark/gta/rph/read_probe_expectations.json').read_text(encoding='utf-8'))
        self.assertEqual(profile['plugin']['sha256'], json.loads(manifest.read_text())['plugin_sha256'])


@unittest.skipUnless(os.name == 'nt', 'Windows Framework fixture compiler required')
class HarnessReportTests(unittest.TestCase):
    """The verdict reads the exact JSON the real C# harness writes (reviewed fixture, fake callbacks)."""
    @classmethod
    def setUpClass(cls):
        import test_runtime_probe
        test_runtime_probe.RuntimeProbeTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_fixture(self, scenario):
        import subprocess
        output = self.base / scenario
        result = subprocess.run([str(self.exe), scenario, str(output)], capture_output=True, timeout=10,
                                creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        return Path(result.stdout.decode().strip().splitlines()[0])

    def test_harness_reports_are_judged_by_their_real_field_format(self):
        path = self.run_fixture('ok')
        report = json.loads(path.read_text(encoding='utf-8-sig'))
        profile = json.loads((ROOT / 'mods/gta-ark/gta/rph/read_probe_expectations.json').read_text(encoding='utf-8'))
        profile['executable'] = {'name': self.exe.name, 'file_version': report['file_version'], 'sha256': probe.sha256(self.exe)}
        profile['plugin']['sha256'] = report['plugin_sha256']
        profile['plugin']['deployed_relative_path'] = self.exe.name
        profile['loader_log']['required'] = False
        self.assertEqual(probe.judge(path, profile)[:2], ('native_reads_verified', []))
        verdict, reasons, _ = probe.judge(self.run_fixture('wrong_hash'), profile)
        self.assertEqual(verdict, 'rejected')
        self.assertIn('stage_not_native_reads_observed', reasons); self.assertIn('samples_not_4', reasons)


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='smelter-runtime-inventory-')
        self.base = Path(self.temp.name)
        fixed = struct.pack('<IIII', 0xFEEF04BD, 0x10000, (1 << 16) | 124, (7 << 16) | 9)
        self.pe = b'MZ' + b'\0' * 60 + b'VS_VERSION_INFO' + fixed + b'\0' * 32

    def tearDown(self):
        self.temp.cleanup()

    def test_zip_members_are_hashed_and_versioned_without_extraction(self):
        archive = self.base / 'runtime.zip'
        with zipfile.ZipFile(archive, 'w') as out:
            out.writestr('Loader.exe', self.pe); out.writestr('Plugins/readme.txt', 'hello'); out.writestr('NoVersion.dll', b'MZ\0\0')
        value = runtime.inventory(archive)
        rows = {row['path']: row for row in value['files']}
        self.assertEqual(rows['Loader.exe']['file_version'], '1.124.7.9')
        self.assertIsNone(rows['NoVersion.dll']['file_version'])
        self.assertNotIn('file_version', rows['Plugins/readme.txt'])
        self.assertEqual(rows['Plugins/readme.txt']['sha256'], hashlib.sha256(b'hello').hexdigest())
        self.assertEqual(value['archive_sha256'], hashlib.sha256(archive.read_bytes()).hexdigest())
        self.assertEqual(sorted(p.name for p in self.base.iterdir()), ['runtime.zip'])

    def test_folders_are_inventoried_and_other_inputs_rejected(self):
        folder = self.base / 'unpacked'; (folder / 'sub').mkdir(parents=True)
        (folder / 'sub' / 'Loader.exe').write_bytes(self.pe)
        self.assertEqual(runtime.inventory(folder)['files'][0]['path'], 'sub/Loader.exe')
        with self.assertRaises(ValueError):
            runtime.inventory(self.base / 'missing')


if __name__ == '__main__':
    unittest.main()
