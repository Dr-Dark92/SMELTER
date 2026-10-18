"""SMELTER V1.4 workflow planner. Dry-run only; never executes tools."""
from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4
from extensions import EXTENSIONS

WORKFLOWS = {
    "asset_preflight": {
        "label": "Asset preflight",
        "description": "Validate archive, 3D and media tooling before an asset workflow.",
        "steps": [
            {"id": "archive", "label": "Inspect archive capability", "extension": "7z"},
            {"id": "model", "label": "Check 3D capability", "extension": "blender"},
            {"id": "media", "label": "Check media capability", "extension": "ffmpeg"},
        ],
    },
    "media_preflight": {
        "label": "Media preflight",
        "description": "Validate media-processing dependencies.",
        "steps": [{"id": "media", "label": "Check media capability", "extension": "ffmpeg"}],
    },
}

def definitions() -> list[dict]:
    return [{"id": key, **value} for key, value in WORKFLOWS.items()]

def plan(workflow_id: str, scan: dict, state: dict) -> dict:
    if not isinstance(workflow_id, str) or workflow_id not in WORKFLOWS:
        raise ValueError("Unknown workflow")
    statuses = {item["name"]: item["status"] for item in scan["tools"]}
    enabled = set(state["enabled"])
    steps = []
    for step in WORKFLOWS[workflow_id]["steps"]:
        extension = step["extension"]
        tool = EXTENSIONS[extension]["tool"]
        verified = statuses.get(tool) == "installed"
        active = extension in enabled
        steps.append({**step, "tool": tool, "tool_status": statuses.get(tool, "missing"),
                      "extension_enabled": active, "status": "ready" if verified and active else "blocked",
                      "reason": None if verified and active else (
                          "dependency not verified" if not verified else "extension disabled")})
    return {
        "run_id": str(uuid4()), "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "workflow_id": workflow_id, "mode": "dry_run",
        "status": "ready" if all(step["status"] == "ready" for step in steps) else "blocked",
        "steps": steps, "executed": False, "permissions_granted": False,
        "note": "Planning only. No files processed, no tools launched.",
    }
