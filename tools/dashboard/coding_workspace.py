"""Scoped code proposals, transactional edits and fixed confined tests.

Each workspace is a new child of the registered sibling V2, never the original
checkout or an existing frontend copy. No model-supplied commands are accepted.
"""
from contextlib import contextmanager, closing
import difflib
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
from uuid import UUID, uuid4

from access_policy import require
from python_tools import _plain_path, _linked

MAX_FILE = 128 * 1024
MAX_FILES = 20000
MAX_COPY = 128 * 1024 * 1024
MAX_PATCH = 512 * 1024
MAX_CHANGES = 6
EDITABLE = {'.py', '.js', '.mjs', '.cjs', '.css', '.html', '.json', '.md', '.toml', '.yaml', '.yml',
            '.c', '.cpp', '.h', '.hpp', '.lua', '.txt', '.hex'}
# Build outputs never enter a coding copy. Scripts (.bat/.ps1/.cmd) are copied but not editable,
# so model edits cannot change anything SMELTER runs on the host.
BUILD_OUTPUTS = {'.exe', '.obj', '.asi', '.dll', '.lib', '.pdb', '.exp', '.ilk', '.bin'}
PRIVATE = {'.git', '.smelter', 'projects', 'node_modules', 'third-party', '__pycache__', '.venv', 'venv',
           '.npmrc', '.pypirc', 'credentials.json', 'secrets.json'}
RESERVED = re.compile(r'(?i)^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?$')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def identifier(value):
    if not isinstance(value, str):
        raise ValueError('Expected a workspace/proposal UUID')
    try:
        parsed = str(UUID(value))
    except ValueError:
        raise ValueError('Invalid workspace/proposal UUID') from None
    if parsed != value:
        raise ValueError('Use the exact recorded UUID')
    return parsed


def relative_path(value, *, edit=False):
    if not isinstance(value, str) or not value or len(value) > 240 or '\\' in value or ':' in value:
        raise ValueError('Use a bounded relative path with forward slashes')
    parts = value.split('/')
    if any(not re.fullmatch(r'[A-Za-z0-9_.-]+', p) or p in ('.', '..') or p.endswith(('.', ' ')) or
           p.lower() in PRIVATE or p.lower().startswith('.env') or RESERVED.fullmatch(p) for p in parts):
        raise ValueError('Protected or unsafe code path')
    if parts[0] == 'mods':
        if len(parts) < 3:
            raise ValueError('Mod files live in mods/<mod>/...')
        if Path(value).suffix.lower() in BUILD_OUTPUTS:
            raise ValueError('Build outputs are not coding workspace files')
    elif parts[0] not in ('tools', 'skills') and value not in ('README.md', 'REQUIREMENTS.md', 'MASTER_HANDOVER.md'):
        raise ValueError('Code paths must be in tools/, skills/ or mods/<mod>/, or an existing top-level project document')
    if Path(value).suffix.lower() in ('.pem', '.pfx', '.key'):
        raise ValueError('Credential material is excluded')
    if edit and Path(value).suffix.lower() not in EDITABLE:
        raise ValueError('This file type has no coding editor adapter')
    return value


def base_path(root):
    return _plain_path(Path(root).resolve() / '.smelter/coding-workspaces')


def reserve_metadata(root, amount, count=1):
    from storage_budget import inventory
    rows = inventory(root, ('coding-workspaces',))
    if sum(row['bytes'] for row in rows) + amount > 128 * 1024 * 1024 or len(rows) + count > 4096:
        raise ValueError('Coding evidence quota reached (128 MiB / 4,096 files); existing evidence preserved')


def workspace_path(root, workspace_id):
    source = Path(root).resolve()
    return _plain_path(source.with_name(source.name + 'V2') / 'coding' / identifier(workspace_id))


@contextmanager
def locked(root):
    base = base_path(root)
    base.mkdir(parents=True, exist_ok=True)
    database = _plain_path(base / 'operations.sqlite3')
    with closing(sqlite3.connect(database, timeout=5)) as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS lock_owner (id INTEGER PRIMARY KEY)')
        conn.execute('BEGIN IMMEDIATE')
        try:
            yield
            conn.commit()
        finally:
            conn.rollback()


def _save(path, value):
    path = _plain_path(path)
    temporary = _plain_path(path.with_name(path.name + '.' + uuid4().hex + '.tmp'))
    try:
        with temporary.open('x', encoding='utf-8', newline='\n') as stream:
            json.dump(value, stream, ensure_ascii=True)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def load(root, workspace_id):
    sid = identifier(workspace_id)
    path = _plain_path(base_path(root) / sid / 'workspace.json')
    if not path.is_file() or path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError('Prepare a managed coding workspace first')
    value = json.loads(path.read_text(encoding='utf-8'))
    target = workspace_path(root, sid)
    if value.get('schema_version') != 1 or value.get('source') != str(Path(root).resolve()) or value.get('path') != str(target):
        raise ValueError('Coding workspace ownership marker does not match')
    require(target, 'read')
    return value, target


def _file(target, relative, *, edit=False):
    path = _plain_path(target / relative_path(relative, edit=edit))
    if path.exists() and not path.is_file():
        raise ValueError('Code target is not a regular file')
    require(path, 'write' if edit else 'read')
    return path


def _scan(target):
    from frontend_workspace import _source_files
    files = _source_files(target, ('mods',))
    result, size = {}, 0
    for relative, path in files.items():
        try:
            relative_path(relative)
        except ValueError:
            continue
        require(path, 'read')
        size += path.stat().st_size
        if size > MAX_COPY or len(result) >= MAX_FILES:
            raise ValueError('Coding snapshot exceeds 20,000 files or 128 MiB')
        result[relative] = digest(path.read_bytes())
    return result


