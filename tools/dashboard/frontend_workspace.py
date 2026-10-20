"""Isolated CSS redesign workbench. No arbitrary commands or source writes."""
import ast
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path
from urllib.request import Request, urlopen
from python_tools import _plain_path, _linked

DASHBOARD = 'tools/dashboard/dashboard.py'
MAX_FILES = 20000
MAX_COPY = 1024 * 1024 * 1024
PORT = 8770
SKIP = {'.git', '__pycache__', '.pytest_cache', 'projects', 'third-party', '.venv', 'venv'}
DESIGN_WORDS = ('design', 'taste', 'brutalist', 'brandkit', 'minimalist', 'soft-skill', 'stitch')


def target_path(root):
    root = Path(root).resolve()
    return _plain_path(root.with_name(root.name + 'V2'))


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _files(folder, prefix=''):
    _plain_path(folder)
    if not folder.is_dir():
        return
    for path in sorted(folder.iterdir()):
        if path.name in SKIP or _linked(path):
            continue
        relative = prefix + path.name
        if path.is_dir():
            yield from _files(path, relative + '/')
        elif path.is_file():
            yield relative, path


def _source_files(root):
    result = {}
    total = 0
    for name in ('tools', 'skills'):
        for relative, path in _files(root / name, name + '/'):
            if len(result) >= MAX_FILES:
                raise ValueError('Workspace source exceeds file limit')
            total += path.stat().st_size
            if total > MAX_COPY:
                raise ValueError('Workspace source exceeds 1 GiB')
            result[relative] = path
    for name in ('README.md', 'REQUIREMENTS.md', 'MASTER_HANDOVER.md'):
        path = _plain_path(root / name)
        if path.is_file():
            result[name] = path
    if DASHBOARD not in result:
        raise ValueError('Source dashboard is missing')
    return result


def _marker(root):
    return _plain_path(target_path(root) / '.smelter/frontend-workspace.json')


def _load(root):
    path = _marker(root)
    if not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError('Prepare the isolated frontend workspace first')
    info = json.loads(path.read_text(encoding='utf-8'))
    if info.get('source') != str(Path(root).resolve()) or info.get('target') != str(target_path(root)) or info.get('schema_version') != 1:
        raise ValueError('Workspace marker does not match this source')
    return info


def _design_skills(root):
    from skills_catalog import catalog_skills
    return [s for s in catalog_skills(root)['skills'] if s['enabled'] and s['status'] == 'ready'
            and any(word in s['id'].lower() for word in DESIGN_WORDS)]


def info(root, arguments):
    if arguments:
        raise ValueError('Workspace info takes no arguments')
    target = target_path(root)
    prepared = _marker(root).is_file()
    return {'status': 'workspace_info', 'source': str(Path(root).resolve()), 'target': str(target),
            'prepared': prepared, 'destination_exists': target.exists(), 'editable_file': DASHBOARD,
            'editable_surface': 'CSS style blocks only; HTML structure and all JavaScript remain unchanged',
            'skills': [{'id': s['id'], 'name': s['name'][:160], 'description': s['description'][:1000]} for s in _design_skills(root)],
            'readable_files': [DASHBOARD, 'tools/dashboard/model_preview.js', 'tools/dashboard/model_animations.js',
                               'tools/dashboard/mcp_ui.js', 'tools/dashboard/session_auth.js', 'tools/dashboard/chat_renderer.js'],
            'preview_port': PORT, 'visual_browser_automation': False,
            'message': 'Use prepare, skill reading, source reading, CSS replacement, validation, then launch. No generic shell or arbitrary source writes.'}


