"""Regression tests for cross-layer defects; no real model or user files."""
import io
import json
import sqlite3
from contextlib import closing
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from database import select_database, chosen_database
from config_store import load_config, save_config
from chats import create_chat, read_chat
from chat_inference import ask
from access_policy import Policy, defaults, current, save, using
from chat_jobs import Jobs


class RevisionContracts(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.base=Path(t.name);self.root=self.base/'SMELTER';self.root.mkdir()
        select_database(self.root,str(self.base/'data'));self.cid=create_chat(self.root,'Fixture')['id']

    def test_http_config_roundtrip_and_toggles_preserve_previous(self):
        import dashboard
        tools={'tools':[{'name':'ollama','status':'installed'},{'name':'opencode','status':'installed'}]}
        with patch.object(dashboard,'ROOT',self.root),patch.object(dashboard,'scan',return_value=tools),patch.object(dashboard,'list_models',return_value={'status':'connected','models':[{'name':'other-model'}]}):
            server=ThreadingHTTPServer(('127.0.0.1',0),dashboard.handler('fixture-token'))
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def call(path,body=None):
                request=Request(f'http://127.0.0.1:{server.server_port}'+path,headers={'X-Smelter-Token':'fixture-token','Content-Type':'application/json'},data=json.dumps(body).encode() if body else None)
                with urlopen(request,timeout=3) as r:return json.load(r)
            try:
                for name in ('ollama','opencode'):call('/api/extensions',{'id':name,'enabled':True})
                self.assertEqual({x['id'] for x in call('/api/extensions')['extensions'] if x['enabled']},{'ollama','opencode'})
                call('/api/ollama/preferences',{'role':'reasoning','model':'other-model'})
                self.assertEqual(call('/api/ollama/preferences')['preferences']['models']['reasoning'],'other-model')
            finally:server.shutdown();server.server_close();thread.join(timeout=3)

    def test_actual_inference_uses_saved_model(self):
        save_config(self.root,'model_preferences.json',{'schema_version':1,'models':{'reasoning':'selected-model'}})
        seen=[]
        def opener(req,timeout):
            seen.append(json.loads(req.data));return io.BytesIO(b'{"message":{"content":"fixture"}}')
        result=ask(self.root,self.cid,'Hello',opener=opener)
        self.assertEqual(seen[0]['model'],'selected-model');self.assertEqual(result['model'],'selected-model')

    def test_latest_history_and_older_page_do_not_lose_messages(self):
        with closing(sqlite3.connect(chosen_database(self.root))) as c, c:
            c.executemany('INSERT INTO messages(conversation_id,role,content) VALUES(?,?,?)',[(self.cid,'user',str(i)) for i in range(1002)])
        latest=read_chat(self.root,self.cid);self.assertEqual(latest['messages'][-1]['content'],'1001');self.assertTrue(latest['has_older'])
        previous=read_chat(self.root,self.cid,before=latest['older_cursor']);self.assertEqual([m['content'] for m in previous['messages']],['0','1'])
        self.assertFalse(previous['has_older'])

    def test_followup_failure_returns_partial_with_durable_receipt(self):
        calls=[{'message':{'content':'','tool_calls':[{'function':{'name':'write_diagnostic_markdown','arguments':{'filename':'fixture.md','content':'saved'}}}]}},ValueError('injected follow-up failure')]
        def opener(*a,**k):
            result=calls.pop(0)
            if isinstance(result,Exception):raise result
            return io.BytesIO(json.dumps(result).encode())
        result=ask(self.root,self.cid,'Save',opener=opener,tool_permissions={'write_diagnostics':True})
        self.assertEqual(result['status'],'partial');self.assertEqual((self.root/'diagnostics/fixture.md').read_text(),'saved')
        self.assertEqual(read_chat(self.root,self.cid)['messages'][-1]['execution']['outcome'],'partial')

    def test_job_preserves_partial_outcome(self):
        jobs=Jobs();job=jobs.start(self.root,{'id':self.cid,'content':'fixture'},worker=lambda *a,**k:{'status':'partial','error':'fixture'})
        import time
        for _ in range(100):
            status=jobs.status(job['id'])
            if status['state']!='running':break
            time.sleep(.005)
        self.assertEqual(status['state'],'partial')

    def test_default_policy_and_specific_denials(self):
        policy=current(self.root);target=self.root.with_name('SMELTERV2')
        policy.authorize(self.root/'tools/a.py','read');policy.authorize(target/'a.py','write');policy.authorize(target,'execute','tests')
        for path,action in [(self.root/'a.py','write'),(self.base/'outside','read'),(self.root/'.smelter/secret','read')]:
            with self.assertRaisesRegex(ValueError,'Access denied'):policy.authorize(path,action)
        value=defaults(self.root);value['locations'][1]['exclusions'].append('private/**');policy=Policy(value)
        with self.assertRaises(ValueError):policy.authorize(target/'private/x','write')
        with self.assertRaises(ValueError):policy.authorize(target,'execute','rea')

    def test_links_and_whole_root_grants_rejected(self):
        target=self.base/'real';target.mkdir();link=self.root/'link'
        try:link.symlink_to(target,target_is_directory=True)
        except OSError:self.skipTest('Symlink creation unavailable')
        with self.assertRaises(ValueError):current(self.root).authorize(link/'x','read')
        value=defaults(self.root);value['locations'][0]['path']=str(Path(self.root.anchor))
        with self.assertRaisesRegex(ValueError,'Whole-drive'):Policy(value)

    def test_policy_snapshot_does_not_expand_during_task(self):
        policy=current(self.root);value=defaults(self.root);value['locations'][1]['write']=False;save(self.root,value)
        target=self.root.with_name('SMELTERV2')/'x'
        policy.authorize(target,'write')
        with self.assertRaises(ValueError):current(self.root).authorize(target,'write')
        with self.assertRaises(ValueError):Jobs().start(self.root,{'id':self.cid,'content':'edit','tool_permissions':{'frontend_workspace':True}})

    def test_tool_session_cannot_bypass_registered_scope(self):
        from python_tools import ToolSession
        outside=self.base/'outside';outside.mkdir()
        with self.assertRaisesRegex(ValueError,'not registered'):ToolSession(self.root,{'inventory_root':str(outside)})
        with self.assertRaisesRegex(ValueError,'confined'):ToolSession(self.root,{'mcp_tools':[{'server':'x','name':'read'}]})

    def test_new_database_failure_can_be_retried(self):
        root=self.base/'fresh';(root/'.smelter').mkdir(parents=True);legacy=root/'.smelter/extensions.json';legacy.write_text('{broken')
        with self.assertRaises(ValueError):select_database(root,str(self.base/'fresh-data'))
        self.assertFalse((self.base/'fresh-data/smelter.sqlite3').exists())
        legacy.write_text('{"schema_version":1,"enabled":[]}');select_database(root,str(self.base/'fresh-data'))

    def test_context_budget_drops_complete_old_turn_or_fails_explicitly(self):
        from context_budget import bounded
        messages=[{'role':'system','content':'policy'},{'role':'user','content':'old'},{'role':'assistant','content':'x'*2000},{'role':'user','content':'current'}]
        rows,meta=bounded(messages,[],2048,1024)
        self.assertEqual([x['content'] for x in rows],['policy','current']);self.assertGreater(meta['history_messages_removed'],0)
        with self.assertRaisesRegex(ValueError,'prompt budget'):bounded([{'role':'user','content':'x'*10000}],[],2048,1024)

    def test_opencode_context_replays_text_without_old_tool_grants(self):
        from opencode_runtime import conversation_prompt
        text=conversation_prompt({'messages':[{'role':'user','content':'ALPHA'},{'role':'assistant','content':'old receipt','execution':{'model_text':'Remembered','permissions':{'shell':True}}}]},'What marker?')
        self.assertIn('ALPHA',text);self.assertIn('What marker?',text);self.assertNotIn('shell',text);self.assertNotIn('old receipt',text)

    def test_inherited_skill_snapshot_rejects_changes_and_new_skills(self):
        from skill_runtime import initialize, export_snapshot, inherit_snapshot
        folder=self.root/'skills/fixture';folder.mkdir(parents=True)
        manifest=folder/'SKILL.md';manifest.write_text('# Fixture\n\n## Purpose\nOriginal instructions.\n')
        initialize(self.root);encoded=export_snapshot(self.root)
        self.assertIn('Original instructions',inherit_snapshot(self.root,encoded).manifest('fixture'))
        manifest.write_text('# Fixture\n\n## Purpose\nChanged instructions.\n')
        other=self.root/'skills/newskill';other.mkdir();(other/'SKILL.md').write_text('# New\n\n## Purpose\nNew instructions.\n')
        child=inherit_snapshot(self.root,encoded)
        for sid in ('fixture','newskill'):
            with self.assertRaisesRegex(ValueError,'restart'):child.manifest(sid)
        self.assertIn('Changed instructions',initialize(self.root).manifest('fixture'))

    def test_opencode_second_turn_has_history_and_updated_policy_denials(self):
        from test_opencode_runtime import Fixture
        from opencode_runtime import ask as agent_ask, session_rules
        target=self.root.with_name('SMELTERV2');target.mkdir();client=Fixture(target)
        agent_ask(self.root,self.cid,'Remember ALPHA',model_key='local/qwen3.5:9b',approval=True,client=client)
        value=defaults(self.root);value['locations'][1]['exclusions'].append('tools/private/**');save(self.root,value)
        client.policy=session_rules(target,current(self.root))
        agent_ask(self.root,self.cid,'What marker?',model_key='local/qwen3.5:9b',approval=True,client=client)
        prompts=[body for path,method,body in client.calls if path.endswith('/prompt_async')]
        self.assertIn('Remember ALPHA',json.dumps(prompts[-1]))
        self.assertIn('What marker?',json.dumps(prompts[-1]))
        policies=[body['permission'] for path,method,body in client.calls if path=='/session' and method=='POST']
        self.assertEqual(len(policies),2)
        self.assertIn({'permission':'read','pattern':'tools/private/**','action':'deny'},policies[-1])
        self.assertNotIn({'permission':'read','pattern':'tools/private/**','action':'deny'},policies[0])
