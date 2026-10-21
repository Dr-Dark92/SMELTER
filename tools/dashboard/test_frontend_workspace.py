import ast
import json
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
import frontend_workspace as workspace
from python_tools import ToolSession


class FrontendWorkspaceTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / 'SMELTER'
        self.code = self.root / workspace.DASHBOARD
        self.code.parent.mkdir(parents=True)
        self.html = '<html><style>body{color:red}</style><button id="send">Send</button><script>const api="/api/chat";</script></html>'
        self.code.write_text('HTML = ' + repr(self.html) + '\n\ndef handler():\n    return "backend unchanged"\n', encoding='utf-8')
        (self.code.parent / 'chat_renderer.js').write_text('const fixture=true;', encoding='utf-8')
        skill = self.root / 'skills/redesign-skill'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('---\nname: redesign-skill\ndescription: Redesign existing frontends\n---\nUse readable typography.', encoding='utf-8')
        self.original = self.code.read_bytes()

    def prepare(self):
        return workspace.prepare(self.root, {})

    def edit(self):
        current = workspace.read_file(self.root, {})
        return workspace.replace_css(self.root, {'expected_sha256': current['sha256'],
            'old_text': 'body{color:red}', 'new_text': 'body{color:blue;font-family:system-ui}'})

    def test_prepare_keeps_original_and_uses_a_separate_database(self):
        result = self.prepare()
        target = workspace.target_path(self.root)
        self.assertEqual(self.code.read_bytes(), self.original)
        self.assertEqual(Path(result['target']), target)
        self.assertNotEqual(Path(result['data_directory']).parent, target)
        self.assertTrue((Path(result['data_directory']) / 'smelter.sqlite3').is_file())
        self.assertTrue(workspace.prepare(self.root, {})['reused'])

    def test_unmanaged_destination_is_not_overwritten(self):
        target = workspace.target_path(self.root)
        target.mkdir()
        (target / 'keep.txt').write_text('keep')
        with self.assertRaisesRegex(ValueError, 'unmanaged'):
            self.prepare()
        self.assertEqual((target / 'keep.txt').read_text(), 'keep')

    def test_css_edit_preserves_backend_javascript_and_source(self):
        self.prepare()
        result = self.edit()
        self.assertEqual(result['status'], 'workspace_edited')
        workspace._check(self.root)
        self.assertEqual(self.code.read_bytes(), self.original)
        _, node = workspace._html((workspace.target_path(self.root) / workspace.DASHBOARD).read_text())
        self.assertIn('color:blue', node.value)
        self.assertIn('<script>const api="/api/chat";</script>', node.value)
        # Quotes and backslashes cannot escape the literal into Python code.
        current = workspace.read_file(self.root, {})
        workspace.replace_css(self.root, {'expected_sha256': current['sha256'], 'old_text': 'font-family:system-ui',
            'new_text': 'font-family:"system-ui";--quoted:"\\\\path"'})
        workspace._check(self.root)

    def test_stale_hash_html_injection_and_arbitrary_paths_are_rejected(self):
        self.prepare()
        for payload in ({'expected_sha256': 'stale', 'old_text': 'body', 'new_text': 'main'},
                        {'expected_sha256': 'stale', 'old_text': 'body', 'new_text': '</style><script>bad()</script>'}):
            with self.assertRaises(ValueError):
                workspace.replace_css(self.root, payload)
        with self.assertRaises(ValueError):
            workspace.read_file(self.root, {'relative_path': '../../secret.txt'})
        self.assertEqual((workspace.target_path(self.root) / workspace.DASHBOARD).read_bytes(), self.original)

    def test_backend_or_script_changes_block_validation_and_launch(self):
        self.prepare()
        target = workspace.target_path(self.root) / workspace.DASHBOARD
        target.write_text(self.original.decode().replace('backend unchanged', 'backend changed'))
        with self.assertRaisesRegex(ValueError, 'backend changed'):
            workspace._check(self.root)
        target.write_text(self.original.decode().replace('/api/chat', '/api/changed'))
        with self.assertRaisesRegex(ValueError, 'JavaScript changed'):
            workspace._check(self.root)
        target.write_bytes(self.original)
        self.code.write_text(self.original.decode() + '\n# source changed')
        with self.assertRaisesRegex(ValueError, 'Original source changed'):
            workspace._check(self.root)

    def test_only_enabled_actual_design_skills_can_be_read(self):
        info = workspace.info(self.root, {})
        self.assertEqual(info['skills'][0]['id'], 'redesign-skill')
        result = workspace.read_skill(self.root, {'skill_id': 'redesign-skill'})
        self.assertIn('Use readable typography', result['text'])
        with self.assertRaises(ValueError):
            workspace.read_skill(self.root, {'skill_id': 'imaginary-modern-ui'})

    def test_permission_is_explicit_and_workspace_has_24_call_budget(self):
        ordinary = ToolSession(self.root, {})
        self.assertEqual(ordinary.call_limit, 4)
        self.assertFalse(ordinary.tools)
        approved = ToolSession(self.root, {'frontend_workspace': True})
        self.assertEqual(approved.call_limit, 24)
        self.assertIn('prepare_frontend_workspace', [t['function']['name'] for t in approved.tools])
        self.assertIn(str(workspace.target_path(self.root)), approved.context())
        with self.assertRaises(ValueError):
            workspace.execute(self.root, {}, 'prepare_frontend_workspace', {})

    def test_validation_uses_confined_runner_and_new_edits_invalidate_launch(self):
        self.prepare()
        checks=[{'command':['python','-m','unittest','discover'],'exit_code':0,'output':b'fixture passed','sandbox':'docker-no-network','image':'sha256:fixture'}]
        with patch('sandbox.tests',return_value=checks) as runner:
            result=workspace.validate(self.root,{})
        runner.assert_called_once_with(self.root,workspace.target_path(self.root))
        self.assertEqual(result['status'],'workspace_validated')
        self.assertEqual(result['sandbox'],'docker-no-network')
        self.edit()
        with self.assertRaisesRegex(ValueError,'after the last CSS edit'):workspace.launch(self.root,{})

    def test_workspace_reads_are_not_cached_after_css_changes(self):
        self.prepare()
        session = ToolSession(self.root, {'frontend_workspace': True})
        request = {'function': {'name': 'read_frontend_file', 'arguments': {}}}
        first = session.execute(request)
        self.edit()
        second = session.execute(request)
        self.assertNotEqual(first['sha256'], second['sha256'])
        self.assertIn('color:blue', second['text'])
        self.assertFalse(session.events[-1]['reused'])

    def test_failed_validation_invalidates_previous_pass(self):
        self.prepare()
        def checks(code):return [{'command':['python'],'exit_code':code,'output':b'fixture','sandbox':'docker-no-network'}]
        with patch('sandbox.tests',return_value=checks(0)):workspace.validate(self.root,{})
        record=workspace.target_path(self.root)/'.smelter/frontend-validation/passed.json'
        self.assertTrue(record.is_file())
        with patch('sandbox.tests',return_value=checks(1)):workspace.validate(self.root,{})
        self.assertFalse(record.exists())
        with self.assertRaisesRegex(ValueError,'validation'):workspace.launch(self.root,{})

    def test_preview_uses_confined_runner_and_rejects_legacy_pass(self):
        self.prepare();folder=workspace.target_path(self.root)/'.smelter/frontend-validation';folder.mkdir()
        record=folder/'passed.json';record.write_text(json.dumps({'dashboard_sha256':workspace._digest(self.original)}))
        with patch('sandbox.preview') as preview:
            with self.assertRaisesRegex(ValueError,'confined'):workspace.launch(self.root,{})
            preview.assert_not_called()
        record.write_text(json.dumps({'dashboard_sha256':workspace._digest(self.original),'sandbox':'docker-no-network'}))
        with patch('sandbox.preview',return_value={'url':'http://127.0.0.1:8770/#token=fixture','sandbox':'docker-no-network'}) as preview:
            self.assertEqual(workspace.launch(self.root,{})['status'],'workspace_launched')
            preview.assert_called_once_with(self.root,workspace.target_path(self.root))

    def test_unavailable_confinement_has_no_host_fallback(self):
        self.prepare()
        with patch('sandbox.status',return_value={'ready':False,'reason':'fixture unavailable'}),patch('subprocess.Popen') as spawn:
            with self.assertRaisesRegex(ValueError,'Confined tests unavailable'):workspace.validate(self.root,{})
            spawn.assert_not_called()
