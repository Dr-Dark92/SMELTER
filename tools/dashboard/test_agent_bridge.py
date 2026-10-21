import hashlib
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_bridge import AgentBridge
from chat_jobs import ChatCancelled, Control, Jobs
from chats import create_chat, read_chat
from database import select_database
from mcp_connections import sdk_status
from opencode_runtime import ask, session_rules
from test_opencode_runtime import Fixture


class BridgeTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.base=Path(tmp.name);self.root=self.base/'SMELTER';self.root.mkdir()
        self.target=self.base/'SMELTERV2';self.target.mkdir()
        select_database(self.root,str(self.base/'data'))
        self.cid=create_chat(self.root,'Bridge test')['id']
        folder=self.root/'skills/documentation';folder.mkdir(parents=True)
        self.reference='# Documentation\n\n## Purpose\nUse verified receipts. BRIDGE_REFERENCE_MARKER\n'
        (folder/'SKILL.md').write_text(self.reference,encoding='utf-8')

    def bridge(self,**kwargs):
        with patch('mcp_connections.sdk_status',return_value={'status':'installed'}):
            return AgentBridge(self.root,self.cid,'Write a report',**kwargs)

    def test_actual_selected_instruction_snapshot_and_no_implied_tools(self):
        bridge=self.bridge(skills=['documentation'])
        self.assertIn('BRIDGE_REFERENCE_MARKER',bridge.instructions())
        self.assertEqual(bridge.summary()['skills'][0]['sha256'],hashlib.sha256(self.reference.encode()).hexdigest())
        self.assertEqual(bridge.tools,[])
        result=bridge.call('write_diagnostic_markdown',{'filename':'denied.md','content':'Denied'})
        self.assertTrue(result['isError'])
        self.assertFalse((self.root/'diagnostics/denied.md').exists())

    def test_auto_selection_and_explicit_selection_share_context(self):
        self.assertEqual(self.bridge(auto_skills=True).skills['selected'],['documentation'])
        self.assertEqual(self.bridge(skills=['documentation'],auto_skills=True).skills['selected'],['documentation'])
        for kwargs in ({'skills':'documentation'},{'auto_skills':'yes'},{'grants':['bad']},
                       {'grants':{'mcp_tools':[{'server':'external','name':'write'}]}}):
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):self.bridge(**kwargs)

    def test_changed_skill_is_blocked_before_task_creation(self):
        from skill_runtime import initialize
        initialize(self.root)
        (self.root/'skills/documentation/SKILL.md').write_text(self.reference+'Changed')
        with self.assertRaisesRegex(ValueError,'restart'):self.bridge(skills=['documentation'])

    def test_cancel_and_closed_bridge_cannot_execute(self):
        control=Control();bridge=self.bridge(grants={'write_diagnostics':True},control=control)
        control.cancel()
        with self.assertRaises(ChatCancelled):bridge.call('write_diagnostic_markdown',{'filename':'cancel.md','content':'Denied'})
        self.assertEqual(bridge.session.events,[])
        bridge.close()
        with self.assertRaisesRegex(ValueError,'closed'):bridge.call('inventory_directory',{})

    def test_unknown_skill_is_rejected_during_job_admission(self):
        with patch('threading.Thread') as thread,self.assertRaises(ValueError):
            Jobs().start(self.root,{'id':self.cid,'content':'fixture','engine':'opencode',
                'opencode_approval':True,'skills':['missing']})
        thread.assert_not_called()

    def test_exact_mcp_names_are_allowed_without_native_edit_or_shell(self):
        rules=session_rules(self.target,tool_names=['write_diagnostic_markdown'])
        self.assertIn({'permission':'smelter_write_diagnostic_markdown','pattern':'*','action':'allow'},rules)
        self.assertFalse(any(x['action']=='allow' and x['permission'] in ('edit','shell','bash','task') for x in rules))

    @unittest.skipUnless(sdk_status()['status']=='installed','Pinned MCP SDK required')
    def test_real_mcp_inventory_rejects_escape_and_freezes_registered_exclusions(self):
        from access_policy import current,Policy
        (self.target/'public.txt').write_text('public')
        (self.target/'secret.txt').write_text('private')
        value=current(self.root).value
        row=next(row for row in value['locations'] if Path(row['path']).resolve()==self.target.resolve())
        row['exclusions'].append('secret.txt')
        bridge=self.bridge(grants={'inventory_root':str(self.target.resolve())},policy=Policy(value))
        result=bridge.call('inventory_directory',{'relative_path':'.'})['structuredContent']['tool_result']
        self.assertEqual(result['files_observed'],1)
        self.assertNotIn('secret.txt',json.dumps(result))
        for relative in ('../SMELTER','/etc','C:/Windows'):
            response=bridge.call('inventory_directory',{'relative_path':relative})
            self.assertTrue(response['isError'])

    def test_runtime_forwards_skills_and_rejects_disconnected_mcp(self):
        bridge=self.bridge(skills=['documentation'],grants={'write_diagnostics':True})
        client=Fixture(self.target);client.policy=session_rules(self.target,tool_names=['write_diagnostic_markdown'])
        original=client.request
        client.request=lambda path,*a,**k:{'smelter':{'status':'connected'}} if path=='/mcp' else original(path,*a,**k)
        result=ask(self.root,self.cid,'Write a report',model_key='local/qwen3.5:9b',approval=True,
                   agent_mode=True,bridge=bridge,client=client)
        self.assertEqual(result['status'],'completed')
        body=next(body for path,_,body in client.calls if path.endswith('/prompt_async'))
        self.assertIn('BRIDGE_REFERENCE_MARKER',body['system'])
        self.assertIn('smelter_',body['system'])
        saved=read_chat(self.root,self.cid)['messages'][-1]['execution']
        self.assertEqual(saved['skills'],['documentation'])
        self.assertEqual(saved['skill_snapshots'],bridge.skills['snapshots'])
        client=Fixture(self.target);original=client.request
        client.request=lambda path,*a,**k:{'smelter':{'status':'failed'}} if path=='/mcp' else original(path,*a,**k)
        with self.assertRaisesRegex(ValueError,'MCP bridge'):
            ask(self.root,self.cid,'fixture',model_key='local/qwen3.5:9b',approval=True,
                agent_mode=True,bridge=self.bridge(grants={'write_diagnostics':True}),client=client)
        self.assertFalse(any(method=='POST' for _,method,_ in client.calls))

    @unittest.skipUnless(sdk_status()['status']=='installed','Pinned MCP SDK required')
    def test_actual_mcp_write_deduplicates_and_retains_receipt_after_model_error(self):
        bridge=self.bridge(skills=['documentation'],grants={'write_diagnostics':True})
        client=Fixture(self.target);client.policy=session_rules(self.target,tool_names=['write_diagnostic_markdown'])
        original=client.request
        def request(path,*args,**kwargs):
            if path=='/mcp':return {'smelter':{'status':'connected'}}
            if path.endswith('/prompt_async'):
                call={'filename':'actual.md','content':'# Actual MCP bridge\n'}
                self.assertFalse(bridge.call('write_diagnostic_markdown',call)['isError'])
                self.assertFalse(bridge.call('write_diagnostic_markdown',call)['isError'])
            if '/message?' in path:raise ValueError('Injected follow-up failure')
            return original(path,*args,**kwargs)
        client.request=request
        result=ask(self.root,self.cid,'Write actual report',model_key='local/qwen3.5:9b',approval=True,
                   agent_mode=True,bridge=bridge,client=client)
        self.assertEqual(result['status'],'partial')
        self.assertIn('[MCP]',result['reply'])
        saved=read_chat(self.root,self.cid)['messages'][-1]['execution']
        self.assertEqual(saved['events'][0]['result']['status'],'written')
        self.assertTrue(saved['events'][1]['reused'])
        self.assertEqual((self.root/'diagnostics/actual.md').read_bytes(),b'# Actual MCP bridge\n')
        self.assertFalse((self.root/'diagnostics/actual_01.md').exists())
        self.assertTrue(Path(saved['events'][0]['result']['mcp_audit_path']).is_file())


if __name__=='__main__':unittest.main()