def tree_digest(files):
    return digest(json.dumps(files, sort_keys=True, separators=(',', ':')).encode())


def prepare(root, arguments):
    if arguments:
        raise ValueError('Coding preparation accepts no paths or commands')
    from frontend_workspace import _source_files
    with locked(root):
        base = base_path(root)
        reserve_metadata(root, 8 * 1024 * 1024)
        if len(list(base.glob('*/workspace.json'))) >= 10:
            raise ValueError('Ten coding workspaces already exist; preserve/review them before starting more')
        source = Path(root).resolve()
        files = {}
        size = 0
        for relative, path in _source_files(source, ('mods',)).items():
            try:
                relative_path(relative)
            except ValueError:
                continue
            require(path, 'read')
            size += path.stat().st_size
            if len(files) >= MAX_FILES or size > MAX_COPY:
                raise ValueError('Coding copy exceeds 20,000 files or 128 MiB')
            files[relative] = path
        sid = str(uuid4())
        target = workspace_path(root, sid)
        require(target, 'write')
        require(target, 'execute', 'tests')
        if shutil.disk_usage(source).free < size + 64 * 1024 * 1024:
            raise ValueError('Insufficient space for coding copy')
        target.mkdir(parents=True, exist_ok=False)
        metadata = base / sid
        metadata.mkdir(exist_ok=False)
        try:
            hashes = {}
            for relative, path in files.items():
                destination = _file(target, relative, edit=False)
                require(destination, 'write')
                destination.parent.mkdir(parents=True, exist_ok=True)
                raw = path.read_bytes()
                destination.write_bytes(raw)
                hashes[relative] = digest(raw)
            value = {'schema_version': 1, 'workspace_id': sid, 'source': str(source), 'path': str(target),
                     'baseline': hashes, 'tests': {}, 'edits': []}
            _save(metadata / 'workspace.json', value)
        except Exception:
            shutil.rmtree(target)
            shutil.rmtree(metadata)
            raise
        from workspace_tracking import observe
        tracking = observe(root, value, target, hashes, 'prepared')
        return {'status': 'coding_workspace_ready', 'workspace_id': sid, 'path': str(target), 'tracking': tracking,
                'copied_files': len(hashes), 'bytes': size, 'baseline_sha256': tree_digest(hashes),
                'source_written': False, 'existing_v2_preserved': True,
                'limitations': 'UTF-8 file create/replace only; no deletion, dependencies, shell, Git commits or preview'}


def read(root, arguments):
    if set(arguments) - {'workspace_id', 'relative_path', 'offset', 'limit', 'start_line', 'line_count'}:
        raise ValueError('Unknown coding read argument')
    with locked(root):
        _, target = load(root, arguments.get('workspace_id'))
        relative = arguments.get('relative_path')
        path = _file(target, relative)
        if not path.is_file():
            raise ValueError('File not found in HOST coding directory: ' + str(path)
                             + '. Use list_coding_files with a filename query; the Melty folder is a separate location.')
        if path.stat().st_size > MAX_FILE:
            raise ValueError('Choose a UTF-8 code file of at most 128 KiB')
        raw = path.read_bytes()
        text = raw.decode('utf-8')
        location = {'workspace_root': str(target), 'source_root': str(Path(root).resolve()),
                    'newline_style': newline_style(text),
                    'physical_path': str(path), 'storage': 'host_directory',
                    'test_working_directory': '/'.join(Path(relative).parts[:2]) if relative.startswith('mods/') else '.',
            'tests_use': 'read-only Docker snapshots, not the live edit directory',
            'preferred_edit_tool':'propose_coding_edit',
            'edit_argument_names':['workspace_id','relative_path','expected_sha256','old_text','new_text']}
        if 'start_line' in arguments or 'line_count' in arguments:
            # Models often send a default offset/limit alongside line arguments;
            # rejecting that cost whole turns. Lines win and the result says so.
            ignored = sorted(k for k in ('offset', 'limit') if k in arguments)
            start, count = arguments.get('start_line', 1), arguments.get('line_count', 80)
            if type(start) is not int or start < 1 or type(count) is not int or not 1 <= count <= 300:
                raise ValueError('Use start_line >= 1 and line_count 1-300')
            lines = text.splitlines(keepends=True)
            chunk = ''.join(lines[start - 1:start - 1 + count])
            if len(chunk) > 16000:
                raise ValueError('Selected lines exceed 16000 characters; reduce line_count or use character pagination')
            returned = len(lines[start - 1:start - 1 + count])
            return {'status': 'coding_file_read', 'workspace_id': arguments['workspace_id'], 'relative_path': relative,
                    'sha256': digest(raw), 'bytes': len(raw), 'text': chunk, 'pagination_unit': 'lines',
                    'start_line': start, 'lines_returned': returned, 'total_lines': len(lines),
                    'has_more': start - 1 + returned < len(lines), **location,
                    **({'ignored_arguments': ignored, 'note': 'Line pagination used; character offset/limit ignored.'} if ignored else {})}
        offset, limit = arguments.get('offset', 0), arguments.get('limit', 16000)
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 16000:
            raise ValueError('Invalid code pagination')
        return {'status': 'coding_file_read', 'workspace_id': arguments['workspace_id'], 'relative_path': relative,
                'sha256': digest(raw), 'bytes': len(raw), 'text': text[offset:offset + limit],
                'offset': offset, 'pagination_unit': 'characters', 'next_offset': min(len(text), offset + limit),
                'total_characters': len(text), 'has_more': offset + limit < len(text), **location}


