"""Contract scaffolds: interface-correct skeletons, proposed never applied."""
import unittest
from unittest.mock import patch

import acceptance_contracts as acceptance
import coding_workspace as cw
import sandbox
from contract_scaffold import render, scaffold
from python_tools import ToolSession
import test_coding_workspace as base_tests
from test_lua_profile import toolchain

SPEC = acceptance.DEFINITIONS['predator-controller-v1']['scaffold']


class RenderTests(unittest.TestCase):
    def test_render_is_deterministic_pure_and_validates_every_declared_capability(self):
        source = render('predator-controller-v1', SPEC)
        self.assertEqual(source, render('predator-controller-v1', SPEC))
        for function in SPEC['deps'][0]['functions']:
            self.assertIn('"unsupported_capability:' + function + '"', source)
        self.assertIn('deps.profile.attack_radius <= deps.profile.detect_radius', source)
        self.assertIn('function controller:update(actor_id)', source)
        self.assertIn('local state = {}', source.split('function M.new')[1])
        code = '\n'.join(line.split('--')[0] for line in source.splitlines())
        for forbidden in ('require', 'os.', 'io.', 'print(', '_G', 'debug', 'load('):
            self.assertNotIn(forbidden, code)
        self.assertLessEqual(max(map(len, source.splitlines())), 120)

    def test_malformed_specs_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'no scaffold'):render('x', None)
        with self.assertRaisesRegex(ValueError, 'identifiers'):
            render('x', {'deps': [{'name': 'a b', 'type': 'table'}], 'methods': [{'name': 'u'}]})
        with self.assertRaisesRegex(ValueError, 'dependency type'):
            render('x', {'deps': [{'name': 'a', 'type': 'userdata'}], 'methods': [{'name': 'u'}]})
        with self.assertRaisesRegex(ValueError, 'rules'):
            render('x', {'deps': [{'name': 'p', 'type': 'table', 'rules': [['a', '==', 'b']]}], 'methods': [{'name': 'u'}]})
        with self.assertRaisesRegex(ValueError, 'one to six methods'):render('x', {'deps': [], 'methods': []})


class ScaffoldToolTests(unittest.TestCase):
    def setUp(self):
        base_tests.CodingWorkspaceTests.setUp(self)
        ready = toolchain()
        if ready:
            configured = patch('sandbox.config', return_value={**sandbox.DEFAULT, **ready['configured']})
            configured.start(); self.addCleanup(configured.stop)
    def tearDown(self): base_tests.CodingWorkspaceTests.tearDown(self)
    prepare = base_tests.CodingWorkspaceTests.prepare

    def fixture(self, register=True):
        relative = 'mods/demo/Scripts/controller.lua'; path = self.root / relative; path.parent.mkdir(parents=True)
        path.write_text('local M = {}\nreturn M\n', encoding='utf-8')
        (self.root / 'mods/demo/tests').mkdir()
        (self.root / 'mods/demo/tests/test_load.lua').write_text('print("ok")\n', encoding='utf-8')
        sid, target = self.prepare()
        if register:acceptance.register(self.root, sid, 'predator-controller-v1', relative)
        return sid, target, relative

    def test_tool_is_registered_for_coding_grants(self):
        names = [t['function']['name'] for t in ToolSession(self.root, {'coding_workspace': True}).tools]
        self.assertIn('scaffold_contract_subject', names)

    def test_scaffold_is_a_proposal_for_the_registered_subject_only(self):
        sid, target, relative = self.fixture()
        before = (target / relative).read_bytes()
        with patch('sandbox.lua_parse', return_value=None):
            result = scaffold(self.root, {'workspace_id': sid, 'contract_id': 'predator-controller-v1'})
        self.assertEqual(result['status'], 'coding_patch_proposed')
        self.assertEqual(result['files'][0]['relative_path'], relative)
        self.assertEqual((target / relative).read_bytes(), before)
        self.assertEqual(result['todo'], ['eligible', 'select_target', 'current_distance', 'update'])
        with self.assertRaisesRegex(ValueError, 'not registered'):
            scaffold(self.root, {'workspace_id': sid, 'contract_id': 'entity-policy-v1'})
        with self.assertRaisesRegex(ValueError, 'requires'):
            scaffold(self.root, {'workspace_id': sid, 'contract_id': 'predator-controller-v1', 'extra': 1})

    def test_contract_without_scaffold_spec_is_refused(self):
        sid, target, relative = self.fixture(register=False)
        acceptance.register(self.root, sid, 'entity-policy-v1', relative)
        with self.assertRaisesRegex(ValueError, 'no scaffold specification'):
            scaffold(self.root, {'workspace_id': sid, 'contract_id': 'entity-policy-v1'})

    def test_checkpoint_restore_reports_discarded_newer_versions(self):
        sid, target, relative = self.fixture(register=False)
        shas = []
        for n in range(3):
            current = cw.digest((target / relative).read_bytes()); shas.append(current)
            proposal = cw.propose(self.root, {'workspace_id': sid, 'changes': [{'relative_path': relative,
                'expected_sha256': current, 'content': 'local M = {}\n-- v' + str(n) + '\nreturn M\n'}]})
            cw.apply(self.root, {'workspace_id': sid, 'proposal_id': proposal['proposal_id']})
        old = cw.propose_restore(self.root, {'workspace_id': sid, 'relative_paths': [relative], 'checkpoint_sha256': shas[0]})
        self.assertEqual(old['restore_warning']['newer_versions_discarded'], 2)
        self.assertIn('discards 2 newer', old['restore_warning']['message'])
        latest = cw.propose_restore(self.root, {'workspace_id': sid, 'relative_paths': [relative], 'checkpoint_sha256': shas[2]})
        self.assertEqual(latest['restore_warning']['newer_versions_discarded'], 0)

    @unittest.skipUnless(toolchain(), 'Pinned Lua sandbox required')
    def test_applied_scaffold_parses_and_passes_constructor_checks_only(self):
        sid, target, relative = self.fixture()
        result = scaffold(self.root, {'workspace_id': sid, 'contract_id': 'predator-controller-v1'})
        self.assertEqual(result['lua_syntax'], {'checked': True, 'remaining_syntax_errors': []})
        cw.apply(self.root, {'workspace_id': sid, 'proposal_id': result['proposal_id']})
        tested = cw.test(self.root, {'workspace_id': sid, 'profile': 'lua'})
        counts = tested['acceptance']['contracts'][0]['counts']
        self.assertEqual(counts['checks'], 48)
        self.assertEqual(counts['failures'], 40)
        self.assertIn('not_implemented', tested['diagnostic']['failed_checks'][0])


if __name__ == '__main__': unittest.main()
