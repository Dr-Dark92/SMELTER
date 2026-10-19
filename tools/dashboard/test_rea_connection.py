"""Adapter contracts with isolated files and mocked Node; no live REA claims."""
import hashlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from rea_connection import package_status, run_rea, VERSION
from python_tools import permissions, REA_SKILL_ID
from chat_inference import ask
from chats import create_chat
from database import select_database


class ReaConnectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        # Windows tempfile may return an 8.3 alias; the adapter resolves paths.
        self.base = Path(temp.name).resolve()
        self.root = self.base / 'checkout'
        self.root.mkdir()
        self.game = self.base / 'game'
        self.game.mkdir()
        (self.game / 'sample.exe').write_bytes(b'MZfixture')
        self.node = self.base / 'node.exe'
        self.node.touch()
        self.finder = lambda name: str(self.node)
        self.package = self.root / '.smelter/tooling/rea/node_modules/rea-agents'
        (self.package / 'scripts').mkdir(parents=True)
        (self.package / 'scripts/rea.mjs').touch()
        (self.package / 'package.json').write_text(json.dumps({'name': 'rea-agents', 'version': VERSION}))
        skill = self.root / '.smelter/managed-skills/collections/morluto-rea/reverse-engineer-anything'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('# REA\n\n## Purpose\nREA fixture instructions.\n')
        (self.root / '.smelter/skill-state.json').write_text(json.dumps({REA_SKILL_ID: True}))
        self.grants = permissions(self.root, {'rea_analysis': True, 'rea_root': str(self.game)})
        self.raw = b'{"capabilities":["pe_resources"],"ok":true}'
        self.runner = Mock(side_effect=[subprocess.CompletedProcess([], 0, b'v22.19.0\n', b''),
                                        subprocess.CompletedProcess([], 0, self.raw, b'')])

    def run_tool(self, name='rea_capabilities', args=None):
        return run_rea(self.root, self.grants, name, args or {}, runner=self.runner, finder=self.finder)

    def test_fixed_command_and_exact_evidence(self):
        result = self.run_tool('rea_inspect_pe_resources', {'relative_path': 'sample.exe'})
        command = self.runner.call_args.args[0]
        self.assertEqual(command, [str(self.node), str(self.package / 'scripts/rea.mjs'),
                                  'inspect-pe-resources', str(self.game / 'sample.exe'), '--json'])
        self.assertFalse(self.runner.call_args.kwargs['shell'])
        self.assertEqual(Path(result['evidence_path']).read_bytes(), self.raw)
        self.assertEqual(result['evidence_sha256'], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(result['status'], 'rea_completed')

    def test_no_approval_no_process(self):
        with self.assertRaises(ValueError):
            run_rea(self.root, {}, 'rea_capabilities', {}, runner=self.runner, finder=self.finder)
        self.runner.assert_not_called()

    def test_skill_required_and_disabled_rejected(self):
        (self.root / '.smelter/skill-state.json').write_text(json.dumps({REA_SKILL_ID: False}))
        with self.assertRaises(ValueError):
            permissions(self.root, {'rea_analysis': True})

    def test_paths_types_and_flags_rejected_before_process(self):
        (self.game / 'bad.exe').write_bytes(b'not PE')
        (self.game / 'sample.oppc').write_bytes(b'MZ')
        for relative in ('../node.exe', '/etc/passwd', 'C:/Windows/a.exe', 'sample.oppc', 'bad.exe'):
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                self.run_tool('rea_inspect_pe_resources', {'relative_path': relative})
        with self.assertRaises(ValueError):
            self.run_tool(args={'command': 'arbitrary'})
        with patch('rea_connection.MAX_FILE_BYTES', 1), self.assertRaises(ValueError):
            self.run_tool('rea_inspect_pe_resources', {'relative_path': 'sample.exe'})
        self.runner.assert_not_called()

    def test_symlink_rejected(self):
        try:
            (self.game / 'linked.exe').symlink_to(self.node)
        except OSError:
            self.skipTest('Symlink privilege unavailable')
        with self.assertRaises(ValueError):
            self.run_tool('rea_inspect_pe_resources', {'relative_path': 'linked.exe'})
        self.runner.assert_not_called()

    def test_windows_rooted_path_rejected_before_resolution(self):
        from pathlib import PureWindowsPath
        self.assertFalse(PureWindowsPath('/etc/passwd').is_absolute())
        with self.assertRaisesRegex(ValueError, 'escapes approved folder'):
            self.run_tool('rea_inspect_pe_resources', {'relative_path': '/etc/passwd'})
        self.runner.assert_not_called()

    def test_missing_file_is_validation_error(self):
        with self.assertRaisesRegex(ValueError, 'missing or inaccessible'):
            self.run_tool('rea_inspect_pe_resources', {'relative_path': 'missing.exe'})
        self.runner.assert_not_called()

    def test_missing_and_incompatible_package(self):
        self.assertEqual(package_status(self.root, lambda _: None)['status'], 'missing')
        (self.package / 'package.json').write_text('{"name":"rea-agents","version":"0"}')
        self.assertEqual(package_status(self.root, self.finder)['status'], 'incompatible')
        with self.assertRaises(ValueError):
            self.run_tool()
        self.runner.assert_not_called()

    def test_unsupported_node_rejected(self):
        self.runner.side_effect = [subprocess.CompletedProcess([], 0, b'v25.1.0', b'')]
        with self.assertRaises(ValueError):
            self.run_tool()
        self.assertEqual(self.runner.call_count, 1)

    def test_failed_result_retained(self):
        self.runner.side_effect = [subprocess.CompletedProcess([], 0, b'v24.11.0', b''),
                                  subprocess.CompletedProcess([], 1, b'{"ok":false}', b'failure')]
        result = self.run_tool()
        self.assertEqual(result['status'], 'rea_failed')
        self.assertTrue(Path(result['evidence_path']).exists())

    def test_invalid_json_and_timeout(self):
        for outcome in (subprocess.CompletedProcess([], 0, b'not JSON', b''),
                        subprocess.TimeoutExpired('node', 35)):
            self.runner.side_effect = [subprocess.CompletedProcess([], 0, b'v26.0.0', b''), outcome]
            with self.assertRaises(ValueError):
                self.run_tool()
        self.assertFalse((self.root / '.smelter/rea-evidence').exists())

    def test_large_preview_is_explicitly_partial(self):
        raw = json.dumps({'items': ['x' * 1000] * 30}).encode()
        self.runner.side_effect = [subprocess.CompletedProcess([], 0, b'v26.0.0', b''),
                                  subprocess.CompletedProcess([], 0, raw, b'')]
        result = self.run_tool()
        self.assertTrue(result['preview_truncated'])
        self.assertLess(len(json.dumps(result['result_preview'])), 10000)
        self.assertEqual(Path(result['evidence_path']).read_bytes(), raw)

    def test_qwen_receives_skill_and_actual_tool_result(self):
        select_database(self.root, str(self.base / 'data'))
        cid = create_chat(self.root, 'REA')['id']
        requests = []
        replies = iter([{'content': '', 'tool_calls': [{'function': {'name': 'rea_capabilities', 'arguments': {}}}]},
                        {'content': 'PE resources supported.'}])
        def opener(request, timeout):
            requests.append(json.loads(request.data))
            return io.BytesIO(json.dumps({'message': next(replies)}).encode())
        def adapter(root, grants, name, arguments):
            return run_rea(root, grants, name, arguments, runner=self.runner, finder=self.finder)
        with patch('rea_connection.run_rea', side_effect=adapter):
            result = ask(self.root, cid, 'Discover REA', tool_permissions={'rea_analysis': True}, opener=opener)
        self.assertIn(REA_SKILL_ID, result['skills_used'])
        self.assertIn('REA fixture instructions', json.dumps(requests[0]))
        self.assertIn('pe_resources', json.dumps(requests[1]))
        self.assertTrue(result['tools_executed'])
        self.assertEqual(result['tool_events'][0]['skill_id'], REA_SKILL_ID)


if __name__ == '__main__':
    unittest.main()
