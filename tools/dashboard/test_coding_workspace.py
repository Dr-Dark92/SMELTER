"""Code isolation, hash admission, rollback, real MCP and evidence freshness."""
import hashlib
import json
import subprocess
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import coding_workspace as coding
from access_policy import current, Policy, using
from python_tools import ToolSession, permissions
from mcp_connections import sdk_status


class CodingWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'SMELTER'
        folder = self.root / 'tools/dashboard'
        folder.mkdir(parents=True)
        (folder / 'dashboard.py').write_bytes(b'VALUE = 0\n')
        (folder / 'example.py').write_bytes(b'def add(a, b):\n    return a - b\n')
        (folder / 'test_example.py').write_bytes(b'import unittest\nclass Example(unittest.TestCase):\n def test_one(self): self.assertEqual(1, 1)\n')
        (self.root / 'skills').mkdir()
        self.original = {p.relative_to(self.root).as_posix(): p.read_bytes() for p in folder.iterdir()}
        self.policy = current(self.root)
        self.context = using(self.policy)
        self.context.__enter__()

    def tearDown(self):
        self.context.__exit__(None, None, None)
        self.temp.cleanup()

    def prepare(self):
        result = coding.prepare(self.root, {})
        return result['workspace_id'], Path(result['path'])

    def change(self, sid, target, relative, content):
        path = target / relative
        return {'workspace_id': sid, 'changes': [{'relative_path': relative, 'content': content,
                 'expected_sha256': coding.digest(path.read_bytes()) if path.exists() else None}]}

    def test_copy_preserves_original_and_existing_v2(self):
        existing = self.root.with_name('SMELTERV2')
        existing.mkdir()
        (existing / 'user-work.txt').write_text('preserve')
        sid, target = self.prepare()
        self.assertEqual((existing / 'user-work.txt').read_text(), 'preserve')
        proposal = coding.propose(self.root, self.change(sid, target, 'tools/dashboard/example.py', 'VALUE=42\n'))
        coding.apply(self.root, {'workspace_id': sid, 'proposal_id': proposal['proposal_id']})
        for relative, raw in self.original.items():
            self.assertEqual((self.root / relative).read_bytes(), raw)
        self.assertEqual((target / 'tools/dashboard/example.py').read_bytes(), b'VALUE=42\n')

    def test_proposal_is_reviewable_but_does_not_edit_until_apply(self):
        sid, target = self.prepare()
        path = target / 'tools/dashboard/example.py'
        before = path.read_bytes()
        proposal = coding.propose(self.root, self.change(sid, target, 'tools/dashboard/example.py', 'VALUE=42\n'))
        self.assertIn('-def add', proposal['files'][0]['diff'])
        self.assertFalse(proposal['applied'])
        self.assertEqual(path.read_bytes(), before)

    def test_six_file_patch_and_new_file_hash_contract(self):
        sid, target = self.prepare()
        changes = [{'relative_path': f'tools/dashboard/new_{n}.py', 'expected_sha256': None,
                    'content': f'VALUE={n}\n'} for n in range(6)]
        proposed = coding.propose(self.root, {'workspace_id': sid, 'changes': changes})
        result = coding.apply(self.root, {'workspace_id': sid, 'proposal_id': proposed['proposal_id']})
        self.assertEqual(len(result['files']), 6)
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            coding.propose(self.root, {'workspace_id': sid, 'changes': changes})

    def test_stale_second_file_rejects_whole_patch_before_any_write(self):
        sid, target = self.prepare()
        changes = [self.change(sid, target, p, 'CHANGED=True\n')['changes'][0]
                   for p in ('tools/dashboard/example.py', 'tools/dashboard/dashboard.py')]
        proposal = coding.propose(self.root, {'workspace_id': sid, 'changes': changes})
        (target / 'tools/dashboard/dashboard.py').write_text('concurrent user edit\n')
        before = (target / 'tools/dashboard/example.py').read_bytes()
        with self.assertRaisesRegex(ValueError, 'changed'):
            coding.apply(self.root, {'workspace_id': sid, 'proposal_id': proposal['proposal_id']})
        self.assertEqual((target / 'tools/dashboard/example.py').read_bytes(), before)

    def test_second_replace_failure_rolls_back_first_file(self):
        sid, target = self.prepare()
        changes = [self.change(sid, target, p, 'CHANGED=True\n')['changes'][0]
                   for p in ('tools/dashboard/example.py', 'tools/dashboard/dashboard.py')]
        proposed = coding.propose(self.root, {'workspace_id': sid, 'changes': changes})
        original_replace = Path.replace
        def replace(path, destination):
            if Path(destination) == target / 'tools/dashboard/dashboard.py':
                raise OSError('simulated disk failure')
            return original_replace(path, destination)
        with patch.object(Path, 'replace', replace), self.assertRaisesRegex(OSError, 'disk failure'):
            coding.apply(self.root, {'workspace_id': sid, 'proposal_id': proposed['proposal_id']})
        self.assertEqual((target / 'tools/dashboard/example.py').read_bytes(), self.original['tools/dashboard/example.py'])
        self.assertEqual(coding.proposal(self.root, sid, proposed['proposal_id'])[1]['state'], 'rolled_back')

    def test_replay_is_idempotent_and_never_overwrites_a_later_edit(self):
        sid, target = self.prepare()
        proposed = coding.propose(self.root, self.change(sid, target, 'tools/dashboard/example.py', 'VALUE=42\n'))
        arguments = {'workspace_id': sid, 'proposal_id': proposed['proposal_id']}
        self.assertFalse(coding.apply(self.root, arguments)['reused'])
        self.assertTrue(coding.apply(self.root, arguments)['reused'])
        (target / 'tools/dashboard/example.py').write_text('later change')
        with self.assertRaisesRegex(ValueError, 'subsequent'):
            coding.apply(self.root, arguments)
        self.assertEqual((target / 'tools/dashboard/example.py').read_text(), 'later change')

    def test_portable_unsafe_paths_and_duplicate_case_are_rejected(self):
        sid, target = self.prepare()
        for relative in ('../source.py', '/etc/passwd', 'C:/Windows/file.py', 'tools/a.py:stream',
                         'tools/../x.py', 'tools/.smelter/a.py', 'tools/CON.py', 'tools/x./a.py',
                         'tools/.env', 'tools/secrets.json', 'tools/a\\b.py'):
            with self.subTest(relative=relative), self.assertRaises(ValueError):
                coding.propose(self.root, {'workspace_id': sid, 'changes': [
                    {'relative_path': relative, 'expected_sha256': None, 'content': 'x'}]})
        with self.assertRaisesRegex(ValueError, 'case-colliding'):
            coding.propose(self.root, {'workspace_id': sid, 'changes': [
                {'relative_path': 'tools/New.py', 'expected_sha256': None, 'content': 'a'},
                {'relative_path': 'tools/new.py', 'expected_sha256': None, 'content': 'b'}]})

    def test_cross_workspace_proposal_cannot_be_applied(self):
        sid, target = self.prepare()
        second, _ = self.prepare()
        proposal = coding.propose(self.root, self.change(sid, target, 'tools/dashboard/example.py', 'VALUE=42\n'))
        with self.assertRaises(ValueError):
            coding.apply(self.root, {'workspace_id': second, 'proposal_id': proposal['proposal_id']})

    def test_full_sha_and_crlf_are_preserved(self):
        sid, target = self.prepare()
        path = target / 'tools/dashboard/example.py'
        path.write_bytes('NAME="é"\r\n'.encode())
        result = coding.read(self.root, {'workspace_id': sid, 'relative_path': 'tools/dashboard/example.py', 'limit': 3})
        self.assertEqual(result['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertTrue(result['has_more'])

    def test_execution_requires_registered_test_scope(self):
        value = self.policy.value
        row = next(r for r in value['locations'] if r['id'] == 'development')
        row.update(execute=False, operations=[])
        with self.assertRaises(ValueError):
            ToolSession(self.root, {'coding_workspace': True}, policy=Policy(value))
        self.assertFalse(coding.base_path(self.root).exists())

    def test_new_permission_is_boolean_and_tools_are_not_exposed_without_it(self):
        for value in ('yes', 1, {}, None):
            with self.assertRaises(ValueError):permissions(self.root, {'coding_workspace': value})
        session = ToolSession(self.root)
        self.assertNotIn('apply_coding_patch', [t['function']['name'] for t in session.tools])

    def test_current_green_evidence_is_invalidated_by_any_edit(self):
        sid, target = self.prepare()
        evidence = {'stage': 'GREEN', 'exit_code': 0, 'counts': {'tests': 1}, 'cleanup_confirmed': True,
                    '_raw_output': b'actual fixture log', 'log_tail': 'actual fixture log'}
        with patch('sandbox.coding_test', return_value=evidence):
            result = coding.test(self.root, {'workspace_id': sid, 'profile': 'python'})
        self.assertTrue(Path(result['evidence_path']).is_file())
        self.assertTrue(coding.review(self.root, {'workspace_id': sid})['all_current_tests_passed'])
        proposal = coding.propose(self.root, self.change(sid, target, 'tools/dashboard/example.py', 'VALUE=42\n'))
        coding.apply(self.root, {'workspace_id': sid, 'proposal_id': proposal['proposal_id']})
        self.assertFalse(coding.review(self.root, {'workspace_id': sid})['all_current_tests_passed'])

    def test_review_requires_both_detected_profiles(self):
        sid, target = self.prepare()
        (target / 'tools/dashboard/test_other.js').write_text('test')
        evidence = {'stage': 'GREEN', 'exit_code': 0, 'cleanup_confirmed': True, '_raw_output': b'fixture', 'log_tail': ''}
        with patch('sandbox.coding_test', return_value=evidence):
            coding.test(self.root, {'workspace_id': sid, 'profile': 'python'})
        review = coding.review(self.root, {'workspace_id': sid})
        self.assertEqual(review['required_profiles'], ['python', 'node'])
        self.assertFalse(review['all_current_tests_passed'])
        self.assertEqual(review['coverage'], 'not measured')

    def test_command_arguments_are_rejected_before_a_runner_starts(self):
        sid, _ = self.prepare()
        with patch('sandbox.coding_test') as runner, self.assertRaises(ValueError):
            coding.test(self.root, {'workspace_id': sid, 'profile': 'python', 'command': 'echo unsafe'})
        runner.assert_not_called()

    def test_runner_classifies_assertions_separately_from_import_and_empty_errors(self):
        from sandbox import coding_test
        sid, target = self.prepare()
        cases = [({'tests':1,'failures':1,'errors':0,'skipped':0},1,'RED'),
                 ({'tests':1,'failures':0,'errors':1,'skipped':0},1,'ERROR'),
                 ({'tests':1,'failures':0,'errors':0,'skipped':1},0,'ERROR'),
                 ({'tests':1,'failures':0,'errors':0,'skipped':0},0,'GREEN')]
        for counts, code, expected in cases:
            with self.subTest(expected=expected, counts=counts):
                folder = Path(self.temp.name) / 'fake-snapshot'
                folder.mkdir()
                output = ('SMELTER_TEST_RESULT|' + json.dumps(counts) + '\n').encode()
                ready = {'ready':True,'docker':'docker','configured':{'python_image':'sha256:'+'a'*64}}
                with patch('sandbox.status',return_value=ready), patch('sandbox.snapshot',return_value=(folder,folder)), \
                     patch('sandbox.run',return_value=subprocess.CompletedProcess([],code,output,b'')) as runner, \
                     patch('sandbox._remove',return_value=True), patch('sandbox.record_owner'):
                    result = coding_test(self.root,target,'python')
                self.assertEqual(result['stage'],expected)
                command = runner.call_args.args[0]
                self.assertIn('--network',command)
                self.assertIn('none',command)
                self.assertIn('--read-only',command)
                self.assertIn('-I',command)
                self.assertNotIn('--privileged',command)

    @unittest.skipUnless(sdk_status()['status'] == 'installed', 'Pinned MCP SDK required')
    def test_real_mcp_patch_receipts_and_file_cards(self):
        session = ToolSession(self.root, {'coding_workspace': True, 'transport': 'mcp'})
        call = lambda name, args: session.execute({'function': {'name': name, 'arguments': args}})
        ready = call('prepare_coding_workspace', {})
        sid, target = ready['workspace_id'], Path(ready['path'])
        proposed = call('propose_coding_patch', self.change(sid, target, 'tools/dashboard/example.py', 'VALUE=42\n'))
        self.assertEqual(session.file_activity.snapshot()[0]['status'], 'proposed')
        result = call('apply_coding_patch', {'workspace_id': sid, 'proposal_id': proposed['proposal_id']})
        self.assertEqual(result['status'], 'coding_patch_applied')
        card = session.file_activity.snapshot()[0]
        self.assertEqual(card['status'], 'saved')
        self.assertEqual(card['after'], 'VALUE=42\n')
        self.assertIn('def add', card['before'])
        self.assertTrue(all(event['transport'] == 'mcp' for event in session.events))
        self.assertTrue(Path(result['mcp_audit_path']).is_file())


if __name__ == '__main__':unittest.main()
