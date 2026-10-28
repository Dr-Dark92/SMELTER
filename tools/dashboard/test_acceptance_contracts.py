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
    def test_verifier_subject_identity_mismatch_and_missing_subject_are_errors(self):
        sid,target,relative=self.fixture();contracts=acceptance.load(self.root,sid,target)
        result=acceptance.run(self.root,target,contracts,{relative:'0'*64});result.pop('_raw_output')
        self.assertEqual(result['stage'],'ERROR')
        (target/relative).unlink()
        result=acceptance.run(self.root,target,contracts,{});result.pop('_raw_output')
        self.assertEqual(result['stage'],'ERROR')


if __name__=='__main__':unittest.main()
