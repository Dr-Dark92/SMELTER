"""REA CLI adapter. Fixed operations, local pinned package, no shell or npx.

The target is parsed as data, never executed. Native-engine decompilation and
arbitrary CLI commands are intentionally not part of this adapter.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from uuid import uuid4

VERSION = "6.7.0"
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_OUTPUT = 2 * 1024 * 1024


def package_status(root, finder=shutil.which):
    from python_tools import _plain_path
    base = Path(root).resolve() / ".smelter" / "tooling" / "rea"
    package = base / "node_modules" / "rea-agents"
    node = finder("node")
    info = {"package": "rea-agents", "required_version": VERSION,
            "package_directory": str(package), "node": node,
            "status": "missing", "installed_version": None,
            "tools": ["rea_capabilities", "rea_inspect_pe_resources"]}
    if not node:
        return {**info, "reason": "Node.js is not on the dashboard process PATH"}
    executable = Path(node).resolve()
    if not executable.is_file() or (os.name == "nt" and executable.suffix.lower() != ".exe"):
        return {**info, "reason": "A real Node executable is required; command shims are not run"}
    try:
        _plain_path(package)
        manifest_path = package / "package.json"
        _plain_path(manifest_path)
        if not manifest_path.is_file():
            return {**info, "reason": "Install the pinned local REA package first"}
        if manifest_path.stat().st_size > 100000:
            raise ValueError("REA package manifest is unexpectedly large")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("name") != "rea-agents" or manifest.get("version") != VERSION:
            return {**info, "status": "incompatible", "installed_version": manifest.get("version"),
                    "reason": "This adapter is verified against rea-agents@" + VERSION}
        entry = _plain_path(package / "scripts" / "rea.mjs")
        if not entry.is_file():
            return {**info, "reason": "REA launcher is absent from the installed package"}
        return {**info, "status": "installed", "installed_version": VERSION,
                "node": str(executable), "launcher": str(entry),
                "working_directory": str(base),
                "reason": "Package found; live runtime verification occurs on approved tool invocation"}
    except (OSError, ValueError, TypeError) as exc:
        return {**info, "status": "invalid", "reason": str(exc)}


def _runtime_version(node, runner):
    result = runner([node, "--version"], shell=False, capture_output=True,
                    stdin=subprocess.DEVNULL, timeout=5, check=False)
    raw = result.stdout.decode("utf-8", errors="replace") if isinstance(result.stdout, bytes) else str(result.stdout)
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)\s*", raw)
    if result.returncode != 0 or not match:
        raise ValueError("Unable to verify Node.js version")
    major, minor, _ = map(int, match.groups())
    if not (major == 22 and minor >= 19 or major == 24 and minor >= 11 or major >= 26):
        raise ValueError("REA 6.7.0 requires Node 22.19+, 24.11+, or 26+ (23/25 are unsupported)")
    return raw.strip()


def _preview(value, depth=0):
    """Explicitly partial preview; the full REA JSON is retained separately."""
    if depth >= 5 and isinstance(value, (list, dict)):
        return {"preview_omitted": True, "type": type(value).__name__, "items": len(value)}
    if isinstance(value, dict):
        result = {str(k): _preview(v, depth + 1) for k, v in list(value.items())[:10]}
        if len(value) > 10:
            result["additional_keys_omitted"] = len(value) - 10
        return result
    if isinstance(value, list):
        result = [_preview(x, depth + 1) for x in value[:5]]
        if len(value) > 5:
            result.append({"additional_items_omitted": len(value) - 5})
        return result
    if isinstance(value, str) and len(value) > 700:
        return value[:700] + " [preview truncated]"
    return value


def run_rea(root, grants, name, arguments, runner=subprocess.run, finder=shutil.which):
    from python_tools import _plain_path
    if grants.get("rea_analysis") is not True:
        raise ValueError("REA process execution was not approved for this message")
    if not isinstance(arguments, dict):
        raise ValueError("REA arguments must be an object")
    status = package_status(root, finder)
    if status["status"] != "installed":
        raise ValueError("REA unavailable: " + status["reason"])
    target = None
    if name == "rea_capabilities":
        if arguments:
            raise ValueError("rea_capabilities takes no arguments")
        operation = ["capabilities", "--json"]
    elif name == "rea_inspect_pe_resources":
        if set(arguments) != {"relative_path"}:
            raise ValueError("Provide relative_path only")
        scope = grants.get("rea_root")
        relative = arguments["relative_path"]
        if not scope:
            raise ValueError("Select an approved analysis folder")
        if not isinstance(relative, str) or not relative or len(relative) > 500 or "\\" in relative or ":" in relative:
            raise ValueError("Use a relative path with forward slashes")
        rel = Path(relative)
        # Windows rooted paths such as /etc/passwd have an anchor but are not
        # is_absolute() until a drive is supplied. Reject them on every OS.
        if relative.startswith("/") or rel.anchor or ".." in rel.parts:
            raise ValueError("Path escapes approved folder")
        try:
            target = _plain_path(Path(scope) / rel).resolve(strict=True)
        except OSError as exc:
            raise ValueError("REA target is missing or inaccessible") from exc
        if not target.is_relative_to(Path(scope)) or not target.is_file():
            raise ValueError("REA target must be a file inside the approved folder")
        if target.suffix.lower() not in {".exe", ".dll"}:
            raise ValueError("This REA operation supports PE .exe/.dll files only; it is not an .oppc extractor")
        if target.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("PE inspection input exceeds 64 MiB")
        with target.open("rb") as source:
            if source.read(2) != b"MZ":
                raise ValueError("Selected file has no PE/DOS MZ signature")
        operation = ["inspect-pe-resources", str(target), "--json"]
    else:
        raise ValueError("REA operation is not allowed")
    try:
        node_version = _runtime_version(status["node"], runner)
        # No .cmd/.bat launchers or model-supplied commands/flags are accepted.
        command = [status["node"], status["launcher"], *operation]
        result = runner(command, cwd=status["working_directory"], shell=False,
                        capture_output=True, stdin=subprocess.DEVNULL, timeout=35, check=False)
    except subprocess.TimeoutExpired as exc:
        raise ValueError("REA timed out; no target program was launched") from exc
    raw = result.stdout if isinstance(result.stdout, bytes) else result.stdout.encode("utf-8")
    error = result.stderr if isinstance(result.stderr, bytes) else result.stderr.encode("utf-8")
    if not raw or len(raw) > MAX_OUTPUT:
        raise ValueError("REA returned no JSON or exceeded the 2 MiB output limit: " + error[:1000].decode("utf-8", errors="replace"))
    try:
        evidence = json.loads(raw)
        if not isinstance(evidence, (dict, list)):
            raise ValueError("Expected an object or array")
    except (ValueError, UnicodeError) as exc:
        raise ValueError("REA returned invalid JSON: " + error[:1000].decode("utf-8", errors="replace")) from exc
    folder = _plain_path(Path(root).resolve() / ".smelter" / "rea-evidence")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (str(uuid4()) + ".json")
    with path.open("xb") as output:
        output.write(raw)
    digest = hashlib.sha256(raw).hexdigest()
    full = len(json.dumps(evidence, ensure_ascii=True)) <= 10000
    preview = evidence if full else _preview(evidence)
    if len(json.dumps(preview, ensure_ascii=True)) > 10000:
        preview = {"preview_omitted": True, "reason": "Read the retained evidence file for the complete result"}
    failed = result.returncode != 0 or isinstance(evidence, dict) and (evidence.get("ok") is False or evidence.get("status") in ("error", "failed"))
    return {"status": "rea_failed" if failed else "rea_completed", "operation": operation[0],
            "package_version": VERSION, "node_version": node_version,
            "target": str(target) if target else None, "exit_code": result.returncode,
            "evidence_path": str(path), "evidence_bytes": len(raw), "evidence_sha256": digest,
            "result_preview": preview, "preview_truncated": not full,
            "stderr": error[:1000].decode("utf-8", errors="replace"),
            "scope": "REA capability discovery or static PE resources only; target not executed; no asset extraction or native decompilation"}


if __name__ == "__main__":
    print(json.dumps(package_status(Path(__file__).resolve().parents[2]), indent=2))
