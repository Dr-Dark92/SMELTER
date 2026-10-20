"""V1.6.2: SQLite-backed configuration with validated one-time legacy import."""
from __future__ import annotations
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from database import chosen_database, inspect_database

ALLOWED = {"extensions.json", "model_preferences.json", "runtime_settings.json", "access_policy.json"}

def _db(root: Path) -> Path:
    status = inspect_database(root)
    if not status["ready"]:
        raise ValueError("Database is not ready: " + status["status"])
    return chosen_database(root)

def load_config(root: Path, name: str) -> dict:
    if name not in ALLOWED:
        raise ValueError("Unknown configuration")
    with closing(sqlite3.connect(_db(root), timeout=5)) as conn:
        row = conn.execute("SELECT payload FROM config_snapshots WHERE name=?", (name,)).fetchone()
    if row is None:
        if name == 'access_policy.json':
            from access_policy import defaults
            return defaults(root)
        if name == 'runtime_settings.json':
            return {'schema_version': 1, 'settings': {}}
        return {"schema_version": 1, "enabled": []} if name == "extensions.json" else {"schema_version": 1, "models": {}}
    result = json.loads(row[0])
    _validate(name, result)
    return result

def _validate(name: str, value: dict) -> None:
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("Invalid configuration schema")
    if name == 'access_policy.json':
        from access_policy import validate
        validate(value)
    elif name == "extensions.json":
        from extensions import EXTENSIONS
        enabled = value.get("enabled")
        if not isinstance(enabled, list) or len(set(enabled)) != len(enabled) or any(not isinstance(x, str) or x not in EXTENSIONS for x in enabled):
            raise ValueError("Invalid extension configuration")
    elif name == 'runtime_settings.json':
        from runtime_settings import validate
        validate(value.get('settings'))
    else:
        from model_preferences import ROLES
        models = value.get("models")
        if not isinstance(models, dict) or any(k not in ROLES or not isinstance(v, str) or not v or len(v) > 256 for k,v in models.items()):
            raise ValueError("Invalid model configuration")

def save_config(root: Path, name: str, value: dict) -> None:
    if name not in ALLOWED:
        raise ValueError("Unknown configuration")
    _validate(name, value)
    payload = json.dumps(value, ensure_ascii=False)
    with closing(sqlite3.connect(_db(root), timeout=5)) as conn, conn:
        conn.execute("INSERT INTO config_snapshots(name,payload,imported_at) VALUES(?,?,CURRENT_TIMESTAMP) ON CONFLICT(name) DO UPDATE SET payload=excluded.payload,imported_at=CURRENT_TIMESTAMP", (name,payload))

