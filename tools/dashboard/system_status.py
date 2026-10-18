"""SMELTER local, read-only system status. No subprocess or command execution."""
from __future__ import annotations
import os
import shutil
import time
from pathlib import Path
from database import inspect_database

def system_status(root: Path) -> dict:
    db = inspect_database(root)
    drive = Path.home().anchor or str(Path.home())
    disk = shutil.disk_usage(drive)
    return {
        "timestamp": int(time.time()),
        "database": {"status": db["status"], "path": db.get("database")},
        "services": {"dashboard": "running", "ollama": "check_via_models", "opencode": "not_started"},
        "storage": {"path": str(drive), "total_bytes": disk.total, "free_bytes": disk.free},
        "cpu": {"status": "not_instrumented"},
        "memory": {"status": "not_instrumented"},
        "gpu": {"status": "not_instrumented"},
        "read_only": True
    }
