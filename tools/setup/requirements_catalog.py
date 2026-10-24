"""Load the machine-readable SMELTER requirements file (standard library only).

The scanner, profiles and winget queue all read system-requirements.json at the
repository root, so tools and profiles are declared in one place.
"""
from __future__ import annotations

import json
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parents[2] / "system-requirements.json"


def load(path: Path = CATALOG_PATH) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError(f"Unsupported requirements schema in {path}")
    tools, profiles = data.get("tools"), data.get("profiles")
    if not isinstance(tools, dict) or not isinstance(profiles, dict) or "vanilla" not in profiles:
        raise ValueError(f"Requirements file {path} needs tools and a vanilla profile")
    for name, tool in tools.items():
        check = tool.get("check")
        if not isinstance(check, list) or not check or not all(isinstance(x, str) for x in check):
            raise ValueError(f"Tool {name} needs a check command list")
        if tool.get("policy") not in ("recommended", "optional"):
            raise ValueError(f"Tool {name} has an unknown policy")
        if "winget" in tool and not isinstance(tool["winget"], str):
            raise ValueError(f"Tool {name} has an invalid winget ID")
        if "npm" in tool and not (isinstance(tool["npm"], str) and "@" in tool["npm"].lstrip("@")):
            raise ValueError(f"Tool {name} needs a version-pinned npm package")
    setup = data.setdefault("setup", {})
    if not isinstance(setup, dict):
        raise ValueError(f"Requirements file {path} has an invalid setup section")
    for name, step in setup.items():
        if step.get("kind") not in SETUP_FIELDS:
            raise ValueError(f"Setup step {name} has an unknown kind")
        missing = [field for field in SETUP_FIELDS[step["kind"]] if not isinstance(step.get(field), str)]
        if missing:
            raise ValueError(f"Setup step {name} needs {', '.join(missing)}")
        if step["kind"] in ("npm_prefix",) and "@" not in step["package"].lstrip("@"):
            raise ValueError(f"Setup step {name} needs a version-pinned npm package")
        unknown = [t for t in step.get("needs", []) if t not in tools] + [s for s in step.get("after", []) if s not in setup]
        if unknown:
            raise ValueError(f"Setup step {name} references unknown entries: {', '.join(unknown)}")
    defaults = data.setdefault("defaults", {})
    hardware = defaults.get("hardware_profiles", [])
    if not isinstance(hardware, list) or any(not isinstance(p, dict) or not isinstance(p.get("model"), str)
                                             or not isinstance(p.get("runtime_profile"), str) for p in hardware):
        raise ValueError(f"Requirements file {path} has invalid hardware profiles")
    if hardware and hardware[-1].get("max_vram_mib") is not None:
        raise ValueError(f"The last hardware profile in {path} must have no VRAM limit")
    for key, step in defaults.get("images", {}).items():
        if setup.get(step, {}).get("kind") not in ("docker_pull", "docker_build"):
            raise ValueError(f"Default image {key} must name a Docker setup step")
    for name, profile in profiles.items():
        unknown = [tool for tool in profile.get("requires", []) if tool not in tools]
        if unknown:
            raise ValueError(f"Profile {name} requires unknown tools: {', '.join(unknown)}")
        unknown = [step for step in profile.get("setup", []) if step not in setup]
        if unknown:
            raise ValueError(f"Profile {name} uses unknown setup steps: {', '.join(unknown)}")
    return data


# Required string fields per setup step kind; install_missing.ps1 implements each kind.
SETUP_FIELDS = {
    "pip": ("requirements", "package", "version"),
    "ollama_pull": ("model",),
    "docker_pull": ("image",),
    "docker_build": ("image", "dockerfile"),
    "npm_prefix": ("prefix", "package"),
    "playwright_browser": ("browser",),
    "powershell_script": ("script", "check_path"),
    "wsl_platform": (),
}


CATALOG = load()