def list_files(root, arguments):
    if set(arguments) - {'workspace_id', 'offset', 'limit', 'query'}:
        raise ValueError('Unknown coding list argument')
    with locked(root):
        metadata, target = load(root, arguments.get('workspace_id'))
        files = _scan(target)
        offset, limit = arguments.get('offset', 0), arguments.get('limit', 100)
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError('Invalid coding list pagination')
        query = arguments.get('query', '')
        if not isinstance(query, str) or len(query) > 200:
            raise ValueError('Use a filename/path substring query of at most 200 characters')
        names = sorted(name for name in files if query.casefold() in name.casefold())
        from workspace_tracking import observe
        tracking = observe(root, metadata, target, files, 'listed')
        return {'status': 'coding_files_listed', 'workspace_id': arguments['workspace_id'], 'total': len(names),
                'files': [{'relative_path': p, 'sha256': files[p], 'physical_path': str(target / p)} for p in names[offset:offset + limit]],
                'has_more': offset + limit < len(names), 'tree_sha256': tree_digest(files),
                'workspace_root': str(target), 'source_root': str(Path(root).resolve()), 'storage': 'host_directory',
                'query': query, 'tracking': tracking}


def _summary(full, index, checkpoints, contracts):
    """Compact model view: changed files and evidence, not every hash/path/graph node.

    The full view cost a 128K-context model ~27K tokens per call (hex hashes and
    absolute paths tokenize poorly), which forced compaction mid-task.
    """
    def row(item):
        return {'relative_path': item['relative_path'], 'sha256': item.get('sha256'), 'status': item.get('status')}
    from access_policy import allowed
    changed = [row(item) for item in index['files'] if item.get('status') not in (None, 'unchanged')
               and allowed(Path(index['workspace_root']) / item['relative_path'], 'read')]
    files = full['files']
    return {**{k: full[k] for k in ('workspace_id', 'workspace_root', 'source_root', 'revision', 'tests')},
            'detail': 'summary', 'query': full['query'], 'files': [row(item) for item in files],
            'matching_files': full['matching_files'], 'total_files': full['total_files'],
            'offset': full['offset'], 'has_more': full['has_more'],
            'changed_files': changed[:30], 'changed_files_total': len(changed),
            'checkpoints': [{k: c.get(k) for k in ('relative_path', 'sha256')} for c in checkpoints[-6:]],
            'acceptance_contracts': contracts,
            'more': 'Use read_coding_file for one exact path, query to search paths, or detail="full" for graph/history/absolute paths.'}


def context(root, arguments):
    if set(arguments) - {'workspace_id', 'query', 'offset', 'limit', 'detail'}:
        raise ValueError('Workspace context accepts workspace_id, query, pagination and detail only')
    detail = arguments.get('detail', 'summary')
    if detail not in ('summary', 'full'):
        raise ValueError('detail must be summary or full')
    from workspace_tracking import registry, capture, view
    with locked(root):
        if 'workspace_id' not in arguments:
            if arguments:
                raise ValueError('Select a workspace_id before searching its files')
            return {'status': 'coding_workspace_registry', **registry(root)}
        metadata, target = load(root, arguments['workspace_id'])
        value = capture(root, metadata, target, _scan(target), 'context refreshed')
        checkpoints = []
        for item in metadata.get('checkpoints', [])[-12:]:
            try:
                _file(target, item['relative_path'])
                checkpoints.append(item)
            except (ValueError, OSError, KeyError):
                continue
        from acceptance_contracts import load as load_contracts, summary
        contracts = summary(load_contracts(root, arguments['workspace_id'], target))
        if detail == 'summary':
            # Without a query the summary lists changed files only, not every file.
            limit = arguments.get('limit', 20) if arguments.get('query') else arguments.get('limit', 1)
            full = view(value, arguments.get('query', ''), arguments.get('offset', 0), limit)
            if not arguments.get('query'):
                full['files'] = []
            return {'status': 'coding_workspace_context', **_summary(full, value, checkpoints, contracts)}
        return {'status': 'coding_workspace_context', **view(value, arguments.get('query', ''),
                arguments.get('offset', 0), arguments.get('limit', 50)), 'checkpoints': checkpoints,
                'acceptance_contracts': contracts, 'detail': 'full'}


