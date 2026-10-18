"""SMELTER V1.4.1 read-only input validation and bounded dry-run history."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from uuid import UUID

MAX_INPUTS = 16
MAX_REPORTS = 100

def validate_inputs(paths: list[str] | None) -> list[dict]:
    if paths is None:
        paths = []
    if not isinstance(paths, list) or len(paths) > MAX_INPUTS:
        raise ValueError("Input paths must be a list of at most 16 entries")
    result = []
    for raw in paths:
        if not isinstance(raw, str) or not raw.strip() or len(raw) > 2048 or "\x00" in raw:
            raise ValueError("Invalid input path")
        path = Path(raw).expanduser()
        if not path.is_absolute():
            raise ValueError("Input paths must be absolute")
        # No directory traversal or content reads; inspect metadata only.
        try:
            if not path.exists():
                status, kind = "missing", None
            elif path.is_file():
                status, kind = "valid", "file"
            elif path.is_dir():
                status, kind = "valid", "directory"
            else:
                status, kind = "unsupported", None
        except OSError:
            status, kind = "unavailable", None
        result.append({"path": str(path), "status": status, "kind": kind})
    return result

def attach_inputs(report: dict, paths: list[str] | None) -> dict:
    inputs = validate_inputs(paths)
    report = dict(report)
    report["inputs"] = inputs
    if any(item["status"] != "valid" for item in inputs):
        report["status"] = "blocked"
    report["output_validation"] = {"status": "not_applicable", "reason": "dry_run; no output produced"}
    return report

def save_report(folder: Path, report: dict) -> Path:
    identifier = str(UUID(report["run_id"]))
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / (identifier + ".json")
    # Exclusive creation avoids replacing an existing report.
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
        stream.write("\n")
    return destination

def list_reports(folder: Path, limit: int = 20) -> list[dict]:
    if not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("Invalid report limit")
    if not folder.is_dir():
        return []
    reports = []
    # Only files named with canonical UUIDs, never follow report symlinks.
    for path in folder.iterdir():
        try:
            if path.is_symlink() or not path.is_file() or path.suffix != ".json":
                continue
            if str(UUID(path.stem)) != path.stem or path.stat().st_size > 128 * 1024:
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and data.get("run_id") == path.stem and data.get("mode") == "dry_run":
                reports.append(data)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
    reports.sort(key=lambda item: item.get("timestamp_utc", ""), reverse=True)
    return reports[:limit]
