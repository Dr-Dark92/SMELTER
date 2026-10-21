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

    @staticmethod
    def _dashboard_modules():
        # Trusted sibling implementation, independent of caller's working directory.
        import sys
        source=Path(__file__).resolve().parents[1]/'dashboard'
        if str(source) not in sys.path:sys.path.insert(0,str(source))

    def skills(self) -> list[dict[str, str]]:
        self._dashboard_modules()
        from skills_catalog import catalog_skills
        from skill_runtime import skill_folder
        return [{**skill,'path':str(skill_folder(self.root,skill)/'SKILL.md')} for skill in catalog_skills(self.root)['skills']]

    def skill_instructions(self, skill_id: str, *, limit: int = 16000) -> str:
        self._dashboard_modules()
        from skill_context import build_skill_context
        from skill_runtime import monitor
        monitor(self.root)
        known={s['id'] for s in self.skills()}
        canonical=skill_id if skill_id in known else 'legacy/'+skill_id
        return build_skill_context(self.root,[canonical])[:min(max(1,limit),48000)]

    def connect_dashboard(self, grants, conversation_id=None):
        """Explicit compatibility adapter to the same scoped/audited tool session.

        Does not register or execute code from skill text. Writes also retain
        Registry.invoke's allow_writes gate and all ToolSession restrictions.
        """
        self._dashboard_modules()
        from python_tools import ToolSession
        session=ToolSession(self.root,grants,conversation_id)
        read_only={'frontend_workspace_info','read_frontend_file','read_enabled_design_skill','inventory_directory','inspect_model_attachment','rea_capabilities','rea_inspect_pe_resources'}
        for tool in session.tools:
            function=tool['function'];name=function['name']
            def handler(value,name=name):
                return session.execute({'function':{'name':name,'arguments':value['arguments']}})
            self.register(Capability('smelter/'+name,function['description'],{'arguments':'object'},handler,name in read_only))
        return session
