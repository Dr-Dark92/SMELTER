"""AERO V0.1: deterministic task classification, preview only.

No model loading, tool execution, persistence, or filesystem access.
Unknown/ambiguous tasks are reported instead of inventing a classification.
"""
from __future__ import annotations

import re

DOMAINS = {
    "coding": ("python", "powershell", "code", "function", "unit test", "pytest", "debug script", "refactor", "api endpoint", "git commit"),
    "3d_modeling": ("blender", "mesh", "rigging", "rig", "uv map", "texture", "animation", "glb", "gltf", "armature", "bone weights"),
    "game_modding": ("game mod", "modding", "mod", "gta", "ark", "unreal engine", "asset conversion", "game asset", "plugin for game"),
    "reverse_engineering": ("reverse engineering", "disassemble", "binary analysis", "ghidra", "ida", "hex dump", "decompile", "file format", "firmware analysis"),
    "automation": ("automate", "automation", "scheduled job", "batch processing", "pipeline", "workflow", "cron", "task scheduler"),
}
COMPLEXITY = {
    "high": ("architecture redesign", "distributed system", "race condition", "memory corruption", "multi stage", "multi-stage", "cross engine", "cross-engine"),
    "medium": ("debug", "refactor", "integrate", "convert", "pipeline", "rigging", "decompile", "unit test"),
}


def classify_task(prompt):
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 4000:
        raise ValueError("Task must be nonempty text up to 4000 characters")
    normalized = " " + re.sub(r"[^a-z0-9]+", " ", prompt.lower()) + " "
    scores = {}
    evidence = {}
    for domain, phrases in DOMAINS.items():
        matches = [term for term in phrases if " " + term.replace("-", " ") + " " in normalized]
        if matches:
            scores[domain] = len(matches)
            evidence[domain] = matches
    ordered = sorted(scores, key=lambda d: (-scores[d], d))
    top = scores[ordered[0]] if ordered else 0
    tied = len(ordered) > 1 and scores[ordered[1]] == top
    primary = ordered[0] if ordered and not tied else None
    complexity = "low"
    for level in ("high", "medium"):
        if any(" " + term.replace("-", " ") + " " in normalized for term in COMPLEXITY[level]):
            complexity = level
            break
    return {
        "primary_domain": primary,
        "candidate_domains": ordered,
        "evidence": evidence,
        "ambiguous": bool(tied),
        "classification": "matched" if primary else ("ambiguous" if tied else "unknown"),
        "complexity_hint": complexity,
        "recommended_model": None,
        "model_switch_performed": False,
        "tools_executed": False,
        "read_only": True,
        "version": "aero-0.1",
    }
