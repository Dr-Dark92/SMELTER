"""Private prompt capture and durable, at-most-once recovery reservations."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import time
from uuid import uuid4

MAX_RETRIES=3
MAX_PROMPT=32768
MAX_TASKS=128
TERMINAL={'green','red','exhausted','cancelled','superseded'}


def process_running(pid,expected_identity):
    """An exited Windows process may retain its PID/creation-time handle."""
    from job_store import alive,identity
    if type(pid) is not int or pid<=0 or not expected_identity or not alive(pid) or identity(pid)!=expected_identity:return False
    import os
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes as w
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE
        kernel.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];kernel.GetExitCodeProcess.restype=w.BOOL
        kernel.CloseHandle.argtypes=[w.HANDLE]
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle:return False
        try:
            code=w.DWORD()
            return bool(kernel.GetExitCodeProcess(handle,ctypes.byref(code)) and code.value==259)
        finally:kernel.CloseHandle(handle)
    try:
        stat=Path('/proc')/str(pid)/'stat'
        if stat.is_file() and stat.read_text().rsplit(')',1)[1].split()[0]=='Z':return False
    except OSError:return False
    return True


def folder(root):
    from python_tools import _plain_path
    return _plain_path(Path(root).resolve()/'.smelter/watchdog')


def binding(root):
    from python_tools import _plain_path
    path=_plain_path(Path(root).resolve()/'.smelter/native-progress/state.json')
    if not path.is_file() or path.stat().st_size>2*1024*1024:raise ValueError('Native binding unavailable')
    value=json.loads(path.read_text(encoding='utf-8'))
    if value.get('source_root')!=str(Path(root).resolve()) or not value.get('binding'):raise ValueError('Native binding ownership mismatch')
    return value


def config(root):
    from python_tools import _plain_path
    path=_plain_path(folder(root)/'config.json')
    if not path.is_file():return {'enabled':False,'max_retries':MAX_RETRIES,'stall_seconds':300,'idle_grace_seconds':30,'poll_seconds':5}
    if path.stat().st_size>4096:raise ValueError('Watchdog config exceeds bound')
    value=json.loads(path.read_text(encoding='utf-8'))
    if value.get('source_root')!=str(Path(root).resolve()) or value.get('max_retries')!=MAX_RETRIES:raise ValueError('Watchdog configuration identity/limit mismatch')
    if type(value.get('enabled')) is not bool:raise ValueError('Watchdog enabled must be boolean')
    for key,low,high in [('stall_seconds',120,1800),('idle_grace_seconds',10,120),('poll_seconds',1,10)]:
        if type(value.get(key)) is not int or not low<=value[key]<=high:raise ValueError('Invalid watchdog interval')
    return value


def configure(root,enabled=True):
    from coding_workspace import _save
    base=folder(root);base.mkdir(parents=True,exist_ok=True)
    value={'schema_version':1,'source_root':str(Path(root).resolve()),'enabled':bool(enabled),'max_retries':MAX_RETRIES,
           'stall_seconds':300,'idle_grace_seconds':30,'poll_seconds':5}
    _save(base/'config.json',value)
    return value


class Store:
    def __init__(self,root):
        self.root=Path(root).resolve();base=folder(root);base.mkdir(parents=True,exist_ok=True)
        from python_tools import _plain_path
        self.path=_plain_path(base/'tasks.sqlite3')
        if self.path.exists() and self.path.stat().st_size>8*1024*1024:raise ValueError('Private watchdog database quota reached')
        with closing(self.connect()) as db,db:
            db.executescript('''CREATE TABLE IF NOT EXISTS tasks(
              id TEXT PRIMARY KEY,session_id TEXT NOT NULL,directory TEXT NOT NULL,workspace_id TEXT NOT NULL,
              binding_revision TEXT NOT NULL,origin_id TEXT NOT NULL,created REAL NOT NULL,origin_ms INTEGER NOT NULL,
              server_port INTEGER NOT NULL,native_pid INTEGER NOT NULL,native_identity TEXT,
              prompt TEXT,prompt_sha256 TEXT NOT NULL,model TEXT NOT NULL,agent TEXT,variant TEXT,
              request_options TEXT NOT NULL DEFAULT '{}',started INTEGER NOT NULL DEFAULT 0,
              state TEXT NOT NULL,retries INTEGER NOT NULL DEFAULT 0,next_retry REAL NOT NULL DEFAULT 0,
              reason TEXT,last_observed REAL,flag TEXT,flag_receipt TEXT,
              UNIQUE(session_id,origin_id));
            CREATE TABLE IF NOT EXISTS attempts(
              id TEXT PRIMARY KEY,task_id TEXT NOT NULL,number INTEGER NOT NULL,message_id TEXT UNIQUE NOT NULL,
              state TEXT NOT NULL,created REAL NOT NULL,updated REAL NOT NULL,UNIQUE(task_id,number));''')

    def connect(self):
        db=sqlite3.connect(self.path,timeout=2);db.row_factory=sqlite3.Row
        db.execute('PRAGMA secure_delete=ON');return db

    def current(self):
        with closing(self.connect()) as db:
            row=db.execute('SELECT * FROM tasks ORDER BY created DESC,rowid DESC LIMIT 1').fetchone()
            return dict(row) if row else None

    def attempts(self,task_id):
        with closing(self.connect()) as db:
            return [dict(r) for r in db.execute('SELECT * FROM attempts WHERE task_id=? ORDER BY number',(task_id,))]

    def capture(self,value,bound,*,rearm_legacy_red=False):
        from native_progress import same_directory,token
        b=bound['binding'];sid=token(value.get('session_id'),'ses');origin=token(value.get('message_id'),'msg')
        if not bound.get('enabled') or sid!=b['session_id'] or not same_directory(value.get('directory',''),b['directory']):raise ValueError('Prompt is outside the enabled bound task')
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            reserved=db.execute('SELECT a.*,t.state AS task_state,t.origin_id FROM attempts a JOIN tasks t ON t.id=a.task_id WHERE message_id=?',(origin,)).fetchone()
            if reserved:
                latest=db.execute('SELECT id FROM tasks ORDER BY created DESC,rowid DESC LIMIT 1').fetchone()
                if not latest or latest['id']!=reserved['task_id'] or reserved['task_state'] in TERMINAL or reserved['state'] not in ('reserved','unknown','sent'):
                    raise ValueError('Recovery reservation is no longer active')
                return {'status':'recovery_recognized','task_id':reserved['task_id']}
            if origin.startswith('msg_smelter_wd_'):raise ValueError('Unrecognized recovery message')
            text=value.get('text')
            if value.get('has_attachments') or not isinstance(text,str) or not text.strip() or len(text.encode('utf-8'))>MAX_PROMPT:raise ValueError('Watchdog captures text-only prompts up to 32 KiB')
            old=db.execute('SELECT * FROM tasks WHERE session_id=? AND origin_id=?',(sid,origin)).fetchone()
            if old:
                if old['prompt_sha256']!=hashlib.sha256(text.encode('utf-8')).hexdigest():raise ValueError('Captured prompt identity changed')
                if not rearm_legacy_red:return {'status':'already_captured','task_id':old['id']}
            elif rearm_legacy_red:raise ValueError('No legacy RED watch to rearm')
            model=value.get('model')
            if not isinstance(model,dict) or set(model)!={'providerID','modelID'} or any(not isinstance(s,str) or not 1<=len(s)<=160 for s in model.values()):raise ValueError('Original model identity required')
            for key in ('agent','variant'):
                if value.get(key) is not None and (not isinstance(value[key],str) or not re.fullmatch(r'[A-Za-z0-9_.:/ -]{1,160}',value[key])):raise ValueError('Invalid original model setting')
            options=value.get('request_options',{})
            if not isinstance(options,dict) or set(options)-{'tools','system','format'} or len(json.dumps(options).encode('utf-8'))>32768:raise ValueError('Original request options exceed supported bounds')
            if 'system' in options and (not isinstance(options['system'],str) or len(options['system'].encode('utf-8'))>16384):raise ValueError('Invalid original system override')
            if 'tools' in options and (not isinstance(options['tools'],dict) or len(options['tools'])>256 or any(not isinstance(k,str) or len(k)>200 or type(v) is not bool for k,v in options['tools'].items())):raise ValueError('Invalid original tool restrictions')
            if 'format' in options and not isinstance(options['format'],dict):raise ValueError('Invalid original output format')
            if type(value.get('server_port')) is not int or not 1<=value['server_port']<=65535 or type(value.get('native_pid')) is not int or value['native_pid']<=0:raise ValueError('Exact originating native process and port required')
            from job_store import identity
            native_identity=identity(value['native_pid'])
            if not native_identity:raise ValueError('Originating native process identity unavailable')
            if old:
                latest=db.execute('SELECT id FROM tasks ORDER BY created DESC,rowid DESC LIMIT 1').fetchone()
                if (not latest or latest['id']!=old['id'] or old['state']!='red' or old['reason']!='verified_end_flag'
                        or old['retries']>=MAX_RETRIES or old['workspace_id']!=b['workspace_id']
                        or old['binding_revision']!=bound['configuration_revision']
                        or old['native_pid']!=value['native_pid'] or old['native_identity']!=native_identity
                        or old['server_port']!=value['server_port']):
                    raise ValueError('Only the current legacy RED watch on its original backend can be rearmed')
                # Operator-only repair of the old receipt-as-end bug. The journal,
                # original identity and consumed retry budget remain unchanged.
                db.execute("UPDATE tasks SET state='watching',reason='legacy_red_rearmed',prompt=?,request_options=?,flag=NULL,flag_receipt=NULL,next_retry=0 WHERE id=?",
                           (text,json.dumps(options),old['id']))
                return {'status':'legacy_red_rearmed','task_id':old['id'],'retries':old['retries'],'max_retries':MAX_RETRIES}
            if db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]>=MAX_TASKS:raise ValueError('Watchdog task capacity reached; inspect private state')
            task_id=uuid4().hex;now=time.time();origin_ms=value.get('created_ms')
            if type(origin_ms) is not int or abs(origin_ms/1000-now)>300:origin_ms=int(now*1000)
            db.execute("UPDATE tasks SET state='superseded',reason='new_human_prompt',prompt=NULL,request_options='{}' WHERE state NOT IN ('green','red','exhausted','cancelled','superseded')")
            db.execute('''INSERT INTO tasks(id,session_id,directory,workspace_id,binding_revision,origin_id,created,origin_ms,
              server_port,native_pid,native_identity,prompt,prompt_sha256,model,agent,variant,request_options,state) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'watching')''',
              (task_id,sid,b['directory'],b['workspace_id'],bound['configuration_revision'],origin,now,origin_ms,
               value['server_port'],value['native_pid'],native_identity,text,
               hashlib.sha256(text.encode('utf-8')).hexdigest(),json.dumps(model),value.get('agent'),value.get('variant'),json.dumps(options)))
            return {'status':'captured','task_id':task_id,'max_retries':MAX_RETRIES}

    def update(self,task_id,state,reason,**fields):
        allowed={'next_retry','last_observed','flag','flag_receipt','started'}
        if set(fields)-allowed:raise ValueError('Unknown watchdog state field')
        with closing(self.connect()) as db,db:
            current=db.execute('SELECT state FROM tasks WHERE id=?',(task_id,)).fetchone()
            if not current or current['state'] in TERMINAL:return
            values={'state':state,'reason':reason,**fields}
            if state in TERMINAL:values.update(prompt=None,request_options='{}')
            db.execute('UPDATE tasks SET '+','.join(k+'=?' for k in values)+' WHERE id=?',(*values.values(),task_id))

    def reserve(self,task_id,now):
        with closing(self.connect()) as db,db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM tasks WHERE id=?',(task_id,)).fetchone()
            latest=db.execute('SELECT id FROM tasks ORDER BY created DESC,rowid DESC LIMIT 1').fetchone()
            if not row or not latest or latest['id']!=task_id or row['state'] in TERMINAL or row['retries']>=MAX_RETRIES or row['next_retry']>now:return None
            if db.execute("SELECT 1 FROM attempts WHERE task_id=? AND state IN ('reserved','unknown')",(task_id,)).fetchone():return None
            identity=uuid4().hex;number=row['retries']+1;message_id='msg_smelter_wd_'+identity
            db.execute('INSERT INTO attempts VALUES(?,?,?,?,?,?,?)',(identity,task_id,number,message_id,'reserved',now,now))
            db.execute("UPDATE tasks SET retries=?,state='dispatching',reason='stall_recovery_reserved' WHERE id=?",(number,task_id))
            return {'id':identity,'task_id':task_id,'number':number,'message_id':message_id}

    def delivery(self,attempt_id,state):
        if state not in ('sent','unknown','rejected'):raise ValueError('Invalid delivery state')
        with closing(self.connect()) as db,db:
            db.execute('UPDATE attempts SET state=?,updated=? WHERE id=?',(state,time.time(),attempt_id))

    def public(self):
        row=self.current()
        if not row:return {'state':'waiting_for_prompt','max_retries':MAX_RETRIES}
        return {k:row.get(k) for k in ('id','session_id','workspace_id','origin_id','prompt_sha256','state','retries','reason','last_observed','flag','flag_receipt','next_retry')}|{'max_retries':MAX_RETRIES}


def decide(task,observed,settings,now):
    """Only a quiet, verified idle backend can admit a continuation."""
    if task['state'] in TERMINAL:return 'none'
    if observed.get('cancelled'):return 'cancel'
    if observed.get('superseded'):return 'supersede'
    if not observed.get('available'):return 'wait_runtime'
    if observed.get('pending_access') or observed.get('pending_question'):return 'wait_human'
    if observed.get('active_tools'):return 'wait_tool_timeout' if now-observed.get('last_progress',now)>=settings['stall_seconds'] else 'wait_tool'
    if observed.get('native_phase')=='retry':return 'wait_provider'
    if observed.get('native_phase')!='idle':return 'wait_native_timeout' if now-observed.get('last_progress',now)>=settings['stall_seconds'] else 'wait_native'
    if not observed.get('turn_ended') and now-observed.get('last_progress',now)<settings['stall_seconds']:return 'wait_native'
    if observed.get('flag') in ('RED','GREEN'):return observed['flag'].lower()
    if observed.get('unrecognized_tool_domain'):return 'wait_scope_review'
    if now-observed.get('last_progress',now)<settings['idle_grace_seconds']:return 'wait_grace'
    if task['retries']>=MAX_RETRIES:return 'exhaust'
    if observed.get('protocol_error_burst'):return 'wait_tool_contract'
    if (observed.get('validation_progress') or {}).get('stalled'):return 'wait_validation_progress'
    if now<task.get('next_retry',0):return 'wait_cooldown'
    return 'retry'
