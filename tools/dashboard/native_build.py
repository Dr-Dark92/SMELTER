"""Confined MinGW-w64 builds of a mod. Artifacts are never executed.

The mod declares targets in mods/<mod>/native.json; SMELTER fixes the compiler flags,
validates every manifest field against allowlists, copies the mod's C/C++ sources
into a frozen build folder, and runs a fixed cross-compiler in a no-network
Linux container. Host MSVC is an operator utility only, never a model fallback.
Running built code is a separate, unimplemented decision.
"""
import hashlib
import base64
import json
import os
import re
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from python_tools import _plain_path

SOURCES = {'.c', '.cpp'}
HEADERS = {'.h', '.hpp'}
LIBS = {'kernel32', 'user32', 'shell32', 'ole32', 'advapi32', 'gdi32'}
KINDS = {'asi', 'exe', 'obj'}
FLAGS = ['-std=c++17', '-Wall', '-Wextra', '-Werror', '-DUNICODE', '-D_UNICODE']
MAX_FILE = 128 * 1024
MAX_TOTAL = 1024 * 1024
MAX_FILES = 200
MAX_TARGETS = 6
TARGET_TIMEOUT = 180
KEEP_RUNS = 20
FORBIDDEN = [
    (re.compile(r'^\s*#\s*(import|using)\b', re.M), '#import/#using load external type libraries'),
    (re.compile(r'^\s*#\s*pragma\s+comment\s*\(\s*(linker|lib)\b', re.M | re.I), 'linker/library pragmas bypass the manifest allowlist'),
    (re.compile(r'^\s*#\s*include\s*[<"]\s*([A-Za-z]:|[\\/])', re.M), 'includes must stay inside the mod or the SDK'),
    (re.compile(r'^\s*#\s*include\s*<[^>]*\.\.', re.M), 'includes must stay inside the mod or the SDK'),
]
QUOTED_INCLUDE = re.compile(r'^\s*#\s*include\s*"([^"]+)"', re.M)


def _escapes(relative, include):
    """True when a quoted include, resolved from the including file, leaves the mod folder."""
    import posixpath
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(relative), include.replace('\\', '/')))
    return resolved == '..' or resolved.startswith('../')
_ENVIRONMENT = None


def _name(value, what, pattern=r'[A-Za-z0-9][A-Za-z0-9_-]{0,40}'):
    if not isinstance(value, str) or not re.fullmatch(pattern, value) or re.fullmatch(r'(?i:con|prn|aux|nul|com[1-9]|lpt[1-9])', value):
        raise ValueError('Invalid ' + what)
    return value


def _inside(mod_dir, value, what):
    if not isinstance(value, str) or not value or len(value) > 200 or '\\' in value or ':' in value:
        raise ValueError(what + ' must be a relative forward-slash path inside the mod')
    parts = value.split('/')
    if any(p in ('', '.', '..') or p.endswith('.') or not re.fullmatch(r'[A-Za-z0-9_.-]+', p)
           or re.fullmatch(r'(?i:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', p) for p in parts):
        raise ValueError('Unsafe ' + what + ': ' + value)
    return value


def manifest(mod_dir):
    path = _plain_path(mod_dir / 'native.json')
    if not path.is_file() or path.stat().st_size > 16 * 1024:
        raise ValueError('The mod needs a native.json build manifest (at most 16 KiB)')
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or set(value) != {'schema_version', 'targets'} or type(value['schema_version']) is not int or value['schema_version'] != 1:
        raise ValueError('native.json needs schema_version 1 and targets only')
    targets = value['targets']
    if not isinstance(targets, list) or not 1 <= len(targets) <= MAX_TARGETS:
        raise ValueError('native.json declares 1-6 targets')
    seen = set()
    for target in targets:
        if not isinstance(target, dict) or not set(target) <= {'name', 'kind', 'sources', 'include_dirs', 'defines', 'libs', 'entry'} or \
                not {'name', 'kind', 'sources'} <= set(target):
            raise ValueError('Each target has name, kind, sources and optional include_dirs, defines, libs')
        if _name(target['name'], 'target name').lower() in seen:
            raise ValueError('Duplicate target name')
        seen.add(target['name'].lower())
        if not isinstance(target['kind'], str) or target['kind'] not in KINDS:
            raise ValueError('Target kind must be asi, exe or obj')
        if 'entry' in target and (target['kind'] != 'exe' or target['entry'] not in ('main', 'wmain')):
            raise ValueError('Only exe targets may choose entry main or wmain')
        sources = target['sources']
        if not isinstance(sources, list) or not 1 <= len(sources) <= 16:
            raise ValueError('A target has 1-16 sources')
        for source in sources:
            if Path(_inside(mod_dir, source, 'source')).suffix.lower() not in SOURCES:
                raise ValueError('Sources are .c or .cpp files')
        folders = target.get('include_dirs', [])
        if not isinstance(folders, list) or len(folders) > 16:
            raise ValueError('Include directories are up to 16 relative paths')
        for folder in folders:
            _inside(mod_dir, folder, 'include directory')
        defines = target.get('defines', [])
        if not isinstance(defines, list) or len(defines) > 8 or any(
                not isinstance(d, str) or not re.fullmatch(r'[A-Z_][A-Z0-9_]{0,40}(=[0-9]{1,9})?', d) for d in defines):
            raise ValueError('Defines are up to 8 NAME or NAME=number entries')
        libs = target.get('libs', [])
        if not isinstance(libs, list) or len(libs) > 8 or any(not isinstance(l, str) or l not in LIBS for l in libs):
            raise ValueError('Libraries are limited to ' + ', '.join(sorted(LIBS)))
    return targets


