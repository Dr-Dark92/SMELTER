"""Atomic transcript/outcome finalization shared by both model engines."""
import json
import sqlite3
import time
from contextlib import closing,nullcontext
from chats import _db,EXECUTION_SCHEMA
from task_contract import outcome


def finalize(root,conversation_id,prompt,answer,execution,*,control=None,error=None,partial=False,cancelled=False,receipt='',cancel_answer=None):
    with control.lock if control else nullcontext():
        cancelled=cancelled or bool(control and control.cancelled.is_set())
        if cancelled:
            if cancel_answer is not None:answer=cancel_answer
            elif not answer.startswith('OpenCode request stopped.'):
                answer='OpenCode request stopped. Completed observations remain below.\n'+answer
        terminal=outcome(cancelled,error,partial)
        execution={**execution,'outcome':terminal['status'],'error':terminal['error'],'cancelled':cancelled,
                   'model_text':answer[:-len(receipt)] if receipt else answer}
        from workspace_tracking import task_snapshot
        tracking = task_snapshot(root, execution)
        if tracking:
            execution['workspace_tracking'] = tracking
        jid=getattr(control,'job_id',None)
        if jid:execution['job_id']=jid
        phase=None
        with closing(sqlite3.connect(_db(root),timeout=5)) as conn,conn:
            conn.execute('PRAGMA foreign_keys=ON')
            if not conn.execute('SELECT 1 FROM conversations WHERE id=?',(conversation_id,)).fetchone():raise ValueError('Conversation no longer exists')
            conn.execute("INSERT INTO messages(conversation_id,role,content) VALUES(?,'user',?)",(conversation_id,prompt.strip()))
            mid=conn.execute("INSERT INTO messages(conversation_id,role,content) VALUES(?,'assistant',?)",(conversation_id,answer)).lastrowid
            conn.execute(EXECUTION_SCHEMA)
            conn.execute('INSERT INTO message_execution(message_id,payload) VALUES(?,?)',(mid,json.dumps(execution)))
            if jid:
                from job_store import finalize_in_transaction
                phase=finalize_in_transaction(conn,jid,terminal,time.monotonic()-control.admitted_at)
        if control:
            control.terminal_result=terminal;control.completed=True
            control.journal_committed=bool(jid)
            if phase:control.phase=phase
        return {'reply':answer,'stored':True,**terminal}
