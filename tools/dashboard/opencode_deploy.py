"""V1.5.4: isolated, explicitly approved OpenCode provider config deployment.

Never writes to the user's OpenCode settings or SMELTER projects.
"""
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path

APPROVAL = "DEPLOY ISOLATED CONFIG"

def deploy_isolated_config(root: Path, preview: dict, approval: str) -> dict:
    if approval != APPROVAL:
        raise ValueError("Explicit DEPLOY ISOLATED CONFIG approval required")
    if preview.get("status") != "preview_ready" or preview.get("written") or preview.get("executed"):
        raise ValueError("A valid read-only provider preview is required")
    root = root.resolve()
    if root.name != "opencode-isolated" or root.parent.name != ".smelter":
        raise ValueError("Destination must be .smelter/opencode-isolated")
    if root.is_symlink() or root.parent.is_symlink():
        raise ValueError("Symlink destination is not supported")
    root.mkdir(parents=True, exist_ok=True)
    target = root / "opencode.json"
    if target.is_symlink():
        raise ValueError("Symlink config is not supported")
    # Never overwrite a previous deployment. Preserve it for manual review.
    if target.exists():
        raise ValueError("Isolated configuration already exists; no overwrite performed")
    payload = json.dumps(preview["config"], indent=2, ensure_ascii=False) + "\n"
    if len(payload.encode("utf-8")) > 32768:
        raise ValueError("Configuration exceeds size limit")
    # Exclusive create avoids clobbering even if another request races us.
    with target.open("x", encoding="utf-8") as handle:
        handle.write(payload)
    return {"status": "deployed", "path": str(target), "written": True,
            "executed": False, "agent_permissions": False,
            "note": "Isolated configuration only. OpenCode has not been launched."}