def _changes(target, changes, allow_large_replacement=False):
    if not isinstance(changes, list) or not 1 <= len(changes) <= MAX_CHANGES:
        raise ValueError('Propose one to six file replacements')
    result, seen, size = [], set(), 0
    for change in changes:
        if not isinstance(change, dict) or set(change) != {'relative_path', 'expected_sha256', 'content'}:
            raise ValueError('Each change requires relative_path, expected_sha256 and complete content')
        relative = relative_path(change['relative_path'], edit=True)
        if relative.lower() in seen:
            raise ValueError('Duplicate/case-colliding patch path: group all replacements for a file in ONE edits entry, or use propose_coding_edit for one replacement')
        seen.add(relative.lower())
        path = _file(target, relative, edit=True)
        expected = change['expected_sha256']
        if expected is not None and (not isinstance(expected, str) or not re.fullmatch(r'[a-f0-9]{64}', expected)):
            raise ValueError('Use an exact SHA-256, or null for a new file')
        if path.is_file() and path.stat().st_size > MAX_FILE:
            raise ValueError('Existing code file exceeds 128 KiB')
        before = path.read_bytes() if path.is_file() else None
        current_hash = digest(before) if before is not None else None
        if current_hash != expected:
            raise ValueError('File changed or create would overwrite: ' + relative
                             + '. Current DESTINATION sha256: ' + str(current_hash)
                             + '. expected_sha256 must match the destination before editing; null is only for a missing file.'
                             + ' To restore original checkout bytes, use propose_coding_restore.')
        text = change['content']
        if not isinstance(text, str) or '\x00' in text:
            raise ValueError('Code content must be UTF-8 text without NUL')
        after = text.encode('utf-8')
        size += len(after)
        if len(after) > MAX_FILE or size > MAX_PATCH:
            raise ValueError('Patch exceeds 128 KiB per file or 512 KiB total')
        old = before.decode('utf-8') if before is not None else ''
        before_lines, after_lines = len(old.splitlines()), len(text.splitlines())
        large_drop = bool(before and len(before) >= 1024 and before_lines >= 30 and
                          len(after) < len(before) * .35 and after_lines < before_lines * .5)
        if large_drop and not allow_large_replacement:
            raise ValueError('Likely snippet-as-file replacement rejected for ' + relative +
                ': ' + str(before_lines) + ' lines would become ' + str(after_lines) +
                '. content replaces the ENTIRE file. Use propose_coding_edits for targeted changes. '
                'Only intentional whole-file rewrites may set allow_large_replacement=true.')
        diff = ''.join(difflib.unified_diff(old.splitlines(keepends=True), text.splitlines(keepends=True),
                       fromfile='before/' + relative, tofile='after/' + relative))
        result.append({**change, 'after_sha256': digest(after), 'bytes': len(after), 'diff': diff[:2600],
                       'diff_truncated': len(diff) > 2600, 'before_lines': before_lines,
                       'after_lines': after_lines, 'large_replacement': large_drop})
    return result


def _record_proposal(root, workspace_id, changes, restoration_source=None, restoration_checkpoint=None):
    """Record validated changes while the caller holds the workspace lock."""
    pid = str(uuid4())
    value = {'proposal_id': pid, 'workspace_id': workspace_id, 'state': 'proposed', 'changes': changes}
    value['allow_large_replacement'] = any(c['large_replacement'] for c in changes)
    if restoration_source is not None:
        value['restoration_source'] = restoration_source
    if restoration_checkpoint is not None:
        value['restoration_checkpoint'] = restoration_checkpoint
    reserve_metadata(root, len(json.dumps(value).encode()))
    folder = base_path(root) / workspace_id / 'proposals'
    folder.mkdir(exist_ok=True)
    _save(folder / (pid + '.json'), value)
    result = {'status': 'coding_patch_proposed', 'workspace_id': workspace_id, 'proposal_id': pid,
              'files': [{k: c[k] for k in ('relative_path', 'expected_sha256', 'after_sha256', 'bytes', 'diff', 'diff_truncated', 'before_lines', 'after_lines', 'large_replacement')}
                        for c in changes], 'applied': False}
    if restoration_source is not None:
        result['restoration_source'] = restoration_source
    if restoration_checkpoint is not None:
        result['restoration_checkpoint'] = restoration_checkpoint
    return result


def _lua_gate(root, target, changes):
    """Refuse a proposal that would break a parsing Lua file; never executes code.

    A file that already fails to parse may be edited stepwise, so the result
    then only carries the remaining parser error instead of a refusal.
    """
    lua = [c for c in changes if c['relative_path'].lower().endswith('.lua')]
    if not lua:
        return None
    sources = {}
    for c in lua:
        path = _file(target, c['relative_path'], edit=True)
        if path.is_file():
            sources['before:' + c['relative_path']] = path.read_bytes().decode('utf-8', errors='replace')
        sources['after:' + c['relative_path']] = c['content']
    from sandbox import lua_parse
    parsed = lua_parse(root, sources)
    if parsed is None:
        return {'checked': False, 'reason': 'Lua parser sandbox unavailable; run_coding_tests will still preflight syntax'}
    report = []
    for c in lua:
        relative = c['relative_path']
        error = parsed.get('after:' + relative)
        if not error:
            continue
        before_ok = 'before:' + relative not in sources or parsed.get('before:' + relative) is None
        lines = c['content'].splitlines()
        number = int(error.split(':', 1)[0]) if error.split(':', 1)[0].isdigit() else 0
        excerpt = '\n'.join(str(i + 1) + ': ' + lines[i][:200] for i in range(max(0, number - 3), min(len(lines), number + 2)))
        if before_ok:
            raise ValueError('Lua syntax error; proposal NOT recorded: ' + relative + ':' + error +
                             '\n' + excerpt + '\nPut one statement per line, balance every do/if/function with end, '
                             'then propose again against the same expected_sha256.')
        report.append({'relative_path': relative, 'error': error, 'excerpt': excerpt,
                       'note': 'File already failed to parse before this edit; fix this remaining error next.'})
    return {'checked': True, 'remaining_syntax_errors': report}


def propose(root, arguments):
    if set(arguments) - {'workspace_id', 'changes', 'allow_large_replacement'} or not {'workspace_id', 'changes'} <= set(arguments):
        raise ValueError('Coding proposals require workspace_id, changes and optional allow_large_replacement')
    allow = arguments.get('allow_large_replacement', False)
    if type(allow) is not bool:
        raise ValueError('allow_large_replacement must be boolean')
    with locked(root):
        _, target = load(root, arguments['workspace_id'])
        changes = _changes(target, arguments['changes'], allow)
        syntax = _lua_gate(root, target, changes)
        return _with_syntax(_record_proposal(root, arguments['workspace_id'], changes), syntax)


