"""Read-only host counters, storage and local Ollama allocation; no execution."""
from __future__ import annotations
import os
import shutil
import time
from pathlib import Path
from database import inspect_database
from resource_metrics import resource_status

def system_status(root: Path) -> dict:
    db = inspect_database(root)
    drive = str(root.resolve())
    disk = shutil.disk_usage(drive)
    return {
        "timestamp": int(time.time()),
        "database": {"status": db["status"], "path": db.get("database")},
        "services": {"dashboard": "running", "ollama": "check_via_models", "opencode": "not_checked"},
        "storage": {"path": str(drive), "total_bytes": disk.total, "free_bytes": disk.free},
        **resource_status(),
        "read_only": True
    }

