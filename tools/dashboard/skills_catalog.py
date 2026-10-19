"""Read-only discovery of SMELTER skills.

A skill is a directory directly beneath skills/ containing SKILL.md.
Discovery never executes skill content, follows symlinks, or writes files.
"""
from __future__ import annotations

from pathlib import Path
import re

MAX_SKILL_BYTES = 64 * 1024
MAX_SKILLS = 256


def catalog_skills(root):
    base = Path(root) / "skills"
    if not base.is_dir() or base.is_symlink():
        return {"skills": [], "count": 0, "read_only": True}
    found = []
    for folder in sorted(base.iterdir(), key=lambda p: p.name.casefold()):
        if len(found) >= MAX_SKILLS:
            break
        if folder.is_symlink() or not folder.is_dir() or folder.name.startswith("."):
            continue
        manifest = folder / "SKILL.md"
        if manifest.is_symlink() or not manifest.is_file():
            continue
        size = manifest.stat().st_size
        if size > MAX_SKILL_BYTES:
            found.append({"id": folder.name, "status": "oversized", "description": "", "bytes": size})
            continue
        try:
            text = manifest.read_text(encoding="utf-8")
        except (UnicodeError, OSError):
            found.append({"id": folder.name, "status": "unreadable", "description": "", "bytes": size})
            continue
        heading = re.search(r"^#\s+(.+?)\s*$", text, re.MULTILINE)
        purpose = re.search(r"^##\s+Purpose\s*$\n+([^#\n][^\n]*)", text, re.MULTILINE | re.IGNORECASE)
        valid = bool(heading and purpose)
        found.append({
            "id": folder.name,
            "name": heading.group(1).strip()[:120] if heading else folder.name,
            "description": purpose.group(1).strip()[:300] if purpose else "",
            "status": "ready" if valid else "incomplete",
            "bytes": size,
            "loaded_into_model": False,
            "executable": False,
        })
    return {"skills": found, "count": len(found), "read_only": True}
