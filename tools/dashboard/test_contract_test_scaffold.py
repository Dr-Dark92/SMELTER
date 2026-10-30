"""Contract-derived editable tests stay scoped, hash-pinned and reviewable."""
import unittest
from unittest.mock import patch

import acceptance_contracts as acceptance
import coding_workspace as cw
import contract_test_scaffold as scaffold
import test_provider_admission as provider
from test_lua_profile import toolchain


class ContractTestScaffoldTests(unittest.TestCase):
    setUp = provider.ProviderAdmissionTests.setUp
    tearDown = provider.ProviderAdmissionTests.tearDown
    prepare = provider.ProviderAdmissionTests.prepare
    fixture = provider.ProviderAdmissionTests.fixture

    def test_proposal_preserves_files_and_binds_exact_registered_source(self):
        sid, target, subject = self.fixture()
        path = target / 'mods/demo/tests/test_load.lua'
        before = path.read_bytes()
        with patch.object(cw, '_lua_gate'):
            result = scaffold.propose(self.root, sid, 'provider-admission-v1', 'mods/demo/tests/test_load.lua')
        self.assertFalse(result['applied'])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(result['checks'], 26)
        _, proposal = cw.proposal(self.root, sid, result['proposal_id'])
        change = proposal['changes'][0]
        self.assertEqual(change['expected_sha256'], cw.digest(before))
        self.assertIn('local arg = {"Scripts/provider.lua"}', change['content'])
        self.assertIn(result['verifier_sha256'], change['content'])
        self.assertTrue(change['content'].endswith(acceptance.verifier_path('provider-admission-v1').read_text(encoding='utf-8')))

    def test_unregistered_contract_or_cross_project_destination_rejects(self):
        sid, _, _ = self.fixture()
        for identity, dest in [('unknown','mods/demo/tests/test_x.lua'),
                               ('provider-admission-v1','mods/other/tests/test_x.lua'),
                               ('provider-admission-v1','mods/demo/Scripts/provider.lua'),
                               ('provider-admission-v1','mods/demo/tests/helper.lua')]:
            with self.subTest(identity=identity, destination=dest), self.assertRaises(ValueError):
                scaffold.propose(self.root, sid, identity, dest)

    def test_verifier_change_rejects_before_proposal(self):
        import json
        sid, _, _ = self.fixture()
        path = acceptance._config(self.root, sid)
        value = json.loads(path.read_text(encoding='utf-8'))
        value['contracts'][0]['verifier_sha256'] = '0' * 64
        path.write_text(json.dumps(value), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'verifier changed'):
            scaffold.propose(self.root, sid, 'provider-admission-v1', 'mods/demo/tests/test_x.lua')

    @unittest.skipUnless(toolchain(), 'Pinned Lua sandbox required')
    def test_generated_fixture_runs_real_subject_and_detects_refusal_mutant(self):
        sid, target, subject = self.fixture()
        dest = 'mods/demo/tests/test_provider.lua'
        proposed = scaffold.propose(self.root, sid, 'provider-admission-v1', dest)
        cw.apply(self.root, {'workspace_id':sid, 'proposal_id':proposed['proposal_id']})
        result = cw.test(self.root, {'workspace_id':sid, 'profile':'lua'})
        self.assertEqual(result['stage'], 'GREEN', result.get('log_tail'))
        original = (target / subject).read_text(encoding='utf-8')
        changed = original.replace('  return p\n', '''  local a = {}
  for k, f in pairs(p) do a[k] = f end
  a.stop = function(...) p.stop(...); return true end
  return a
''')
        self.assertNotEqual(changed, original)
        (target / subject).write_text(changed, encoding='utf-8')
        result = cw.test(self.root, {'workspace_id':sid, 'profile':'lua'})
        self.assertEqual(result['stage'], 'RED', result.get('log_tail'))
        self.assertEqual(result['workspace_tests_stage'], 'RED')
        self.assertEqual(result['acceptance']['stage'], 'RED')
        self.assertGreater(result['acceptance']['contracts'][0]['counts']['failures'], 0)


if __name__ == '__main__':
    unittest.main()