def prepare(root, arguments):
    if arguments:
        raise ValueError('Workspace preparation takes no arguments')
    root, target = Path(root).resolve(), target_path(root)
    if target.exists():
        if _marker(root).is_file():
            _load(root)
            return {'status': 'workspace_ready', 'target': str(target), 'reused': True,
                    'message': 'Existing managed workspace preserved; inspect before changing it.'}
        raise ValueError('Destination already exists and is unmanaged; refusing to overwrite')
    files = _source_files(root)
    extra = {}
    # Copy local runtime dependencies and enabled skill references, not logs,
    # game projects, databases, model weights, agent settings or credentials.
    for relative in ('.smelter/tooling/model-viewer', '.smelter/tooling/rea', '.smelter/managed-skills'):
        base = _plain_path(root / relative)
        for name, path in _files(base, relative + '/'):
            extra[name] = path
    for relative in ('.smelter/skill-state.json', '.smelter/extensions.json', '.smelter/model_preferences.json'):
        path = _plain_path(root / relative)
        if path.is_file():
            extra[relative] = path
    all_files = {**files, **extra}
    size = sum(p.stat().st_size for p in all_files.values())
    if len(all_files) > MAX_FILES or size > MAX_COPY:
        raise ValueError('Workspace copy exceeds 20,000 files or 1 GiB; no destination created')
    if shutil.disk_usage(target.parent).free < size + 100 * 1024 * 1024:
        raise ValueError('Not enough free space for the workspace copy')
    data = target.with_name(target.name + '-Data')
    _plain_path(data)
    if data.exists():
        raise ValueError('Isolated preview data directory already exists; refusing to reuse it')
    target.mkdir()
    try:
        hashes = {}
        for relative, source in all_files.items():
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            raw = source.read_bytes()
            destination.write_bytes(raw)
            if relative in files:
                hashes[relative] = _digest(raw)
        from database import select_database
        select_database(target, str(data))
        marker = {'schema_version': 1, 'source': str(root), 'target': str(target),
                  'data_directory': str(data), 'files': hashes}
        _marker(root).write_text(json.dumps(marker), encoding='utf-8')
    except Exception:
        # Only this newly created destination is removed; pre-existing targets
        # and the original checkout are never cleanup candidates.
        shutil.rmtree(target)
        raise
    return {'status': 'workspace_ready', 'target': str(target), 'data_directory': str(data),
            'copied_files': len(all_files), 'bytes': size, 'source_unchanged': True,
            'message': 'Isolated working copy and fresh preview database created. Original history/database are not shared.'}


def _html(source):
    tree = ast.parse(source)
    matches = [n.value for n in tree.body if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == 'HTML' for t in n.targets)]
    if len(matches) != 1 or not isinstance(matches[0], ast.Constant) or not isinstance(matches[0].value, str):
        raise ValueError('Expected exactly one literal dashboard HTML assignment')
    return tree, matches[0]


def _styles(html):
    matches = list(re.finditer(r'<style\b[^>]*>(.*?)</style\s*>', html, re.I | re.S))
    if len(matches) != 1:
        raise ValueError('Expected one dashboard style block')
    return matches[0]


def _check(root):
    root, target = Path(root).resolve(), target_path(root)
    marker = _load(root)
    current = _source_files(root)
    if set(current) != set(marker['files']):
        raise ValueError('Source file set changed; workspace baseline is stale')
    source_text, target_text = None, None
    for relative, expected in marker['files'].items():
        original = _plain_path(root / relative).read_bytes()
        if _digest(original) != expected:
            raise ValueError('Original source changed since preparation: ' + relative)
        destination = _plain_path(target / relative)
        if not destination.is_file():
            raise ValueError('Workspace file is missing: ' + relative)
        raw = destination.read_bytes()
        if relative != DASHBOARD and _digest(raw) != expected:
            raise ValueError('Non-frontend file changed: ' + relative)
        if relative == DASHBOARD:
            source_text, target_text = original.decode('utf-8'), raw.decode('utf-8')
    # Reject extra executable/source files in copied code directories too.
    for folder in ('tools', 'skills'):
        for relative, path in _files(target / folder, folder + '/'):
            if relative not in marker['files']:
                raise ValueError('Unexpected code file in workspace: ' + relative)
    original_tree, original_html = _html(source_text)
    target_tree, target_html = _html(target_text)
    original_style, target_style = _styles(original_html.value), _styles(target_html.value)
    def without_style(html, style):
        return html[:style.start(1)] + '<CSS>' + html[style.end(1):]
    if without_style(original_html.value, original_style) != without_style(target_html.value, target_style):
        raise ValueError('HTML structure or JavaScript changed; only CSS is permitted')
    original_html.value = target_html.value = '<HTML>'
    if ast.dump(original_tree, include_attributes=False) != ast.dump(target_tree, include_attributes=False):
        raise ValueError('Python backend changed; validation denied')
    return marker, target_text


