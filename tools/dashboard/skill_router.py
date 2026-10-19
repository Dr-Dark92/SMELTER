"""Deterministic, read-only skill suggestions based on user text.

No LLM, filesystem execution, or writes. Only ready installed skills may route.
Unknown tasks select nothing. Explicit user selections take precedence.
"""
from __future__ import annotations

import re
from skills_catalog import catalog_skills

KEYWORDS = {
    "documentation": ("documentation", "document", "readme", "handover", "report", "write docs", "technical writing"),
    "diagrams": ("diagram", "mermaid", "flowchart", "architecture chart", "sequence diagram", "data flow"),
}
MAX_AUTO_SKILLS = 2


def route_skills(root, prompt):
    if not isinstance(prompt, str):
        raise ValueError("Prompt must be text")
    words = " " + re.sub(r"[^a-z0-9]+", " ", prompt.lower()) + " "
    available = {s["id"] for s in catalog_skills(root)["skills"] if s["status"] == "ready"}
    scores = []
    for skill, keywords in KEYWORDS.items():
        if skill not in available:
            continue
        score = sum(1 for term in keywords if " " + term + " " in words)
        if score:
            scores.append((-score, skill))
    return [skill for _, skill in sorted(scores)[:MAX_AUTO_SKILLS]]
