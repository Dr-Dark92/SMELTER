"""Fixed headless Ghidra operations over approved local binary snapshots.

The installed Ghidra parser runs as a bounded trusted host process. Targets are
never launched. Model arguments cannot select scripts, commands or output paths.
"""
from __future__ import annotations
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import tempfile
from uuid import UUID, uuid4

from process_runner import run as bounded_run

MAX_INPUT = 64 * 1024 * 1024
MAX_RESULT = 512 * 1024
MAX_PREVIEW = 64 * 1024
MAX_PROJECT = 256 * 1024 * 1024
ANALYSIS_TIMEOUT = 180
QUERY_TIMEOUT = 60
SCRIPT = Path(__file__).with_name('ghidra_scripts') / 'SmelterAnalysis.java'
OPERATIONS = {'rea_ghidra_analyze': 'analyze', 'rea_ghidra_functions': 'functions',
              'rea_ghidra_strings': 'strings', 'rea_ghidra_decompile': 'decompile',
              'rea_ghidra_xrefs': 'xrefs'}
_lock = threading.Lock()


def _plain(path):
    from python_tools import _plain_path
    return _plain_path(Path(path))


def status(root=None, home=None):
    """Observe configured Ghidra files only; never starts the engine."""
    try:
        base = _plain(home or os.environ.get('GHIDRA_INSTALL_DIR') or 'C:/Tools/Ghidra').resolve()
        launcher = _plain(base / 'support' / ('analyzeHeadless.bat' if os.name == 'nt' else 'analyzeHeadless'))
        properties = _plain(base / 'Ghidra/application.properties')
        version = None
        if properties.is_file() and properties.stat().st_size <= 65536:
            match = re.search(r'^application.version=(.+)$', properties.read_text(encoding='utf-8'), re.M)
            version = match.group(1).strip() if match else None
        ready = launcher.is_file() and SCRIPT.is_file()
        return {'status': 'installed' if ready else 'missing', 'home': str(base),
                'launcher': str(launcher), 'version': version, 'tools': list(OPERATIONS),
                'reason': 'Headless files found; invocation verifies execution' if ready else 'Install/configure Ghidra and the fixed SMELTER script',
                'boundary': 'Bounded trusted host parser; target is not executed; not an OS sandbox'}
    except (ValueError, OSError) as exc:
        return {'status': 'invalid', 'reason': str(exc), 'tools': list(OPERATIONS)}


def _target(grants, relative):
    if not isinstance(relative, str) or not relative or len(relative) > 500 or '\\' in relative or ':' in relative:
        raise ValueError('Use a relative binary path with forward slashes')
    rel = Path(relative)
    if rel.anchor or relative.startswith(('/', '-')) or '..' in rel.parts:
        raise ValueError('Binary path escapes the approved folder')
    scope = grants.get('rea_root')
    if not scope:
        raise ValueError('Select an approved REA analysis folder')
    base = _plain(scope).resolve(strict=True)
    target = _plain(base / rel).resolve(strict=True)
    if not target.is_relative_to(base) or not target.is_file():
        raise ValueError('Binary must be a regular file inside the approved folder')
    from access_policy import require
    require(target, 'read')
    if target.stat().st_size > MAX_INPUT:
        raise ValueError('Ghidra input exceeds 64 MiB')
    raw = target.read_bytes()
    if len(raw) > MAX_INPUT:
        raise ValueError('Ghidra input changed beyond its size limit')
    if raw[:4] == b'\x7fELF': suffix = '.elf'
    elif raw[:2] == b'MZ' and target.suffix.lower() in ('.exe', '.dll'): suffix = target.suffix.lower()
    else: raise ValueError('This adapter accepts PE .exe/.dll or ELF files only')
    return target, raw, suffix


def _identifier(value):
    try:
        valid = isinstance(value, str) and str(UUID(value)) == value
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('Use the exact analysis_id returned by rea_ghidra_analyze')
    return value


def _address(value):
    if not isinstance(value, str) or not re.fullmatch(r'(?:0x)?[0-9a-fA-F]{1,16}', value):
        raise ValueError('Provide a hexadecimal address returned by Ghidra')
    return value.removeprefix('0x').lower()


