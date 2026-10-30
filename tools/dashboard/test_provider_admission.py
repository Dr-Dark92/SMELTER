"""Prove admission checks with a disposable reference and meaningful regressions."""
import unittest

import acceptance_contracts as acceptance
import coding_workspace as cw
import test_acceptance_contracts as fixtures
from test_lua_profile import toolchain

# Satisfiable operator fixture only. Never copied to a mod or coding subject.
REFERENCE = r'''
local M = {}
local mode = "uninitialized"
local CAPS = {"position", "describe", "candidates", "move_to", "attack", "stop"}
function M.new(p)
  if type(p) ~= "table" then return nil, "unsupported_runtime" end
  for _, k in ipairs(CAPS) do
    if type(p[k]) ~= "function" then return nil, "unsupported_capability:" .. k end
  end
  return p
end
function M.get_adapter_type() return mode end
local function init(p, label)
  mode = "uninitialized"
  local a, why = M.new(p)
  if not a then return nil, why end
  mode = label
  return a
end
function M.init_simulation(p) return init(p, "simulation") end
function M.init_real_game(p) return init(p, "provider") end
function M.spawn_raptor() return nil, "unsupported_capability:spawn" end
return M
'''


@unittest.skipUnless(toolchain(), 'Pinned Lua sandbox required')
class ProviderAdmissionTests(unittest.TestCase):
    setUp = fixtures.AcceptanceTests.setUp
    tearDown = fixtures.AcceptanceTests.tearDown
    prepare = fixtures.AcceptanceTests.prepare

    def fixture(self):
        relative = 'mods/demo/Scripts/provider.lua'
        path = self.root / relative
        path.parent.mkdir(parents=True)
        path.write_text(REFERENCE, encoding='utf-8')
        tests = self.root / 'mods/demo/tests'
        tests.mkdir()
        (tests / 'test_load.lua').write_text('assert(true)\n', encoding='utf-8')
        sid, target = self.prepare()
        acceptance.register(self.root, sid, 'provider-admission-v1', relative)
        return sid, target, relative

    def run_subject(self, sid, target, relative, source):
        (target / relative).write_text(source, encoding='utf-8')
        expected = {relative: cw.digest((target / relative).read_bytes())}
        result = acceptance.run(self.root, target, acceptance.load(self.root, sid, target), expected)
        result.pop('_raw_output', None)
        return result

    def test_reference_is_satisfiable_and_missing_module_is_counted_red(self):
        sid, target, relative = self.fixture()
        result = cw.test(self.root, {'workspace_id':sid, 'profile':'lua'})
        self.assertEqual(result['stage'], 'GREEN', result.get('log_tail'))
        self.assertEqual(result['acceptance']['contracts'][0]['counts'], {'checks':26, 'failures':0})
        missing = self.run_subject(sid, target, relative, 'return {}\n')
        self.assertEqual(missing['stage'], 'RED')
        self.assertEqual(missing['contracts'][0]['counts'], {'checks':26, 'failures':26})

    def test_contract_rejects_data_loss_false_success_and_implicit_modes(self):
        sid, target, relative = self.fixture()
        wrapper = '''local a = {}
  for k, f in pairs(p) do a[k] = f end
  %s
  return a'''
        mutants = {
            'wrapped_position': REFERENCE.replace('  return p\n', '  ' + wrapper % 'a.position = function(id) return {position=p.position(id)} end' + '\n'),
            'wrapped_candidates': REFERENCE.replace('  return p\n', '  ' + wrapper % 'a.candidates = function(...) return {cand=p.candidates(...)} end' + '\n'),
            'swallowed_refusal': REFERENCE.replace('  return p\n', '  ' + wrapper % 'a.attack = function(...) pcall(p.attack, ...); return true end' + '\n'),
            'scalar_panic': REFERENCE.replace('if type(p) ~= "table"', 'if p == nil'),
            'wrong_missing_reason': REFERENCE.replace('"unsupported_capability:" .. k', '"unsupported_runtime"'),
            'implicit_simulation': REFERENCE.replace('function M.init_simulation(p) return init(p, "simulation") end', 'function M.init_simulation(p) mode="simulation"; return p or {} end'),
            'always_refused_real': REFERENCE.replace('function M.init_real_game(p) return init(p, "provider") end', 'function M.init_real_game(p) mode="uninitialized"; return nil,"unsupported_runtime" end'),
            'fake_spawn': REFERENCE.replace('function M.spawn_raptor() return nil, "unsupported_capability:spawn" end', 'function M.spawn_raptor() return true end'),
        }
        for name, source in mutants.items():
            with self.subTest(mutant=name):
                self.assertNotEqual(source, REFERENCE)
                result = self.run_subject(sid, target, relative, source)
                self.assertEqual(result['stage'], 'RED', result)
                counts = result['contracts'][0]['counts']
                self.assertEqual(counts['checks'], 26)
                self.assertGreater(counts['failures'], 0)


if __name__ == '__main__':
    unittest.main()
