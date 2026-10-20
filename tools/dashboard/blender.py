"""SMELTER V1.4.4: explicitly approved Blender version capability check.

Only invokes Blender's built-in --version; never loads .blend files or scripts.
"""
from __future__ import annotations
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from check_requirements import find_executable

APPROVAL = "CHECK BLENDER"
MAX_OUTPUT = 12000

def inspect_blender(approval: str, state: dict, tool_status: dict,
                    runner=subprocess.run, finder=find_executable) -> dict:
    if approval != APPROVAL:
        raise ValueError("Explicit CHECK BLENDER approval required")
    if "blender" not in state.get("enabled", []):
        raise ValueError("Blender extension disabled")
    if tool_status.get("blender") != "installed":
        raise ValueError("Blender dependency not verified")
    executable = finder("blender")
    if not executable or Path(executable).suffix.lower() in (".cmd", ".bat", ".ps1") or (os.name == "nt" and Path(executable).suffix.lower() != ".exe"):
        raise ValueError("Verified Blender executable unavailable")
    command = [executable, "--version"]
    report = {"run_id": str(uuid4()), "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "workflow_id": "blender_capability", "mode": "approved_read_only",
              "executed": True, "permissions_granted": True, "inputs": [],
              "output_validation": {"status": "not_applicable", "reason": "version query only"}}
    try:
        result = runner(command, shell=False, capture_output=True, text=True,
                        errors="replace", stdin=subprocess.DEVNULL, timeout=20, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        stdout = (result.stdout or "")[:MAX_OUTPUT]
        stderr = (result.stderr or "")[:4000]
        valid = result.returncode == 0 and stdout.lstrip().startswith("Blender ")
        return {**report, "status": "completed" if valid else "failed",
                "exit_code": result.returncode, "stdout": stdout, "stderr": stderr}
    except subprocess.TimeoutExpired:
        return {**report, "status": "timeout", "exit_code": None,
                "stdout": "", "stderr": "20-second timeout"}
