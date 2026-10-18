"""SMELTER V1.4.2: tightly scoped, explicitly approved archive listing."""
from __future__ import annotations

import subprocess
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

from reports import validate_inputs
from check_requirements import find_executable

MAX_OUTPUT = 12000
APPROVAL = "LIST ARCHIVE"

def inspect_archive(path: str, approval: str, state: dict, tool_status: dict,
                    runner=subprocess.run, finder=find_executable) -> dict:
    """List archive metadata via 7z l; no extraction or shell execution."""
    if approval != APPROVAL:
        raise ValueError("Explicit LIST ARCHIVE approval required")
    if "7z" not in state.get("enabled", []):
        raise ValueError("7-Zip extension disabled")
    if tool_status.get("7z") != "installed":
        raise ValueError("7-Zip dependency not verified")
    inputs = validate_inputs([path])
    if inputs[0]["status"] != "valid" or inputs[0]["kind"] != "file":
        raise ValueError("Input must be an existing regular file")
    source = Path(path)
    if source.is_symlink():
        raise ValueError("Symlink inputs are not supported")
    executable = finder("7z")
    if not executable or Path(executable).suffix.lower() != ".exe":
        raise ValueError("Verified 7-Zip executable unavailable")
    command = [executable, "l", "-slt", "-bd", "--", str(source)]
    # 7z supports '--' as switch terminator on supported versions; absolute path follows.
    try:
        result = runner(command, shell=False, capture_output=True, text=True,
                        errors="replace", stdin=subprocess.DEVNULL, timeout=20, check=False)
        status = "completed" if result.returncode == 0 else "failed"
        output = (result.stdout or "")[:MAX_OUTPUT]
        error = (result.stderr or "")[:MAX_OUTPUT]
        return {"run_id": str(uuid4()), "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "workflow_id": "archive_inspection", "mode": "approved_read_only",
                "status": status, "executed": True, "permissions_granted": True,
                "inputs": inputs, "exit_code": result.returncode, "stdout": output,
                "stderr": error, "output_validation": {"status": "not_applicable",
                "reason": "read-only listing; no files generated"}}
    except subprocess.TimeoutExpired:
        return {"run_id": str(uuid4()), "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "workflow_id": "archive_inspection", "mode": "approved_read_only",
                "status": "timeout", "executed": True, "permissions_granted": True,
                "inputs": inputs, "exit_code": None, "stdout": "", "stderr": "20-second timeout",
                "output_validation": {"status": "not_applicable", "reason": "read-only listing"}}