def _with_syntax(result, syntax):
    if syntax is not None:
        result['lua_syntax'] = syntax
    return result


def newline_style(text):
    crlf = text.count('\r\n')
    lf = text.count('\n') - crlf
    cr = text.count('\r') - crlf
    kinds = [name for name, count in (('CRLF', crlf), ('LF', lf), ('CR', cr)) if count]
    return 'mixed' if len(kinds) > 1 else kinds[0] if kinds else 'none'


def replace_context(text, old, new):
    """Only normalize CRLF/LF for matching; preserve bytes outside that match.

    Match uniqueness is checked on the normalized view even if one raw match
    exists: otherwise two visually identical contexts could select arbitrarily.
    Bare CR and whitespace are never treated as equivalent.
    """
    normalized, needle = text.replace('\r\n', '\n'), old.replace('\r\n', '\n')
    count = normalized.count(needle)
    if count != 1:
        raise ValueError('Exact edit context matched ' + str(count) + ' times; provide unique current context')
    start = normalized.index(needle)
    # Map LF-view character boundaries back to original UTF-8 text boundaries.
    boundaries, index = [0], 0
    while index < len(text):
        index += 2 if text.startswith('\r\n', index) else 1
        boundaries.append(index)
    first, last = boundaries[start], boundaries[start + len(needle)]
    matched = text[first:last]
    style = newline_style(matched)
    if style == 'CRLF':
        new = new.replace('\r\n', '\n').replace('\n', '\r\n')
    elif style == 'LF':
        new = new.replace('\r\n', '\n')
    return text[:first] + new + text[last:]


def edit_changes(target, changes):
    """Assemble complete files on the controller from unique exact contexts."""
    if not isinstance(changes, list) or not 1 <= len(changes) <= MAX_CHANGES:
        raise ValueError('Edit one to six existing files')
    assembled = []
    for change in changes:
        if not isinstance(change, dict) or set(change) != {'relative_path', 'expected_sha256', 'edits'}:
            raise ValueError('Exact edits require relative_path, expected_sha256 and edits')
        path = _file(target, change['relative_path'], edit=True)
        if not path.is_file() or path.stat().st_size > MAX_FILE:
            raise ValueError('Read an existing UTF-8 file before targeted edits')
        raw = path.read_bytes()
        if digest(raw) != change['expected_sha256']:
            raise ValueError('File changed before exact edits; read the current destination hash')
        edits = change['edits']
        if not isinstance(edits, list) or not 1 <= len(edits) <= 16:
            raise ValueError('Use one to sixteen exact text replacements per file')
        text = raw.decode('utf-8')
        for edit in edits:
            if not isinstance(edit, dict) or set(edit) != {'old_text', 'new_text'}:
                raise ValueError('Each edit needs old_text and new_text')
            old, new = edit['old_text'], edit['new_text']
            if not isinstance(old, str) or not old or not isinstance(new, str) or '\x00' in old + new:
                raise ValueError('Use nonempty exact old_text and UTF-8 new_text without NUL')
            if len(old.encode('utf-8')) > MAX_FILE or len(new.encode('utf-8')) > MAX_FILE:
                raise ValueError('Exact edit text exceeds 128 KiB')
            text = replace_context(text, old, new)
        assembled.append({'relative_path': change['relative_path'], 'expected_sha256': change['expected_sha256'], 'content': text})
    return assembled


def propose_edits(root, arguments):
    if set(arguments) != {'workspace_id', 'changes'}:
        raise ValueError('Exact edit proposals require workspace_id and changes')
    with locked(root):
        _, target = load(root, arguments['workspace_id'])
        changes = _changes(target, edit_changes(target, arguments['changes']))
        syntax = _lua_gate(root, target, changes)
        return _with_syntax(_record_proposal(root, arguments['workspace_id'], changes), syntax)


def propose_edit(root, arguments):
    """Scalar one-file/one-replacement interface; same checked proposal engine."""
    if set(arguments) != {'workspace_id','relative_path','expected_sha256','old_text','new_text'}:
        raise ValueError('Single edit requires workspace_id, relative_path, expected_sha256, old_text and new_text')
    return propose_edits(root, {'workspace_id':arguments['workspace_id'], 'changes':[{
        'relative_path':arguments['relative_path'], 'expected_sha256':arguments['expected_sha256'],
        'edits':[{'old_text':arguments['old_text'], 'new_text':arguments['new_text']}]}]})


def _checkpoint_path(root, sid, relative, sha):
    relative = relative_path(relative, edit=True)
    if not isinstance(sha, str) or not re.fullmatch(r'[a-f0-9]{64}', sha):
        raise ValueError('Choose an exact checkpoint SHA-256')
    # Short deterministic storage keys keep atomic-temp filenames below Windows
    # path limits. Full path ownership and the complete SHA are checked in JSON.
    key = digest((relative + '\x00' + sha).encode('utf-8'))[:32]
    return _plain_path(base_path(root) / identifier(sid) / 'checkpoints' / (key + '.json'))


def read_checkpoint(root, sid, relative, sha):
    path = _checkpoint_path(root, sid, relative, sha)
    if not path.is_file() or path.stat().st_size > MAX_FILE * 6 + 4096:
        raise ValueError('No bounded checkpoint exists for this workspace, path and hash')
    value = json.loads(path.read_text(encoding='utf-8'))
    if (value.get('workspace_id') != sid or value.get('relative_path') != relative or
        value.get('sha256') != sha or not isinstance(value.get('content'), str)):
        raise ValueError('Checkpoint ownership mismatch')
    raw = value['content'].encode('utf-8')
    if len(raw) > MAX_FILE or digest(raw) != sha:
        raise ValueError('Checkpoint bytes changed')
    return raw


