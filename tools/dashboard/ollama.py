"""SMELTER V1.5.0: optional, read-only local Ollama model discovery.

No model downloads, prompts, or process launches. Loopback only.
"""
from __future__ import annotations
import json
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

URL = "http://127.0.0.1:11434/api/tags"
MAX_BYTES = 256 * 1024

def list_models(state: dict, tool_status: dict, opener=urlopen) -> dict:
    if "ollama" not in state.get("enabled", []):
        raise ValueError("Ollama extension disabled")
    if tool_status.get("ollama") != "installed":
        raise ValueError("Ollama executable not verified")
    request = Request(URL, headers={"Accept": "application/json"}, method="GET")
    try:
        with opener(request, timeout=3) as response:
            data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("Ollama response exceeds size limit")
        payload = json.loads(data)
        if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
            raise ValueError("Invalid Ollama model response")
        models = []
        for item in payload["models"]:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not isinstance(name, str) or not name or len(name) > 256:
                continue
            models.append({"name": name, "size": item.get("size") if type(item.get("size")) is int else None,
                           "modified_at": item.get("modified_at") if isinstance(item.get("modified_at"), str) else None})
        return {"status": "connected", "endpoint": "127.0.0.1:11434", "models": models[:200],
                "read_only": True, "executed": False}
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        return {"status": "unavailable", "endpoint": "127.0.0.1:11434",
                "models": [], "read_only": True, "executed": False,
                "error": type(error).__name__}
