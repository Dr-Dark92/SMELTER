"""Persistent conversation notes in SMELTER's selected SQLite database.

This module stores text only. It does not invoke a model, execute commands,
or access project files.
"""
from __future__ import annotations
import sqlite3
import uuid
import json
from contextlib import closing
from pathlib import Path
from database import chosen_database, inspect_database

EXECUTION_SCHEMA = """CREATE TABLE IF NOT EXISTS message_execution (
message_id INTEGER PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
payload TEXT NOT NULL)"""

def _db(root: Path) -> Path:
    if not inspect_database(root)["ready"]:
        raise ValueError("Database not ready")
    return chosen_database(root)

def _id(value: str) -> str:
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Invalid conversation ID") from None

def list_chats(root: Path) -> dict:
    with closing(sqlite3.connect(_db(root))) as conn:
        rows = conn.execute("SELECT id,title,created_at FROM conversations ORDER BY created_at DESC, rowid DESC LIMIT 200").fetchall()
    return {"conversations": [{"id": i, "title": t, "created_at": d} for i,t,d in rows]}

def create_chat(root: Path, title: str = None) -> dict:
    if not isinstance(title, str) or not title.strip() or len(title) > 120:
        raise ValueError("Invalid title")
    cid = str(uuid.uuid4())
    with closing(sqlite3.connect(_db(root))) as conn, conn:
        conn.execute("INSERT INTO conversations(id,title) VALUES(?,?)", (cid, title.strip()))
    return {"id": cid, "title": title.strip()}

def read_chat(root: Path, cid: str, before=None, limit=1000) -> dict:
    cid = _id(cid)
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError('Page limit must be 1–1000')
    if before is not None:
        if isinstance(before, bool) or not str(before).isdigit() or not 0 < int(before) < 2**63:
            raise ValueError('Invalid message cursor')
        before = int(before)
    with closing(sqlite3.connect(_db(root))) as conn:
        row = conn.execute("SELECT title FROM conversations WHERE id=?", (cid,)).fetchone()
        if row is None:
            raise ValueError("Conversation not found")
        messages = conn.execute("SELECT id,role,content,created_at FROM messages WHERE conversation_id=? AND (? IS NULL OR id<?) ORDER BY id DESC LIMIT ?", (cid,before,before,limit+1)).fetchall()
        has_older = len(messages) > limit
        messages = list(reversed(messages[:limit]))
        page_ids = [m[0] for m in messages]
        page_placeholders = ','.join('?' for _ in page_ids) or 'NULL'
        has_execution = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='message_execution'").fetchone()
        evidence = dict(conn.execute("SELECT e.message_id,e.payload FROM message_execution e JOIN messages m ON m.id=e.message_id WHERE m.conversation_id=? AND m.id IN ("+page_placeholders+")", (cid,*page_ids))) if has_execution else {}
        has_models = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='model_attachments'").fetchone()
        models = {mid: {'id': aid, 'filename': filename, **json.loads(metadata)} for mid, aid, filename, metadata in conn.execute('SELECT a.message_id,a.id,a.filename,a.metadata FROM model_attachments a JOIN messages m ON m.id=a.message_id WHERE m.conversation_id=? AND m.id IN ('+page_placeholders+')', (cid,*page_ids))} if has_models else {}
    return {"id": cid, "title": row[0], 'has_older': has_older,
            'older_cursor': messages[0][0] if has_older and messages else None, "messages": [
        {"id": mid, "role": r, "content": c, "created_at": d,
         "execution": json.loads(evidence[mid]) if mid in evidence else None,
         "model_attachment": models.get(mid)}
        for mid,r,c,d in messages]}

def add_note(root: Path, cid: str, content: str) -> dict:
    cid = _id(cid)
    if not isinstance(content, str) or not content.strip() or len(content) > 1800:
        raise ValueError("Message must be 1–1800 characters")
    with closing(sqlite3.connect(_db(root))) as conn, conn:
        conn.execute("PRAGMA foreign_keys=ON")
        if conn.execute("SELECT 1 FROM conversations WHERE id=?", (cid,)).fetchone() is None:
            raise ValueError("Conversation not found")
        conn.execute("INSERT INTO messages(conversation_id,role,content) VALUES(?,'user',?)", (cid, content.strip()))
    return {"saved": True, "conversation_id": cid}

def rename_chat(root: Path, cid: str, title: str) -> dict:
    cid = _id(cid)
    if not isinstance(title, str) or not title.strip() or len(title) > 120:
        raise ValueError("Invalid title")
    with closing(sqlite3.connect(_db(root))) as conn, conn:
        if not conn.execute("UPDATE conversations SET title=? WHERE id=?", (title.strip(), cid)).rowcount:
            raise ValueError("Conversation not found")
    return {"id": cid, "title": title.strip()}

def delete_chat(root: Path, cid: str) -> dict:
    cid = _id(cid)
    attachments=[]
    with closing(sqlite3.connect(_db(root))) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='model_attachments'").fetchone():
            attachments=[r[0] for r in conn.execute('SELECT a.id FROM model_attachments a JOIN messages m ON m.id=a.message_id WHERE m.conversation_id=?',(cid,))]
            conn.execute('DELETE FROM model_attachments WHERE message_id IN (SELECT id FROM messages WHERE conversation_id=?)', (cid,))
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='message_execution'").fetchone():
            conn.execute("DELETE FROM message_execution WHERE message_id IN (SELECT id FROM messages WHERE conversation_id=?)", (cid,))
        conn.execute("DELETE FROM messages WHERE conversation_id=?", (cid,))
        if not conn.execute("DELETE FROM conversations WHERE id=?", (cid,)).rowcount:
            raise ValueError("Conversation not found")
    # SQL commits first. Interrupted/failed file cleanup is recoverable by maintenance.
    cleanup_errors=[]
    from python_tools import _plain_path
    for aid in attachments:
        try:_plain_path(Path(root)/'.smelter/model-assets'/(_id(aid)+'.glb')).unlink(missing_ok=True)
        except (OSError,ValueError):cleanup_errors.append(aid)
    return {'deleted':True,'attachments_removed':len(attachments)-len(cleanup_errors),'cleanup_pending':cleanup_errors}