def checkpoint(root, sid, relative, raw):
    sha = digest(raw); path = _checkpoint_path(root, sid, relative, sha)
    if path.exists():
        if read_checkpoint(root, sid, relative, sha) != raw:
            raise ValueError('Existing checkpoint does not match its hash')
    else:
        value = {'workspace_id': sid, 'relative_path': relative, 'sha256': sha, 'content': raw.decode('utf-8')}
        reserve_metadata(root, len(json.dumps(value).encode('utf-8')))
        path.parent.mkdir(parents=True, exist_ok=True)
        _save(path, value)
    return {'relative_path': relative, 'sha256': sha, 'bytes': len(raw)}


def _restore_position(metadata, relative, sha):
    """Say how old a restored checkpoint is; a model once restored its first,
    wrong draft and silently discarded a dozen later fixes."""
    history = [c['sha256'] for c in metadata.get('checkpoints', []) if c.get('relative_path') == relative]
    index = max((i for i, value in enumerate(history) if value == sha), default=-1)
    newer = len(history) - index - 1 if index >= 0 else None
    return {'checkpoint_position': (index + 1) if index >= 0 else None, 'checkpoints_for_path': len(history),
            'newer_versions_discarded': newer,
            'message': ('Restoring version ' + str(index + 1) + ' of ' + str(len(history)) + ' for this path discards '
                        + str(newer) + ' newer saved version(s). Prefer the most recent checkpoint unless you know '
                        'this older one is correct; compare the diff before applying.') if newer else
                       'Restoring the most recent saved version of this path.'}


def propose_restore(root, arguments):
    """Snapshot original text and destination hashes, without applying edits."""
    if set(arguments) - {'workspace_id', 'relative_paths', 'checkpoint_sha256'} or not {'workspace_id', 'relative_paths'} <= set(arguments):
        raise ValueError('Restoration accepts workspace_id, relative_paths and optional checkpoint_sha256')
    paths = arguments['relative_paths']
    if (not isinstance(paths, list) or not 1 <= len(paths) <= MAX_CHANGES
            or any(not isinstance(p, str) for p in paths)
            or len({p.lower() for p in paths}) != len(paths)):
        raise ValueError('Restore one to six distinct original source paths')
    with locked(root):
        _, target = load(root, arguments['workspace_id'])
        if 'checkpoint_sha256' in arguments:
            if len(paths) != 1:
                raise ValueError('Restore one checkpoint path at a time')
            relative = relative_path(paths[0], edit=True)
            _file(target, relative)
            raw = read_checkpoint(root, arguments['workspace_id'], relative, arguments['checkpoint_sha256'])
            destination = _file(target, relative, edit=True)
            if destination.is_file() and destination.stat().st_size > MAX_FILE:
                raise ValueError('Existing code file exceeds 128 KiB')
            before = destination.read_bytes() if destination.is_file() else None
            changes = [{'relative_path': relative, 'content': raw.decode('utf-8'),
                        'expected_sha256': digest(before) if before is not None else None}]
            origin = [{'relative_path': relative, 'sha256': digest(raw)}]
            result = _record_proposal(root, arguments['workspace_id'], _changes(target, changes, True), restoration_checkpoint=origin)
            result['restore_warning'] = _restore_position(load(root, arguments['workspace_id'])[0], relative, digest(raw))
            return result
        changes, sources = [], []
        for supplied in paths:
            relative = relative_path(supplied, edit=True)
            source = _file(Path(root).resolve(), relative)
            if not source.is_file() or source.stat().st_size > MAX_FILE:
                raise ValueError('Original UTF-8 source is missing or oversized: ' + relative +
                    '. Workspace-only files have no checkout baseline; choose a saved checkpoint_sha256 from workspace context.')
            raw = source.read_bytes()
            destination = _file(target, relative, edit=True)
            if destination.is_file() and destination.stat().st_size > MAX_FILE:
                raise ValueError('Existing code file exceeds 128 KiB')
            before = destination.read_bytes() if destination.is_file() else None
            changes.append({'relative_path': relative, 'content': raw.decode('utf-8'),
                            'expected_sha256': digest(before) if before is not None else None})
            sources.append({'relative_path': relative, 'sha256': digest(raw)})
        return _record_proposal(root, arguments['workspace_id'], _changes(target, changes, True), sources)


def proposal(root, workspace_id, proposal_id):
    path = _plain_path(base_path(root) / identifier(workspace_id) / 'proposals' / (identifier(proposal_id) + '.json'))
    # JSON escapes can expand valid UTF-8 content beyond its raw byte budget.
    if not path.is_file() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError('Unknown or oversized coding proposal')
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('workspace_id') != workspace_id or value.get('proposal_id') != proposal_id:
        raise ValueError('Coding proposal ownership mismatch')
    return path, value


