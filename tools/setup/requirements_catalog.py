"""Load the machine-readable SMELTER requirements file (standard library only).

The scanner, profiles and winget queue all read system-requirements.json at the
repository root, so tools and profiles are declared in one place.
"""
from __future__ import annotations

import json
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parents[2] / "system-requirements.json"


def load(path: Path = CATALOG_PATH) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError(f"Unsupported requirements schema in {path}")
    tools, profiles = data.get("tools"), data.get("profiles")
    if not isinstance(tools, dict) or not isinstance(profiles, dict) or "vanilla" not in profiles:
        raise ValueError(f"Requirements file {path} needs tools and a vanilla profile")
    for name, tool in tools.items():
        check = tool.get("check")
        if not isinstance(check, list) or not check or not all(isinstance(x, str) for x in check):
            raise ValueError(f"Tool {name} needs a check command list")
        if tool.get("policy") not in ("recommended", "optional"):
            raise ValueError(f"Tool {name} has an unknown policy")
        if "winget" in tool and not isinstance(tool["winget"], str):
            raise ValueError(f"Tool {name} has an invalid winget ID")
    for name, profile in profiles.items():
        unknown = [tool for tool in profile.get("requires", []) if tool not in tools]
        if unknown:
            raise ValueError(f"Profile {name} requires unknown tools: {', '.join(unknown)}")
    return data


CATALOG = load()
