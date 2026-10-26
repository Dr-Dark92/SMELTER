"""SMELTER V1.6.1 bootstrap: user-selected SQLite location and readiness gate.

Legacy JSON files remain untouched. Database holds imported configuration snapshots
until the corresponding subsystems are migrated to database-backed storage.
"""
from __future__ import annotations
import json
import sqlite3
from contextlib import closing
from pathlib import Path

MARKER = ".smelter/database-location.json"
DB_NAME = "smelter.sqlite3"
CONFIG_FILES = ("extensions.json", "model_preferences.json")
SCHEMA = """CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS config_snapshots (name TEXT PRIMARY KEY, payload TEXT NOT NULL, imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS conversations (id TEXT PRIMARY KEY, title TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id TEXT NOT NULL REFERENCES conversations(id), role TEXT NOT NULL, content TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id,id);
"""

def marker_path(root: Path) -> Path:
    return root / MARKER

def chosen_database(root: Path) -> Path | None:
    marker = marker_path(root)
    if not marker.exists():
        return None
    data = json.loads(marker.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Invalid database location marker")
    location = data.get("path")
    if not isinstance(location, str) or not Path(location).is_absolute():
        raise ValueError("Invalid database location")
    db = Path(location)
    if db.name != DB_NAME or db.is_symlink() or db.parent.is_symlink():
        raise ValueError("Invalid database target")
    return db

def select_database(root: Path, directory: str) -> dict:
    if chosen_database(root) is not None:
        raise ValueError("Database already selected; relocation requires a separate migration")
    if not isinstance(directory, str) or not directory.strip() or len(directory) > 1024:
        raise ValueError("Choose an absolute database directory")
    folder = Path(directory.strip())
    if not folder.is_absolute() or folder.is_symlink():
        raise ValueError("Database directory must be absolute and not a symlink")
    if folder.resolve() == root.resolve() or root.resolve() in folder.resolve().parents:
        raise ValueError("Choose a database directory outside the SMELTER checkout")
    folder.mkdir(parents=True, exist_ok=True)
    db = folder / DB_NAME
    if db.is_symlink() or db.exists():
        raise ValueError("Database target already exists; refusing to overwrite")
    # Validate legacy data before creating any persistent database file.
    from config_store import _validate
    imported = []
    for name in CONFIG_FILES:
        legacy = root / ".smelter" / name
        if legacy.is_file() and not legacy.is_symlink():
            payload = json.loads(legacy.read_text(encoding="utf-8"))
            _validate(name, payload)
            imported.append((name, json.dumps(payload)))
    marker = marker_path(root)
    marker.parent.mkdir(parents=True, exist_ok=True)
    created_db = created_marker = False
    try:
        with db.open('xb'):
            created_db = True
        with closing(sqlite3.connect(db)) as connection, connection:
            connection.executescript(SCHEMA)
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("INSERT INTO metadata(key,value) VALUES('schema_version','1')")
            connection.executemany("INSERT INTO config_snapshots(name,payload) VALUES(?,?)", imported)
        with marker.open("x", encoding="utf-8") as stream:
            created_marker = True
            # Packaged Windows apps can redirect LocalAppData. Persist the
            # actual created file so native Melty/OpenCode sees the same DB.
            json.dump({"schema_version": 1, "path": str(db.resolve(strict=True))}, stream)
    except Exception:
        if created_marker:
            marker.unlink(missing_ok=True)
        if created_db:
            db.unlink(missing_ok=True)
        raise
    return {"status": "configured", "path": str(db.resolve(strict=True)), "legacy_files_preserved": True}

def inspect_database(root: Path, *, integrity=False) -> dict:
    db = chosen_database(root)
    if db is None:
        return {"status": "setup_required", "database": None, "ready": False}
    if not db.is_file():
        return {"status": "database_missing", "database": str(db), "ready": False}
    try:
        with closing(sqlite3.connect(db.resolve().as_uri()+'?mode=ro', uri=True, timeout=3)) as connection:
            schema = connection.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
            integrity_result = connection.execute("PRAGMA quick_check").fetchone() if integrity else ("not_requested",)
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        ready = schema == ("1",) and (not integrity or integrity_result == ("ok",)) and {"config_snapshots", "conversations", "messages"}.issubset(tables)
        return {"status": "ready" if ready else "invalid_schema", "database": str(db), "ready": ready, "integrity":integrity_result[0]}
    except sqlite3.Error as exc:
        return {"status": "database_error", "database": str(db), "ready": False, "error": str(exc)}
