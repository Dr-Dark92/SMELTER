"""Persistent conversation notes in SMELTER's selected SQLite database.

This module stores text only. It does not invoke a model, execute commands,
or access project files.
"""
from __future__ import annotations
import sqlite3
import uuid
from contextlib import closing
from pathlib import Path
from database import chosen_database, inspect_database

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

def read_chat(root: Path, cid: str) -> dict:
    cid = _id(cid)
    with closing(sqlite3.connect(_db(root))) as conn:
        row = conn.execute("SELECT title FROM conversations WHERE id=?", (cid,)).fetchone()
        if row is None:
            raise ValueError("Conversation not found")
        messages = conn.execute("SELECT role,content,created_at FROM messages WHERE conversation_id=? ORDER BY id LIMIT 1000", (cid,)).fetchall()
    return {"id": cid, "title": row[0], "messages": [{"role": r, "content": c, "created_at": d} for r,c,d in messages]}

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
    with closing(sqlite3.connect(_db(root))) as conn, conn:
        conn.execute("DELETE FROM messages WHERE conversation_id=?", (cid,))
        if not conn.execute("DELETE FROM conversations WHERE id=?", (cid,)).rowcount:
            raise ValueError("Conversation not found")
    return {"deleted": True}

