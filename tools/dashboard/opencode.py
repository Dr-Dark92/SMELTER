"""SMELTER V1.5.2: read-only OpenCode installation diagnostics.

No agent sessions, prompts, repository access or shell execution.
"""
from __future__ import annotations
from pathlib import Path
from check_requirements import find_executable

def inspect_opencode(state: dict, tool_status: dict, finder=find_executable) -> dict:
    if "opencode" not in state.get("enabled", []):
        raise ValueError("OpenCode extension disabled")
    entry = tool_status.get("opencode")
    if entry is None:
        raise ValueError("OpenCode scanner result missing")
    status = entry.get("status")
    if status not in ("installed", "detected_unverified", "missing"):
        raise ValueError("Invalid OpenCode scanner status")
    executable = finder("opencode")
    suffix = Path(executable).suffix.lower() if executable else None
    return {
        "status": status,
        "detected": bool(executable),
        "entry_type": suffix,
        "version": entry.get("version") if status == "installed" else None,
        "execution_enabled": False,
        "project_access": False,
        "notes": ("Windows .cmd/.bat shims are not executed by the scanner; "
                  "detected_unverified does not mean OpenCode is broken."),
    }
