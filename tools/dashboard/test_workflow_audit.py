"""Cross-layer audit regressions. Disposable files and synthetic model responses only."""
import io
import json
from pathlib import Path
import tempfile
import unittest
import shutil
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

from access_policy import current
from chats import create_chat, read_chat
from database import inspect_database, select_database


class WorkflowAuditTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.root = self.base / 'SMELTER'
        (self.root / 'tools/dashboard').mkdir(parents=True)
        (self.root / 'tools/dashboard/dashboard.py').write_text('VALUE=1\n', encoding='utf-8')
        (self.root / 'skills').mkdir()
        select_database(self.root, str(self.base / 'data'))
        self.cid = create_chat(self.root, 'Workflow audit')['id']

    def test_plain_opencode_task_does_not_require_or_read_an_existing_v2(self):
        from opencode_sandbox import ManagedClient
        from task_contract import configuration
        # Stop at the actual snapshot boundary; no process or model is started.
        ready = {'ready': True, 'docker': 'fixture', 'configured': {}}
        with patch('opencode_sandbox.status', return_value=ready), \
             patch('opencode_sandbox.snapshot', side_effect=ValueError('snapshot captured')) as snapshot:
            with self.assertRaisesRegex(ValueError, 'snapshot captured'):
                ManagedClient(self.root, current(self.root), configuration(self.root), allow_inference=True)
        self.assertEqual(snapshot.call_args.args[1], self.root.resolve())
        self.assertFalse(self.root.with_name('SMELTERV2').exists())

    def test_direct_coding_infrastructure_error_is_saved_as_partial(self):
        from chat_inference import ask
        packets = [
            {'message': {'content': '', 'tool_calls': [{'function': {
                'name': 'run_coding_tests', 'arguments': {'workspace_id': 'fixture', 'profile': 'python'}}}]}},
            {'message': {'content': 'Synthetic final response'}},
        ]
        def opener(*args, **kwargs):
            return io.BytesIO(json.dumps(packets.pop(0)).encode())
        evidence = {'status': 'coding_tests_failed', 'stage': 'ERROR', 'exit_code': 1}
        with patch('python_tools.ToolSession._invoke', return_value=evidence):
            result = ask(self.root, self.cid, 'Run tests', opener=opener,
                         tool_permissions={'coding_workspace': True})
        self.assertEqual(result['status'], 'partial')
        stored = read_chat(self.root, self.cid)['messages'][-1]['execution']
        self.assertEqual(stored['outcome'], 'partial')
        self.assertEqual(stored['events'][0]['result'], evidence)

    def test_expected_tdd_red_is_not_an_infrastructure_failure(self):
        from tool_contract import result_failed
        self.assertFalse(result_failed({'status': 'coding_tests_failed', 'stage': 'RED'}))
        self.assertTrue(result_failed({'status': 'coding_tests_failed', 'stage': 'ERROR'}))
        self.assertTrue(result_failed({'status': 'coding_tests_failed'}))

    def test_frontend_validation_receives_its_fixed_longer_mcp_deadline(self):
        from mcp_connections import call
        envelope = {'structuredContent': {'tool_result': {'status': 'workspace_validated'}}}
        with patch('mcp_connections.exchange', return_value=envelope) as exchange:
            call(self.root, {'frontend_workspace': True}, 'validate_frontend_workspace', {})
        self.assertGreaterEqual(exchange.call_args.kwargs.get('timeout', 120), 420)

    def test_bridge_deadlines_outlive_host_operation_and_cleanup(self):
        from agent_bridge import AgentBridge
        from tool_contract import operation_timeout, BRIDGE_RPC_TIMEOUT
        with patch('mcp_connections.sdk_status', return_value={'status': 'installed'}):
            bridge = AgentBridge(self.root, self.cid, 'Review', grants={'frontend_workspace': True})
        manifest = bridge.manifest(30)
        timeout = manifest['tool_timeouts']['validate_frontend_workspace']
        self.assertGreater(timeout, operation_timeout('validate_frontend_workspace'))
        self.assertGreater(BRIDGE_RPC_TIMEOUT, timeout)
        self.assertGreater(manifest['timeout_seconds'], operation_timeout('inventory_directory'))

    def test_coding_cards_reject_malformed_function_before_touching_files(self):
        from coding_activity import CodingActivity
        activity = CodingActivity(self.root, SimpleNamespace(propose=lambda call: None), current(self.root))
        for function in (None, [], 'invalid', 12):
            with self.subTest(function=function):
                self.assertEqual(activity._changes({'function': function}), [])

    def test_capability_catalog_exposes_coding_tools_and_separate_runner_readiness(self):
        from capability_catalog import catalog
        ready = lambda root, operation='frontend': {
            'ready': operation == 'coding_python', 'reason': operation}
        with patch('sandbox.status', side_effect=ready):
            report = catalog(self.root)
        tools = {row['id']: row for row in report['capabilities']}
        self.assertIn('propose_coding_patch', tools)
        self.assertEqual(tools['run_coding_tests']['profiles']['python']['availability'], 'requires_per_message_grants')
        self.assertEqual(tools['run_coding_tests']['profiles']['node']['availability'], 'blocked')

    def test_database_directory_with_hash_character_is_readable(self):
        root = self.base / 'second'
        root.mkdir()
        result = select_database(root, str(self.base / 'data#archive'))
        self.assertTrue(Path(result['path']).is_file())
        self.assertTrue(inspect_database(root, integrity=True)['ready'])

    def test_github_malformed_file_packet_is_a_validation_error(self):
        from github_skill_discovery import discover_github_skill
        with self.assertRaises(ValueError):
            discover_github_skill('https://github.com/fixture/repo/blob/main/SKILL.md',
                                  opener=lambda *a, **k: io.BytesIO(b'[]'))

    def test_direct_admission_rejects_bad_skills_before_starting_a_worker(self):
        from chat_jobs import Jobs
        with patch('chat_jobs.threading.Thread') as thread:
            with self.assertRaisesRegex(ValueError, 'Skill unavailable'):
                Jobs().start(self.root, {'id': self.cid, 'content': 'Fixture', 'skills': ['missing']})
        thread.assert_not_called()

    def test_installed_catalogue_never_silently_hides_overflow(self):
        from skills_catalog import catalog_skills
        for name in ('one', 'two', 'three'):
            folder = self.root / 'skills' / name
            folder.mkdir()
            (folder / 'SKILL.md').write_text('# Fixture\n\n## Purpose\nSynthetic reference.\n', encoding='utf-8')
        with patch('skills_catalog.MAX_SKILLS', 2), self.assertRaisesRegex(ValueError, 'exceeds'):
            catalog_skills(self.root)

    def test_collection_capacity_is_checked_before_any_import(self):
        from skill_collections import install_collection
        import hashlib
        content = '# Fixture\n\n## Purpose\nNew bounded reference.\n'
        selected = [{'id': 'one', 'url': 'https://github.com/fixture/repo/blob/main/one/SKILL.md',
                     'sha256': hashlib.sha256(content.encode()).hexdigest()}]
        with patch('skills_catalog.MAX_SKILLS', 0), self.assertRaisesRegex(ValueError, 'exceed'):
            install_collection(self.root, 'https://github.com/fixture/repo', selected, True,
                               discover=lambda url: {'content': content, 'sha256': selected[0]['sha256']})
        self.assertFalse((self.root / '.smelter/managed-skills/collections').exists())

    def test_direct_task_uses_and_records_its_admitted_skill_snapshot(self):
        from chat_jobs import Jobs
        from skill_manager import set_skill_enabled
        from chat_inference import ask
        folder = self.root / 'skills/reference'
        folder.mkdir()
        raw = b'# Reference\n\n## Purpose\nADMITTED_INSTRUCTION_MARKER\n'
        (folder / 'SKILL.md').write_bytes(raw)
        jobs = Jobs()
        with patch('chat_jobs.threading.Thread'):
            admitted = jobs.start(self.root, {'id': self.cid, 'content': 'Fixture', 'skills': ['reference']})
        control = jobs.jobs[admitted['id']]['control']
        set_skill_enabled(self.root, 'reference', False, approval=True)
        requests = []
        def infer(body, *args):
            requests.append(body)
            return b'{"message":{"content":"Synthetic response"}}'
        with patch.object(control, 'infer', side_effect=infer):
            result = ask(self.root, self.cid, 'Fixture', skills=['reference'], control=control)
        self.assertEqual(result['status'], 'completed')
        self.assertIn('ADMITTED_INSTRUCTION_MARKER', json.dumps(requests))
        saved = read_chat(self.root, self.cid)['messages'][-1]['execution']
        import hashlib
        self.assertEqual(saved['skill_snapshots'][0]['sha256'], hashlib.sha256(raw).hexdigest())

    @unittest.skipUnless(shutil.which('node'), 'Node executable required for fixed reporter fixtures')
    def test_real_node_reporter_separates_assertion_import_error_green_and_all_skipped(self):
        from sandbox import CODING_NODE, node_test_result
        code = self.root / 'tools/dashboard/test_node_fixture.js'
        prefix = "const {test}=require('node:test');const assert=require('node:assert/strict');"
        cases = [('RED', prefix + "test('one',()=>assert.equal(1,2));", False),
                 ('ERROR', prefix + "test('one',()=>assert.equal(1,2));", True),
                 ('GREEN', prefix + "test('one',()=>assert.equal(1,1));", False),
                 ('ERROR', prefix + "test.skip('one',()=>{});", False)]
        for expected, source, broken_import in cases:
            with self.subTest(stage=expected, broken_import=broken_import):
                code.write_text(source, encoding='utf-8')
                other = code.with_name('test_broken.js')
                if broken_import:other.write_text("require('./deliberately-absent-module');", encoding='utf-8')
                else:other.unlink(missing_ok=True)
                result = subprocess.run([shutil.which('node'), '-e', CODING_NODE], cwd=self.root,
                                        capture_output=True, text=True, timeout=10)
                stage, counts = node_test_result(result.returncode, result.stdout)
                self.assertEqual(stage, expected, result.stdout + result.stderr)
                self.assertGreater(counts['tests'], 0)


if __name__ == '__main__':
    unittest.main()