def _query(arguments):
    query, offset, limit = arguments.get('query', ''), arguments.get('offset', 0), arguments.get('limit', 50)
    if not isinstance(query, str) or len(query) > 200 or any(ord(c) < 32 for c in query):
        raise ValueError('Query must be up to 200 plain characters')
    if type(offset) is not int or not 0 <= offset <= 200000 or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('Choose offset 0–200000 and limit 1–100')
    return base64.b64encode(query.encode('utf-8')).decode('ascii') or '-', str(offset), str(limit)


def _environment():
    # Ghidra's batch launcher expands its own arguments; never inherit Java agent
    # options or arbitrary Ghidra VM flags from the parent environment.
    # Read-only Windows locations are kept: without SystemDrive/ProgramData, Windows
    # components expand '%SystemDrive%' relative to the working directory.
    allowed = ('SystemRoot', 'SystemDrive', 'ProgramData', 'ProgramFiles', 'ProgramFiles(x86)', 'ALLUSERSPROFILE',
               'WINDIR', 'COMSPEC', 'TEMP', 'TMP', 'LOCALAPPDATA', 'APPDATA', 'USERPROFILE', 'HOME', 'PATH', 'JAVA_HOME')
    env = {k: os.environ[k] for k in allowed if k in os.environ}
    if os.name == 'nt':
        # A stale/quoted JAVA_HOME must not reach Ghidra's batch launcher.
        configured = Path(env.get('JAVA_HOME', '').strip('"')) if env.get('JAVA_HOME') else None
        candidates = []
        for base in ('C:/Program Files/Microsoft', 'C:/Program Files/Eclipse Adoptium'):
            candidates.extend(Path(base).glob('jdk-21*/bin/java.exe'))
        if configured is not None and (configured / 'bin/java.exe').is_file():
            env['JAVA_HOME'] = str(configured)
        elif candidates:
            env['JAVA_HOME'] = str(sorted(candidates)[-1].parent.parent)
        else:
            raise ValueError('A valid JDK 21 installation is required for Ghidra')
        # PowerShell otherwise treats .bat as a document and can open a separate
        # interactive console. Keep executable-extension resolution explicit.
        env['PATHEXT'] = '.COM;.EXE;.BAT;.CMD'
    env['GHIDRA_HEADLESS_MAXMEM'] = '1G'
    return env


