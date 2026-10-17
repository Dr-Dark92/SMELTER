"""SMELTER reusable capability and skill registry (standard library only).

Capabilities are declarative, and the registry never executes commands from skill text.
External integrations must be explicitly registered by trusted Python code.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
import json

@dataclass(frozen=True)
class Capability:
    name: str
    description: str
    parameters: dict[str, str]
    handler: Callable[[dict[str, Any]], dict[str, Any]]
    read_only: bool = True

class Registry:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.capabilities: dict[str, Capability] = {}

    def register(self, capability: Capability) -> None:
        if not capability.name or capability.name in self.capabilities:
            raise ValueError("Duplicate or invalid capability")
        self.capabilities[capability.name] = capability

    def catalog(self, *, read_only: bool = False) -> list[dict[str, Any]]:
        return [
            {"id": c.name, "description": c.description, "parameters": c.parameters, "read_only": c.read_only}
            for c in sorted(self.capabilities.values(), key=lambda c: c.name)
            if not read_only or c.read_only
        ]

    def invoke(self, name: str, arguments: dict[str, Any], *, allow_writes: bool = False) -> dict[str, Any]:
        if name not in self.capabilities:
            raise ValueError("Unknown capability: " + name)
        c = self.capabilities[name]
        if not c.read_only and not allow_writes:
            raise PermissionError("Write capability requires explicit authorization")
        if not isinstance(arguments, dict):
            raise TypeError("Capability arguments must be a JSON object")
        missing = set(c.parameters) - set(arguments)
        unexpected = set(arguments) - set(c.parameters)
        if missing or unexpected:
            raise ValueError(f"Argument mismatch: missing={sorted(missing)}, unexpected={sorted(unexpected)}")
        for k, expected in c.parameters.items():
            v = arguments[k]
            valid = {"string": lambda x: isinstance(x, str), "object": lambda x: isinstance(x, dict),
                     "array": lambda x: isinstance(x, list), "boolean": lambda x: isinstance(x, bool),
                     "integer": lambda x: isinstance(x, int) and not isinstance(x, bool)}
            if expected not in valid or not valid[expected](v):
                raise TypeError(f"Invalid type for {k}: expected {expected}")
        result = c.handler(arguments)
        if not isinstance(result, dict):
            raise TypeError("Capability must return a JSON object")
        json.dumps(result)
        return result

    def skills(self) -> list[dict[str, str]]:
        base = self.root / ".agents" / "skills"
        found = []
        if not base.is_dir():
            return found
        for child in sorted(base.iterdir()):
            path = child / "SKILL.md"
            if not path.is_file():
                continue
            raw = path.read_text(encoding="utf-8-sig", errors="replace")
            description = ""
            if raw.startswith("---"):
                parts = raw.split("---", 2)
                if len(parts) == 3:
                    for line in parts[1].splitlines():
                        if line.startswith("description:"):
                            description = line.partition(":")[2].strip().strip("'\"")
                            break
            found.append({"id": child.name, "description": description, "path": str(path)})
        return found

    def skill_instructions(self, skill_id: str, *, limit: int = 16000) -> str:
        known = {skill["id"]: skill["path"] for skill in self.skills()}
        if skill_id not in known:
            raise ValueError("Unknown skill")
        return Path(known[skill_id]).read_text(encoding="utf-8-sig", errors="replace")[:limit]
