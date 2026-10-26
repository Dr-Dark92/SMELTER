import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from access_policy import current, save, require, using
from access_requests import AccessRequests, candidate
from chat_jobs import Control, Jobs
from database import select_database
from python_tools import ToolSession


class AccessRequestTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        base=Path(self.tmp.name);self.root=base/'app';self.root.mkdir()
        self.folder=base/'game';self.folder.mkdir();(self.folder/'sample.txt').write_text('fixture')
        select_database(self.root,str(base/'data'))
        self.session=ToolSession(self.root,{'access_requests':True})
        self.control=Control();self.broker=AccessRequests(self.root,'a'*32,'chat',self.control,self.session)
        self.control.access_requests=self.broker;self.session.access_requests=self.broker

    def pending(self):
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            request=self.broker.snapshot()
            if request:return request
            time.sleep(.01)
        self.fail('request did not become pending')

    def start_request(self,folder=None):
        result=[]
        thread=threading.Thread(target=lambda:result.append(self.session.execute({'function':{
            'name':'request_directory_access','arguments':{'directory':str(folder or self.folder),'reason':'Inspect game archives'}}})))
        thread.start();self.addCleanup(lambda:thread.join(2));self.addCleanup(self.control.cancel)
        return thread,result,self.pending()

    def resolve(self,request,decision='allow_task'):
        return self.broker.resolve(request['id'],decision,request['policy_revision'])

    def test_request_waits_without_authority_then_continues_same_session(self):
        thread,result,request=self.start_request()
        self.assertTrue(thread.is_alive())
        with self.assertRaises(ValueError):self.session.policy.authorize(self.folder,'read')
        self.assertEqual(self.control.phase,'Waiting for directory access')
        self.control.update('generic model progress')
        self.assertEqual(self.control.phase,'Waiting for directory access')
        self.resolve(request);thread.join(2)
        self.assertFalse(thread.is_alive());self.assertEqual(result[0]['status'],'access_granted')
        inventory=self.session.execute({'function':{'name':'inventory_directory','arguments':{'relative_path':'.'}}})
        self.assertEqual(inventory['status'],'inventoried');self.assertEqual(inventory['files_observed'],1)
        self.assertEqual(len(self.session.events),2)
        with self.assertRaises(ValueError):current(self.root).authorize(self.folder,'read')
        with self.assertRaises(ValueError):self.session.policy.authorize(self.folder,'write')
        self.assertGreater(self.control.permission_wait_time(),0)

    def test_attempted_external_read_automatically_pauses_and_retries_only_that_read(self):
        result=[]
        call={'function':{'name':'inventory_directory','arguments':{'relative_path':str(self.folder)}}}
        thread=threading.Thread(target=lambda:result.append(self.session.execute(call)))
        thread.start();self.addCleanup(lambda:thread.join(2));self.addCleanup(self.control.cancel)
        request=self.pending();self.assertFalse(result)
        self.assertEqual(request['directory'],str(self.folder.resolve()))
        self.resolve(request);thread.join(3)
        self.assertEqual(result[0]['status'],'inventoried');self.assertEqual(result[0]['files_observed'],1)
        self.assertEqual(len(self.session.events),1);self.assertEqual(self.session.events[0]['tool'],'inventory_directory')

    def test_remembered_scope_is_read_only_and_reused_by_later_task(self):
        thread,result,request=self.start_request();self.resolve(request,'allow_project');thread.join(2)
        current(self.root).authorize(self.folder,'read')
        other=AccessRequests(self.root,'b'*32,'chat',Control(),ToolSession(self.root,{'access_requests':True}))
        result=other.request({'directory':str(self.folder),'reason':'Inspect again'})
        self.assertEqual(result['status'],'access_granted');self.assertEqual(result['duration'],'project')
        self.assertIsNone(other.snapshot())
        for action in ('write','execute'):
            with self.assertRaises(ValueError):current(self.root).authorize(self.folder,action)

    def test_existing_registered_read_permission_needs_no_repeated_prompt(self):
        policy=current(self.root);value=policy.value
        value['locations'].append({'id':'existing_game','name':'Game','path':str(self.folder),'enabled':True,
                                  'read':True,'write':False,'execute':False,'operations':[],'exclusions':[]})
        save(self.root,value,policy.revision)
        result=self.broker.request({'directory':str(self.folder),'reason':'Inspect known folder'})
        self.assertEqual(result['status'],'access_granted');self.assertEqual(result['duration'],'project')
        self.assertIsNone(self.broker.snapshot())

    def test_denial_and_cancel_wake_without_replaying_work(self):
        thread,result,request=self.start_request();self.resolve(request,'deny');thread.join(2)
        self.assertEqual(result[0]['status'],'access_denied')
        result=self.broker.request({'directory':str(self.folder),'reason':'Again'})
        self.assertEqual(result['status'],'access_denied');self.assertIsNone(self.broker.snapshot())
        child=self.folder/'child';child.mkdir()
        result=self.broker.request({'directory':str(child),'reason':'Try a child of the declined folder'})
        self.assertEqual(result['status'],'access_denied');self.assertIsNone(self.broker.snapshot())
        other=self.folder.with_name('other');other.mkdir()
        thread,result,request=self.start_request(other);self.control.cancel();thread.join(2)
        self.assertFalse(thread.is_alive());self.assertIsNone(self.broker.snapshot())
        with self.assertRaises(ValueError):current(self.root).authorize(other,'read')

    def test_expiry_is_bounded_and_does_not_grant(self):
        with patch('access_requests.ACCESS_WAIT_SECONDS',.05):
            thread,result,request=self.start_request();thread.join(2)
        self.assertEqual(result[0]['status'],'access_denied')
        with self.assertRaises(ValueError):current(self.root).authorize(self.folder,'read')

    def test_stale_or_wrong_request_cannot_grant(self):
        thread,result,request=self.start_request()
        with self.assertRaises(ValueError):self.broker.resolve('wrong','allow_task',request['policy_revision'])
        policy=current(self.root);value=policy.value;value['locations'][0]['name']='Changed'
        save(self.root,value,policy.revision)
        with self.assertRaisesRegex(ValueError,'policy changed'):self.resolve(request)
        self.resolve(request,'deny');thread.join(2)
        with self.assertRaises(ValueError):self.resolve(request)

    def test_existing_denials_exclusions_and_protected_paths_are_not_overridden(self):
        policy=current(self.root);value=policy.value
        value['locations'].append({'id':'blocked','name':'blocked','path':str(self.folder),'enabled':True,
                                  'read':False,'write':False,'execute':False,'operations':[],'exclusions':[]})
        save(self.root,value,policy.revision)
        with self.assertRaises(ValueError):candidate(self.root,current(self.root),self.folder)
        secret=self.root/'.smelter';secret.mkdir(exist_ok=True)
        with self.assertRaises(ValueError):candidate(self.root,current(self.root),secret)
        with self.assertRaises(ValueError):candidate(self.root,current(self.root),self.root)

    def test_task_scopes_accumulate_without_persisting_other_scopes(self):
        thread,result,request=self.start_request();self.resolve(request);thread.join(2)
        other=self.folder.with_name('other');other.mkdir()
        thread,result,request=self.start_request(other);self.resolve(request,'allow_project');thread.join(2)
        self.session.policy.authorize(self.folder,'read');self.session.policy.authorize(other,'read')
        with self.assertRaises(ValueError):current(self.root).authorize(self.folder,'read')
        current(self.root).authorize(other,'read')
        result=self.broker.request({'directory':str(self.folder),'reason':'Return to first folder'})
        self.assertEqual(result['status'],'access_granted');self.session.policy.authorize(self.folder,'read')

    def test_decision_audit_failure_does_not_grant(self):
        thread,result,request=self.start_request()
        with patch.object(self.broker,'_record',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.resolve(request,'allow_project')
        with self.assertRaises(ValueError):current(self.root).authorize(self.folder,'read')
        with self.assertRaises(ValueError):self.session.policy.authorize(self.folder,'read')
        self.resolve(request,'deny');thread.join(2)

    def test_request_audit_failure_leaves_no_orphaned_prompt(self):
        with patch.object(self.broker,'_record',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.broker.request({'directory':str(self.folder),'reason':'Inspect'})
        self.assertIsNone(self.broker.snapshot())
        with self.assertRaises(ValueError):self.session.policy.authorize(self.folder,'read')

    def test_no_standalone_or_model_argument_can_approve_itself(self):
        other=ToolSession(self.root,{'access_requests':True})
        result=other.execute({'function':{'name':'request_directory_access','arguments':{'directory':str(self.folder),'reason':'Look'}}})
        self.assertEqual(result['status'],'error')
        with self.assertRaises(ValueError):self.broker.request({'directory':str(self.folder),'reason':'Look','approval':True})
        with self.assertRaises(ValueError):ToolSession(self.root,{'access_requests':'yes'})

    def test_job_with_unregistered_selected_folder_pauses_before_worker_and_resumes(self):
        from chats import create_chat
        chat=create_chat(self.root,'Access integration');jobs=Jobs();seen=[]
        def worker(root,cid,prompt,**kwargs):
            control=kwargs['control'];control.access_policy.authorize(self.folder,'read');seen.append(control.job_id)
            return {'content':'done','status':'completed'}
        with patch('task_contract.configuration',return_value={'revision':'test','runtime':{}}),patch('component_controls.check_admission'):
            job=jobs.start(self.root,{'id':chat['id'],'content':'inspect','tool_permissions':{'access_requests':True,'inventory_root':str(self.folder)}},worker=worker)
        deadline=time.monotonic()+3
        while time.monotonic()<deadline:
            state=jobs.status(job['id'])
            if state.get('pending_access'):break
            time.sleep(.01)
        self.assertFalse(seen);request=state['pending_access']
        jobs.resolve_access(self.root,job['id'],request['id'],'allow_task',request['policy_revision'])
        deadline=time.monotonic()+3
        while time.monotonic()<deadline and jobs.status(job['id'])['state']=='running':time.sleep(.01)
        self.assertEqual(seen,[job['id']]);self.assertEqual(jobs.status(job['id'])['state'],'done')

    def test_real_mcp_bridge_keeps_waiting_call_and_uses_the_new_scope(self):
        from agent_bridge import AgentBridge
        from mcp_connections import sdk_status
        if sdk_status()['status']!='installed':self.skipTest('Pinned MCP SDK required')
        bridge=AgentBridge(self.root,None,'Inspect another directory',grants={'access_requests':True},control=self.control)
        broker=AccessRequests(self.root,'c'*32,None,self.control,bridge.session)
        self.control.access_requests=broker;bridge.session.access_requests=broker
        result=[];thread=threading.Thread(target=lambda:result.append(bridge.call('request_directory_access',{'directory':str(self.folder),'reason':'Read the fixture'})))
        thread.start();self.addCleanup(lambda:thread.join(2));self.addCleanup(self.control.cancel)
        deadline=time.monotonic()+3
        while time.monotonic()<deadline and broker.snapshot() is None:time.sleep(.01)
        pending=broker.snapshot();self.assertIsNotNone(pending);self.assertTrue(bridge.active.is_set())
        budget=bridge.manifest()['tool_timeouts']['request_directory_access']
        self.assertGreater(budget,300)
        broker.resolve(pending['id'],'allow_task',pending['policy_revision']);thread.join(3)
        self.assertFalse(result[0]['isError']);self.assertFalse(bridge.active.is_set())
        read=bridge.call('read_inventory_file',{'relative_path':'sample.txt'})
        self.assertFalse(read['isError']);self.assertEqual(read['structuredContent']['tool_result']['text'],'fixture')
        self.assertEqual(len(bridge.session.events),2)

    def test_http_decision_is_authenticated_bound_to_job_and_does_not_start_over(self):
        import dashboard
        from http.client import HTTPConnection
        from http.server import ThreadingHTTPServer
        jobs=Jobs();jobs.jobs['a'*32]={'id':'a'*32,'state':'running','root':self.root,'control':self.control}
        thread,result,pending=self.start_request()
        with patch.object(dashboard,'ROOT',self.root),patch.object(dashboard,'JOBS',jobs):
            server=ThreadingHTTPServer(('127.0.0.1',0),dashboard.handler('access-fixture-token'))
            runner=threading.Thread(target=server.serve_forever,daemon=True);runner.start()
            def post(authorized=True,origin=None,**extra):
                headers={'Content-Type':'application/json'}
                if authorized:headers['X-Smelter-Token']='access-fixture-token'
                if origin:headers['Origin']=origin
                body={'job_id':'a'*32,'request_id':pending['id'],'decision':'allow_task','expected_revision':pending['policy_revision'],**extra}
                conn=HTTPConnection('127.0.0.1',server.server_port,timeout=3)
                conn.request('POST','/api/access-requests',json.dumps(body),headers)
                response=conn.getresponse();data=json.load(response);status=response.status;conn.close();return status,data
            try:
                self.assertEqual(post(authorized=False)[0],403)
                self.assertEqual(post(origin='https://untrusted.example')[0],403)
                self.assertEqual(post(request_id='forged')[0],400)
                self.assertTrue(thread.is_alive());self.assertEqual(post()[0],200)
                thread.join(2);self.assertEqual(result[0]['status'],'access_granted')
                self.assertEqual(post()[0],400)
            finally:server.shutdown();server.server_close();runner.join(3)

    def test_real_node_proxy_keeps_the_mcp_call_open_for_the_decision(self):
        import shutil,subprocess
        from agent_bridge import AgentBridge
        if not shutil.which('node'):self.skipTest('Node required')
        bridge=AgentBridge(self.root,None,'Inspect fixture',grants={'access_requests':True},control=self.control)
        broker=AccessRequests(self.root,'d'*32,None,self.control,bridge.session);bridge.session.access_requests=broker
        queue=self.root/'.smelter/proxy-test';queue.mkdir(parents=True)
        manifest=bridge.manifest();manifest['tools'] += [{'name':'fixture_'+str(i),'description':'fixture','inputSchema':{'type':'object'}} for i in range(34-len(manifest['tools']))]
        manifest_path=queue/'manifest.json';manifest_path.write_text(json.dumps(manifest))
        process=subprocess.Popen([shutil.which('node'),str(Path(__file__).with_name('opencode_mcp_proxy.mjs')),'--manifest',str(manifest_path),'--queue',str(queue)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        answers=[];errors=[]
        def relay():
            try:
                end=time.monotonic()+5
                while time.monotonic()<end:
                    files=list(queue.glob('*.request'))
                    if files:
                        packet=json.loads(files[0].read_text());reply=bridge.call(packet['name'],packet['arguments'])
                        files[0].with_suffix('.response').write_text(json.dumps({'mcp_result':reply}));return
                    time.sleep(.01)
                errors.append('No proxy request')
            except Exception as exc:errors.append(str(exc))
        relay_thread=threading.Thread(target=relay);relay_thread.start()
        requests=[{'jsonrpc':'2.0','id':1,'method':'tools/list'}, {'jsonrpc':'2.0','id':2,'method':'tools/call','params':{'name':'request_directory_access','arguments':{'directory':str(self.folder),'reason':'Read the fixture'}}}]
        def communicate():
            try:answers.append(process.communicate('\n'.join(json.dumps(r) for r in requests)+'\n',timeout=8))
            except Exception as exc:errors.append(str(exc))
        client=threading.Thread(target=communicate);client.start()
        try:
            end=time.monotonic()+4
            while time.monotonic()<end and broker.snapshot() is None:time.sleep(.01)
            pending=broker.snapshot();self.assertIsNotNone(pending);self.assertIsNone(process.poll())
            broker.resolve(pending['id'],'allow_task',pending['policy_revision'])
            client.join(5);relay_thread.join(5);self.assertFalse(errors);self.assertFalse(client.is_alive())
            responses=[json.loads(line) for line in answers[0][0].splitlines()]
            self.assertEqual(len(responses[0]['result']['tools']),34)
            self.assertEqual(responses[1]['result']['structuredContent']['tool_result']['status'],'access_granted')
            self.assertEqual(process.returncode,0)
        finally:
            self.control.cancel()
            if process.poll() is None:process.kill()
            client.join(3);relay_thread.join(3);process.wait(timeout=3)


if __name__=='__main__':unittest.main()
