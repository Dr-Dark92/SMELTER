"""No model calls: deterministic lifecycle, durable retries and loopback fixtures."""
from contextlib import closing
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError

from watchdog_store import Store,configure,decide,MAX_RETRIES,process_running
from watchdog_native import Native,GUARD_ERROR
from task_watchdog import Controller,handler,leader
import test_coding_workspace as base_tests
import coding_workspace as cw
from job_store import identity


class WatchdogTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=(Path(self.temp.name)/'root').resolve();self.root.mkdir();configure(self.root)
        self.bound={'schema_version':1,'source_root':str(self.root),'enabled':True,'configuration_revision':'rev',
            'binding':{'session_id':'ses_bound','directory':str(self.root),'workspace_id':'owned'}}
        path=self.root/'.smelter/native-progress/state.json';path.parent.mkdir(parents=True);path.write_text(json.dumps(self.bound),encoding='utf-8')
        self.store=Store(self.root)
        self.value={'session_id':'ses_bound','directory':str(self.root),'message_id':'msg_original','text':'Repair the existing module.',
            'created_ms':int(time.time()*1000),'model':{'providerID':'ollama','modelID':'original-qwen'},'agent':'build','variant':'smelter-tools',
            'server_port':12345,'native_pid':os.getpid()}

    def capture(self,**extra):return self.store.capture({**self.value,**extra},self.bound)

    def observation(self,**extra):
        return {'available':True,'native_phase':'idle','turn_ended':True,'assistant_seen':True,'last_progress':0,'active_tools':0,
                'pending_access':False,'pending_question':False,'delivered':set(),**extra}

    def fake(self):
        outer=self
        class Fake:
            def __init__(self):self.sent=[];self.error=False;self.override={};self.persisted=True
            def snapshot(self,task,attempts):return outer.observation(delivered={a['message_id'] for a in attempts} if self.persisted else set(),**self.override)
            def send(self,task,attempt):
                self.sent.append(attempt)
                if self.error:raise TimeoutError('ambiguous network delivery')
        return Fake()

    def test_original_model_prompt_and_scope_are_captured_but_not_public(self):
        self.capture();row=self.store.current()
        self.assertEqual(row['prompt'],self.value['text']);self.assertEqual(json.loads(row['model']),self.value['model'])
        self.assertNotIn(self.value['text'],json.dumps(self.store.public()))
        for extra in [{'session_id':'ses_other'},{'directory':str(self.root.parent)},{'has_attachments':True},{'text':'x'*32769}]:
            with self.subTest(extra=list(extra)),self.assertRaises(ValueError):self.capture(**extra)

    def test_new_human_supersedes_old_but_reserved_retry_does_not_reset_budget(self):
        self.capture();first=self.store.current();attempt=self.store.reserve(first['id'],100)
        result=self.capture(message_id=attempt['message_id']);self.assertEqual(result['status'],'recovery_recognized')
        self.assertEqual(self.store.current()['retries'],1)
        self.capture(message_id='msg_second',text='A new human objective')
        self.assertNotEqual(self.store.current()['id'],first['id'])
        with self.assertRaises(ValueError):self.capture(message_id=attempt['message_id'])

    def test_three_retries_survive_restart_and_original_prompt_is_removed_on_exit(self):
        self.capture();fake=self.fake();clock=[1000]
        control=Controller(self.root,self.store,fake,lambda:clock[0])
        for elapsed in (0,31,92):
            clock[0]=1000+elapsed;control.tick();control.store=Store(self.root)
        self.assertEqual(len(fake.sent),3);self.assertEqual(control.store.current()['retries'],3)
        clock[0]=1300;control.tick()
        self.assertEqual(control.store.current()['state'],'exhausted');self.assertIsNone(control.store.current()['prompt'])
        control.tick();self.assertEqual(len(fake.sent),3)

    def test_verified_red_and_green_are_end_flags_without_retry(self):
        for flag in ('RED','GREEN'):
            self.capture(message_id='msg_'+flag);fake=self.fake();fake.override={'flag':flag,'flag_receipt':'receipt'}
            Controller(self.root,self.store,fake,lambda:1000).tick()
            self.assertEqual(self.store.current()['state'],flag.lower());self.assertEqual(fake.sent,[])
            self.assertEqual(self.store.current()['reason'],'explicit_verified_end_flag')

    def test_operator_legacy_red_rearm_preserves_budget_and_cannot_revive_other_terminals(self):
        self.capture();task=self.store.current();attempt=self.store.reserve(task['id'],100)
        self.store.delivery(attempt['id'],'sent');self.store.update(task['id'],'red','verified_end_flag')
        self.assertEqual(self.capture()['status'],'already_captured')
        result=self.store.capture(self.value,self.bound,rearm_legacy_red=True)
        self.assertEqual(result['status'],'legacy_red_rearmed')
        self.assertEqual(self.store.current()['id'],task['id']);self.assertEqual(self.store.current()['retries'],1)
        self.assertEqual(len(self.store.attempts(task['id'])),1)
        self.store.update(task['id'],'cancelled','native_cancelled')
        with self.assertRaises(ValueError):self.store.capture(self.value,self.bound,rearm_legacy_red=True)
        value={**self.value,'message_id':'msg_limited'};self.store.capture(value,self.bound);task=self.store.current()
        for number in range(3):
            attempt=self.store.reserve(task['id'],100+number)
            self.store.delivery(attempt['id'],'sent')
        self.store.update(task['id'],'red','verified_end_flag')
        with self.assertRaises(ValueError):self.store.capture(value,self.bound,rearm_legacy_red=True)

    def test_stop_access_questions_and_active_work_never_admit_a_retry(self):
        for index,extra in enumerate([{'cancelled':True},{'pending_access':True},{'pending_question':True},{'active_tools':1},{'native_phase':'busy'},{'native_phase':'retry'}]):
            self.capture(message_id='msg_guard_'+str(index));fake=self.fake();fake.override=extra
            Controller(self.root,self.store,fake,lambda:1000).tick()
            self.assertEqual(fake.sent,[])
            if extra.get('cancelled'):self.assertEqual(self.store.current()['state'],'cancelled')

    def test_uncertain_post_is_not_replayed_after_controller_restart(self):
        self.capture();fake=self.fake();fake.error=True;fake.persisted=False
        control=Controller(self.root,self.store,fake,lambda:1000);control.tick()
        self.assertEqual(len(fake.sent),1);self.assertEqual(self.store.current()['state'],'delivery_unknown')
        Controller(self.root,Store(self.root),fake,lambda:9999).tick()
        self.assertEqual(len(fake.sent),1)

    def test_no_reply_prompt_is_never_started_by_watchdog(self):
        self.capture();fake=self.fake();fake.override={'assistant_seen':False,'turn_ended':False}
        Controller(self.root,self.store,fake,lambda:9999).tick()
        self.assertEqual(fake.sent,[]);self.assertEqual(self.store.current()['state'],'wait_initial_assistant')

    def test_unknown_external_tool_domain_is_not_automatically_replayed(self):
        self.capture();fake=self.fake();fake.override={'unrecognized_tool_domain':True}
        Controller(self.root,self.store,fake,lambda:9999).tick()
        self.assertEqual(fake.sent,[]);self.assertEqual(self.store.current()['state'],'wait_scope_review')

    def test_tool_contract_error_burst_holds_without_spending_retry(self):
        self.capture();fake=self.fake();fake.override={'protocol_error_burst':True}
        control=Controller(self.root,self.store,fake,lambda:9999);control.tick()
        self.assertEqual(fake.sent,[]);self.assertEqual(self.store.current()['retries'],0)
        self.assertEqual(self.store.current()['state'],'wait_tool_contract')
        # A real explicit, verified end still wins; this is a hold, not a new
        # terminal outcome or a way to fake RED/GREEN.
        fake.override.update(flag='RED',flag_receipt='receipt');control.tick()
        self.assertEqual(self.store.current()['state'],'red')

    def test_nonimproving_validation_holds_but_does_not_extend_the_three_retry_limit(self):
        self.capture();fake=self.fake();fake.override={'validation_progress':{'stalled':True}}
        control=Controller(self.root,self.store,fake,lambda:9999);control.tick()
        self.assertEqual(fake.sent,[]);self.assertEqual(self.store.current()['state'],'wait_validation_progress')
        task=self.store.current()
        for index in range(3):
            attempt=self.store.reserve(task['id'],100+index);self.store.delivery(attempt['id'],'sent')
        control.tick();self.assertEqual(self.store.current()['state'],'exhausted');self.assertEqual(fake.sent,[])

    def test_native_state_change_at_final_preflight_prevents_submission(self):
        self.capture();fake=self.fake();control=Controller(self.root,self.store,fake,lambda:1000)
        first=fake.snapshot;calls=[0]
        def snapshot(task,attempts):
            calls[0]+=1;return first(task,attempts) if calls[0]==1 else self.observation(cancelled=True)
        fake.snapshot=snapshot;control.tick();self.assertEqual(fake.sent,[])

    def test_singleton_prevents_two_watchdog_process_leaders(self):
        with leader(self.root):
            with self.assertRaises(OSError):
                with leader(self.root):pass

    def test_exited_process_handle_is_not_a_running_watchdog(self):
        child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(.4)'])
        self.addCleanup(lambda:child.wait(timeout=3))
        stamp=identity(child.pid);self.assertTrue(process_running(child.pid,stamp))
        child.wait(timeout=3)
        self.assertFalse(process_running(child.pid,stamp))

    def test_loopback_capture_rejects_browser_origin_and_bad_credentials(self):
        self.capture();fake=self.fake();fake.ports=lambda:[12345]
        server=ThreadingHTTPServer(('127.0.0.1',0),handler(Controller(self.root,self.store,fake),'private-secret'))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        url='http://127.0.0.1:'+str(server.server_port)+'/status'
        for headers in [{},{'Authorization':'Bearer wrong'},{'Authorization':'Bearer private-secret','Origin':'http://untrusted'}]:
            with self.assertRaises(HTTPError):urlopen(Request(url,headers=headers),timeout=2)
        with urlopen(Request(url,headers={'Authorization':'Bearer private-secret'}),timeout=2) as reply:value=json.load(reply)
        self.assertEqual(value['origin_id'],'msg_original');self.assertNotIn('prompt',value)

    def test_same_session_rest_submission_preserves_model_variant_and_checkpoint_request(self):
        requests=[]
        class Fixture(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_POST(self):
                requests.append((self.path,json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                self.send_response(204);self.end_headers()
        server=ThreadingHTTPServer(('127.0.0.1',0),Fixture);threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        self.capture(server_port=server.server_port,request_options={'tools':{'bash':False},'system':'original caller constraint'});row=self.store.current();attempt=self.store.reserve(row['id'],100)
        native=Native(self.root,ports=lambda:[server.server_port]);native.send(row,attempt)
        path,body=requests[0];self.assertTrue(path.startswith('/session/ses_bound/prompt_async?'))
        self.assertEqual(body['messageID'],attempt['message_id']);self.assertEqual(body['model'],self.value['model']);self.assertEqual(body['variant'],'smelter-tools')
        self.assertEqual(body['tools'],{'bash':False});self.assertEqual(body['system'],'original caller constraint')
        self.assertIn('coding_recovery_context',body['parts'][0]['text']);self.assertIn(self.value['text'],body['parts'][0]['text'])


class EndFlagTests(unittest.TestCase):
    def setUp(self):base_tests.CodingWorkspaceTests.setUp(self)
    def tearDown(self):base_tests.CodingWorkspaceTests.tearDown(self)
    prepare=base_tests.CodingWorkspaceTests.prepare

    def fixture(self,stage='GREEN'):
        from sandbox import lua_runner_sha256
        sid,target=self.prepare();base=cw.base_path(self.root)/sid/'test-runs';base.mkdir()
        log=base/'sample.log';log.write_bytes(b'real local output');path=log.with_suffix('.json')
        value={'workspace_id':sid,'profile':'lua','tree_sha256':cw.tree_digest(cw._scan(target)),'current_tree_matches':True,
               'stage':stage,'runner_sha256':lua_runner_sha256(),'source_snapshot':{'bytes_match':True},'log_sha256':cw.digest(log.read_bytes())}
        path.write_text(json.dumps(value),encoding='utf-8');native=Native(self.root);task={'workspace_id':sid}
        records=[(1,sid,'lua',str(path))]
        metadata,_=cw.load(self.root,sid);metadata['tests']['lua']={'path':str(path)}
        cw._save(cw.base_path(self.root)/sid/'workspace.json',metadata)
        return sid,target,path,value,native,task,records

    @staticmethod
    def ending(sid,result,stamp=2):
        return (stamp,sid,result['outcome'],json.dumps(['lua']),result['status'],result['outcome'],
                result['tree_sha256'],json.dumps(result['profiles']),json.dumps(result['receipts']))

    def test_test_red_or_green_alone_never_ends_a_task(self):
        for stage in ('RED','GREEN'):
            with self.subTest(stage=stage):
                _,_,_,_,native,task,records=self.fixture(stage)
                self.assertIsNone(native.end_flag(task,records))

    def test_explicit_finish_matches_evidence_and_later_validation_invalidates_it(self):
        from coding_finish import finish
        for stage in ('RED','GREEN'):
            sid,_,_,_,native,task,records=self.fixture(stage)
            result=finish(self.root,{'workspace_id':sid,'outcome':stage,'profiles':['lua']})
            ends=[self.ending(sid,result)]
            self.assertEqual(native.end_flag(task,records,ends)['flag'],stage)
            with self.assertRaises(ValueError):finish(self.root,{'workspace_id':sid,'outcome':'GREEN' if stage=='RED' else 'RED','profiles':['lua']})
            self.assertIsNone(native.end_flag(task,[(3,*records[0][1:])],ends))

    def test_stale_unowned_or_tampered_receipts_cannot_become_end_flags(self):
        from coding_finish import finish
        sid,target,path,value,native,task,records=self.fixture()
        result=finish(self.root,{'workspace_id':sid,'outcome':'GREEN','profiles':['lua']});ends=[self.ending(sid,result)]
        value['tree_sha256']='0'*64;path.write_text(json.dumps(value),encoding='utf-8')
        self.assertIsNone(native.end_flag(task,records,ends))
        self.assertIsNone(native.end_flag(task,[(1,sid,'lua',str(self.root/'unowned.json'))],ends))
        with self.assertRaises(ValueError):finish(self.root,{'workspace_id':sid,'outcome':'GREEN','profiles':['lua']})

    def test_finish_requires_coding_grant_and_is_registered_on_both_transports(self):
        from tool_registry import schemas,execute_builtin
        from python_tools import permissions
        self.assertIn('finish_coding_task',{s['function']['name'] for s in schemas(permissions(self.root,{'coding_workspace':True}))})
        self.assertNotIn('finish_coding_task',{s['function']['name'] for s in schemas(permissions(self.root,{}))})
        sid,_,_,_,_,_,_=self.fixture()
        args={'workspace_id':sid,'outcome':'GREEN','profiles':['lua']}
        with self.assertRaises(ValueError):execute_builtin(self.root,{},'finish_coding_task',args)
        self.assertEqual(execute_builtin(self.root,{'coding_workspace':True},'finish_coding_task',args)['status'],'coding_task_end_flag')

    def test_only_stable_hash_verified_frozen_results_can_identify_validation_churn(self):
        import acceptance_contracts as acceptance
        sid,target,path,value,native,task,_=self.fixture('RED')
        relative='mods/demo/policy.lua';subject=target/relative;subject.parent.mkdir(parents=True);subject.write_text('return {}\n')
        acceptance.register(self.root,sid,'entity-policy-v1',relative)
        contracts=acceptance.load(self.root,sid,target);records=[]
        for index in range(3):
            receipt=path.with_name('trend'+str(index)+'.json');log=receipt.with_suffix('.log');log.write_bytes(b'protected runner output')
            v={**value,'log_sha256':cw.digest(log.read_bytes()),'acceptance':{'stage':'RED',
                'contracts_revision':acceptance.revision(contracts),'contracts':[{**contracts[0],'counts':{'checks':30,'failures':6}}]}}
            receipt.write_text(json.dumps(v),encoding='utf-8');records.append((4-index,sid,'lua',str(receipt)))
        trend=native.validation_progress(task,records)
        self.assertTrue(trend['stalled']);self.assertEqual(trend['failures_newest_first'],[6,6,6])
        # Improvement under the same protected verifier does not trigger a hold.
        newest=Path(records[0][3]);v=json.loads(newest.read_text(encoding='utf-8'))
        v['acceptance']['contracts'][0]['counts']['failures']=5;newest.write_text(json.dumps(v),encoding='utf-8')
        self.assertIsNone(native.validation_progress(task,records))
        v['acceptance']['contracts'][0]['counts']['failures']=6;newest.write_text(json.dumps(v),encoding='utf-8')
        newest.with_suffix('.log').write_bytes(b'tampered')
        self.assertIsNone(native.validation_progress(task,records))


class NativeMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        self.path=self.root/'native.db';self.native=Native(self.root,path=self.path,ports=lambda:[])
        self.task={'session_id':'ses_root','directory':str(self.root),'origin_id':'msg_original'}
        with closing(sqlite3.connect(self.path)) as db,db:
            db.executescript('''CREATE TABLE session(id TEXT,parent_id TEXT,directory TEXT,time_created INTEGER);
              CREATE TABLE message(id TEXT,session_id TEXT,time_created INTEGER,time_updated INTEGER,data TEXT);
              CREATE TABLE part(id TEXT,message_id TEXT,session_id TEXT,time_created INTEGER,time_updated INTEGER,data TEXT);''')
            db.execute('INSERT INTO session VALUES(?,?,?,?)',('ses_root',None,str(self.root),0))
        self.message('msg_original','user',1000)
        self.part('part_user','msg_original',{'type':'text','text':'private original prompt'},1000)
        self.message('msg_assistant','assistant',2000,{'time':{'completed':2500},'finish':'stop','text':'private answer','reasoning':'private thoughts'})

    def message(self,mid,role,stamp,extra=None):
        with closing(sqlite3.connect(self.path)) as db,db:db.execute('INSERT INTO message VALUES(?,?,?,?,?)',(mid,'ses_root',stamp,stamp,json.dumps({'role':role,**(extra or {})})))

    def part(self,pid,mid,data,stamp,sid='ses_root'):
        with closing(sqlite3.connect(self.path)) as db,db:db.execute('INSERT INTO part VALUES(?,?,?,?,?,?)',(pid,mid,sid,stamp,stamp,json.dumps(data)))

    def test_metadata_covers_cancellation_and_excludes_prompt_reasoning_and_outputs(self):
        value=self.native.metadata(self.task,[])
        self.assertTrue(value['turn_ended']);self.assertNotIn('private',json.dumps(value,default=list))
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute("UPDATE message SET data=? WHERE id='msg_assistant'",(json.dumps({'role':'assistant','error':{'name':'MessageAbortedError','message':'private error'}}),))
        self.assertTrue(self.native.metadata(self.task,[])['cancelled'])

    def test_new_human_supersedes_but_controller_retry_and_compaction_do_not(self):
        self.message('msg_compact','user',2600);self.part('part_compact','msg_compact',{'type':'text','text':'private summary','synthetic':True},2600)
        self.assertFalse(self.native.metadata(self.task,[])['superseded'])
        self.message('msg_smelter_wd_retry','user',2700);self.part('part_retry','msg_smelter_wd_retry',{'type':'text','text':'private recovery'},2700)
        value=self.native.metadata(self.task,[{'message_id':'msg_smelter_wd_retry'}])
        self.assertFalse(value['superseded']);self.assertFalse(value['turn_ended']);self.assertIn('msg_smelter_wd_retry',value['delivered'])
        self.message('msg_human_new','user',2800);self.part('part_new','msg_human_new',{'type':'text','text':'private new goal'},2800)
        self.assertTrue(self.native.metadata(self.task,[])['superseded'])

    def test_only_named_receipt_pointer_leaves_native_tool_payload(self):
        body={'tool_result':{'evidence_path':'C:/owned/receipt.json'},'private output':'must not leave'}
        self.part('part_test','msg_assistant',{'type':'tool','tool':'smelter_run_coding_tests','state':{'status':'error',
            'input':{'workspace_id':'workspace','profile':'lua'},'error':json.dumps(body)}},2200)
        value=self.native.metadata(self.task,[])
        self.assertEqual(value['receipts'][0][3],'C:/owned/receipt.json');self.assertNotIn('must not leave',json.dumps(value,default=list))
        self.assertFalse(value['unrecognized_tool_domain'])
        self.part('part_external','msg_assistant',{'type':'tool','tool':'unknown_publish_operation','state':{'status':'completed'}},2300)
        self.assertTrue(self.native.metadata(self.task,[])['unrecognized_tool_domain'])

    def test_hallucinated_tool_is_a_protocol_error_not_an_unknown_domain(self):
        for n in range(3):
            self.part('part_invalid_'+str(n),'msg_assistant',{'type':'tool','tool':'invalid','state':{'status':'completed',
                'output':'The arguments provided to the tool are invalid: Model tried to call unavailable tool'}},2200+n)
            value=self.native.metadata(self.task,[])
            self.assertFalse(value['unrecognized_tool_domain'])
            self.assertEqual(value['protocol_errors'],n+1)
        self.assertTrue(value['protocol_error_burst'])

    def test_preexecution_guard_rejection_does_not_count_as_executed_shell(self):
        self.part('part_guard','msg_assistant',{'type':'tool','tool':'bash','state':{'status':'error','error':'Error: '+GUARD_ERROR}},2200)
        self.assertFalse(self.native.metadata(self.task,[])['unrecognized_tool_domain'])
        self.part('part_shell','msg_assistant',{'type':'tool','tool':'bash','state':{'status':'error','error':'external command failed'}},2300)
        self.assertTrue(self.native.metadata(self.task,[])['unrecognized_tool_domain'])

    def test_explicit_finish_extracts_only_named_proof_fields(self):
        proof={'status':'coding_task_end_flag','outcome':'RED','tree_sha256':'a'*64,'profiles':['lua'],'receipts':[], 'private':'not copied'}
        self.part('part_finish','msg_assistant',{'type':'tool','tool':'smelter_finish_coding_task','state':{'status':'completed',
            'input':{'workspace_id':'workspace','outcome':'RED','profiles':['lua']},'output':json.dumps({'tool_result':proof})}},2200)
        value=self.native.metadata(self.task,[])
        self.assertEqual(value['endings'][0][4],'coding_task_end_flag');self.assertNotIn('not copied',json.dumps(value,default=list))

    def test_recent_contract_error_burst_is_detected_without_copying_payloads(self):
        for index,error in enumerate(['Input validation error: private bad code',
                                      json.dumps({'tool_result':{'code':'input_contract_error','error':'private payload'}}),
                                      'Duplicate/case-colliding patch path']):
            self.part('part_bad_'+str(index),'msg_assistant',{'type':'tool','tool':'smelter_propose_coding_edits',
                'state':{'status':'error','error':error}},2200+index)
        value=self.native.metadata(self.task,[])
        self.assertTrue(value['protocol_error_burst']);self.assertEqual(value['protocol_errors'],3)
        self.assertNotIn('private',json.dumps(value,default=list))
        for index in range(12):
            self.part('part_ok_'+str(index),'msg_assistant',{'type':'tool','tool':'smelter_read_coding_file',
                'state':{'status':'completed','output':'private source'}},3000+index)
        self.assertFalse(self.native.metadata(self.task,[])['protocol_error_burst'])

    def test_child_access_and_busy_session_prevent_an_idle_root_retry(self):
        with closing(sqlite3.connect(self.path)) as db,db:db.execute('INSERT INTO session VALUES(?,?,?,?)',('ses_child','ses_root',str(self.root),1500))
        def rpc(task,route,body=None):
            if route=='/session/ses_root':return {'id':'ses_root','directory':str(self.root)}
            if route=='/session/status':return {'ses_child':{'type':'busy'}}
            if route=='/permission':return [{'sessionID':'ses_child'}]
            if route=='/question':return []
            raise AssertionError(route)
        with patch.object(self.native,'rpc',side_effect=rpc):value=self.native.snapshot(self.task,[])
        self.assertTrue(value['pending_access']);self.assertEqual(value['native_phase'],'busy_child')


if __name__=='__main__':unittest.main()
