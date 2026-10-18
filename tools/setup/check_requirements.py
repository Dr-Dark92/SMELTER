#!/usr/bin/env python3
"""SMELTER V1 read-only system requirements scanner (Python standard library)."""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

TOOLS = {
    "git": (["git", "--version"], "recommended"),
    "node": (["node", "--version"], "optional"),
    "npm": (["npm", "--version"], "optional"),
    "java": (["java", "-version"], "optional"),
    "javac": (["javac", "-version"], "optional"),
    "gh": (["gh", "--version"], "optional"),
    "pwsh": (["pwsh", "--version"], "optional"),
    "docker": (["docker", "--version"], "optional"),
    "ollama": (["ollama", "--version"], "optional"),
    "blender": (["blender", "--version"], "optional"),
    "ffmpeg": (["ffmpeg", "-version"], "optional"),
    "7z": (["7z", "i"], "optional"),
}

def find_executable(name: str) -> str | None:
    """Check PATH first, then common Windows locations for optional tools."""
    found = shutil.which(name)
    if found or os.name != "nt":
        return found
    roots = [os.environ.get("ProgramFiles"), os.environ.get("ProgramW6432"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA")]
    candidates = []
    for root in filter(None, roots):
        base = Path(root)
        if name == "7z":
            candidates.append(base / "7-Zip" / "7z.exe")
            candidates.append(base / "Programs" / "7-Zip" / "7z.exe")
        elif name == "blender":
            candidates.extend((base / "Blender Foundation").glob("Blender */blender.exe"))
            candidates.extend((base / "Programs" / "Blender Foundation").glob("Blender */blender.exe"))
        elif name == "ffmpeg":
            candidates.extend(base.glob("ffmpeg*/bin/ffmpeg.exe"))
            candidates.extend((base / "Programs").glob("ffmpeg*/bin/ffmpeg.exe"))
    candidates = [p for p in candidates if p.is_file()]
    return str(sorted(candidates, reverse=True)[0]) if candidates else None

def probe(name: str, argv: list[str], policy: str) -> dict:
    """Never invoke a shell; version checks only, with timeouts and bounded output."""
    found = find_executable(argv[0])
    if not found:
        return {"name": name, "status": "missing", "policy": policy, "version": None}
    try:
        # Windows .cmd shims need shell execution; do not run them in this read-only scanner.
        if os.name == "nt" and Path(found).suffix.lower() in (".cmd", ".bat", ".ps1"):
            return {"name": name, "status": "detected_unverified", "policy": policy, "version": None}
        run = subprocess.run([found, *argv[1:]], capture_output=True, text=True, errors="replace",
                             timeout=5, check=False, stdin=subprocess.DEVNULL)
        output = (run.stdout or run.stderr).strip()
        first = next((line.strip() for line in output.splitlines() if line.strip()), "")
        first = re.sub(r"[\x00-\x1f\x7f]", "", first)[:160]
        return {"name": name, "status": "installed" if run.returncode == 0 else "detected_unverified",
                "policy": policy, "version": first or None}
    except (OSError, subprocess.TimeoutExpired):
        return {"name": name, "status": "detected_unverified", "policy": policy, "version": None}

def scan() -> dict:
    py_ok = sys.version_info >= (3, 12)
    return {
        "schema_version": 1,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "platform": {"system": platform.system(), "machine": platform.machine()},
        "python": {"version": platform.python_version(), "status": "pass" if py_ok else "fail",
                   "minimum": "3.12"},
        "vanilla_ready": py_ok,
        "tools": [probe(name, argv, policy) for name, (argv, policy) in TOOLS.items()],
        "notes": [
            "Optional tools are not required for SMELTER Vanilla.",
            "No packages were installed and no downloads or network requests were performed.",
            "A detected tool is not proof of compatibility with a particular extension.",
        ],
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print JSON instead of summary")
    parser.add_argument("--output", type=Path, help="Write JSON report to this explicit path")
    args = parser.parse_args()
    report = scan()
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("SMELTER V1 Requirements Scan")
        print("Python:", report["python"]["version"], report["python"]["status"])
        print("Vanilla ready:", "YES" if report["vanilla_ready"] else "NO")
        for tool in report["tools"]:
            print(f"  {tool['name']:<9} {tool['status']:<20} {tool['version'] or ''}")
        if args.output:
            print("Report saved:", args.output)
    return 0 if report["vanilla_ready"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