def _freeze(mod_dir, destination):
    """Copy the mod's C/C++ sources and headers after checking them; return relative paths."""
    copied, total = [], 0
    deadline = time.monotonic() + 10
    for visited, path in enumerate(mod_dir.rglob('*')):
        if visited >= 4000 or time.monotonic() > deadline:
            raise ValueError('Native source inventory exceeds 4,000 entries or 10 seconds')
        _plain_path(path)
        if path.is_dir() or path.suffix.lower() not in SOURCES | HEADERS:
            continue
        relative = path.relative_to(mod_dir).as_posix()
        if any(part in ('build', '.git') for part in relative.split('/')[:-1]):
            continue
        _plain_path(path)
        from access_policy import require
        require(path, 'read')
        raw = path.read_bytes()
        total += len(raw)
        if len(raw) > MAX_FILE or total > MAX_TOTAL or len(copied) >= MAX_FILES:
            raise ValueError('Native sources exceed 128 KiB per file, 1 MiB or 200 files')
        text = raw.decode('utf-8')
        for pattern, reason in FORBIDDEN:
            if pattern.search(text):
                raise ValueError('Refused ' + relative + ': ' + reason)
        if any(_escapes(relative, include) for include in QUOTED_INCLUDE.findall(text)):
            raise ValueError('Refused ' + relative + ': includes must stay inside the mod or the SDK')
        out = destination / relative
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(raw)
        copied.append(relative)
    return sorted(copied)


def msvc():
    """Installed MSVC: (installation path, cl.exe path, vcvars64 environment)."""
    global _ENVIRONMENT
    if _ENVIRONMENT is None:
        from process_runner import run
        vswhere = Path(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)')) / 'Microsoft Visual Studio/Installer/vswhere.exe'
        if not vswhere.is_file():
            raise ValueError('Optional operator MSVC is not installed (catalog tool msvc)')
        found = run([str(vswhere), '-latest', '-products', '*', '-requires',
                     'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-property', 'installationPath'],
                    timeout=30, max_output=64 * 1024, capture_output=True, text=True)
        install = Path(found.stdout.strip()) if found.returncode == 0 and found.stdout.strip() else None
        vcvars = install / 'VC/Auxiliary/Build/vcvars64.bat' if install else None
        if not vcvars or not vcvars.is_file():
            raise ValueError('MSVC C++ x64 tools were not found')
        env = {**os.environ, 'PATH': str(vswhere.parent) + os.pathsep + os.environ.get('PATH', '')}
        # Separate arguments: one quoted string gets its inner quotes escaped and cmd cannot parse it.
        captured = run(['cmd.exe', '/d', '/c', 'call', str(vcvars), '&&', 'set'], timeout=120,
                       max_output=512 * 1024, capture_output=True, text=True, env=env)
        environment = dict(line.split('=', 1) for line in captured.stdout.splitlines() if '=' in line and not line.startswith('='))
        cl = shutil.which('cl.exe', path=environment.get('Path') or environment.get('PATH'))
        if captured.returncode != 0 or not cl:
            raise ValueError('vcvars64.bat did not provide cl.exe')
        _ENVIRONMENT = (install, Path(cl), environment)
    return _ENVIRONMENT


