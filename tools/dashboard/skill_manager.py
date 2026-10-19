"""Persistent SMELTER skill management.

Bundled skills remain immutable; managed skills live under .smelter/managed-skills.
Only SKILL.md text is accepted. No code, archives, or remote installation.
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
from skill_manifest import parse_skill_manifest

ID = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
MAX_CONTENT = 48 * 1024


def _paths(root):
    root = Path(root)
    return root / ".smelter" / "skill-state.json", root / ".smelter" / "managed-skills"


def _state(root):
    path, _ = _paths(root)
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or any(not isinstance(k, str) or not isinstance(v, bool) for k, v in data.items()):
        raise ValueError("Invalid skill state")
    return data


def enabled_map(root):
    return _state(root)


def _write_state(root, data):
    path, _ = _paths(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("Unsafe state path")
    temp = path.with_suffix(".tmp")
    if temp.is_symlink():
        raise ValueError("Unsafe temporary state path")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(temp, path)


def _safe_id(name):
    if not isinstance(name, str) or not ID.fullmatch(name):
        raise ValueError("Invalid skill ID")


def add_skill(root, name, content, approval=False):
    _safe_id(name)
    if approval is not True:
        raise ValueError("Explicit approval required")
    if not isinstance(content, str) or not content.strip() or len(content.encode("utf-8")) > MAX_CONTENT:
        raise ValueError("Invalid skill content or size")
    if not parse_skill_manifest(content)["valid"]:
        raise ValueError("SKILL.md requires recognizable name and description")
    state_path, base = _paths(root)
    bundled = Path(root) / "skills" / name
    if bundled.exists() or bundled.is_symlink():
        raise ValueError("Bundled skill ID is reserved")
    if base.is_symlink():
        raise ValueError("Unsafe managed skills directory")
    base.mkdir(parents=True, exist_ok=True)
    folder = base / name
    if folder.exists() or folder.is_symlink():
        raise ValueError("Skill already exists")
    folder.mkdir()
    (folder / "SKILL.md").write_text(content, encoding="utf-8")
    return {"id": name, "added": True, "enabled": True}


def set_skill_enabled(root, name, enabled, approval=False):
    if isinstance(name, str) and "/" in name:
        parts = name.split("/")
        if len(parts) != 2:
            raise ValueError("Invalid collection skill ID")
        for part in parts:
            _safe_id(part)
    else:
        _safe_id(name)
    if not isinstance(enabled, bool) or approval is not True:
        raise ValueError("Explicit approval and boolean enabled value required")
    from skills_catalog import catalog_skills
    known = {s["id"]: s for s in catalog_skills(root)["skills"]}
    if name not in known:
        raise ValueError("Skill not found")
    if enabled and known[name]["status"] != "ready":
        raise ValueError("Skill is not ready")
    state = _state(root)
    state[name] = enabled
    _write_state(root, state)
    return {"id": name, "enabled": enabled}


def remove_skill(root, name, approval=False):
    _safe_id(name)
    if approval is not True:
        raise ValueError("Explicit approval required")
    _, base = _paths(root)
    folder = base / name
    if base.is_symlink() or folder.is_symlink() or not folder.is_dir():
        raise ValueError("Only user-added skills can be removed")
    contents = list(folder.iterdir())
    if len(contents) != 1 or contents[0].name != "SKILL.md" or contents[0].is_symlink() or not contents[0].is_file():
        raise ValueError("Managed skill contains unexpected files; removal blocked")
    contents[0].unlink()
    folder.rmdir()
    state = _state(root)
    state.pop(name, None)
    _write_state(root, state)
    return {"id": name, "removed": True}
