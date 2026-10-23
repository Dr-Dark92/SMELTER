"""Declarative SMELTER V1 profiles. Planning only: no installation commands."""
from __future__ import annotations

from requirements_catalog import CATALOG

# Profiles come from system-requirements.json at the repository root.
PROFILES = {name: {"label": p["label"], "requires": tuple(p.get("requires", ())), "description": p["description"]}
            for name, p in CATALOG["profiles"].items()}

def catalog() -> list[dict]:
    return [{"id": name, **{"label": value["label"], "description": value["description"],
                             "requires": list(value["requires"])}} for name, value in PROFILES.items()]

def resolve(selected: list[str], scan: dict) -> dict:
    if not isinstance(selected, list) or len(selected) > len(PROFILES):
        raise ValueError("Choose one or more known profiles")
    if any(not isinstance(name, str) or name not in PROFILES for name in selected):
        raise ValueError("Unknown profile")
    selected = list(dict.fromkeys(["vanilla", *selected]))
    tools = {item["name"]: item for item in scan["tools"]}
    requirements = sorted({tool for name in selected for tool in PROFILES[name]["requires"]})
    items = []
    for tool in requirements:
        observed = tools.get(tool, {"status": "missing", "version": None})
        items.append({"name": tool, "status": observed["status"], "version": observed.get("version"),
                      "action": "none" if observed["status"] == "installed" else "review_manually"})
    return {"profiles": selected, "dependencies": items,
            "install_actions": [], "downloads": False,
            "note": "Preview only. Optional dependencies are not installed by this version."}