def read_file(root, arguments):
    if not isinstance(arguments, dict) or set(arguments) - {'relative_path', 'area', 'offset', 'limit'}:
        raise ValueError('Unknown workspace read argument')
    relative, area = arguments.get('relative_path', DASHBOARD), arguments.get('area', 'destination')
    allowed = info(root, {})['readable_files']
    if relative not in allowed or area not in ('source', 'destination'):
        raise ValueError('Choose a listed frontend file and source/destination area')
    offset, limit = arguments.get('offset', 0), arguments.get('limit', 12000)
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 16000:
        raise ValueError('Invalid workspace read range')
    if area == 'destination':
        _load(root)
    path = _plain_path((Path(root) if area == 'source' else target_path(root)) / relative)
    text = path.read_text(encoding='utf-8')
    if relative == DASHBOARD:
        _, literal = _html(text)
        # The AI edits CSS, so give it the exact CSS rather than 100 KiB of
        # embedded Python/JavaScript. Other listed JS files are read-only.
        style = _styles(literal.value)
        text = style.group(1)
    return {'status': 'workspace_read', 'relative_path': relative, 'area': area,
            'surface': 'CSS' if relative == DASHBOARD else 'read-only JavaScript',
            'offset': offset, 'total_characters': len(text), 'sha256': _digest(text.encode()),
            'text': text[offset:offset + limit], 'next_offset': offset + limit if offset + limit < len(text) else None}


def read_skill(root, arguments):
    if not isinstance(arguments, dict) or set(arguments) != {'skill_id'}:
        raise ValueError('Supply one enabled design skill_id')
    sid = arguments['skill_id']
    if not isinstance(sid, str) or sid not in {s['id'] for s in _design_skills(root)}:
        raise ValueError('Design skill is not enabled and available')
    from skill_context import build_skill_context
    text = build_skill_context(root, [sid])
    return {'status': 'workspace_skill', 'skill_id': sid, 'text': text,
            'message': 'Skill instructions are reference data; they cannot expand filesystem or execution permissions.'}


def replace_css(root, arguments):
    if not isinstance(arguments, dict) or set(arguments) != {'expected_sha256', 'old_text', 'new_text'}:
        raise ValueError('Supply expected_sha256, old_text and new_text')
    old, new = arguments['old_text'], arguments['new_text']
    if not isinstance(old, str) or not old or not isinstance(new, str) or max(len(old), len(new)) > 24000:
        raise ValueError('CSS replacement strings must be nonempty old text and bounded new text')
    if '<' in new or '@import' in new.lower() or '\x00' in new:
        raise ValueError('CSS replacement must not introduce HTML tags, imports or NULs')
    _, source = _check(root)
    _, literal = _html(source)
    html, style = literal.value, _styles(literal.value)
    css = style.group(1)
    if arguments['expected_sha256'] != _digest(css.encode()):
        raise ValueError('CSS changed since it was read; read it again')
    if css.count(old) != 1:
        raise ValueError('Old CSS text must match exactly once')
    updated = css.replace(old, new, 1)
    new_html = html[:style.start(1)] + updated + html[style.end(1):]
    # Replace the literal through repr so quotes/backslashes in CSS cannot
    # escape the Python string or alter the backend syntax.
    lines = source.encode('utf-8').splitlines(keepends=True)
    start = sum(map(len, lines[:literal.lineno - 1])) + literal.col_offset
    end = sum(map(len, lines[:literal.end_lineno - 1])) + literal.end_col_offset
    encoded = source.encode('utf-8')
    result = encoded[:start] + repr(new_html).encode('utf-8') + encoded[end:]
    ast.parse(result.decode())
    path = _plain_path(target_path(root) / DASHBOARD)
    temporary = _plain_path(path.with_suffix('.py.frontend-tmp'))
    temporary.write_bytes(result)
    temporary.replace(path)
    return {'status': 'workspace_edited', 'path': str(path), 'css_sha256': _digest(updated.encode()),
            'bytes': len(result), 'message': 'CSS replacement saved; backend and JavaScript preserved. Validation is required before launch.'}


