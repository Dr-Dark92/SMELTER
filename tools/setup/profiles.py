"""Declarative SMELTER V1 profiles. Planning only: no installation commands."""
from __future__ import annotations

PROFILES = {
    "vanilla": {"label": "Vanilla", "requires": (), "description": "Python standard-library core"},
    "developer": {"label": "Developer", "requires": ("git", "node", "npm", "gh"), "description": "Git and JavaScript workflows"},
    "local_ai": {"label": "Local AI", "requires": ("ollama",), "description": "Optional local model runtime"},
    "game_modding": {"label": "Game Modding", "requires": ("blender", "ffmpeg", "7z"), "description": "Deferred game asset tools"},
}

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
