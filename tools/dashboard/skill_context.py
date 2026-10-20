"""Bounded, read-only skill context for local Qwen conversations.

Skill manifests are project instructions, not system authority. Never execute
commands embedded in them. Explicit IDs only; no auto-selection yet.
"""
from __future__ import annotations

from pathlib import Path
import re
from skills_catalog import catalog_skills

MAX_SELECTED = 3
MAX_CONTEXT_CHARS = 48000
MAX_MANIFEST_BYTES = 64 * 1024
ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}(?:/[a-z][a-z0-9_-]{0,63})?$")


def build_skill_context(root, selected):
    if selected is None:
        selected = []
    if not isinstance(selected, list) or len(selected) > MAX_SELECTED:
        raise ValueError("Select at most three skills")
    if any(not isinstance(s, str) or not ID_PATTERN.fullmatch(s) for s in selected):
        raise ValueError("Invalid skill identifier")
    if len(set(selected)) != len(selected):
        raise ValueError("Duplicate skill identifier")
    known = {s["id"]: s for s in catalog_skills(root)["skills"] if s["status"] == "ready" and s["enabled"]}
    base = Path(root) / "skills"
    pieces = []
    for name in selected:
        if name not in known:
            raise ValueError("Skill unavailable or incomplete: " + name)
        folder = (base if known[name]["source"] == "bundled" else Path(root) / ".smelter" / "managed-skills") / name
        if known[name]["source"] == "collection":
            folder = Path(root) / ".smelter" / "managed-skills" / "collections" / name
        manifest = folder / "SKILL.md"
        if folder.is_symlink() or manifest.is_symlink() or not manifest.is_file():
            raise ValueError("Unsafe skill path")
        if manifest.stat().st_size > MAX_MANIFEST_BYTES:
            raise ValueError("Skill manifest too large")
        from skill_runtime import runtime_manifest
        snapshot = runtime_manifest(root, name)
        text = snapshot if snapshot is not None else manifest.read_text(encoding="utf-8")
        pieces.append("Skill: " + name + "\n" + text)
    context = "\n\n---\n\n".join(pieces)
    if len(context) > MAX_CONTEXT_CHARS:
        raise ValueError("Selected skills exceed context budget")
    return context