def _command(launcher, args, env):
    if os.name != 'nt': return [str(launcher), *args]
    # Use a fixed PowerShell invocation to preserve Windows batch quoting. No
    # supplied text is interpolated into its code; all arguments are JSON data.
    # Ghidra's own batch launcher uses CALL/delayed expansion, so reject command
    # metacharacters even in paths before passing them to that trusted launcher.
    for value in (str(launcher), *args):
        if any(c in value for c in '\r\n\x00"&|<>^%!'):
            raise ValueError('Ghidra batch launcher cannot safely represent this path or argument')
    shell = Path(os.environ.get('SystemRoot', 'C:/Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
    env['SMELTER_GHIDRA_LAUNCHER'] = str(launcher)
    env['SMELTER_GHIDRA_ARGUMENTS'] = json.dumps(args)
    return [str(shell), '-NoProfile', '-NonInteractive', '-Command',
            '$a = @(ConvertFrom-Json $env:SMELTER_GHIDRA_ARGUMENTS); & $env:SMELTER_GHIDRA_LAUNCHER @a; exit $LASTEXITCODE']


def _size(folder):
    total = 0
    for path in folder.rglob('*'):
        _plain(path)
        if path.is_file(): total += path.stat().st_size
        if total > MAX_PROJECT: raise ValueError('Ghidra project exceeded its 256 MiB retained-size limit')
    return total


def _project_root(root):
    # Ghidra rejects project paths containing any dot-prefixed directory, so
    # its projects cannot live under .smelter. Evidence remains in the checkout.
    base = Path(os.environ.get('LOCALAPPDATA') or tempfile.gettempdir())
    if any(p.startswith('.') for p in base.parts):
        base = Path(tempfile.gettempdir())
    identity = hashlib.sha256(str(Path(root).resolve()).encode()).hexdigest()[:16]
    return _plain(base / 'SMELTER/GhidraProjects' / identity)


def run_ghidra(root, grants, name, arguments, runner=bounded_run, home=None):
    if grants.get('rea_analysis') is not True:
        raise ValueError('REA process execution was not approved for this task')
    if name not in OPERATIONS or not isinstance(arguments, dict):
        raise ValueError('Unknown Ghidra operation or invalid arguments')
    operation = OPERATIONS[name]
    required = {'relative_path'} if operation == 'analyze' else {'analysis_id'}
    allowed = required | ({'query', 'offset', 'limit'} if operation in ('functions', 'strings') else {'address'} if operation in ('decompile', 'xrefs') else set())
    if set(arguments) - allowed or not required.issubset(arguments):
        raise ValueError('Unexpected or missing Ghidra operation arguments')
    extra = _query(arguments) if operation in ('functions', 'strings') else (_address(arguments.get('address')), '0', '100') if operation in ('decompile', 'xrefs') else ('-', '0', '50')
    observed = status(root, home)
    if observed['status'] != 'installed': raise ValueError('Ghidra unavailable: ' + observed['reason'])
    from access_policy import require
    require(Path(observed['home']), 'execute', 'rea')
    base = _plain(Path(root).resolve() / '.smelter/rea-evidence/ghidra')
    if not _lock.acquire(blocking=False): raise ValueError('A Ghidra operation is already running; wait for its result')
    folder = None
    project = None
    output = None
    created = False
    try:
        if operation == 'analyze':
            target, raw, suffix = _target(grants, arguments['relative_path'])
            analysis_id = str(uuid4())
            folder = _plain(base / analysis_id)
            project = _plain(_project_root(root) / analysis_id)
            from storage_budget import require as reserve
            reservation = min(MAX_PROJECT, len(raw) * 8 + 16 * 1024 * 1024)
            reserve(root, reservation)
            if shutil.disk_usage(Path(root)).free < reservation + 64 * 1024 * 1024:
                raise ValueError('Insufficient free space for Ghidra analysis')
            folder.mkdir(parents=True, exist_ok=False); created = True
            project.parent.mkdir(parents=True, exist_ok=True)
            if len(list(project.parent.iterdir())) >= 10:
                raise ValueError('Ten retained Ghidra projects exist; preserve/review them before creating more')
            project.mkdir(exist_ok=False)
            binary = folder / ('input' + suffix)
            binary.write_bytes(raw)
            meta = {'schema_version': 1, 'analysis_id': analysis_id, 'source': str(target),
                    'relative_path': arguments['relative_path'], 'sha256': hashlib.sha256(raw).hexdigest(),
                    'input_name': binary.name, 'ghidra_version': observed['version']}
        else:
            analysis_id = _identifier(arguments['analysis_id'])
            folder = _plain(base / analysis_id)
            project = _plain(_project_root(root) / analysis_id)
            if not project.is_dir():
                raise ValueError('Retained Ghidra project is missing; analyze again')
            marker = _plain(folder / 'analysis.json')
            if not marker.is_file() or marker.stat().st_size > 65536:
                raise ValueError('Ghidra analysis is missing or incomplete')
            meta = json.loads(marker.read_text(encoding='utf-8'))
            if not isinstance(meta, dict) or meta.get('schema_version') != 1 or meta.get('analysis_id') != analysis_id:
                raise ValueError('Invalid Ghidra analysis metadata')
            target, raw, suffix = _target(grants, meta.get('relative_path'))
            if str(target) != meta.get('source') or hashlib.sha256(raw).hexdigest() != meta.get('sha256'):
                raise ValueError('Source binary changed or analysis belongs to a different approved folder; analyze again')
            if meta.get('input_name') != 'input' + suffix:
                raise ValueError('Invalid retained binary name')
            if meta.get('ghidra_version') != observed['version']:
                raise ValueError('Ghidra version changed; analyze again with the current engine')
            binary = _plain(folder / meta['input_name'])
            if not binary.is_file() or binary.stat().st_size > MAX_INPUT or hashlib.sha256(binary.read_bytes()).hexdigest() != meta['sha256']:
                raise ValueError('Retained binary changed; analyze again')
            _size(folder); _size(project)
            from storage_budget import require as reserve
            reserve(root, MAX_RESULT + 2 * 1024 * 1024)
        output = _plain(folder / (str(uuid4()) + '.json'))
        argv = [str(project), 'SMELTER']
        if operation == 'analyze': argv += ['-import', str(binary), '-analysisTimeoutPerFile', '120']
        else: argv += ['-process', binary.name, '-noanalysis', '-readOnly']
        argv += ['-scriptPath', str(SCRIPT.parent.resolve()), '-postScript', SCRIPT.name,
                 operation, str(output), *extra, '-max-cpu', '2']
        env = _environment()
        command = _command(Path(observed['launcher']), argv, env)
        try:
            result = runner(command, cwd=str(folder), env=env, timeout=ANALYSIS_TIMEOUT if created else QUERY_TIMEOUT,
                            max_output=1024 * 1024, capture_output=True, shell=False, check=False)
        except subprocess.TimeoutExpired as exc:
            raise ValueError('Ghidra operation timed out; no target program was launched') from exc
        stderr = result.stderr.decode('utf-8', 'replace') if isinstance(result.stderr, bytes) else str(result.stderr or '')
        stdout = result.stdout.decode('utf-8', 'replace') if isinstance(result.stdout, bytes) else str(result.stdout or '')
        if result.returncode != 0 or not output.is_file():
            raise ValueError('Ghidra did not produce verified analysis output: ' + (stdout + '\n' + stderr)[-2000:])
        _plain(output)
        if output.stat().st_size > MAX_RESULT: raise ValueError('Ghidra result exceeds 512 KiB')
        payload = output.read_bytes()
        evidence = json.loads(payload)
        if not isinstance(evidence, dict) or evidence.get('schema_version') != 1 or evidence.get('operation') != operation or evidence.get('ok') is not True:
            raise ValueError('Ghidra returned invalid or unsuccessful evidence')
        _, current_raw, _ = _target(grants, meta['relative_path'])
        if hashlib.sha256(current_raw).hexdigest() != meta['sha256']:
            raise ValueError('Source binary changed during analysis; results were not admitted')
        size = _size(folder) + _size(project)
        if size > MAX_PROJECT:
            raise ValueError('Ghidra project and evidence exceed the 256 MiB retained-size limit')
        if created:
            (folder / 'analysis.json').write_text(json.dumps(meta, indent=2), encoding='utf-8')
        full = len(json.dumps(evidence, ensure_ascii=True).encode('utf-8')) <= MAX_PREVIEW
        if full:
            preview = evidence
        else:
            from rea_connection import _preview
            preview = _preview(evidence)
            if len(json.dumps(preview, ensure_ascii=True).encode('utf-8')) > MAX_PREVIEW:
                preview = {'preview_omitted': True, 'operation': operation,
                           'reason': 'Read retained evidence or request a smaller page for complete content'}
        return {'status': 'rea_completed', 'provider': 'ghidra', 'operation': operation,
                'analysis_id': analysis_id, 'target': str(target), 'source_sha256': meta['sha256'],
                'ghidra_version': observed['version'], 'exit_code': result.returncode,
                'evidence_path': str(output), 'evidence_sha256': hashlib.sha256(payload).hexdigest(),
                'evidence_bytes': len(payload), 'retained_bytes': size,
                'result_preview': preview, 'preview_truncated': not full,
                'scope': 'Static Ghidra analysis; target not executed; pseudocode is reconstructed, not original source'}
    except Exception:
        if created and folder is not None:
            _plain(folder)
            shutil.rmtree(folder)
            if project is not None and project.is_dir():
                if project.parent != _project_root(root):
                    raise ValueError('Unexpected Ghidra project cleanup location')
                _plain(project)
                shutil.rmtree(project)
        elif output is not None:
            _plain(output)
            output.unlink(missing_ok=True)
        raise
    finally:
        from storage_budget import invalidate
        invalidate(root)
        _lock.release()
