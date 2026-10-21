"""Durable job status; interrupted actions are never replayed automatically."""
import json
import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from database import chosen_database, inspect_database

SCHEMA='''CREATE TABLE IF NOT EXISTS task_jobs (
id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, engine TEXT NOT NULL,
state TEXT NOT NULL, payload TEXT NOT NULL, owner_pid INTEGER NOT NULL,
created REAL NOT NULL, updated REAL NOT NULL)'''


def _connect(root):
    if not inspect_database(root)['ready']:raise ValueError('Database is not ready')
    connection=sqlite3.connect(chosen_database(Path(root)),timeout=5)
    connection.execute(SCHEMA);connection.commit();return connection


def alive(pid):
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
        kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=kernel.OpenProcess(0x1000,False,pid)
        if handle:kernel.CloseHandle(handle);return True
        return ctypes.get_last_error()!=87  # access denied is not proof of death
    try:os.kill(pid,0);return True
    except ProcessLookupError:return False
    except PermissionError:return True


def identity(pid):
    """Distinguish PID reuse; unknown identity remains fail-closed."""
    try:
        if os.name!='nt':
            start=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19]
            return Path('/proc/sys/kernel/random/boot_id').read_text().strip()+':'+start
        import ctypes
        from ctypes import wintypes as w
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE
        kernel.GetProcessTimes.argtypes=[w.HANDLE,ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME),ctypes.POINTER(w.FILETIME)]
        kernel.CloseHandle.argtypes=[w.HANDLE]
        handle=kernel.OpenProcess(0x1000,False,pid)
        if not handle:return None
        try:
            created,exited,kernel_time,user_time=(w.FILETIME() for _ in range(4))
            if not kernel.GetProcessTimes(handle,ctypes.byref(created),ctypes.byref(exited),ctypes.byref(kernel_time),ctypes.byref(user_time)):return None
            return str((created.dwHighDateTime<<32)|created.dwLowDateTime)
        finally:kernel.CloseHandle(handle)
    except (OSError,ValueError,IndexError):return None


def recover(root):
    changed=[]
    with closing(_connect(root)) as conn,conn:
        for jid,pid,raw in conn.execute("SELECT id,owner_pid,payload FROM task_jobs WHERE state='running'").fetchall():
            payload=json.loads(raw);expected=payload.get('owner_identity');actual=identity(pid)
            if alive(pid) and not (expected is not None and actual is not None and expected!=actual):continue
            payload.update(state='interrupted',error='Dashboard process ended before completion. Actions were not replayed; inspect receipts and external processes.',phase='Interrupted',output_text='',tool_activity=[],files=[])
            conn.execute("UPDATE task_jobs SET state='interrupted',payload=?,updated=? WHERE id=?",(json.dumps(payload),time.time(),jid));changed.append(jid)
    return changed


def save(root,payload, *, admitting=False):
    safe={k:payload.get(k) for k in ('id','conversation_id','engine','state','error','policy_revision','configuration','phase','elapsed_seconds','prompt')}
    safe['owner_identity']=identity(os.getpid())
    now=time.time()
    with closing(_connect(root)) as conn,conn:
        conn.execute('BEGIN IMMEDIATE')
        if admitting and conn.execute("SELECT 1 FROM task_jobs WHERE state='running' LIMIT 1").fetchone():
            raise ValueError('Another live task already owns this database')
        conn.execute('INSERT INTO task_jobs VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET state=excluded.state,payload=excluded.payload,updated=excluded.updated',
                     (safe['id'],safe['conversation_id'],safe['engine'],safe['state'],json.dumps(safe),os.getpid(),now,now))
        conn.execute("DELETE FROM task_jobs WHERE state!='running' AND id NOT IN (SELECT id FROM task_jobs ORDER BY updated DESC LIMIT 500)")


def read(root,jid):
    recover(root)
    with closing(_connect(root)) as conn:
        row=conn.execute('SELECT payload FROM task_jobs WHERE id=?',(jid,)).fetchone()
    if not row:raise ValueError('Chat request not found')
    return {**json.loads(row[0]),'durable':True,'output_text':'','tool_activity':[],'files':[],
            'note':'Live chunks are memory-only. Persisted transcript and tool audit remain authoritative.'}


def active(root):
    recover(root)
    with closing(_connect(root)) as conn:
        return [r[0] for r in conn.execute("SELECT id FROM task_jobs WHERE state='running'")]


def list_jobs(root,limit=50):
    recover(root)
    with closing(_connect(root)) as conn:
        rows=conn.execute('SELECT payload FROM task_jobs ORDER BY updated DESC LIMIT ?',(limit,)).fetchall()
    return [json.loads(r[0]) for r in rows]


def admit(root,payload):
    return save(root,payload,admitting=True)


def finalize_in_transaction(conn,jid,terminal,elapsed):
    """Commit the admitted job outcome with its transcript, without a second write."""
    from task_contract import job_state
    row=conn.execute("SELECT payload FROM task_jobs WHERE id=? AND state='running'",(jid,)).fetchone()
    if not row:raise ValueError('Admitted job is missing or already finalized')
    payload=json.loads(row[0]);state=job_state(terminal)
    phase={'done':'Completed','cancelled':'Stopped','partial':'Partially completed','error':'Failed'}[state]
    payload.update(state=state,error=terminal.get('error'),phase=phase,elapsed_seconds=round(elapsed,1))
    conn.execute('UPDATE task_jobs SET state=?,payload=?,updated=? WHERE id=?',
                 (state,json.dumps(payload),time.time(),jid))
    return phase
