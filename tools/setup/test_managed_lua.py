"""Real Lua 5.4 bridge tests in isolated reviewed fixtures; never a game/plugin."""
import json
import os
from pathlib import Path
import tempfile
import unittest

import check_managed_lua as bridge


@unittest.skipUnless(os.name == 'nt' and (bridge.ROOT / '.smelter/tooling/keralua-sdk/1.4.11/KeraLua.dll').is_file(),
                     'Pinned KeraLua development cache and Windows compiler required')
class ManagedLuaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='smelter-managed-lua-')
        cls.folder = Path(cls.temp.name) / 'fixture'
        cls.receipt = bridge.prepare(bridge.ROOT, cls.folder, bridge.ROOT)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_real_controller_uses_all_six_managed_callbacks_and_real_policy(self):
        result = bridge.execute(self.folder, 'gameplay')
        self.assertEqual(result['exit_code'], 0, result['output'])
        self.assertIn('MANAGED_GAMEPLAY_BRIDGE_OK', result['output'])

    def test_import_access_data_thread_and_stack_boundaries(self):
        result = bridge.execute(self.folder, 'boundaries')
        self.assertEqual(result['exit_code'], 0, result['output'])
        self.assertIn('MANAGED_HOST_BOUNDARIES_OK', result['output'])

    def test_callback_lua_and_budget_failures_remain_explicit(self):
        result = bridge.execute(self.folder, 'failures')
        self.assertEqual(result['exit_code'], 0, result['output'])
        self.assertIn('MANAGED_HOST_FAILURES_OK', result['output'])

    def test_all_four_frozen_verifiers_run_unchanged_on_lua54(self):
        result = bridge.execute(self.folder, 'contracts')
        self.assertEqual(result['exit_code'], 0, result['output'])
        self.assertIn('MANAGED_FROZEN_CONTRACTS_OK 128', result['output'])
        self.assertEqual(result['output'].count('[ACCEPTANCE PASS]'), 128)
        self.assertNotIn('[ACCEPTANCE FAIL]', result['output'])
        for subject, identity in bridge.SUBJECTS.items():
            name = bridge.acceptance.DEFINITIONS[identity]['verifier']
            self.assertEqual(bridge.digest(self.folder / 'contracts' / name),
                             bridge.digest(bridge.ROOT / 'tools/dashboard/acceptance' / name))

    def test_missing_attack_mutant_is_rejected_by_the_same_verifiers(self):
        mutated = bridge.mutant_snapshot(self.folder)
        result = bridge.execute(self.folder, 'contracts', mutated)
        self.assertNotEqual(result['exit_code'], 0)
        self.assertIn('[ACCEPTANCE FAIL]', result['output'])
        self.assertIn('acceptance_exit:1', result['output'])

    def test_native_dependency_is_pinned_and_rph_is_never_loaded(self):
        self.assertEqual(self.receipt['sdk']['version'], '1.4.11')
        self.assertFalse(self.receipt['rph_loaded'])
        self.assertFalse(self.receipt['game_runtime_verified'])
        self.assertEqual(set(self.receipt['runtime_files']), {'KeraLua.dll', 'lua54.dll', 'LICENSE'})
        self.assertFalse((self.folder / 'RagePluginHook.dll').exists())
        for name, digest in self.receipt['runtime_files'].items():
            self.assertEqual(bridge.digest(self.folder / name), digest)

    def test_fixture_dispatch_and_snapshot_destination_are_bounded(self):
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            bridge.execute(self.folder, 'arbitrary-command')
        with self.assertRaisesRegex(ValueError, 'new fixture output'):
            bridge.prepare(bridge.ROOT, self.folder, bridge.ROOT)


if __name__ == '__main__':
    unittest.main()
