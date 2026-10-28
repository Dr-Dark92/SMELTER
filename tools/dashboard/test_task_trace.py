from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import unittest
import threading
from types import SimpleNamespace
from unittest.mock import patch

from task_trace import TraceReader, classify, visible_path, LocalInspector, Monitor
import test_workspace_tracking


class TaskTraceTests(unittest.TestCase):
    def setUp(self):
        test_workspace_tracking.WorkspaceTrackingTests.setUp(self)
        self.path = Path(self.tmp.name) / 'trace.db'
        self.binding = {'session_id': 'ses_root', 'directory': str(self.root), 'workspace_id': self.sid}
        with closing(sqlite3.connect(self.path)) as db, db:
            db.executescript('CREATE TABLE session(id TEXT PRIMARY KEY,parent_id TEXT,directory TEXT,time_created INTEGER); CREATE TABLE message(id TEXT PRIMARY KEY,session_id TEXT,time_created INTEGER,time_updated INTEGER,data TEXT); CREATE TABLE part(id TEXT PRIMARY KEY,session_id TEXT,time_updated INTEGER,data TEXT);')
            for sid, parent, folder, stamp in [('ses_root', None, self.root, 100), ('ses_child', 'ses_root', self.root, 1100), ('ses_grandchild', 'ses_child', self.root, 1200), ('ses_old', 'ses_root', self.root, 500), ('ses_other', 'ses_root', self.root.parent, 1300)]:
                db.execute('INSERT INTO session VALUES(?,?,?,?)', (sid,parent,str(folder),stamp))
            db.execute('INSERT INTO message VALUES(?,?,?,?,?)', ('msg_user','ses_root',1000,1000,json.dumps({'role':'user','text':'private-prompt'})))
        self.reader = TraceReader(self.path)
        self.assistant()

    def test_recovery_error_classification_exposes_no_error_body(self):
        self.tool(status='error',error='recovery_required: private failure body')
        result=self.read()
        self.assertEqual(result['tools'][0]['error_code'],'recovery_required')
        self.assertNotIn('private failure body',json.dumps(result))

    def assistant(self, sid='ses_root', finish='tool-calls', error=None):
        data={'role':'assistant','finish':finish,'time':{'completed':None if finish=='tool-calls' else 1300},'error':error,
              'modelID':'qwen-fixture','providerID':'ollama','reasoning':'private-thought','text':'private-answer'}
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute('INSERT OR REPLACE INTO message VALUES(?,?,?,?,?)',('msg_'+sid,sid,1200,1300,json.dumps(data)))

    def tool(self, sid='ses_child', name='smelter_read_coding_file', status='running', inputs=None, error=None, stamp=1400):
        data={'type':'tool','callID':'call_'+name,'tool':name,'state':{'status':status,'time':{'start':1350},
            'input':inputs or {},'output':'private-output','error':error,'metadata':{'secret':'private-metadata'}}}
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute('INSERT OR REPLACE INTO part VALUES(?,?,?,?)',('prt_'+sid+'_'+name,sid,stamp,json.dumps(data)))

    def read(self): return self.reader.read(self.binding,self.target)

    def test_child_correlation_excludes_old_tasks_and_other_directories(self):
        result=self.read()
        self.assertEqual({s['session_id'] for s in result['sessions']},{'ses_root','ses_child','ses_grandchild'})
        self.assertEqual(result['native_turn_id'],'msg_user')

    def test_only_named_metadata_leaves_database_and_no_writes_occur(self):
        self.tool(inputs={'workspace_id':self.sid,'relative_path':'mods/demo/tests/fixture.hex','token':'private-secret'})
        before=hashlib.sha256(self.path.read_bytes()).hexdigest()
        result=self.read()
        self.assertNotIn('private-',json.dumps(result))
        self.assertEqual(before,hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual(result['tools'][0]['file'],str(self.target/'mods/demo/tests/fixture.hex'))
        self.assertEqual(next(s for s in result['sessions'] if s['session_id']=='ses_child')['state'],'using_tool')

    def test_paths_cannot_escape_and_wrong_workspace_cannot_claim_a_file(self):
        self.assertIsNone(visible_path('../secret',self.binding,self.target))
        self.assertIsNone(visible_path(str(self.root.parent/'secret'),self.binding,self.target))
        self.tool(inputs={'workspace_id':'unrelated','relative_path':'mods/demo/tests/fixture.hex'})
        self.assertIsNone(self.read()['tools'][0]['file'])

    def test_loaded_skill_and_budget_error_without_raw_arguments(self):
        self.tool(name='skill',status='completed',inputs={'name':'smelter-debugging','content':'private-source'})
        self.tool(name='smelter_run_coding_tests',status='error',error='private-error: tool call budget exhausted',stamp=1500)
        data=self.read();self.assertEqual(data['skills'],['smelter-debugging'])
        self.assertEqual(data['tools'][0]['error_code'],'tool_budget_exhausted')
        data['binding']=self.binding
        self.assertEqual(classify(data)['phase'],'tool_budget_exhausted')
        self.assertNotIn('private-',json.dumps(data))

    def test_access_wait_and_stall_timers_are_distinct_from_heartbeat(self):
        self.tool();data=self.read();data['binding']=self.binding
        data['permissions']=[{'session_id':'ses_child'}]
        current=datetime.fromtimestamp(200,timezone.utc)
        state=classify(data,current);self.assertEqual(state['phase'],'waiting_access');self.assertFalse(state['possible_stall'])
        data['permissions']=[];state=classify(data,current)
        self.assertEqual(state['phase'],'using_tool');self.assertTrue(state['possible_stall']);self.assertGreater(state['quiet_seconds'],120)
        self.assertIn('does not prove',state['hint'])

    def test_parent_completion_and_cancellation_override_leftover_child_tools(self):
        self.tool();self.assistant(finish='stop')
        data=self.read();data['binding']=self.binding
        self.assertEqual(classify(data)['phase'],'completed')
        self.assistant(finish='stop',error={'name':'MessageAbortedError','message':'private-error'})
        data=self.read();data['binding']=self.binding
        self.assertEqual(classify(data)['phase'],'cancelled')

    def test_finished_response_distinguishes_acceptance_failure_stale_checks_and_verified_scope(self):
        self.assistant(finish='stop');data=self.read();data['binding']=self.binding
        data['validation']=[{'profile':'lua','stage':'RED','current':True,'workspace_tests_stage':'GREEN','acceptance_stage':'RED'}]
        state=classify(data);self.assertEqual(state['phase'],'completed')
        self.assertEqual(state['task_outcome'],'changes_needed');self.assertIn('Frozen acceptance failed',state['outcome_hint'])
        data['validation']=[{'profile':'lua','stage':'GREEN','current':False}]
        self.assertEqual(classify(data)['task_outcome'],'not_verified')
        data['validation'][0]['current']=True
        self.assertEqual(classify(data)['task_outcome'],'checks_passed')

    def test_live_permissions_are_filtered_by_session_and_safe_paths(self):
        inspector=LocalInspector()
        def get(port,route,directory=None):
            if route.startswith('/session/'):return {'id':'ses_root','directory':str(self.root)}
            if route=='/permission':return [{'id':'per_child','sessionID':'ses_child','permission':'external_directory','patterns':[str(self.target/'mods/demo/tests')+'/*'],'metadata':{'secret':'private'}},{'id':'per_other','sessionID':'ses_unrelated','permission':'external_directory','patterns':['private']}]
            if route=='/question':return [{'id':'que_child','sessionID':'ses_child','questions':['private-question']}]
            return {'models':[{'name':'qwen-fixture','context_length':131072}]}
        with patch.object(inspector,'ports_now',return_value=[51748]),patch.object(inspector,'get',side_effect=get):
            data=inspector.inspect(self.binding,self.read()['sessions'],self.target)
        self.assertEqual([p['id'] for p in data['permissions']],['per_child'])
        self.assertEqual(data['ollama']['loaded_models'][0]['context_length'],131072)
        self.assertEqual(data['questions'],[{'id':'que_child','session_id':'ses_child'}])
        self.assertNotIn('private',json.dumps(data))

    def test_fresh_turn_id_and_optional_melty_id_are_never_confused(self):
        monitor=object.__new__(Monitor);monitor.root=self.root;monitor.reader=self.reader
        monitor.inspector=SimpleNamespace(inspect=lambda *args:{'permissions':[],'ollama':{'connection':'unavailable'}})
        native={'binding':self.binding,'enabled':True,'configuration_revision':'rev'}
        with patch('native_progress.manager',return_value=SimpleNamespace(view=lambda:native)):
            value=monitor.collect();self.assertEqual(value['task_id'],'msg_user');self.assertIn('not supplied',value['task_id_source'])
            native['binding']={**self.binding,'melty_task_id':'melty-real-task'}
            value=monitor.collect();self.assertEqual(value['task_id'],'melty-real-task');self.assertEqual(value['native_turn_id'],'msg_user')

    def test_stale_collector_is_not_misreported_as_task_deadlock(self):
        monitor=object.__new__(Monitor);monitor.root=self.root;monitor.lock=threading.RLock()
        monitor.value={**self.read(),'binding':self.binding,'enabled':True,'available':True,'permissions':[],
            'observed_at':'2020-01-01T00:00:00+00:00'}
        native={'binding':self.binding,'enabled':True}
        with patch('native_progress.manager',return_value=SimpleNamespace(view=lambda:native)):
            value=monitor.view()
        self.assertTrue(value['observations_stale']);self.assertEqual(value['status']['phase'],'telemetry_delayed')
        self.assertFalse(value['status']['possible_stall'])

    def test_supplied_task_id_correlation_preserves_session_and_cycle(self):
        import test_native_progress
        test_native_progress.NativeProgressTests.setUp(self)
        before=self.bridge.view()
        linked=self.bridge.correlate('melty-fixture-task',before['configuration_revision'])
        self.assertEqual(linked['binding']['session_id'],before['binding']['session_id'])
        self.assertEqual(linked['cycle'],before['cycle'])
        self.assertEqual(linked['binding']['melty_task_id'],'melty-fixture-task')
        with self.assertRaises(ValueError):self.bridge.correlate('other',before['configuration_revision'])


if __name__=='__main__':unittest.main()
