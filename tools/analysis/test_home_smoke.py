"""Verify home smoke isolation, evidence and failure gates without inference."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import home_smoke
from home_demo import animated_glb, create_fixtures, prepare_demo
from smoke_agent_bridge import smoke_state, CONTENT, FILENAME
from database import select_database
from chats import create_chat
from model_assets import attach_model, inspect_attachment


class HomeSmokeTests(unittest.TestCase):
    def options(self, path, **values):
        defaults = dict(output=str(path), live=False, fixture=False, preflight_only=False,
                        prepare_demo=False, ecc=False, opencode_image=None)
        return argparse.Namespace(**{**defaults, **values})

    def test_glb_fixture_has_real_embedded_animation_times(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'source'
            root.mkdir()
            select_database(root, str(Path(temp) / 'db'))
            cid = create_chat(root, 'known animation')['id']
            raw = animated_glb()
            attachment = attach_model(root, {'conversation_id': cid, 'filename': 'two-clips.glb',
                                             'base64': base64.b64encode(raw).decode()})
            evidence = inspect_attachment(root, {'model_ids': [attachment['id']]}, {'attachment_id': attachment['id']})
            self.assertEqual(evidence['sha256'], hashlib.sha256(raw).hexdigest())
            clips = evidence['animation_clips']
            self.assertEqual([(c['source_name'], c['duration_seconds']) for c in clips], [('Lift_1s', 1), ('Slide_2s', 2)])
            self.assertTrue(all(c['duration_status'] == 'verified_embedded_keyframe_times' for c in clips))

    def test_inventory_expected_values_match_disk(self):
        with tempfile.TemporaryDirectory() as temp:
            manifest = create_fixtures(Path(temp) / 'inputs')
            root = Path(manifest['inventory']['path'])
            files = [p for p in root.rglob('*') if p.is_file()]
            self.assertEqual(len(files), 3)
            self.assertEqual(sum(p.stat().st_size for p in files), manifest['inventory']['total_file_bytes'])
            self.assertNotIn(Path(manifest['outside']), list(root.rglob('*')))

    def test_existing_report_folder_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'existing'
            path.mkdir()
            marker = path / 'important.txt'
            marker.write_text('preserve')
            with self.assertRaises(FileExistsError):
                home_smoke.execute(self.options(path))
            self.assertEqual(marker.read_text(), 'preserve')

    def test_failed_contract_stops_before_any_runtime_request(self):
        with tempfile.TemporaryDirectory() as temp:
            calls = []
            def command(argv, **kwargs):
                calls.append(argv)
                self.assertEqual(kwargs['env']['SMELTER_VISION_LIVE'], '0')
                self.assertEqual(kwargs['env']['SMELTER_TEST_DOCKER'], '0')
                return subprocess.CompletedProcess(argv, 1, '', 'test failure')
            with patch.object(home_smoke, 'preflight', return_value=([{'name': 'prerequisites', 'status': 'PASS'}], {})):
                code = home_smoke.execute(self.options(Path(temp) / 'report', live=True), command=command)
            self.assertEqual(code, 1)
            self.assertEqual(len(calls), 1)
            summary = json.loads((Path(temp) / 'report/summary.json').read_text())
            self.assertEqual(summary['live_qwen'], 'NOT_RUN')
            self.assertEqual(summary['gui'], 'MANUAL_PENDING')

    def test_missing_prerequisite_blocks_all_processes(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(home_smoke, 'preflight', return_value=([{'name': 'Docker', 'status': 'BLOCKED'}], {})):
                command = unittest.mock.Mock(side_effect=AssertionError('must not start'))
                code = home_smoke.execute(self.options(Path(temp) / 'report', live=True), command=command)
            self.assertEqual(code, 2)
            command.assert_not_called()

    def test_evidence_survives_failure_and_only_smoke_temp_is_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence = Path(temp) / 'evidence'
            with self.assertRaisesRegex(ValueError, 'simulated model failure'):
                with smoke_state(evidence) as base:
                    root = base / 'SMELTER'
                    root.mkdir()
                    select_database(root, str(base / 'db'))
                    create_chat(root, 'failure evidence')
                    (root / 'diagnostics').mkdir()
                    (root / 'diagnostics' / FILENAME).write_bytes(CONTENT.encode())
                    raise ValueError('simulated model failure')
            self.assertFalse(base.exists())
            self.assertEqual((evidence / FILENAME).read_bytes(), CONTENT.encode())
            self.assertTrue((evidence / 'chat-evidence.json').is_file())
            self.assertFalse(json.loads((evidence / 'evidence-index.json').read_text())['production_state_copied'])

    def test_demo_does_not_reuse_existing_v2_or_database(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            original = base / 'original'
            (original / 'tools/dashboard').mkdir(parents=True)
            (original / 'tools/dashboard/dashboard.py').write_text('HTML="<style>body{color:red}</style>"\n')
            select_database(original, str(base / 'production-db'))
            database = base / 'production-db/smelter.sqlite3'
            before = database.read_bytes()
            existing = base / 'originalV2'
            existing.mkdir()
            (existing / 'preserve.txt').write_text('old work')
            report = base / 'report'
            report.mkdir()
            fixtures = create_fixtures(report / 'inputs')
            demo = prepare_demo(original, report, {key: None for key in ('opencode_image', 'python_image', 'node_image')}, fixtures)
            self.assertTrue(Path(demo['target']).is_dir())
            self.assertEqual((existing / 'preserve.txt').read_text(), 'old work')
            self.assertEqual(database.read_bytes(), before)
            self.assertFalse(demo['started'])

    def test_token_urls_are_redacted_from_logs(self):
        result = home_smoke.redact('http://127.0.0.1:8780/#token=abc123\nAuthorization: Bearer headersecret\npassword=secret')
        for secret in ('abc123', 'headersecret', 'password=secret'):
            self.assertNotIn(secret, result)

    def test_live_summary_distinguishes_direct_failure_from_unrun_managed_route(self):
        requested = ['direct-ollama-live', 'agent-runtime', 'ecc-coding-runtime']
        cases = [([], 'NOT_RUN'),
                 ([('direct-ollama-live', 'FAIL')], 'FAIL'),
                 ([('direct-ollama-live', 'PASS')], 'PARTIAL'),
                 ([('direct-ollama-live', 'PASS'), ('agent-runtime', 'FAIL')], 'FAIL'),
                 ([(name, 'PASS') for name in requested], 'PASS')]
        for phases, expected in cases:
            with self.subTest(phases=phases):
                report = {'mode': 'live', 'requested_live_stages': requested,
                          'phases': [{'name': name, 'status': status} for name, status in phases]}
                self.assertEqual(home_smoke.live_acceptance(report), expected)
                report['mode'] = 'fixture'
                self.assertEqual(home_smoke.live_acceptance(report), 'NOT_RUN')

    def test_failed_direct_acceptance_stops_before_managed_inference(self):
        with tempfile.TemporaryDirectory() as temporary:
            images = {key: 'sha256:' + 'a' * 64 for key in ('python_image', 'node_image', 'opencode_image')}
            command = unittest.mock.Mock(return_value=subprocess.CompletedProcess(['node'], 0, '', ''))
            names = []
            def phase(directory, name, argv, **kwargs):
                names.append(name)
                return {'name': name, 'status': 'FAIL' if name == 'direct-ollama-live' else 'PASS',
                        'exit_code': 1 if name == 'direct-ollama-live' else 0}
            with patch.object(home_smoke, 'preflight', return_value=([{'name': 'Base', 'status': 'PASS'}], images)), \
                 patch.object(home_smoke, 'phase', side_effect=phase), \
                 patch('model_assets.viewer_bundle', return_value={}), \
                 patch('install_ecc_skills.preview', return_value=[]):
                output = Path(temporary) / 'report'
                code = home_smoke.execute(self.options(output, full=True, live=True), command=command)
            report = json.loads((output / 'summary.json').read_text())
            self.assertEqual(code, 1)
            self.assertEqual(names[-1], 'direct-ollama-live')
            self.assertNotIn('agent-runtime', names)
            self.assertNotIn('ecc-coding-runtime', names)
            self.assertEqual(report['live_qwen'], 'FAIL')
            self.assertEqual(report['live_direct_ollama'], 'FAIL')
            self.assertEqual(report['live_opencode'], 'NOT_RUN')
            self.assertEqual(report['live_ecc_coding'], 'NOT_RUN')
            summary = (output / 'SUMMARY.md').read_text()
            self.assertIn('Live Qwen acceptance: **FAIL**', summary)
            self.assertIn('Managed OpenCode (live): **NOT_RUN**', summary)

    def test_failed_command_retains_bounded_redacted_native_error(self):
        error = subprocess.CalledProcessError(1, ['docker', 'info'], stderr=(
            'Cannot connect to dockerDesktopLinuxEngine\nAuthorization: Bearer secret\n' +
            'x' * 10000).encode())
        detail = home_smoke.failure_detail(error)
        self.assertIn('Cannot connect to dockerDesktopLinuxEngine', detail)
        self.assertNotIn('secret', detail)
        self.assertLessEqual(len(detail), 4096)

    def test_docker_preflight_uses_standard_json_and_keeps_resource_guards(self):
        packet = dict(ServerVersion='29.8.2', OSType='linux', MemoryLimit=True,
                      SwapLimit=True, CpuCfsQuota=True, PidsLimit=True,
                      SecurityOptions=['name=seccomp,profile=builtin'],
                      HttpProxy='private-proxy-setting')
        for denied in (None, 'MemoryLimit', 'SwapLimit', 'CpuCfsQuota', 'PidsLimit', 'SecurityOptions'):
            with self.subTest(denied=denied):
                info = dict(packet)
                if denied:
                    info[denied] = [] if denied == 'SecurityOptions' else False
                calls = []
                def command(argv, **kwargs):
                    calls.append(argv)
                    if argv == ['node', '--version']:
                        output = 'v24.20.0'
                    elif argv[:3] == ['docker', 'context', 'inspect']:
                        output = 'npipe:////./pipe/dockerDesktopLinuxEngine'
                    elif argv[:2] == ['docker', 'info']:
                        self.assertEqual(argv, ['docker', 'info', '--format', '{{json .}}'])
                        output = json.dumps(info)
                    elif argv[:3] == ['docker', 'image', 'inspect']:
                        output = 'sha256:' + 'a' * 64
                    else:
                        self.fail('Unexpected process: ' + repr(argv))
                    return subprocess.CompletedProcess(argv, 0, output, '')
                with patch.object(home_smoke, 'configured_images', return_value={key: None for key in
                            ('python_image', 'node_image', 'opencode_image')}), \
                     patch.object(home_smoke, 'version', return_value='1.30.0'):
                    checks, images = home_smoke.preflight(Path('.'), runtime=True, command=command,
                                                          lookup=lambda name: name)
                docker = next(row for row in checks if row['name'] == 'Docker confinement prerequisites')
                self.assertEqual(docker['status'], 'BLOCKED' if denied else 'PASS')
                self.assertNotIn('private-proxy-setting', json.dumps(checks))
                image_calls = [argv for argv in calls if argv[:3] == ['docker', 'image', 'inspect']]
                self.assertEqual(len(image_calls), 0 if denied else 3)
                if not denied:
                    self.assertTrue(all(value == 'sha256:' + 'a' * 64 for value in images.values()))

    def test_docker_probe_failure_reports_stderr_and_never_inspects_images(self):
        calls = []
        def command(argv, **kwargs):
            calls.append(argv)
            if argv[:2] == ['docker', 'info']:
                raise subprocess.CalledProcessError(1, argv, stderr='Actual Docker failure; password=secret')
            output = 'v24.20.0' if argv[0] == 'node' else 'npipe:////./pipe/dockerDesktopLinuxEngine'
            return subprocess.CompletedProcess(argv, 0, output, '')
        with patch.object(home_smoke, 'configured_images', return_value={key: None for key in
                    ('python_image', 'node_image', 'opencode_image')}), \
             patch.object(home_smoke, 'version', return_value='1.30.0'):
            checks, _ = home_smoke.preflight(Path('.'), runtime=True, command=command, lookup=lambda name: name)
        result = next(row for row in checks if row['name'] == 'Docker confinement prerequisites')
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertIn('Actual Docker failure', result['detail'])
        self.assertNotIn('secret', result['detail'])
        self.assertFalse(any(argv[:3] == ['docker', 'image', 'inspect'] for argv in calls))

    def test_unverified_saved_image_ids_never_count_as_resolved_images(self):
        selected = dict(python_image='sha256:' + 'a' * 64, node_image='sha256:' + 'b' * 64,
                        opencode_image='sha256:' + 'c' * 64)
        packet = dict(ServerVersion='29.8.2', OSType='linux', MemoryLimit=True,
                      SwapLimit=True, CpuCfsQuota=True, PidsLimit=True,
                      SecurityOptions=['name=seccomp,profile=builtin'])
        for failed in ('daemon', selected['python_image']):
            with self.subTest(failed=failed):
                def command(argv, **kwargs):
                    if argv[0] == 'node':
                        output = 'v24.20.0'
                    elif argv[:3] == ['docker', 'context', 'inspect']:
                        output = 'npipe:////./pipe/dockerDesktopLinuxEngine'
                    elif argv[:2] == ['docker', 'info']:
                        if failed == 'daemon':
                            raise subprocess.CalledProcessError(1, argv, stderr='Engine unavailable')
                        output = json.dumps(packet)
                    else:
                        self.assertEqual(argv[:3], ['docker', 'image', 'inspect'])
                        if argv[-1] == failed:
                            raise subprocess.CalledProcessError(1, argv, stderr='No such image')
                        output = argv[-1]
                    return subprocess.CompletedProcess(argv, 0, output, '')
                with patch.object(home_smoke, 'configured_images', return_value=dict(selected)), \
                     patch.object(home_smoke, 'version', return_value='1.30.0'):
                    checks, images = home_smoke.preflight(Path('.'), runtime=True, command=command,
                                                          lookup=lambda name: name)
                self.assertIsNone(images['python_image'])
                if failed == 'daemon':
                    self.assertTrue(all(value is None for value in images.values()))
                else:
                    self.assertEqual(images['node_image'], selected['node_image'])
                    self.assertEqual(images['opencode_image'], selected['opencode_image'])
                    self.assertIn('No such image', next(row for row in checks if row['name'] == 'python_image')['detail'])

    def test_ecc_pin_mismatch_fails_before_install(self):
        from install_ecc_skills import preview
        with self.assertRaisesRegex(ValueError, 'integrity mismatch'):
            preview(lambda url: {'sha256': '0' * 64})

    def test_full_smoke_requires_browser_before_running_models(self):
        with tempfile.TemporaryDirectory() as temp:
            images = {key: 'sha256:' + 'a' * 64 for key in ('python_image', 'node_image', 'opencode_image')}
            command = unittest.mock.Mock(side_effect=OSError('fixture browser is missing'))
            with patch.object(home_smoke, 'preflight', return_value=([{'name': 'Base', 'status': 'PASS'}], images)), \
                 patch('install_ecc_skills.preview', return_value=[]):
                code = home_smoke.execute(self.options(Path(temp) / 'report', full=True, live=True), command=command)
            self.assertEqual(code, 2)
            summary = json.loads((Path(temp) / 'report/summary.json').read_text())
            self.assertEqual(summary['status'], 'BLOCKED')
            self.assertEqual(summary['live_direct_ollama'], 'NOT_RUN')
            self.assertEqual(summary['phases'], [])
            self.assertEqual(command.call_count, 1)

    def test_full_preflight_requires_both_test_images_without_running_phases(self):
        with tempfile.TemporaryDirectory() as temp:
            images = {'opencode_image': 'sha256:' + 'a' * 64, 'python_image': None, 'node_image': None}
            command = unittest.mock.Mock(return_value=subprocess.CompletedProcess(['node'], 0, '', ''))
            with patch.object(home_smoke, 'preflight', return_value=([{'name': 'Base', 'status': 'PASS'}], images)), \
                 patch('model_assets.viewer_bundle', return_value={}):
                code = home_smoke.execute(self.options(Path(temp) / 'report', full=True, preflight_only=True),
                                          command=command)
            summary = json.loads((Path(temp) / 'report/summary.json').read_text())
            self.assertEqual(code, 2)
            for name in ('Full smoke python_image', 'Full smoke node_image'):
                self.assertEqual(next(row for row in summary['checks'] if row['name'] == name)['status'], 'BLOCKED')
            self.assertEqual(summary['phases'], [])
            self.assertEqual(summary['live_qwen'], 'NOT_RUN')
            self.assertEqual(command.call_count, 1)


if __name__ == '__main__':
    unittest.main()
