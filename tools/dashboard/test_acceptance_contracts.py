"""Frozen-check identity, independent execution, bypass and regression controls."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import acceptance_contracts as acceptance
import sandbox
import coding_workspace as cw
from python_tools import ToolSession
import test_coding_workspace as base_tests
from test_lua_profile import toolchain

COMPLIANT=r'''
local M={}
local function map(t)
 if type(t)~='table' then return false end
 for k,v in pairs(t) do if type(k)~='string' or type(v)~='boolean' then return false end end
 return true
end
function M.evaluate(e,p)
 if type(e)~='table' or type(e.id)~='string' or type(e.kind)~='string' or not map(e.traits) then return false,'entity_invalid' end
 if type(p)~='table' or not map(p.allowed_kinds) then return false,'policy_invalid' end
 for _,key in ipairs({'blocked_kinds','required_traits','any_traits'}) do if p[key]~=nil and not map(p[key]) then return false,'policy_invalid' end end
 if e.valid~=true or e.alive~=true then return false,'inactive' end
 if p.blocked_kinds and p.blocked_kinds[e.kind]==true or p.allowed_kinds[e.kind]~=true then return false,'kind' end
 for key,value in pairs(p.required_traits or {}) do if value and e.traits[key]~=true then return false,'required' end end
 if p.any_traits~=nil then
  local matched=false
  for key,value in pairs(p.any_traits) do if value and e.traits[key]==true then matched=true end end
  if not matched then return false,'any' end
 end
 return true,'allowed'
end
return M
'''

# Satisfiable reference for predator-controller-v1; a test fixture, not mod source.
CONTROLLER=r'''
local M = {}
local CAPS = {"position", "describe", "candidates", "move_to", "attack", "stop"}
local function finite(n) return type(n) == "number" and n == n and n ~= math.huge and n ~= -math.huge end
local function pos_ok(p) return type(p) == "table" and finite(p.x) and finite(p.y) and finite(p.z) end
local function dist(a, b) local dx, dy, dz = a.x - b.x, a.y - b.y, a.z - b.z; return math.sqrt(dx*dx + dy*dy + dz*dz) end

function M.new(d)
  if type(d) ~= "table" or type(d.adapter) ~= "table" then return nil, "adapter_required" end
  for _, c in ipairs(CAPS) do if type(d.adapter[c]) ~= "function" then return nil, "unsupported_capability:" .. c end end
  if type(d.evaluate) ~= "function" then return nil, "evaluate_required" end
  if type(d.clock) ~= "function" then return nil, "clock_required" end
  if type(d.policy) ~= "table" then return nil, "policy_required" end
  local p = d.profile
  if type(p) ~= "table" then return nil, "profile_required" end
  for _, k in ipairs({"detect_radius", "attack_radius", "lose_radius", "attack_cooldown"}) do
    if not finite(p[k]) or p[k] < 0 then return nil, "profile_invalid:" .. k end
  end
  if not (p.attack_radius <= p.detect_radius and p.detect_radius <= p.lose_radius) then return nil, "profile_radius_order" end
  local a, states = d.adapter, {}
  local function call(name, ...)
    local okc, res, err = pcall(a[name], ...)
    if not okc then return false, "adapter_error:" .. name end
    if not res then return false, "adapter_refused:" .. name .. ":" .. tostring(err) end
    return true
  end
  local function eligible(e, actor, origin, radius)
    if type(e) ~= "table" or e.id == actor or not pos_ok(e.position) then return nil end
    local okv, allowed = pcall(d.evaluate, e, d.policy)
    if not okv or allowed ~= true then return nil end
    local r = dist(origin, e.position)
    if r > radius then return nil end
    return r
  end
  local c = {}
  function c:update(actor)
    local s = states[actor] or {}; states[actor] = s
    local okp, origin = pcall(a.position, actor)
    if not okp or not pos_ok(origin) then return {action = "error", reason = "actor_position_unavailable"} end
    local r
    if s.target then
      local okd, e = pcall(a.describe, s.target)
      r = okd and eligible(e, actor, origin, p.lose_radius)
      if not r then
        local lost = s.target; s.target, s.moving = nil, false
        local okstop, why = call("stop", actor)
        return {action = okstop and "lost" or "error", target_id = lost, reason = okstop and "target_lost" or why}
      end
    else
      local okc, list = pcall(a.candidates, actor, origin, p.detect_radius)
      if not okc or type(list) ~= "table" then return {action = "error", reason = "candidates_failed"} end
      local best, bestr
      for _, e in ipairs(list) do
        local er = eligible(e, actor, origin, p.detect_radius)
        if er and (not bestr or er < bestr or (er == bestr and e.id < best)) then best, bestr = e.id, er end
      end
      if not best then return {action = "idle", reason = "no_eligible_target"} end
      s.target, s.moving, r = best, false, bestr
    end
    local t = s.target
    if r > p.attack_radius then
      if s.moving then return {action = "move", target_id = t, issued = false, reason = "chasing"} end
      local okm, why = call("move_to", actor, t)
      if not okm then return {action = "error", target_id = t, reason = why} end
      s.moving = true
      return {action = "move", target_id = t, issued = true, reason = "chase_started"}
    end
    local now = d.clock()
    if s.last_attack and now - s.last_attack < p.attack_cooldown then
      return {action = "wait", target_id = t, reason = "cooldown"}
    end
    local oka, why = call("attack", actor, t)
    if not oka then return {action = "error", target_id = t, reason = why} end
    s.last_attack, s.moving = now, false
    return {action = "attack", target_id = t, reason = "attacked"}
  end
  return c
end
return M
'''


class AcceptanceTests(unittest.TestCase):
    def setUp(self):
        base_tests.CodingWorkspaceTests.setUp(self)
        ready=toolchain()
        if ready:
            configured=patch('sandbox.config',return_value={**sandbox.DEFAULT,**ready['configured']})
            configured.start();self.addCleanup(configured.stop)
    def tearDown(self):base_tests.CodingWorkspaceTests.tearDown(self)
    prepare=base_tests.CodingWorkspaceTests.prepare

    def fixture(self,subject=COMPLIANT):
        relative='mods/demo/Scripts/policy.lua';path=self.root/relative;path.parent.mkdir(parents=True)
        path.write_text(subject,encoding='utf-8')
        tests=self.root/'mods/demo/tests';tests.mkdir()
        (tests/'test_print_only.lua').write_text('print("editable suite says GREEN")\n',encoding='utf-8')
        sid,target=self.prepare();acceptance.register(self.root,sid,'entity-policy-v1',relative)
        return sid,target,relative

    def test_registry_is_operator_only_and_marks_old_green_receipts_stale(self):
        sid,target,relative=self.fixture()
        contracts=acceptance.load(self.root,sid,target)
        self.assertFalse(acceptance.fresh(self.root,sid,target,'lua',{}))
        self.assertTrue(acceptance.fresh(self.root,sid,target,'lua',{'acceptance_revision':acceptance.revision(contracts)}))
        names=[t['function']['name'] for t in ToolSession(self.root,{'coding_workspace':True}).tools]
        self.assertNotIn('register_acceptance',names)
        context=cw.context(self.root,{'workspace_id':sid})
        self.assertFalse(context['acceptance_contracts'][0]['model_editable'])
        with self.assertRaises(ValueError):cw.relative_path('.smelter/acceptance.json',edit=True)
        with self.assertRaisesRegex(ValueError,'already registered'):acceptance.register(self.root,sid,'entity-policy-v1',relative)

    def test_registry_tampering_and_verifier_revision_changes_fail_closed(self):
        sid,target,_=self.fixture();path=acceptance._config(self.root,sid)
        original=path.read_bytes();value=json.loads(original);value['workspace_id']='different'
        path.write_text(json.dumps(value),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'ownership'):acceptance.load(self.root,sid,target)
        path.write_bytes(original);value=json.loads(original);value['contracts'][0]['verifier_sha256']='0'*64
        path.write_text(json.dumps(value),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'verifier changed'):acceptance.load(self.root,sid,target)

    def test_frozen_failure_is_a_native_mcp_failure_signal_but_tdd_red_stays_evidence(self):
        from tool_contract import result_failed
        self.assertTrue(result_failed({'status':'coding_tests_failed','stage':'RED','acceptance':{'stage':'RED'}}))
        self.assertFalse(result_failed({'status':'coding_tests_failed','stage':'RED'}))

    @unittest.skipUnless(toolchain(),'Pinned Lua sandbox required')
    def test_controller_gate_rejects_regression_despite_green_editable_tests(self):
        sid,target,relative=self.fixture("return {evaluate=function() return true,'allowed' end}\n")
        before=(target/relative).read_bytes()
        result=cw.test(self.root,{'workspace_id':sid,'profile':'lua'})
        self.assertEqual(result['workspace_tests_stage'],'GREEN')
        self.assertEqual(result['stage'],'RED')
        self.assertEqual(result['acceptance']['stage'],'RED')
        self.assertGreater(result['acceptance']['contracts'][0]['counts']['failures'],0)
        self.assertEqual((target/relative).read_bytes(),before)
        self.assertEqual(result['diagnostic']['classification'],'acceptance_failure')
        session=ToolSession(self.root,{'coding_workspace':True})
        session.events=[{'tool':'run_coding_tests','result':result,'reused':False}]
        self.assertIn('Editable tests: GREEN | Frozen acceptance: RED | Overall: RED',session.receipt())
        from coding_finish import finish
        with self.assertRaises(ValueError):finish(self.root,{'workspace_id':sid,'outcome':'GREEN','profiles':['lua']})
        self.assertEqual(finish(self.root,{'workspace_id':sid,'outcome':'RED','profiles':['lua']})['status'],'coding_task_end_flag')

    @unittest.skipUnless(toolchain(),'Pinned Lua sandbox required')
    def test_compliant_subject_passes_and_copy_verifier_edits_do_not_change_controller(self):
        sid,target,relative=self.fixture()
        copied=target/'tools/dashboard/acceptance/entity_policy_v1.lua';copied.parent.mkdir(parents=True)
        copied.write_text('print("forged success")\n',encoding='utf-8')
        result=cw.test(self.root,{'workspace_id':sid,'profile':'lua'})
        self.assertEqual(result['stage'],'GREEN',result.get('log_tail'))
        item=result['acceptance']['contracts'][0]
        self.assertEqual(item['counts'],{'checks':30,'failures':0})
        self.assertEqual(item['subject_sha256'],cw.digest((target/relative).read_bytes()))
        self.assertEqual(item['verifier_sha256'],cw.digest(acceptance.verifier_path('entity-policy-v1').read_bytes()))

    @unittest.skipUnless(toolchain(),'Pinned Lua sandbox required')
    def test_predator_controller_contract_accepts_reference_and_rejects_state_only_controller(self):
        relative='mods/demo/Scripts/controller.lua';path=self.root/relative;path.parent.mkdir(parents=True)
        path.write_text(CONTROLLER,encoding='utf-8')
        tests=self.root/'mods/demo/tests';tests.mkdir()
        (tests/'test_print_only.lua').write_text('print("editable suite says GREEN")\n',encoding='utf-8')
        sid,target=self.prepare();acceptance.register(self.root,sid,'predator-controller-v1',relative)
        result=cw.test(self.root,{'workspace_id':sid,'profile':'lua'})
        self.assertEqual(result['stage'],'GREEN',result.get('log_tail'))
        self.assertEqual(result['acceptance']['contracts'][0]['counts'],{'checks':52,'failures':0})
        # A controller that only mutates state (no adapter commands) cannot pass.
        state_only=CONTROLLER.replace('local okm, why = call("move_to", actor, t)','local okm, why = true, nil')
        contracts=acceptance.load(self.root,sid,target);(target/relative).write_text(state_only,encoding='utf-8')
        ran=acceptance.run(self.root,target,contracts,{relative:cw.digest((target/relative).read_bytes())});ran.pop('_raw_output')
        self.assertEqual(ran['stage'],'RED')
        self.assertGreater(ran['contracts'][0]['counts']['failures'],0)
        # A module without new(deps) is a counted RED, not a count-mismatch ERROR.
        (target/relative).write_bytes(b'return {}\n')
        ran=acceptance.run(self.root,target,contracts,{relative:cw.digest(b'return {}\n')});ran.pop('_raw_output')
        self.assertEqual(ran['stage'],'RED')
        self.assertEqual(ran['contracts'][0]['counts'],{'checks':52,'failures':52})

    def predator_fixture(self,subject=None):
        relative='mods/demo/Scripts/controller.lua';path=self.root/relative;path.parent.mkdir(parents=True)
        path.write_text(CONTROLLER if subject is None else subject,encoding='utf-8')
        tests=self.root/'mods/demo/tests';tests.mkdir()
        (tests/'test_print_only.lua').write_text('print("editable suite says GREEN")\n',encoding='utf-8')
        sid,target=self.prepare();acceptance.register(self.root,sid,'predator-controller-v1',relative)
        return sid,target,relative

    @unittest.skipUnless(toolchain(),'Pinned Lua sandbox required')
    def test_redundant_describe_mutant_cannot_attack_without_verified_range(self):
        # Reproduce the reviewed regression without touching the saved mod copy.
        mutant=CONTROLLER.replace('    local t = s.target', '''    local okagain, again = pcall(a.describe, s.target)
    r = okagain and eligible(again, actor, origin, p.lose_radius) or nil
    local t = s.target''').replace('    if r > p.attack_radius then','    if type(r) == "number" and r > p.attack_radius then')
        self.assertNotEqual(mutant,CONTROLLER)
        sid,target,relative=self.predator_fixture(mutant)
        contracts=acceptance.load(self.root,sid,target)
        ran=acceptance.run(self.root,target,contracts,{relative:cw.digest((target/relative).read_bytes())})
        self.assertEqual(ran['stage'],'RED',ran.get('log_tail'))
        item=ran['contracts'][0]
        self.assertEqual(item['counts'],{'checks':52,'failures':4})
        self.assertTrue(all('verified range' in name for name in item['failed_checks']))

    def test_summary_carries_interface_checklist_for_contracts_that_define_one(self):
        sid,target,_=self.predator_fixture()
        item=acceptance.summary(acceptance.load(self.root,sid,target))[0]
        self.assertTrue(any('candidates(actor_id, origin, radius)' in line for line in item['interface']))
        self.assertNotIn('interface',acceptance.summary([{'id':'entity-policy-v1','profile':'lua','subject_path':'x','verifier_sha256':'0'}])[0])

    def test_operator_migration_repins_verifier_logs_reason_and_refuses_noop(self):
        sid,target,relative=self.predator_fixture();path=acceptance._config(self.root,sid)
        value=json.loads(path.read_text(encoding='utf-8'));value['contracts'][0]['verifier_sha256']='a'*64
        path.write_text(json.dumps(value),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'verifier changed'):acceptance.load(self.root,sid,target)
        with self.assertRaisesRegex(ValueError,'review reason'):acceptance.migrate(self.root,sid,'predator-controller-v1','short')
        with self.assertRaisesRegex(ValueError,'not registered'):acceptance.migrate(self.root,sid,'entity-policy-v1','reviewed verifier update')
        result=acceptance.migrate(self.root,sid,'predator-controller-v1','reviewed observed-value output')
        self.assertEqual(result['migrated']['from_verifier_sha256'],'a'*64)
        self.assertEqual(acceptance.load(self.root,sid,target)[0]['subject_path'],relative)
        log=(path.parent/'acceptance-migrations.jsonl').read_text(encoding='utf-8').splitlines()
        self.assertEqual(json.loads(log[0])['reason'],'reviewed observed-value output')
        with self.assertRaisesRegex(ValueError,'unchanged'):acceptance.migrate(self.root,sid,'predator-controller-v1','reviewed again later')
        names=[t['function']['name'] for t in ToolSession(self.root,{'coding_workspace':True}).tools]
        self.assertFalse(any('migrat' in n or 'register' in n for n in names))

    @unittest.skipUnless(toolchain(),'Pinned Lua sandbox required')
    def test_broken_editable_test_cannot_hide_frozen_failures_or_contract_text(self):
        sid,target,relative=self.predator_fixture("local M={}\nfunction M.new(d) return require('x') end\nreturn M\n")
        (target/'mods/demo/tests/test_broken.lua').write_text('do if x then end\n',encoding='utf-8')
        result=cw.test(self.root,{'workspace_id':sid,'profile':'lua'})
        self.assertEqual(result['stage'],'ERROR')
        detail=result['diagnostic']
        self.assertEqual(detail['classification'],'acceptance_failure')
        self.assertEqual(detail['failed_total'],52)
        self.assertIn("observed: raised:",detail['failed_checks'][0])
        self.assertIn('require',detail['failed_checks'][0])
        self.assertEqual(detail['workspace_diagnostic']['classification'],'test_failure')
        self.assertEqual([c['id'] for c in detail['failing_contracts']],['predator-controller-v1'])
        self.assertIn('interface',detail['failing_contracts'][0])
        item=result['acceptance']['contracts'][0]
        self.assertEqual(item['failed_total'],52);self.assertEqual(len(item['failed_checks']),8)
        from coding_recovery import recover
        context=recover(self.root,{'workspace_id':sid})
        lua=[t for t in context['tests'] if t['profile']=='lua'][0]
        self.assertEqual(lua['diagnostic']['failing_contracts'][0]['id'],'predator-controller-v1')

    @unittest.skipUnless(toolchain(),'Pinned Lua sandbox required')
    def test_verifier_subject_identity_mismatch_and_missing_subject_are_errors(self):
        sid,target,relative=self.fixture();contracts=acceptance.load(self.root,sid,target)
        result=acceptance.run(self.root,target,contracts,{relative:'0'*64});result.pop('_raw_output')
        self.assertEqual(result['stage'],'ERROR')
        (target/relative).unlink()
        result=acceptance.run(self.root,target,contracts,{});result.pop('_raw_output')
        self.assertEqual(result['stage'],'ERROR')


if __name__=='__main__':unittest.main()