def apply(root, arguments):
    if set(arguments) != {'workspace_id', 'proposal_id'}:
        raise ValueError('Apply a recorded proposal ID, never a command or new payload')
    with locked(root):
        metadata, target = load(root, arguments['workspace_id'])
        record, plan = proposal(root, arguments['workspace_id'], arguments['proposal_id'])
        if plan['state'] == 'applied':
            if any(not _file(target, c['relative_path']).is_file() or
                   digest(_file(target, c['relative_path']).read_bytes()) != c['after_sha256'] for c in plan['changes']):
                raise ValueError('Already-applied proposal has subsequent edits; inspect current files')
            return {'status': 'coding_patch_applied', 'workspace_id': arguments['workspace_id'],
                    'proposal_id': arguments['proposal_id'], 'reused': True, 'files': plan['files'], 'checkpoints': plan.get('checkpoints', [])}
        if plan['state'] != 'proposed':
            raise ValueError('Proposal is not replayable: ' + plan['state'])
        for original in plan.get('restoration_source', []):
            source = _file(Path(root).resolve(), original['relative_path'])
            if (not source.is_file() or source.stat().st_size > MAX_FILE
                    or digest(source.read_bytes()) != original['sha256']):
                raise ValueError('Original source changed since restoration proposal: ' + original['relative_path'])
        for original in plan.get('restoration_checkpoint', []):
            read_checkpoint(root, arguments['workspace_id'], original['relative_path'], original['sha256'])
        changes = _changes(target, [{k: c[k] for k in ('relative_path', 'expected_sha256', 'content')} for c in plan['changes']],
                           plan.get('allow_large_replacement') is True)
        backups, staged, installed = {}, [], []
        plan['checkpoints'] = []
        plan['state'] = 'applying'
        _save(record, plan)
        try:
            for change in changes:
                path = _file(target, change['relative_path'], edit=True)
                backups[path] = path.read_bytes() if path.exists() else None
                if backups[path] is not None:
                    plan['checkpoints'].append(checkpoint(root, arguments['workspace_id'], change['relative_path'], backups[path]))
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = _plain_path(path.with_name('.smelter-patch-' + uuid4().hex))
                with temporary.open('xb') as stream:
                    stream.write(change['content'].encode('utf-8'))
                staged.append((temporary, path, change))
            _save(record, plan)  # Persist recovery references before replacing any source bytes.
            for temporary, path, change in staged:
                current = path.read_bytes() if path.exists() else None
                if (digest(current) if current is not None else None) != change['expected_sha256']:
                    raise ValueError('Concurrent file edit before apply: ' + change['relative_path'])
                temporary.replace(path)
                installed.append((path, change))
                if digest(path.read_bytes()) != change['after_sha256']:
                    raise ValueError('Saved bytes did not match proposal')
            plan['files'] = [{k: c[k] for k in ('relative_path', 'after_sha256', 'bytes')} for c in changes]
            metadata['edits'].append(plan['proposal_id'])
            references = metadata.get('checkpoints', []) + plan['checkpoints']
            metadata['checkpoints'] = list({(c['relative_path'], c['sha256']): c for c in references}.values())[-64:]
            _save(base_path(root) / arguments['workspace_id'] / 'workspace.json', metadata)
            plan['state'] = 'applied'
            _save(record, plan)
        except Exception:
            restored = True
            for path, change in reversed(installed):
                try:
                    _plain_path(path)
                    if digest(path.read_bytes()) != change['after_sha256']:
                        restored = False
                        continue
                    if backups[path] is None:
                        path.unlink()
                    else:
                        restored_file = _plain_path(path.with_name('.smelter-restore-' + uuid4().hex))
                        try:
                            with restored_file.open('xb') as stream:stream.write(backups[path])
                            restored_file.replace(path)
                        finally:restored_file.unlink(missing_ok=True)
                except OSError:
                    restored = False
            plan['state'] = 'rolled_back' if restored else 'partial_unconfirmed'
            _save(record, plan)
            raise
        finally:
            for temporary, _, _ in staged:
                temporary.unlink(missing_ok=True)
        from workspace_tracking import observe
        tracking = observe(root, metadata, target, None, 'patch applied')
        return {'status': 'coding_patch_applied', 'workspace_id': arguments['workspace_id'],
                'proposal_id': plan['proposal_id'], 'files': plan['files'], 'reused': False,
                'source_written': False, 'tracking': tracking, 'checkpoints': plan['checkpoints']}


def test_profiles(target):
    folder = target / 'tools/dashboard'
    profiles = [name for name, pattern in [('python', 'test_*.py'), ('node', 'test_*.js')]
                if any(folder.glob(pattern))]
    return (profiles + (['mods'] if any(target.glob('mods/*/tests/test_*.py')) else [])
            + (['cpp'] if any(target.glob('mods/*/tests/cpp/test_*.cpp')) else [])
            + (['lua'] if any(target.glob('mods/*/tests/test_*.lua')) else []))


