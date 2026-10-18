"""V1.6.2 startup preflight; no services launched without permission."""
from __future__ import annotations
from pathlib import Path
from database import inspect_database

def startup_report(root: Path, scan_tools, ollama_probe) -> dict:
    db = inspect_database(root)
    checks = [{"name": "database", "status": db["status"], "required": True}]
    if not db["ready"]:
        return {**db, "checks": checks, "services": {"dashboard": "running", "ollama": "not_started", "opencode": "not_started"}}
    try:
        tools = scan_tools()
        statuses = {item["name"]: item["status"] for item in tools["tools"]}
        checks.append({"name": "tools", "status": "inspected", "required": False, "details": statuses})
    except (OSError, ValueError, KeyError) as exc:
        checks.append({"name": "tools", "status": "degraded", "required": False, "error": str(exc)})
        statuses = {}
    try:
        from config_store import load_config
        config = load_config(root, "extensions.json")
        checks.append({"name": "configuration", "status": "valid", "required": True, "extensions": config["enabled"]})
        models = load_config(root, "model_preferences.json")
        checks.append({"name": "model_preferences", "status": "valid", "required": True, "models": models["models"]})
    except (ValueError, OSError) as exc:
        checks.append({"name": "configuration", "status": "invalid", "required": True, "error": str(exc)})
    try:
        discovery = ollama_probe(config if "config" in locals() else {"enabled": []}, statuses)
        checks.append({"name": "ollama", "status": discovery.get("status", "unknown"), "required": False})
    except (ValueError, OSError, KeyError) as exc:
        checks.append({"name": "ollama", "status": "degraded", "required": False, "error": str(exc)})
    ready = db["ready"] and all(x["status"] == "valid" for x in checks if x["required"] and x["name"] != "database")
    return {**db, "ready": ready, "status": "ready" if ready else "validation_failed",
            "checks": checks, "services": {"dashboard": "running", "ollama": "health_checked_only", "opencode": "not_started"}}
