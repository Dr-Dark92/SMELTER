import hashlib
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from native_activity import NativeActivity
import native_progress
import test_native_progress


class ActivityFixture:
    def __init__(self, path, directory, sid='ses_activity'):
        self.path=path; self.directory=directory; self.sid=sid
        with closing(sqlite3.connect(path)) as connection,connection:
            connection.executescript('CREATE TABLE session(id TEXT PRIMARY KEY,directory TEXT); CREATE TABLE message(id TEXT PRIMARY KEY,session_id TEXT,time_created INTEGER,time_updated INTEGER,data TEXT); CREATE TABLE part(id TEXT PRIMARY KEY,session_id TEXT,time_updated INTEGER,data TEXT);')
            connection.execute('INSERT INTO session VALUES(?,?)',(sid,str(directory)))

    def message(self, phase='tool-calls', completed=True, stamp=200):
        with closing(sqlite3.connect(self.path)) as connection,connection:
            connection.execute('INSERT OR REPLACE INTO message VALUES(?,?,?,?,?)',('msg_user',self.sid,100,100,json.dumps({'role':'user','text':'private-prompt'})))
            data={'role':'assistant','finish':phase,'time':{'completed':stamp if completed else None},'text':'private-answer','reasoning':'private-reasoning'}
            connection.execute('INSERT OR REPLACE INTO message VALUES(?,?,?,?,?)',('msg_assistant',self.sid,150,stamp,json.dumps(data)))

    def tool(self, identifier='prt_a', phase='running', stamp=201, kind='tool'):
        with closing(sqlite3.connect(self.path)) as connection,connection:
            connection.execute('INSERT OR REPLACE INTO part VALUES(?,?,?,?)',(identifier,self.sid,stamp,json.dumps({'type':kind,'callID':'call_'+identifier,'tool':'smelter_read_coding_file','state':{'status':phase,'input':{'token':'private-secret'},'output':'private-output','error':'private-error'},'text':'private-reasoning'})))

    @property
    def binding(self):return {'session_id':self.sid,'directory':str(self.directory)}


class NativeActivityTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.folder=Path(tmp.name);self.path=self.folder/'native.db'
        self.fixture=ActivityFixture(self.path,self.folder)
        self.reader=NativeActivity(self.path)

    def test_only_allowlisted_lifecycle_columns_are_returned_and_database_is_unchanged(self):
        self.fixture.message(completed=False);self.fixture.tool();self.fixture.tool('prt_hidden',kind='reasoning',stamp=999)
        before=hashlib.sha256(self.path.read_bytes()).hexdigest()
        result=self.reader.poll(self.fixture.binding)
        self.assertEqual(result['phase'],'busy');self.assertEqual(len(result['events']),1)
        self.assertNotIn('private-',json.dumps(result))
        self.assertEqual(before,hashlib.sha256(self.path.read_bytes()).hexdigest())

    def test_tool_call_turn_is_busy_and_stop_turn_is_idle(self):
        self.fixture.message();self.assertEqual(self.reader.poll(self.fixture.binding)['phase'],'busy')
        self.fixture.message('stop');self.assertEqual(self.reader.poll(self.fixture.binding)['phase'],'idle')

    def test_same_part_update_is_observed_with_a_new_timestamp(self):
        self.fixture.message();self.fixture.tool(stamp=201)
        first=self.reader.poll(self.fixture.binding)
        self.assertEqual(self.reader.poll(self.fixture.binding,first['cursor'])['events'],[])
        self.fixture.tool(phase='completed',stamp=202)
        second=self.reader.poll(self.fixture.binding,first['cursor'])
        self.assertEqual(second['events'][0]['properties']['part']['state']['status'],'completed')

    def test_session_directory_is_verified(self):
        with self.assertRaisesRegex(ValueError,'does not match'):
            self.reader.poll({**self.fixture.binding,'directory':str(self.folder/'other')})

    def test_backfill_is_bounded_and_resumes_without_skipping_rows(self):
        for i in range(20):self.fixture.tool('prt_'+str(i).zfill(3),stamp=200+i)
        first=self.reader.poll(self.fixture.binding);self.assertTrue(first['has_more']);self.assertEqual(len(first['events']),16)
        second=self.reader.poll(self.fixture.binding,first['cursor']);self.assertFalse(second['has_more']);self.assertEqual(len(second['events']),4)

    def test_schema_mismatch_fails_closed(self):
        with closing(sqlite3.connect(self.path)) as connection,connection:connection.execute('DROP TABLE part')
        with self.assertRaises(sqlite3.Error):self.reader.poll(self.fixture.binding)