def test(root, arguments):
    if set(arguments) != {'workspace_id', 'profile'} or arguments.get('profile') not in ('python', 'node', 'mods', 'cpp', 'lua'):
        raise ValueError('Choose the fixed python, node, mods, cpp or lua test profile; no command arguments')
    sid, profile = arguments['workspace_id'], arguments['profile']
    with locked(root):
        metadata, target = load(root, sid)
        require(target, 'execute', 'tests')
        if profile not in test_profiles(target):
            raise ValueError('No tests exist for this profile')
        files = _scan(target)
        before = tree_digest(files)
        from acceptance_contracts import load as load_contracts, run as run_contracts, revision
        contracts=[c for c in load_contracts(root,sid,target) if c['profile']==profile]
        from workspace_tracking import observe
        observe(root, metadata, target, files, 'testing ' + profile)
        from sandbox import coding_test
        reserve_metadata(root, 3 * 1024 * 1024, 2)
        # The runner takes its own immutable snapshot before releasing this
        # operation lock. Other tool processes cannot race snapshot creation.
        evidence = coding_test(root, target, profile)
        if contracts:
            try:
                accepted=run_contracts(root,target,contracts,files)
            except (ValueError,OSError) as exc:
                accepted={'stage':'ERROR','contracts_revision':revision(contracts),'contracts':[],
                          'error':str(exc)[:500],'_raw_output':('ACCEPTANCE ERROR: '+str(exc)[:500]).encode('utf-8')}
            evidence['_raw_output']+=b'\n[CONTROLLER ACCEPTANCE]\n'+accepted.pop('_raw_output')
            evidence['workspace_tests_stage']=evidence['stage']
            evidence['acceptance']=accepted
            stages=(evidence['stage'],accepted['stage'])
            evidence['stage']='ERROR' if 'ERROR' in stages else 'RED' if 'RED' in stages else 'GREEN'
            if accepted['stage']!='GREEN':evidence['exit_code']=1
            evidence['log_tail']=evidence['_raw_output'].decode('utf-8',errors='replace')[-10000:]
        current, _ = load(root, sid)
        current_tree = tree_digest(_scan(target))
        result = {**evidence, 'workspace_id': sid, 'profile': profile, 'tree_sha256': before,
                  'current_tree_matches': current_tree == before}
        folder = base_path(root) / sid / 'test-runs'
        folder.mkdir(exist_ok=True)
        run_id = str(uuid4())
        raw = result.pop('_raw_output')
        from coding_recovery import diagnose
        result['diagnostic'] = diagnose(raw)
        if contracts and result.get('acceptance', {}).get('stage') != 'GREEN':
            from coding_recovery import anchor
            if not result['diagnostic']:
                result['diagnostic'] = {'classification': 'acceptance_error',
                    'guidance': 'Frozen acceptance did not complete; read failing_contracts and the acceptance log section.'}
            anchor(root, sid, target, result['diagnostic'], result['acceptance'])
        output = folder / (run_id + '.log')
        with output.open('xb') as stream:
            stream.write(raw)
        result.update(log_path=str(output), log_sha256=digest(raw))
        log = folder / (run_id + '.json')
        _save(log, result)
        current['tests'][profile] = {'path': str(log), 'tree_sha256': before,
                                    'stage': result['stage'], 'exit_code': result['exit_code']}
        if profile=='lua':
            current['tests'][profile]['runner_sha256']=result.get('runner_sha256')
        if contracts:current['tests'][profile]['acceptance_revision']=revision(contracts)
        if contracts:
            current['tests'][profile].update(workspace_tests_stage=result['workspace_tests_stage'],
                acceptance_stage=result['acceptance']['stage'])
        _save(base_path(root) / sid / 'workspace.json', current)
        tracking = observe(root, current, target, None, 'tested ' + profile + ': ' + result['stage'])
        return {**result, 'evidence_path': str(log),
                'status': 'coding_tests_passed' if result['stage'] == 'GREEN' else 'coding_tests_failed', 'tracking': tracking}


def review(root, arguments):
    if set(arguments) != {'workspace_id'}:
        raise ValueError('Coding review requires workspace_id only')
    with locked(root):
        metadata, target = load(root, arguments['workspace_id'])
        files = _scan(target)
        tree = tree_digest(files)
        baseline = metadata['baseline']
        changed = [{'relative_path': name, 'before_sha256': baseline.get(name), 'after_sha256': files.get(name)}
                   for name in sorted(set(baseline) | set(files)) if baseline.get(name) != files.get(name)]
        profiles = test_profiles(target)
        checks = [{'profile': profile, **metadata['tests'].get(profile, {}),
                   'current': metadata['tests'].get(profile, {}).get('tree_sha256') == tree} for profile in profiles]
        from acceptance_contracts import fresh
        for check in checks:check['current']=check['current'] and fresh(root,arguments['workspace_id'],target,check['profile'],check)
        if 'lua' in profiles:
            from sandbox import lua_runner_sha256
            for check in checks:
                if check['profile']=='lua':
                    check['runner_current']=check.get('runner_sha256')==lua_runner_sha256()
                    check['current']=check['current'] and check['runner_current']
        passed = bool(checks) and all(c.get('stage') == 'GREEN' and c['current'] for c in checks)
        from workspace_tracking import observe
        tracking = observe(root, metadata, target, files, 'reviewed')
        return {'status': 'coding_workspace_reviewed', 'workspace_id': arguments['workspace_id'],
                'path': str(target), 'tree_sha256': tree, 'changed_files': changed[:200],
                'changed_files_total': len(changed), 'changes_truncated': len(changed) > 200,
                'required_profiles': profiles, 'checks': checks, 'all_current_tests_passed': passed,
                'coverage': 'not measured', 'visual_inspection': 'not performed',
                'source_written': False, 'tracking': tracking, 'message': 'Review the diff and actual tests; model narrative is not verification.'}


def execute(root, grants, name, arguments):
    if not grants.get('coding_workspace'):
        raise ValueError('Coding workspace was not approved for this message')
    from coding_recovery import recover
    from coding_finish import finish
    from contract_scaffold import scaffold
    handlers = {'scaffold_contract_subject': scaffold, 'prepare_coding_workspace': prepare, 'coding_workspace_context': context, 'coding_recovery_context': recover, 'list_coding_files': list_files, 'read_coding_file': read,
                'propose_coding_patch': propose, 'propose_coding_edit': propose_edit, 'propose_coding_edits': propose_edits, 'propose_coding_restore': propose_restore,
                'apply_coding_patch': apply, 'run_coding_tests': test, 'finish_coding_task': finish,
                'review_coding_workspace': review}
    if name not in handlers or not isinstance(arguments, dict):
        raise ValueError('Unknown coding operation or invalid arguments')
    return handlers[name](root, arguments)
