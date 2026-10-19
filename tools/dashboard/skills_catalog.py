"""Read-only discovery of SMELTER skills.

A skill is a directory directly beneath skills/ containing SKILL.md.
Discovery never executes skill content, follows symlinks, or writes files.
"""
from __future__ import annotations

from pathlib import Path
import re
from skill_manifest import parse_skill_manifest

MAX_SKILL_BYTES = 64 * 1024
MAX_SKILLS = 256


def catalog_skills(root):
    from skill_manager import enabled_map
    root = Path(root)
    state = enabled_map(root)
    found = []
    sources = ((root / "skills", "bundled"), (root / ".smelter" / "managed-skills", "managed"))
    seen = set()
    for base, source in sources:
        if not base.is_dir() or base.is_symlink():
            continue
        for folder in sorted(base.iterdir(), key=lambda p: p.name.casefold()):
            if len(found) >= MAX_SKILLS:
                break
            if folder.is_symlink() or not folder.is_dir() or folder.name.startswith(".") or folder.name in seen:
                continue
            manifest = folder / "SKILL.md"
            if manifest.is_symlink() or not manifest.is_file():
                continue
            seen.add(folder.name)
            size = manifest.stat().st_size
            status = "ready"
            name = folder.name
            description = ""
            if size > MAX_SKILL_BYTES:
                status = "oversized"
            else:
                try:
                    content = manifest.read_text(encoding="utf-8")
                    metadata = parse_skill_manifest(content)
                    name = metadata["name"] or folder.name
                    description = metadata["description"]
                    if not metadata["valid"]:
                        status = "incomplete"
                except (UnicodeError, OSError):
                    status = "unreadable"
            enabled = state.get(folder.name, True) and status == "ready"
            found.append({
                "id": folder.name, "name": name, "description": description,
                "status": status, "enabled": enabled, "source": source,
                "removable": source == "managed", "bytes": size,
                "loaded_into_model": False, "executable": False,
            })
    collections = root / ".smelter" / "managed-skills" / "collections"
    if collections.is_dir() and not collections.is_symlink():
        for group in sorted(collections.iterdir()):
            if group.is_symlink() or not group.is_dir():
                continue
            for folder in sorted(group.iterdir()):
                if len(found) >= MAX_SKILLS:
                    break
                if folder.is_symlink() or not folder.is_dir():
                    continue
                manifest = folder / "SKILL.md"
                if manifest.is_symlink() or not manifest.is_file():
                    continue
                skill_id = group.name + "/" + folder.name
                size = manifest.stat().st_size
                status = "ready" if size <= MAX_SKILL_BYTES else "oversized"
                meta = {"name": folder.name, "description": ""}
                if status == "ready":
                    try:
                        meta = parse_skill_manifest(manifest.read_text(encoding="utf-8"))
                        if not meta["valid"]:
                            status = "incomplete"
                    except (OSError, UnicodeError):
                        status = "unreadable"
                found.append({
                    "id": skill_id, "name": meta["name"] or folder.name,
                    "description": meta["description"], "status": status,
                    "enabled": state.get(skill_id, False) and status == "ready",
                    "source": "collection", "collection": group.name,
                    "removable": False, "bytes": size,
                    "loaded_into_model": False, "executable": False,
                })
    return {"skills": found, "count": len(found), "read_only": True}