def _artifact(path):
    raw = path.read_bytes()
    return {'file': path.name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def _prune(base):
    runs = sorted((p for p in base.iterdir() if (p / 'run.json').is_file()), key=lambda p: p.stat().st_mtime)
    for old in runs[:-KEEP_RUNS]:
        shutil.rmtree(old)


def build(root, grants, arguments):
    if not grants.get('native_build') or not grants.get('coding_workspace'):
        raise ValueError('Native builds were not approved for this message')
    if set(arguments) != {'workspace_id', 'mod'}:
        raise ValueError('Build a mod in a coding workspace: workspace_id and mod only')
    from access_policy import require
    from coding_workspace import load, locked
    from process_runner import run
    mod = _name(arguments['mod'], 'mod name', r'[a-z0-9][a-z0-9-]{0,40}')
    with locked(root):
        _, workspace = load(root, arguments['workspace_id'])
        mod_dir = _plain_path(workspace / 'mods' / mod)
        if not mod_dir.is_dir():
            raise ValueError('No such mod in this workspace: mods/' + mod)
        require(mod_dir, 'read')
        targets = manifest(mod_dir)
        require(workspace, 'execute', 'tests')
        from sandbox import status, _flags, _remove, record_owner
        ready = status(root, operation='coding_cpp')
        if not ready['ready']:
            raise ValueError('Confined native builds unavailable: ' + ready['reason'])
        base = _plain_path(Path(root).resolve() / '.smelter/native-builds')
        base.mkdir(parents=True, exist_ok=True)
        _prune(base)
        run_dir = base / str(uuid4())
        source, out = run_dir / 'src', run_dir / 'out'
        out.mkdir(parents=True)
        files = _freeze(mod_dir, source)
        (source / '.smelter').mkdir()
        (run_dir / 'manifest.json').write_text(json.dumps({'schema_version': 1, 'targets': targets}, indent=2), encoding='utf-8')
        results, log = [], []
        for target in targets:
            for item in target['sources']:
                if item not in files:
                    raise ValueError('Source not found among the mod C/C++ files: ' + item)
        name = 'smelter-native-' + uuid4().hex
        image = ready['configured']['cpp_image']
        owner = _plain_path(Path(root).resolve() / '.smelter/sandbox-runs' / uuid4().hex)
        owner.mkdir(parents=True)
        record_owner(owner, name, image, 'native-build')
        try:
            worker = Path(__file__).with_name('native_build_worker.py').read_text(encoding='utf-8')
            done = run(_flags(ready['docker'], name, source, exec_scratch=True) + ['--rm', image,
                       'python', '-I', '-c', worker, json.dumps(targets)], timeout=200,
                       max_output=8 * 1024 * 1024, capture_output=True, text=True)
            if done.returncode != 0:
                raise ValueError('Confined native compiler failed; rebuild/select smelter-cpp:2. ' + done.stderr[-1000:])
            payload = json.loads(done.stdout)
        finally:
            confirmed = _remove(ready['docker'], name)
            record_owner(owner, name, image, 'native-build', finished=confirmed)
            if not confirmed:
                raise ValueError('Native build container cleanup was not confirmed: ' + name)
        if len(payload.get('targets', [])) != len(targets):
            raise ValueError('Invalid confined native build result')
        total_artifacts = 0
        for expected, target in zip(targets, payload['targets']):
            if target.get('name') != expected['name'] or target.get('kind') != expected['kind']:
                raise ValueError('Confined build result target differs from manifest')
            name, output, exit_code = target['name'], target['output'], target['exit_code']
            target_out = out / name
            target_out.mkdir()
            artifacts = []
            for artifact in target['artifacts']:
                filename = artifact['file']
                if not re.fullmatch(r'[A-Za-z0-9_-]+\.(asi|exe|obj)', filename):
                    raise ValueError('Unsafe compiled artifact name')
                raw = base64.b64decode(artifact['base64'], validate=True)
                total_artifacts += len(raw)
                if len(raw) > 2 * 1024 * 1024 or total_artifacts > 4 * 1024 * 1024:
                    raise ValueError('Compiled artifacts exceed the output budget')
                path = target_out / filename
                with path.open('xb') as stream:
                    stream.write(raw)
                artifacts.append({**_artifact(path), 'path': str(path)})
            log.append('== ' + name + ' (' + target['kind'] + ') exit ' + str(exit_code) + '\n' + output)
            diagnostics = [line for line in output.splitlines() if re.search(r'\b(error|warning)\b', line)]
            results.append({'name': name, 'kind': target['kind'], 'exit_code': exit_code,
                            'succeeded': exit_code == 0 and bool(artifacts), 'artifacts': artifacts,
                            'diagnostics': '\n'.join(diagnostics)[:3000], 'diagnostics_truncated': len('\n'.join(diagnostics)) > 3000})
        ok = all(r['succeeded'] for r in results)
        (run_dir / 'build.log').write_text('\n'.join(log), encoding='utf-8')
        evidence = {'schema_version': 1, 'workspace_id': arguments['workspace_id'], 'mod': mod,
                    'compiler': payload['compiler'], 'image': image, 'sandbox': 'docker-no-network',
                    'flags': FLAGS, 'sources': {f: hashlib.sha256((source / f).read_bytes()).hexdigest() for f in files},
                    'manifest_targets': targets, 'worker_sha256': hashlib.sha256(worker.encode()).hexdigest(),
                    'manifest_sha256': hashlib.sha256(json.dumps(targets, sort_keys=True).encode()).hexdigest(),
                    'targets': results, 'succeeded': ok, 'executed_artifacts': False,
                    'finished_utc': datetime.now(timezone.utc).isoformat()}
        (run_dir / 'run.json').write_text(json.dumps(evidence, indent=1), encoding='utf-8')
        return {'status': 'native_build_succeeded' if ok else 'native_build_failed', 'workspace_id': arguments['workspace_id'],
                'mod': mod, 'targets': results, 'evidence_path': str(run_dir / 'run.json'), 'executed_artifacts': False,
                'sandbox': 'docker-no-network', 'image': image,
                'message': ('All targets compiled' if ok else 'Some targets failed; read diagnostics') +
                           '. Artifacts were not run; compile success is not runtime or in-game proof.'}
