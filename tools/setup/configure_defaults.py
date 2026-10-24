#!/usr/bin/env python3
"""Write first-run dashboard defaults from this machine's hardware and installed tools.

Reads system-requirements.json (defaults section), detects the NVIDIA GPU, Ollama
models, Docker image IDs and installed tools, then writes
.smelter/deployment-defaults.json. The dashboard uses those values only for
settings that were never saved, so re-running never overrides a user change.
Read-only apart from that one file: no downloads, installs or service changes.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from requirements_catalog import CATALOG, CATALOG_PATH

ROOT = CATALOG_PATH.parent
OUTPUT = ROOT / ".smelter" / "deployment-defaults.json"
SHA256 = re.compile(r"sha256:[a-f0-9]{64}")


def _run(argv: list[str], timeout: int = 20) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(argv, capture_output=True, text=True, errors="replace", timeout=timeout,
                              stdin=subprocess.DEVNULL, shell=False,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired):
        return None


def _find(name: str, known: list[str]) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    return next((path for path in known if Path(path).is_file()), None)


def detect_gpu(run=_run) -> dict:
    smi = _find("nvidia-smi", [r"C:\Windows\System32\nvidia-smi.exe",
                               r"C:\Program Files\NVIDIA Corporation\NVSMI\nvidia-smi.exe"])
    if not smi:
        return {"vendor": None, "vram_mib": 0, "note": "No NVIDIA GPU detected; CPU inference assumed"}
    result = run([smi, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"])
    if result is None or result.returncode != 0 or not result.stdout.strip():
        return {"vendor": "nvidia", "vram_mib": 0, "note": "nvidia-smi did not report a GPU"}
    # Use the GPU with the most memory when several are present.
    rows = [[part.strip() for part in line.split(",")] for line in result.stdout.strip().splitlines()]
    rows = [r for r in rows if len(r) == 3 and r[1].isdigit()]
    if not rows:
        return {"vendor": "nvidia", "vram_mib": 0, "note": "Unreadable nvidia-smi output"}
    name, memory, driver = max(rows, key=lambda r: int(r[1]))
    return {"vendor": "nvidia", "name": name, "vram_mib": int(memory), "driver": driver}


def detect_ram_mib() -> int | None:
    """Total physical memory in MiB, or None when it cannot be read."""
    try:
        if os.name == "nt":
            import ctypes

            class MemoryStatus(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                            ("available", ctypes.c_ulonglong), ("total_page", ctypes.c_ulonglong),
                            ("available_page", ctypes.c_ulonglong), ("total_virtual", ctypes.c_ulonglong),
                            ("available_virtual", ctypes.c_ulonglong), ("available_extended", ctypes.c_ulonglong)]
            status = MemoryStatus(length=ctypes.sizeof(MemoryStatus))
            return status.total // (1024 * 1024) if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)) else None
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") // (1024 * 1024)
    except (OSError, AttributeError, ValueError):
        return None


def _version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text)[:3])


def choose_profile(gpu: dict, catalog: dict = CATALOG) -> dict:
    profiles = catalog["defaults"]["hardware_profiles"]
    for index, profile in enumerate(profiles):
        limit = profile.get("max_vram_mib")
        if limit is None or gpu.get("vram_mib", 0) <= limit:
            # A profile that needs more system RAM than this machine has steps down one level.
            ram, needed = gpu.get("ram_mib"), profile.get("min_ram_mib")
            if needed and ram is not None and ram < needed and index > 0:
                return profiles[index - 1]
            return profile
    raise ValueError("No hardware profile matched")


def ollama_models(opener=urllib.request.urlopen) -> list[str] | None:
    try:
        with opener("http://127.0.0.1:11434/api/tags", timeout=3) as response:
            return [item["name"] for item in json.load(response).get("models", []) if isinstance(item, dict)]
    except (OSError, ValueError, KeyError):
        return None


def choose_model(profile: dict, installed: list[str] | None, catalog: dict = CATALOG) -> tuple[str, list[str]]:
    wanted = profile["model"]
    if installed is None:
        return wanted, [f"Ollama is not running; {wanted} could not be confirmed as installed"]
    if wanted in installed:
        return wanted, []
    # Fall back to the largest installed model that still fits this hardware
    # (this profile's level and below), never to a larger one.
    profiles = catalog["defaults"]["hardware_profiles"]
    fitting = profiles[:next(i for i, p in enumerate(profiles) if p["id"] == profile["id"]) + 1]
    for other in reversed(fitting):
        if other["model"] in installed:
            return other["model"], [f"{wanted} suits this GPU but is not installed; using installed {other['model']}"]
    return wanted, [f"{wanted} is not installed; run install_missing.ps1 to pull it"]


def docker_images(catalog: dict = CATALOG, run=_run) -> tuple[dict, list[str]]:
    images = {key: None for key in catalog["defaults"].get("images", {})}
    docker = _find("docker", [r"C:\Program Files\Docker\Docker\resources\bin\docker.exe"])
    if not docker:
        return images, ["Docker is not installed; image IDs left unset"]
    warnings = []
    for key, step in catalog["defaults"]["images"].items():
        tag = catalog["setup"][step]["image"]
        result = run([docker, "image", "inspect", "--format", "{{.Id}}", tag])
        value = result.stdout.strip() if result is not None and result.returncode == 0 else ""
        if SHA256.fullmatch(value):
            images[key] = value
        else:
            warnings.append(f"Docker image {tag} is not available; {key} left unset")
    return images, warnings


def tool_statuses() -> dict:
    from check_requirements import scan
    return {item["name"]: item for item in scan(refresh=True)["tools"]}


def enabled_extensions(statuses: dict, catalog: dict = CATALOG) -> list[str]:
    def present(name):
        status = statuses.get(name, {}).get("status")
        # npm shims are reported unverified rather than executed; presence is enough here.
        return status == "installed" or (status == "detected_unverified" and "npm" in catalog["tools"].get(name, {}))
    return [name for name in catalog["defaults"].get("extensions", []) if present(name)]


def version_drift(statuses: dict, catalog: dict = CATALOG) -> list[dict]:
    rows = []
    for name, expected in catalog["defaults"].get("versions", {}).items():
        observed = statuses.get(name, {}).get("version") or ""
        found = re.search(r"\d+\.\d+\.\d+", observed)
        rows.append({"tool": name, "expected": expected, "observed": found.group(0) if found else None,
                     "matches": bool(found) and found.group(0) == expected})
    return rows


def profile_by_id(profile_id: str, catalog: dict = CATALOG) -> dict | None:
    """A named hardware profile; 'custom' (None) leaves model and runtime to the user."""
    if profile_id == "custom":
        return None
    for profile in catalog["defaults"]["hardware_profiles"]:
        if profile["id"] == profile_id:
            return profile
    known = ", ".join([p["id"] for p in catalog["defaults"]["hardware_profiles"]] + ["custom"])
    raise ValueError(f"Unknown profile '{profile_id}'. Known: {known}")


def build(gpu=None, installed=..., images=None, statuses=None, catalog: dict = CATALOG, profile_id=None) -> dict:
    gpu = {**detect_gpu(), "ram_mib": detect_ram_mib()} if gpu is None else gpu
    installed = ollama_models() if installed is ... else installed
    statuses = tool_statuses() if statuses is None else statuses
    image_ids, image_warnings = docker_images(catalog) if images is None else (images, [])
    profile = choose_profile(gpu, catalog) if profile_id is None else profile_by_id(profile_id, catalog)
    if profile is None:
        model, warnings = None, ["Custom profile: set the model and runtime in the dashboard"]
    else:
        model, warnings = choose_model(profile, installed, catalog)
    minimum = catalog["defaults"].get("min_nvidia_driver")
    if gpu.get("driver") and minimum and _version_tuple(gpu["driver"]) < _version_tuple(minimum):
        warnings.append(f"NVIDIA driver {gpu['driver']} is older than {minimum}; Ollama may crash or fall back to the CPU")
    drift = version_drift(statuses, catalog)
    warnings += [f"{d['tool']} {d['observed'] or 'not found'} differs from expected {d['expected']}" for d in drift if not d["matches"]]
    storage = os.path.expandvars(catalog["defaults"].get("storage_directory", "")).replace("/", os.sep)
    return {
        "schema_version": 1,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source": "tools/setup/configure_defaults.py",
        "hardware": gpu,
        "hardware_profile": profile["id"] if profile else "custom",
        "profile_source": "detected" if profile_id is None else "chosen",
        "model": model,
        "runtime_profile": profile["runtime_profile"] if profile else "custom",
        "extensions": enabled_extensions(statuses, catalog),
        "images": image_ids,
        "storage_directory": storage if storage and "%" not in storage else None,
        "versions": drift,
        "installed_models": installed,
        "warnings": warnings + image_warnings,
    }


def write(report: dict, path: Path = OUTPUT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, prefix=".defaults-",
                                     suffix=".tmp", delete=False) as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    os.replace(handle.name, path)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print the defaults without writing them")
    parser.add_argument("--show-model", action="store_true", help="Print only the model chosen for this hardware")
    names = [p["id"] for p in CATALOG["defaults"]["hardware_profiles"]] + ["custom"]
    parser.add_argument("--profile", choices=names,
                        help="Use this profile instead of detecting it: " + "; ".join(
                            f"{p['id']}: {p['label']}" for p in CATALOG["defaults"]["hardware_profiles"])
                        + "; custom: you define the model and runtime in the dashboard")
    args = parser.parse_args()
    if args.show_model:
        profile = choose_profile({**detect_gpu(), "ram_mib": detect_ram_mib()}) if args.profile is None else profile_by_id(args.profile)
        print(profile["model"] if profile else "")
        return 0
    report = build(profile_id=args.profile)
    gpu = report["hardware"]
    print("SMELTER deployment defaults")
    print(f"  GPU:        {gpu.get('name') or 'none'} ({gpu.get('vram_mib', 0)} MiB, driver {gpu.get('driver') or 'n/a'})")
    print(f"  RAM:        {gpu.get('ram_mib') or 'unknown'} MiB")
    print(f"  Profile:    {report['hardware_profile']} ({report['profile_source']}) -> runtime '{report['runtime_profile']}', model {report['model'] or 'user defined'}")
    print(f"  Extensions: {', '.join(report['extensions']) or 'none'}")
    print(f"  Images:     " + ", ".join(f"{k}={'set' if v else 'unset'}" for k, v in report["images"].items()))
    print(f"  Storage:    {report['storage_directory'] or 'not set'}")
    for warning in report["warnings"]:
        print(f"  WARNING: {warning}")
    if args.dry_run:
        print("Dry run: nothing written.")
    else:
        print(f"Written: {write(report)}")
        print("The dashboard uses these only for settings you have not saved yourself.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
