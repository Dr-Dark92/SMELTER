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

    def test_ecc_pin_mismatch_fails_before_install(self):
        from install_ecc_skills import preview
        with self.assertRaisesRegex(ValueError, 'integrity mismatch'):
            preview(lambda url: {'sha256': '0' * 64})


if __name__ == '__main__':
    unittest.main()
