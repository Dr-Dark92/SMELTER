"""Deterministic, read-only skill suggestions based on user text.

No LLM, filesystem execution, or writes. Only ready installed skills may route.
Unknown tasks select nothing. Explicit user selections take precedence.
"""
from __future__ import annotations

import re
from skills_catalog import catalog_skills

KEYWORDS = {
    "project-knowledge": ("web search", "internet", "remember", "project memory", "recall", "current documentation", "research"),
    "engine-archive": ("iostore", "utoc", "repak", "retoc", "serializedfile", "unity archive", "archive inspection", "assetbundle"),
    "universal-modder": ("universal modder", "um scan", "field notes", "universal modding tool"),
    "game-modding": ("modding", "game mod", "mashup", "unreal", "ue4", "ue5", "il2cpp", "unity assets", "godot pck"),
    "mod-validation": ("test mod", "native mod", "camera link", "lua mod", "cross compile"),
    "documentation": ("documentation", "document", "readme", "handover", "report", "write docs", "technical writing"),
    "diagrams": ("diagram", "mermaid", "flowchart", "architecture chart", "sequence diagram", "data flow"),
}
MAX_AUTO_SKILLS = 2


def route_skills(root, prompt):
    if not isinstance(prompt, str):
        raise ValueError("Prompt must be text")
    words = " " + re.sub(r"[^a-z0-9]+", " ", prompt.lower()) + " "
    available = {s["id"] for s in catalog_skills(root)["skills"] if s["status"] == "ready" and s["enabled"]}
    from skill_runtime import active_ids
    active = active_ids(root)
    if active is not None:
        available &= active
    scores = []
    for skill, keywords in KEYWORDS.items():
        if skill not in available:
            continue
        score = sum(1 for term in keywords if " " + term + " " in words)
        if score:
            scores.append((-score, skill))
    return [skill for _, skill in sorted(scores)[:MAX_AUTO_SKILLS]]

