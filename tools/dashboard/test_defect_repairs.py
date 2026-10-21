"""Behavior regressions for review findings. No real model or game required."""
import base64
import io
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from http.client import HTTPConnection
from database import select_database,chosen_database,inspect_database
from chats import create_chat,delete_chat,read_chat
from config_store import save_config
from runtime_settings import save_runtime
from model_assets import attach_model,model_path
from test_model_assets import glb
from chat_jobs import Control,Jobs
from process_runner import run,OutputLimitExceeded
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"setup"))


class DefectRepairs(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name);self.root=self.base/'SMELTER';self.root.mkdir();self.root.with_name('SMELTERV2').mkdir()
        select_database(self.root,str(self.base/'data'));self.cid=create_chat(self.root,'Fixture')['id']
        self.raw=glb({'asset':{'version':'2.0'},'nodes':[],'meshes':[]})

    def attach(self):
        result=attach_model(self.root,{'conversation_id':self.cid,'filename':'fixture.glb','base64':base64.b64encode(self.raw).decode()})
        return result,model_path(self.root,result['id'])

    def test_delete_removes_bytes_and_pending_cleanup_can_be_reconciled(self):
        from maintenance import plan,prune
        asset,path=self.attach()
        with patch('python_tools._plain_path') as plain:
            plain.return_value.unlink.side_effect=PermissionError('fixture busy')
            result=delete_chat(self.root,self.cid)
        self.assertEqual(result['cleanup_pending'],[asset['id']]);self.assertTrue(path.exists())
        os.utime(path,(time.time()-40*86400,)*2)
        candidate=plan(self.root,30);self.assertEqual(candidate['files'],1)
        with self.assertRaises(ValueError):prune(self.root,candidate['plan_id'],False)
        self.assertEqual(prune(self.root,candidate['plan_id'],True)['removed'],1);self.assertFalse(path.exists())

    def test_referenced_assets_and_changed_files_are_not_pruned(self):
        from maintenance import plan,prune
        asset,path=self.attach();os.utime(path,(time.time()-40*86400,)*2)
        self.assertEqual(plan(self.root,30)['files'],0)
        report=self.root/'.smelter/reports'/('00000000-0000-0000-0000-000000000001.json');report.parent.mkdir();report.write_text('{}');os.utime(report,(time.time()-40*86400,)*2)
        candidate=plan(self.root,30);report.write_text('{"changed":true}')
        result=prune(self.root,candidate['plan_id'],True)
        self.assertEqual(result['removed'],0);self.assertTrue(result['skipped_changed']);self.assertTrue(path.exists())

    def test_backup_restore_preserves_sqlite_skills_and_glb_bytes(self):
        from maintenance import backup,restore
        asset,path=self.attach();skill=self.root/'.smelter/managed-skills/fixture';skill.mkdir(parents=True);(skill/'SKILL.md').write_text('# Fixture\n\n## Purpose\nInspect synthetic files.\n')
        (self.root/'.smelter/skill-state.json').write_text('{"fixture":true}')
        result=backup(self.root,self.base/'backup',True);self.assertEqual(result['status'],'backed_up')
        fresh=self.base/'fresh';fresh.mkdir()
        restore(self.base/'backup',fresh,self.base/'fresh-data',True)
        self.assertTrue(inspect_database(fresh,integrity=True)['ready'])
        self.assertEqual(model_path(fresh,asset['id']).read_bytes(),self.raw)
        self.assertEqual(read_chat(fresh,self.cid)['title'],'Fixture')
        self.assertTrue((fresh/'.smelter/managed-skills/fixture/SKILL.md').is_file())
        with self.assertRaises(ValueError):restore(self.base/'backup',fresh,self.base/'other-data',True)
        with self.assertRaises(ValueError):backup(self.root,self.base/'backup',True)

    def test_tampered_backup_is_rejected_before_restore(self):
        from maintenance import backup,restore
        backup(self.root,self.base/'backup',True)
        db=self.base/'backup/database.sqlite3';db.write_bytes(db.read_bytes()+b'tampered')
        fresh=self.base/'fresh';fresh.mkdir()
        with self.assertRaisesRegex(ValueError,'verification'):restore(self.base/'backup',fresh,self.base/'fresh-data',True)
        self.assertFalse((fresh/'.smelter').exists())

    def test_artifact_quota_prevents_upload_without_deleting_existing_files(self):
        from storage_budget import invalidate
        invalidate(self.root)
        with patch('storage_budget.MAX_BYTES',10):
            with self.assertRaisesRegex(ValueError,'reservation|quota'):self.attach()
        self.assertFalse((self.root/'.smelter/model-assets').exists())

    def test_stop_at_final_opencode_message_has_one_durable_outcome(self):
        from test_opencode_runtime import Fixture
        from opencode_runtime import ask
        client=Fixture(self.root.with_name('SMELTERV2'));control=Control();request=client.request
        def final(path,*args,**kwargs):
            result=request(path,*args,**kwargs)
            if path.endswith('/message?limit=50'):control.cancel()
            return result
        client.request=final
        result=ask(self.root,self.cid,'Read README',model_key='local/qwen3.5:9b',approval=True,client=client,control=control)
        record=read_chat(self.root,self.cid)['messages'][-1]['execution']
        self.assertEqual(result['status'],'cancelled');self.assertEqual(record['outcome'],'cancelled');self.assertTrue(record['cancelled'])
        self.assertFalse(control.cancel());self.assertEqual(control.terminal_result['status'],'cancelled')

    def test_frontend_inference_preserves_saved_budget(self):
        from chat_inference import ask
        save_runtime(self.root,{'context_tokens':32768,'max_output_tokens':128,'timeout_seconds':30,'thinking':False})
        requests=[]
        def opener(request,timeout):requests.append((json.loads(request.data),timeout));return io.BytesIO(b'{"message":{"content":"fixture"}}')
        ask(self.root,self.cid,'Inspect the workspace',opener=opener,tool_permissions={'frontend_workspace':True})
        self.assertEqual(requests[0][0]['options']['num_predict'],128);self.assertLessEqual(requests[0][1],30)
        stored=read_chat(self.root,self.cid)['messages'][-1]['execution']['configuration']
        self.assertEqual(stored['runtime']['max_output_tokens'],128)

    def test_admission_configuration_is_frozen_and_stale_client_is_rejected(self):
        from task_contract import configuration
        started=threading.Event();release=threading.Event();finished=threading.Event();seen=[]
        def worker(*args,control,**kwargs):
            seen.append(control.configuration);started.set();release.wait(3);finished.set();return {'status':'completed'}
        jobs=Jobs();before=configuration(self.root);job=jobs.start(self.root,{'id':self.cid,'content':'fixture','configuration_revision':before['revision']},worker=worker)
        self.assertTrue(started.wait(2))
        save_config(self.root,'model_preferences.json',{'schema_version':1,'models':{'reasoning':'new-model'}})
        self.assertEqual(seen[0],before);release.set();self.assertTrue(finished.wait(2))
        for _ in range(100):
            if jobs.status(job['id'])['state']!='running':break
            time.sleep(.01)
        with self.assertRaisesRegex(ValueError,'configuration changed'):jobs.start(self.root,{'id':self.cid,'content':'fixture','configuration_revision':before['revision']})

    def test_restart_marks_dead_owner_interrupted_without_replaying(self):
        from job_store import save,recover,read
        jid='fixture';save(self.root,{'id':jid,'conversation_id':self.cid,'engine':'ollama','state':'running','error':None})
        with patch('job_store.alive',return_value=False):self.assertEqual(recover(self.root),[jid])
        self.assertEqual(Jobs().status(jid,root=self.root)['state'],'interrupted')
        self.assertEqual(read_chat(self.root,self.cid)['messages'],[])

    def test_second_controller_cannot_admit_an_overlapping_job(self):
        from job_store import admit
        payload={'id':'first','conversation_id':self.cid,'engine':'ollama','state':'running'}
        admit(self.root,payload)
        with self.assertRaisesRegex(ValueError,'already owns'):admit(self.root,{**payload,'id':'second'})

    def test_json_shape_and_project_contract_use_real_http_boundaries(self):
        import dashboard
        token='fixture-token'
        with patch.object(dashboard,'ROOT',self.root):
            server=ThreadingHTTPServer(('127.0.0.1',0),dashboard.handler(token));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def call(path,value):
                connection=HTTPConnection('127.0.0.1',server.server_port,timeout=3)
                connection.request('POST',path,json.dumps(value),{'X-Smelter-Token':token,'Content-Type':'application/json'})
                response=connection.getresponse();status=response.status;body=json.load(response);connection.close();return status,body
            try:
                for value in (None,[],1,'text'):
                    code,body=call('/api/chats',value);self.assertEqual(code,400);self.assertIn('JSON object',body['error'])
                code,body=call('/api/chats',{'action':'runtime_settings','settings':[]});self.assertEqual(code,400)
                (self.root/'README.md').write_text('Fixture')
                code,body=call('/api/project-contract',{'path':str(self.root)});self.assertEqual(code,200);self.assertTrue(body['required']['README.md'])
                code,body=call('/api/project-contract',{'path':str(self.base)});self.assertEqual(code,400)
            finally:server.shutdown();server.server_close();thread.join(3)

    def test_shared_legacy_skill_catalog_and_scoped_capability_bridge(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core'))
        from smelter_registry import Registry
        from skills_catalog import catalog_skills
        from skill_manager import set_skill_enabled
        from skill_runtime import initialize
        folder=self.root/'.agents/skills/fixture';folder.mkdir(parents=True);(folder/'SKILL.md').write_text('# Fixture\n\n## Purpose\nInspect synthetic files.\n')
        registry=Registry(self.root)
        self.assertIn('legacy/fixture',{s['id'] for s in registry.skills()})
        self.assertFalse(next(s for s in catalog_skills(self.root)['skills'] if s['id']=='legacy/fixture')['enabled'])
        set_skill_enabled(self.root,'legacy/fixture',True,True);initialize(self.root)
        self.assertIn('Inspect synthetic',registry.skill_instructions('legacy/fixture'))
        registry.connect_dashboard({'write_diagnostics':True})
        args={'arguments':{'filename':'bridge.md','content':'fixture'}}
        with self.assertRaises(PermissionError):registry.invoke('smelter/write_diagnostic_markdown',args)
        result=registry.invoke('smelter/write_diagnostic_markdown',args,allow_writes=True)
        self.assertEqual(result['status'],'written');self.assertEqual(Path(result['path']).read_text(),'fixture')

    def test_dependency_cache_is_explicitly_refreshable(self):
        import check_requirements
        with patch.object(check_requirements,'probe',return_value={'name':'fixture','status':'missing','version':None}) as probe:
            first=check_requirements.scan();check_requirements.scan();self.assertEqual(probe.call_count,len(check_requirements.TOOLS))
            check_requirements.scan(refresh=True);self.assertEqual(probe.call_count,2*len(check_requirements.TOOLS));self.assertIn('cache_age_seconds',first)

    def test_integrity_is_explicit_and_not_run_on_each_readiness_check(self):
        import database
        original=sqlite3.connect;seen=[]
        class Connection:
            def __init__(self,*a,**k):self.connection=original(*a,**k)
            def execute(self,sql,*a):seen.append(sql);return self.connection.execute(sql,*a)
            def close(self):self.connection.close()
        with patch.object(database.sqlite3,'connect',side_effect=Connection):
            self.assertTrue(inspect_database(self.root)['ready']);self.assertFalse(any('quick_check' in sql for sql in seen))
            self.assertTrue(inspect_database(self.root,integrity=True)['ready']);self.assertTrue(any('quick_check' in sql for sql in seen))

    def test_unconfined_opencode_is_blocked_before_external_session(self):
        from opencode_runtime import ask
        with patch('opencode_runtime.Client') as client:
            with patch('opencode_sandbox.status',return_value={'ready':False,'reason':'fixture unavailable'}):
                with self.assertRaisesRegex(ValueError,'Confined OpenCode unavailable'):ask(self.root,self.cid,'fixture',approval=True,model_key='local/qwen3.5:9b')
            client.assert_not_called()


class ProcessBoundaryTests(unittest.TestCase):
    def test_success_input_and_nonzero_exit_are_reported(self):
        result=run([sys.executable,'-c','import sys; print(sys.stdin.read()); print("error",file=sys.stderr);sys.exit(3)'],input=b'fixture',timeout=3,text=True)
        self.assertEqual(result.returncode,3);self.assertIn('fixture',result.stdout);self.assertIn('error',result.stderr)

    def test_output_flood_is_killed_and_not_returned_as_success(self):
        with self.assertRaises(OutputLimitExceeded):run([sys.executable,'-c','import sys; sys.stdout.write("x"*1000000);sys.stderr.write("y"*1000000)'],timeout=3,max_output=2048)

    def test_timeout_and_cancellation_stop_owned_processes(self):
        with self.assertRaises(subprocess.TimeoutExpired):run([sys.executable,'-c','import time;time.sleep(5)'],timeout=.1)
        cancel=threading.Event();cancel.set()
        with self.assertRaisesRegex(ValueError,'cancelled'):run([sys.executable,'-c','import time;time.sleep(5)'],cancel=cancel,timeout=3)

    def test_sandbox_flags_have_no_host_execution_escape(self):
        from sandbox import _flags,validate
        args=_flags('/usr/bin/docker','smelter-tests-fixture',Path('/tmp/fixture'))
        self.assertIn('--read-only',args);self.assertEqual(args[args.index('--network')+1],'none')
        self.assertIn('no-new-privileges=true',args);self.assertIn('65534:65534',args);self.assertNotIn('--privileged',args)
        self.assertFalse(any('docker.sock' in value or value.startswith('HOME=') and value!='HOME=/home/app' for value in args))
        with self.assertRaises(ValueError):validate({'schema_version':1,'python_image':'python:latest','node_image':None,'opencode_image':None})


@unittest.skipUnless(os.environ.get('SMELTER_TEST_DOCKER')=='1','Opt-in real Docker isolation check; requires preloaded immutable Python image ID')
class DockerIsolationTest(unittest.TestCase):
    def test_readonly_snapshot_no_host_secret_no_network(self):
        import shutil
        from sandbox import _flags,_remove
        image=os.environ['SMELTER_TEST_PYTHON_IMAGE'];self.assertRegex(image,r'^sha256:[a-f0-9]{64}$')
        docker=shutil.which('docker');self.assertIsNotNone(docker)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'code').mkdir();(root/'code/.smelter').mkdir();(root/'code/allowed.txt').write_text('allowed');(root/'secret.txt').write_text('host secret')
            root.chmod(0o755);(root/'code').chmod(0o755)
            name='smelter-tests-'+__import__('uuid').uuid4().hex
            script='''import os,socket
assert open('/workspace/allowed.txt').read()=='allowed'
assert 'SMELTER_HOST_SECRET' not in os.environ
assert not os.path.exists(HOST_SECRET_PATH)
try:open('/workspace/forbidden.txt','w');raise AssertionError('read-only mount escaped')
except OSError:pass
try:socket.create_connection(('1.1.1.1',80),timeout=.5);raise AssertionError('network escaped')
except OSError:pass
print('isolation checks passed')'''
            script=script.replace('HOST_SECRET_PATH',repr(str(root/'secret.txt')))
            environment={**os.environ,'SMELTER_HOST_SECRET':'must-not-be-inherited'}
            try:
                result=run(_flags(docker,name,root/'code')+['--rm',image,'python','-c',script],timeout=15,text=True,check=True,env=environment)
                self.assertIn('isolation checks passed',result.stdout)
            finally:_remove(docker,name)
