"""SMELTER V1.5.5: offline validation of staged OpenCode configuration.

No subprocess, network, package install, or modification of staged config.
"""
from __future__ import annotations
import json
from pathlib import Path

MAX_CONFIG_BYTES = 32768
PROVIDER = "smelter_ollama"
ENDPOINT = "http://127.0.0.1:11434/v1"

def validate_staged_config(root: Path, preferences: dict, discovery: dict) -> dict:
    if root.name != "opencode-isolated" or root.parent.name != ".smelter":
        raise ValueError("Unexpected isolated configuration directory")
    if root.is_symlink() or root.parent.is_symlink():
        raise ValueError("Symlink directory refused")
    target = root / "opencode.json"
    if target.is_symlink() or not target.is_file():
        raise ValueError("Isolated configuration missing or symlink")
    if target.stat().st_size > MAX_CONFIG_BYTES:
        raise ValueError("Configuration exceeds size limit")
    config = json.loads(target.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("Invalid configuration object")
    provider = config.get("provider", {}).get(PROVIDER)
    if not isinstance(provider, dict):
        raise ValueError("Missing SMELTER Ollama provider")
    if provider.get("npm") != "@ai-sdk/openai-compatible":
        raise ValueError("Unexpected provider package")
    if provider.get("options", {}).get("baseURL") != ENDPOINT:
        raise ValueError("Unexpected provider endpoint")
    models = provider.get("models")
    if not isinstance(models, dict) or not models:
        raise ValueError("No configured models")
    installed = {item["name"] for item in discovery.get("models", [])}
    selected = set(preferences.get("models", {}).values())
    configured = set(models)
    if discovery.get("status") != "connected":
        raise ValueError("Ollama disconnected")
    if not selected or not configured.issubset(installed):
        raise ValueError("Configured model unavailable")
    stale = configured != selected
    return {"status": "valid_stale_preferences" if stale else "valid",
            "path": str(target), "configured_models": sorted(configured),
            "selected_models": sorted(selected), "preferences_stale": stale,
            "schema_checked": True, "opencode_runtime_verified": False,
            "written": False, "executed": False,
            "note": "Static validation only; OpenCode v1.19.3 compatibility still requires isolated runtime testing."}