class CrossProcessProgressTests(unittest.TestCase):
    def test_new_binding_does_not_complete_an_old_cancelled_task(self):
        test_native_progress.NativeProgressTests.setUp(self)
        self.bridge.close()
        path=Path(self.tmp.name)/'cancelled.db';fixture=ActivityFixture(path,self.native,test_native_progress.SID)
        fixture.message('stop')
        with closing(sqlite3.connect(path)) as connection,connection:
            connection.execute("UPDATE message SET data=json_set(data,'$.error',json(?)) WHERE id='msg_assistant'",(json.dumps({'name':'MessageAbortedError','message':'private-error'}),))
        bridge=native_progress.Bridge(self.root,test_native_progress.Metadata,activity=lambda:NativeActivity(path))
        self.addCleanup(bridge.close)
        with patch.object(bridge,'_start'):
            bridge.bind({'session_id':test_native_progress.SID,'directory':str(self.native),'workspace_id':self.sid,'expected_revision':bridge.view()['configuration_revision']})
        worker=threading.Thread(target=bridge._activity_run,daemon=True);worker.start()
        try:
            deadline=time.monotonic()+4
            while time.monotonic()<deadline and bridge.view()['task_state']!='cancelled':time.sleep(.03)
            self.assertEqual(bridge.view()['task_state'],'cancelled')
            self.assertEqual(bridge.view()['completions'],[])
        finally:bridge.close();worker.join(3)

    def test_acp_activity_is_visible_when_the_http_process_has_no_activity(self):
        test_native_progress.NativeProgressTests.setUp(self)
        self.bridge.close()
        path=Path(self.tmp.name)/'acp.db';fixture=ActivityFixture(path,self.native,test_native_progress.SID)
        fixture.message(completed=False,stamp=int(time.time()*1000)+10)
        bridge=native_progress.Bridge(self.root,test_native_progress.Metadata,activity=lambda:NativeActivity(path))
        self.addCleanup(bridge.close)
        with patch.object(bridge,'_start'):
            bridge.bind({'session_id':test_native_progress.SID,'directory':str(self.native),'workspace_id':self.sid,'expected_revision':bridge.view()['configuration_revision']})
        fixture.tool(stamp=int(time.time()*1000)+20)
        worker=threading.Thread(target=bridge._activity_run,daemon=True);worker.start()
        try:
            deadline=time.monotonic()+6
            while time.monotonic()<deadline and bridge.view()['task_state']!='busy':time.sleep(.03)
            value=bridge.view();self.assertEqual(value['task_state'],'busy');self.assertEqual(value['connection'],'connected')
            self.assertEqual(value['events'][-1]['source'],'native_database')
            fixture.tool(phase='completed',stamp=int(time.time()*1000)+30);fixture.message('stop',stamp=int(time.time()*1000)+40)
            deadline=time.monotonic()+8
            while time.monotonic()<deadline and not bridge.view()['completions']:time.sleep(.03)
            self.assertEqual(bridge.view()['task_state'],'idle');self.assertTrue(bridge.view()['completions'])
            self.assertNotIn('private-',native_progress._path(self.root).read_text())
        finally:bridge.close();worker.join(3)


if __name__=='__main__':unittest.main()
