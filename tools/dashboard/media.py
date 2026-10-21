"""SMELTER V1.4.3: approved, read-only FFprobe media inspection."""
from __future__ import annotations
from process_runner import run as bounded_run
import os
import json
import subprocess
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
from reports import validate_inputs
from check_requirements import find_executable

APPROVAL = "PROBE MEDIA"
MAX_OUTPUT = 32000

def resolve_ffprobe(finder=find_executable) -> str | None:
    ffmpeg = finder("ffmpeg")
    if not ffmpeg or Path(ffmpeg).suffix.lower() in (".cmd", ".bat", ".ps1") or (os.name == "nt" and Path(ffmpeg).suffix.lower() != ".exe"):
        return None
    # Only use the companion executable in the verified FFmpeg installation.
    companion = Path(ffmpeg).with_name("ffprobe.exe" if os.name == "nt" else "ffprobe")
    return str(companion) if companion.is_file() else None

def inspect_media(path: str, approval: str, state: dict, tool_status: dict,
                  runner=bounded_run, resolver=resolve_ffprobe) -> dict:
    if approval != APPROVAL:
        raise ValueError("Explicit PROBE MEDIA approval required")
    if "ffmpeg" not in state.get("enabled", []):
        raise ValueError("FFmpeg extension disabled")
    if tool_status.get("ffmpeg") != "installed":
        raise ValueError("FFmpeg dependency not verified")
    inputs = validate_inputs([path])
    if inputs[0]["status"] != "valid" or inputs[0]["kind"] != "file":
        raise ValueError("Input must be an existing regular file")
    source = Path(path)
    if source.is_symlink():
        raise ValueError("Symlink inputs are not supported")
    probe = resolver()
    if not probe or Path(probe).suffix.lower() in (".cmd", ".bat", ".ps1") or (os.name == "nt" and Path(probe).suffix.lower() != ".exe"):
        raise ValueError("ffprobe.exe not found beside verified ffmpeg.exe")
    command = [probe, "-v", "error", "-show_format", "-show_streams",
               "-of", "json", "-i", str(source)]
    base = {"run_id": str(uuid4()), "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "workflow_id": "media_inspection", "mode": "approved_read_only",
            "executed": True, "permissions_granted": True, "inputs": inputs,
            "output_validation": {"status": "not_applicable", "reason": "metadata only; no output generated"}}
    try:
        result = runner(command, shell=False, capture_output=True, text=True,
                        errors="replace", stdin=subprocess.DEVNULL, timeout=20, check=False, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        stdout = (result.stdout or "")[:MAX_OUTPUT]
        stderr = (result.stderr or "")[:4000]
        metadata = None
        status = "failed"
        if result.returncode == 0 and len(result.stdout or "") <= MAX_OUTPUT:
            try:
                parsed = json.loads(stdout)
                if isinstance(parsed, dict) and isinstance(parsed.get("streams"), list):
                    metadata = parsed
                    status = "completed"
            except (ValueError, TypeError):
                pass
        return {**base, "status": status, "exit_code": result.returncode,
                "metadata": metadata, "stdout": stdout, "stderr": stderr}
    except subprocess.TimeoutExpired:
        return {**base, "status": "timeout", "exit_code": None,
                "metadata": None, "stdout": "", "stderr": "20-second timeout"}
