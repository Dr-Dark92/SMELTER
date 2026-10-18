"""SMELTER V1.5.1: validated, optional model preferences (no inference)."""
from __future__ import annotations
import json
import os
import tempfile
from pathlib import Path

ROLES = ("reasoning", "lightweight")
DEFAULT = {"schema_version": 1, "models": {}}

def load_preferences(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": 1, "models": {}}
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("Invalid model preferences")
    models = value.get("models")
    if not isinstance(models, dict) or any(
        key not in ROLES or not isinstance(name, str) or not name or len(name) > 256
        for key, name in models.items()
    ):
        raise ValueError("Invalid model preferences")
    return {"schema_version": 1, "models": dict(models)}

def save_preferences(path: Path, preferences: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                     prefix=".models-", suffix=".tmp", delete=False) as handle:
        temp = Path(handle.name)
        json.dump(preferences, handle, indent=2)
        handle.write("\n")
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)

def configure_model(path: Path, role: str, model: str, discovery: dict) -> dict:
    if role not in ROLES:
        raise ValueError("Unknown model role")
    if discovery.get("status") != "connected":
        raise ValueError("Ollama must be connected to configure models")
    installed = {item["name"] for item in discovery["models"]}
    if not isinstance(model, str) or model not in installed:
        raise ValueError("Model must be installed in Ollama")
    preferences = load_preferences(path)
    preferences["models"][role] = model
    save_preferences(path, preferences)
    return preferences

def configured_status(preferences: dict, discovery: dict) -> dict:
    installed = {item["name"] for item in discovery.get("models", [])}
    return {"preferences": preferences, "availability": {
        role: ("available" if discovery.get("status") == "connected" and model in installed
               else "unavailable") for role, model in preferences["models"].items()
    }, "inference_enabled": False}
