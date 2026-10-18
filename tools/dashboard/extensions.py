"""SMELTER V1.3 local extension catalog. No execution or installation."""
from __future__ import annotations

import json
from pathlib import Path

EXTENSIONS = {
    "blender": {"label": "Blender", "tool": "blender", "permissions": ["local_process"], "description": "3D asset preparation"},
    "ffmpeg": {"label": "FFmpeg", "tool": "ffmpeg", "permissions": ["local_process"], "description": "Media processing"},
    "7z": {"label": "7-Zip", "tool": "7z", "permissions": ["local_process"], "description": "Archive inspection"},
    "ollama": {"label": "Ollama", "tool": "ollama", "permissions": ["loopback_http_read"], "description": "Local model discovery (Qwen and other models)"},
}
DEFAULT = {"schema_version": 1, "enabled": []}

def load_state(path: Path) -> dict:
    if not path.exists():
        return dict(schema_version=1, enabled=[])
    state = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or state.get("schema_version") != 1:
        raise ValueError("Invalid extension state schema")
    enabled = state.get("enabled")
    if not isinstance(enabled, list) or any(not isinstance(x, str) or x not in EXTENSIONS for x in enabled) or len(set(enabled)) != len(enabled):
        raise ValueError("Invalid extension state")
    return {"schema_version": 1, "enabled": enabled}

def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    import os
    import tempfile
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=".extensions-", suffix=".tmp", delete=False) as tmp:
        tmp.write(json.dumps(state, indent=2) + "\n")
        temp = Path(tmp.name)
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)

def catalog(scan: dict, state: dict) -> list[dict]:
    statuses = {tool["name"]: tool["status"] for tool in scan["tools"]}
    result = []
    for key, value in EXTENSIONS.items():
        status = statuses.get(value["tool"], "missing")
        enabled = key in state["enabled"]
        health = "ready" if enabled and status == "installed" else (
            "dependency_unavailable" if enabled else (
                "available_disabled" if status == "installed" else "dependency_unavailable"
            )
        )
        result.append({"id": key, **value, "status": status, "enabled": enabled,
                       "health": health, "permission_granted": False})
    return result

def set_enabled(state: dict, extension_id: str, enabled: bool, scan: dict) -> dict:
    if extension_id not in EXTENSIONS or type(enabled) is not bool:
        raise ValueError("Unknown extension or invalid state")
    statuses = {tool["name"]: tool["status"] for tool in scan["tools"]}
    if enabled and statuses.get(EXTENSIONS[extension_id]["tool"]) != "installed":
        raise ValueError("Extension dependency is not verified")
    current = set(state["enabled"])
    if enabled:
        current.add(extension_id)
    else:
        current.discard(extension_id)
    return {"schema_version": 1, "enabled": sorted(current)}
