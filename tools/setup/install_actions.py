"""SMELTER V1.2: safe, allowlisted dependency action planning.

No command from the browser is ever executed. This module only builds plans.
Execution is handled by the setup engine after exact-plan approval.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys

from requirements_catalog import CATALOG

# Package IDs are exact winget IDs from system-requirements.json; versions and
# publisher should be checked interactively by winget before acceptance. No
# silent or agreement flags.
WINGET_IDS = {name: tool["winget"] for name, tool in CATALOG["tools"].items() if "winget" in tool}

def build_actions(preview: dict, requested: list[str]) -> dict:
    if not isinstance(requested, list) or len(requested) > len(WINGET_IDS):
        raise ValueError("Invalid dependency selection")
    if any(not isinstance(x, str) for x in requested) or len(set(requested)) != len(requested):
        raise ValueError("Duplicate or invalid dependency names")
    dependencies = {d["name"]: d for d in preview["dependencies"]}
    if any(name not in dependencies for name in requested):
        raise ValueError("Dependency not part of selected profiles")
    if any(dependencies[name]["status"] == "installed" for name in requested):
        raise ValueError("Already installed dependency cannot be queued")
    if any(name not in WINGET_IDS for name in requested):
        raise ValueError("Dependency requires manual installation")
    if requested and (sys.platform != "win32" or shutil.which("winget") is None):
        raise ValueError("Automatic installation requires Windows and winget")
    actions = [{"name": name, "package_id": WINGET_IDS[name],
                "command": ["winget", "install", "--id", WINGET_IDS[name], "--exact", "--source", "winget"]
                           + (["--override", CATALOG["tools"][name]["winget_override"]] if "winget_override" in CATALOG["tools"][name] else [])}
               for name in requested]
    fingerprint = hashlib.sha256(json.dumps(actions, sort_keys=True).encode()).hexdigest()
    return {"actions": actions, "fingerprint": fingerprint,
            "notice": "winget may show publisher terms or request elevation. No silent acceptance is enabled."}