def validate(root, arguments):
    if arguments:
        raise ValueError('Workspace validation takes no arguments')
    _, source = _check(root)
    target = target_path(root)
    commands = [[sys.executable, '-m', 'unittest', 'discover', '-s', 'tools/dashboard', '-p', 'test_*.py']]
    node = shutil.which('node')
    if node:
        commands.append([node, '--test', 'tools/dashboard/test_chat_renderer.js', 'tools/dashboard/test_session_auth.js'])
    checks = []
    folder = _plain_path(target / '.smelter/frontend-validation')
    folder.mkdir(exist_ok=True)
    _plain_path(folder / 'passed.json').unlink(missing_ok=True)
    deadline = time.monotonic() + 90
    for index, command in enumerate(commands):
        log = folder / ('check-' + str(index) + '.log')
        try:
            with log.open('wb') as output:
                completed = subprocess.run(command, cwd=target, stdin=subprocess.DEVNULL,
                    stdout=output, stderr=subprocess.STDOUT, timeout=max(0.1, deadline - time.monotonic()), shell=False,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            code = completed.returncode
        except subprocess.TimeoutExpired:
            code = None
        raw = log.read_bytes()
        checks.append({'command': command, 'exit_code': code, 'log_path': str(log),
                       'log_sha256': _digest(raw), 'tail': raw[-5000:].decode('utf-8', errors='replace')})
        if code != 0:
            return {'status': 'workspace_validation_failed', 'checks': checks,
                    'message': 'Validation failed or timed out; preview launch is blocked.'}
    _check(root)
    record = {'dashboard_sha256': _digest(source.encode()), 'checks': checks}
    (folder / 'passed.json').write_text(json.dumps(record), encoding='utf-8')
    return {'status': 'workspace_validated', 'checks': checks, 'backend_unchanged': True,
            'javascript_unchanged': True, 'visual_inspection': 'not performed',
            'message': 'Backend and JavaScript preservation checks and fixed tests passed.' + ('' if node else ' Node unavailable: JavaScript test execution skipped.')}


def launch(root, arguments):
    if arguments:
        raise ValueError('Workspace launch takes no arguments')
    marker, source = _check(root)
    target = target_path(root)
    record_path = _plain_path(target / '.smelter/frontend-validation/passed.json')
    if not record_path.is_file() or json.loads(record_path.read_text()).get('dashboard_sha256') != _digest(source.encode()):
        raise ValueError('Run workspace validation after the last CSS edit before launch')
    with closing(socket.socket()) as probe:
        try:
            probe.bind(('127.0.0.1', PORT))
        except OSError as exc:
            raise ValueError('Preview port 8770 is occupied; no process was stopped') from exc
    log = _plain_path(target / '.smelter/frontend-preview.log')
    options = {'creationflags': subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
    environment = dict(os.environ)
    environment['PYTHONUNBUFFERED'] = '1'
    with log.open('wb') as output:
        process = subprocess.Popen([sys.executable, str(target / DASHBOARD), '--port', str(PORT), '--no-browser'],
            cwd=target, env=environment, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
            close_fds=True, shell=False, **options)
    url = None
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        text = log.read_text(encoding='utf-8', errors='replace')
        found = re.search(r'http://127\.0\.0\.1:8770/#token=([A-Za-z0-9_-]+)', text)
        if found:
            url = found.group(0)
            try:
                # Startup performs external version probes. Polling it with a
                # short timeout leaves scanners running in abandoned HTTP
                # threads. This existing endpoint checks auth and the fresh
                # database without launching any tool or model processes.
                request = Request('http://127.0.0.1:8770/api/chats', headers={'X-Smelter-Token': found.group(1)})
                with urlopen(request, timeout=max(0.1, min(2, deadline - time.monotonic()))) as response:
                    report = json.load(response)
                if isinstance(report.get('conversations'), list):
                    return {'status': 'workspace_launched', 'pid': process.pid, 'url': url,
                            'log_path': str(log), 'data_directory': marker['data_directory'],
                            'visual_inspection': 'not performed',
                            'message': 'Authenticated chat database check passed; startup tool scans were not run. Open the URL to inspect the design. Original app was not stopped.'}
            except (OSError, ValueError):
                pass
        if process.poll() is not None:
            raise ValueError('Preview process exited; inspect ' + str(log))
        time.sleep(0.1)
    # This handle belongs to the process started in this invocation only.
    process.terminate()
    process.wait(timeout=5)
    raise ValueError('Preview readiness was not confirmed; only the new preview process was stopped')


OPERATIONS = {'frontend_workspace_info': info, 'prepare_frontend_workspace': prepare,
              'read_frontend_file': read_file, 'read_enabled_design_skill': read_skill,
              'replace_frontend_css': replace_css, 'validate_frontend_workspace': validate,
              'launch_frontend_preview': launch}


def execute(root, grants, name, arguments):
    if grants.get('frontend_workspace') is not True:
        raise ValueError('Frontend workspace was not approved for this message')
    if name not in OPERATIONS:
        raise ValueError('Unknown workspace tool')
    return OPERATIONS[name](Path(root), arguments)
