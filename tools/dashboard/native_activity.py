"""Read-only OpenCode lifecycle metadata across HTTP and ACP processes.

This compatibility adapter selects named JSON fields in SQL. It never returns
message text, reasoning, prompts, tool arguments/results or error bodies.
"""
from datetime import datetime
from contextlib import closing
import os
from pathlib import Path
import sqlite3


class NativeActivity:
    def __init__(self, path=None):
        base = Path(os.environ['XDG_DATA_HOME']) if os.environ.get('XDG_DATA_HOME') else Path.home() / '.local/share'
        self.path = Path(path) if path else base / 'opencode/opencode.db'

    def poll(self, binding, cursor=None, since=None):
        from native_progress import same_directory, token
        from python_tools import _plain_path
        path = _plain_path(self.path)
        if not path.is_file():
            raise ValueError('Native activity metadata is unavailable')
        sid = token(binding['session_id'], 'ses')
        threshold = int(datetime.fromisoformat(since).timestamp()*1000) if since else 0
        cursor = cursor or {'time': threshold, 'id': ''}
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True, timeout=1)) as connection:
            connection.execute('PRAGMA query_only=ON')
            row = connection.execute('SELECT directory FROM session WHERE id=?', (sid,)).fetchone()
            if not row or not same_directory(row[0], binding['directory']):
                raise ValueError('Native database session does not match the bound directory')
            rows = connection.execute("""SELECT id,time_updated,json_extract(data,'$.callID'),
                json_extract(data,'$.tool'),json_extract(data,'$.state.status') FROM part
                WHERE session_id=? AND json_extract(data,'$.type')='tool'
                AND (time_updated>? OR (time_updated=? AND id>?))
                ORDER BY time_updated,id LIMIT 17""", (sid,cursor['time'],cursor['time'],cursor['id'])).fetchall()
            # Public lifecycle columns only; do not select message.data or part.data.
            latest = connection.execute("""SELECT id,time_created,time_updated,
                json_extract(data,'$.time.completed'),json_extract(data,'$.finish'),
                json_extract(data,'$.error.name') FROM message WHERE session_id=?
                AND json_extract(data,'$.role')='assistant' ORDER BY time_created DESC,id DESC LIMIT 1""", (sid,)).fetchone()
            user = connection.execute("""SELECT MAX(time_created) FROM message WHERE session_id=?
                AND json_extract(data,'$.role')='user'""", (sid,)).fetchone()[0]
        updates=[]
        for part_id,updated,call_id,tool,phase in rows[:16]:
            cursor={'time':updated,'id':part_id}
            updates.append({'id':'db_'+token(part_id)+'_'+str(updated),'type':'message.part.updated',
                'properties':{'sessionID':sid,'timestamp':updated,'part':{'sessionID':sid,'type':'tool',
                    'callID':call_id,'tool':tool,'state':{'status':phase}}}})
        phase='idle'
        if latest and (not user or latest[1]>=user):
            if latest[5]:phase='cancelled' if latest[5]=='MessageAbortedError' else 'failed'
            elif not latest[3] or latest[4]=='tool-calls':phase='busy'
        elif user:
            phase='busy'
        stamp=latest[2] if latest else user or 0
        identifier=latest[0] if latest else 'no_assistant'
        if phase in ('failed','cancelled'):
            state={'id':'dbstatus_'+token(identifier)+'_'+str(stamp),'type':'session.error',
                   'properties':{'sessionID':sid,'error':{'name':'MessageAbortedError' if phase=='cancelled' else 'UnknownError'}}}
        else:
            state={'id':'dbstatus_'+token(identifier)+'_'+str(stamp),'type':'session.status',
                   'properties':{'sessionID':sid,'status':{'type':phase}}}
        return {'events':updates,'cursor':cursor,'has_more':len(rows)>16,'phase':phase,'status_event':state,'status_time':stamp}
