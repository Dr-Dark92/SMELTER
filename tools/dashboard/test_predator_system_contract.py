"""Passive lifecycle contract: satisfiable reference and rejected regressions."""
import unittest
import re

import acceptance_contracts as acceptance
import coding_workspace as cw
import test_acceptance_contracts as fixtures
import test_provider_admission as provider
from test_lua_profile import toolchain

REFERENCE = r'''
local A = require("engine_adapter")
local C = require("predator_controller")
local P = require("entity_policy")
local M = {}
function M.new(d)
  if type(d) ~= "table" then return nil,"deps_required" end
  local p = d.adapter
  if p == nil then p = d.runtime end
  local a, why = A.new(p)
  if not a then return nil,why end
  local function make()
    return C.new({adapter=a,evaluate=P.evaluate,clock=d.clock,profile=d.profile,policy=d.policy})
  end
  local validated, err = make()
  if not validated then return nil,err end
  local actors = {}
  local s = {}
  function s:add_actor(id)
    if type(id) ~= "string" or id == "" then return nil,"invalid_actor" end
    if actors[id] then return nil,"already_registered" end
    local c, e = make()
    if not c then return nil,e end
    actors[id] = c
    return true
  end
  function s:remove_actor(id)
    if not actors[id] then return nil,"unknown_actor" end
    local ok, value, reason = pcall(a.stop,id)
    if not ok then return nil,"adapter_error:"..tostring(value) end
    if not value then return nil,"adapter_refused:"..tostring(reason) end
    actors[id] = nil
    return true
  end
  function s:tick()
    local results = {}
    for id,c in pairs(actors) do
      local ok, value = pcall(c.update,c,id)
      if ok and type(value)=="table" then results[id]=value
      else results[id]={action="error",reason="controller_error:"..tostring(value)} end
    end
    return results
  end
  return s
end
return M
'''


@unittest.skipUnless(toolchain(), 'Pinned Lua sandbox required')
class PredatorSystemContractTests(unittest.TestCase):
    setUp = fixtures.AcceptanceTests.setUp
    tearDown = fixtures.AcceptanceTests.tearDown
    prepare = fixtures.AcceptanceTests.prepare

    def fixture(self):
        relative = 'mods/demo/Scripts/system.lua'
        base = self.root / 'mods/demo/Scripts'
        base.mkdir(parents=True)
        for name, source in {'system.lua':REFERENCE, 'engine_adapter.lua':provider.REFERENCE,
                             'predator_controller.lua':fixtures.CONTROLLER, 'entity_policy.lua':fixtures.COMPLIANT}.items():
            (base/name).write_text(source, encoding='utf-8')
        tests = self.root / 'mods/demo/tests'
        tests.mkdir()
        (tests/'test_load.lua').write_text('assert(true)\n', encoding='utf-8')
        sid, target = self.prepare()
        acceptance.register(self.root, sid, 'predator-system-v1', relative)
        return sid, target, relative

    def execute(self, sid, target, relative, source):
        (target/relative).write_text(source, encoding='utf-8')
        r = acceptance.run(self.root, target, acceptance.load(self.root,sid,target),
                           {relative:cw.digest((target/relative).read_bytes())})
        r.pop('_raw_output', None)
        return r

    def test_reference_passes_and_absent_constructor_is_counted_red(self):
        sid, target, relative = self.fixture()
        r = self.execute(sid,target,relative,REFERENCE)
        self.assertEqual(r['stage'],'GREEN',r.get('log_tail'))
        self.assertEqual(r['contracts'][0]['counts'],{'checks':20,'failures':0})
        r = self.execute(sid,target,relative,'return {}\n')
        self.assertEqual(r['stage'],'RED')
        self.assertEqual(r['contracts'][0]['counts'],{'checks':20,'failures':20})

    def test_rejects_false_removal_stale_state_policy_bypass_and_hidden_fallback(self):
        sid, target, relative = self.fixture()
        mutants = {
            'false_removal':REFERENCE.replace('    local ok, value, reason = pcall(a.stop,id)','    if true then return true end\n    local ok, value, reason = pcall(a.stop,id)'),
            'stale_cooldown':REFERENCE.replace('    local c, e = make()','    local c, e = validated, nil'),
            'bypassed_policy':REFERENCE.replace('evaluate=P.evaluate','evaluate=function() return true,"allowed" end'),
            'hidden_fallback':REFERENCE.replace('local p = d.adapter\n  if p == nil then p = d.runtime end','local p = d.adapter or d.runtime'),
        }
        for name, source in mutants.items():
            with self.subTest(mutant=name):
                self.assertNotEqual(source,REFERENCE)
                r = self.execute(sid,target,relative,source)
                self.assertEqual(r['stage'],'RED',r.get('log_tail'))
                self.assertEqual(r['contracts'][0]['counts']['checks'],20)
                self.assertGreater(r['contracts'][0]['counts']['failures'],0)

    def test_scaffold_has_valid_constructor_and_is_completable(self):
        from contract_scaffold import render
        sid,target,relative = self.fixture()
        spec = acceptance.DEFINITIONS['predator-system-v1']['scaffold']
        source = render('predator-system-v1',spec)
        self.assertIn('function controller:add_actor(id)',source)
        self.assertIn('local state = {}',source.split('function M.new')[1])
        result = self.execute(sid,target,relative,source)
        self.assertEqual(result['stage'],'RED',result.get('log_tail'))
        self.assertEqual(result['contracts'][0]['counts'],{'checks':20,'failures':11})
        # Complete only the three declared method stubs using the disposable
        # reference, proving the scaffold does not hide missing plumbing.
        for method in spec['methods']:
            name = method['name']
            block = re.search(r'^  function s:'+name+r'\([^\n]*\)\n.*?^  end',REFERENCE,re.M|re.S)
            self.assertIsNotNone(block)
            filled = block.group().replace('function s:','function controller:').replace('actors','state').replace('make()','make_controller()').replace('pcall(a.stop','pcall(adapter.stop')
            pattern = r'^  function controller:'+name+r'\([^\n]*\)\n.*?^  end'
            source,count = re.subn(pattern,lambda _:filled,source,count=1,flags=re.M|re.S)
            self.assertEqual(count,1)
        result = self.execute(sid,target,relative,source)
        self.assertEqual(result['stage'],'GREEN',result.get('log_tail'))
        self.assertEqual(result['contracts'][0]['counts'],{'checks':20,'failures':0})


if __name__ == '__main__':
    unittest.main()
