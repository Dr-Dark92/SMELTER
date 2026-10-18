"""SMELTER V1.5.3: preview-only OpenCode/Ollama provider configuration.

Generates JSON in memory. Does not write OpenCode config or invoke an agent.
"""
from __future__ import annotations
from model_preferences import ROLES

def provider_preview(preferences: dict, discovery: dict, opencode: dict) -> dict:
    if opencode.get("status") not in ("installed", "detected_unverified") or not opencode.get("detected"):
        raise ValueError("OpenCode must be detected")
    if discovery.get("status") != "connected":
        raise ValueError("Ollama must be connected")
    installed = {item["name"] for item in discovery.get("models", [])}
    selections = preferences.get("models", {})
    if not selections or any(role not in ROLES or model not in installed for role, model in selections.items()):
        raise ValueError("Configure installed Ollama models first")
    # OpenCode uses the OpenAI-compatible provider via the local Ollama v1 API.
    # The provider's exact runtime compatibility is not verified by this preview.
    config = {"$schema": "https://opencode.ai/config.json",
              "provider": {"smelter_ollama": {
                  "npm": "@ai-sdk/openai-compatible",
                  "name": "SMELTER Local Ollama",
                  "options": {"baseURL": "http://127.0.0.1:11434/v1"},
                  "models": {model: {"name": model} for model in sorted(set(selections.values()))}
              }}}
    return {"status": "preview_ready", "config": config,
            "role_models": {role: "smelter_ollama/" + model for role, model in selections.items()},
            "written": False, "executed": False,
            "note": "Preview only; OpenCode provider/model compatibility has not been tested."}
