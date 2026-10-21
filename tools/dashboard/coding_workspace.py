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
EDITABLE = {'.py', '.js', '.mjs', '.cjs', '.css', '.html', '.json', '.md', '.toml', '.yaml', '.yml'}
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
    if parts[0] not in ('tools', 'skills') and value not in ('README.md', 'REQUIREMENTS.md', 'MASTER_HANDOVER.md'):
        raise ValueError('Code paths must be in tools/ or skills/, or an existing top-level project document')
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
    files = _source_files(target)
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
        for relative, path in _source_files(source).items():
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
        return {'status': 'coding_workspace_ready', 'workspace_id': sid, 'path': str(target),
                'copied_files': len(hashes), 'bytes': size, 'baseline_sha256': tree_digest(hashes),
                'source_written': False, 'existing_v2_preserved': True,
                'limitations': 'UTF-8 file create/replace only; no deletion, dependencies, shell, Git commits or preview'}


def read(root, arguments):
    if set(arguments) - {'workspace_id', 'relative_path', 'offset', 'limit'}:
        raise ValueError('Unknown coding read argument')
    with locked(root):
        _, target = load(root, arguments.get('workspace_id'))
        relative = arguments.get('relative_path')
        path = _file(target, relative)
        if not path.is_file() or path.stat().st_size > MAX_FILE:
            raise ValueError('Choose an existing UTF-8 code file of at most 128 KiB')
        raw = path.read_bytes()
        text = raw.decode('utf-8')
        offset, limit = arguments.get('offset', 0), arguments.get('limit', 16000)
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 16000:
            raise ValueError('Invalid code pagination')
        return {'status': 'coding_file_read', 'workspace_id': arguments['workspace_id'], 'relative_path': relative,
                'sha256': digest(raw), 'bytes': len(raw), 'text': text[offset:offset + limit],
                'offset': offset, 'total_characters': len(text), 'has_more': offset + limit < len(text)}


def list_files(root, arguments):
    if set(arguments) - {'workspace_id', 'offset', 'limit'}:
        raise ValueError('Unknown coding list argument')
    with locked(root):
        _, target = load(root, arguments.get('workspace_id'))
        files = _scan(target)
        offset, limit = arguments.get('offset', 0), arguments.get('limit', 100)
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError('Invalid coding list pagination')
        names = sorted(files)
        return {'status': 'coding_files_listed', 'workspace_id': arguments['workspace_id'], 'total': len(names),
                'files': [{'relative_path': p, 'sha256': files[p]} for p in names[offset:offset + limit]],
                'has_more': offset + limit < len(names), 'tree_sha256': tree_digest(files)}


def _changes(target, changes):
    if not isinstance(changes, list) or not 1 <= len(changes) <= MAX_CHANGES:
        raise ValueError('Propose one to six file replacements')
    result, seen, size = [], set(), 0
    for change in changes:
        if not isinstance(change, dict) or set(change) != {'relative_path', 'expected_sha256', 'content'}:
            raise ValueError('Each change requires relative_path, expected_sha256 and complete content')
        relative = relative_path(change['relative_path'], edit=True)
        if relative.lower() in seen:
            raise ValueError('Duplicate/case-colliding patch path')
        seen.add(relative.lower())
        path = _file(target, relative, edit=True)
        expected = change['expected_sha256']
        if expected is not None and (not isinstance(expected, str) or not re.fullmatch(r'[a-f0-9]{64}', expected)):
            raise ValueError('Use an exact SHA-256, or null for a new file')
        if path.is_file() and path.stat().st_size > MAX_FILE:
            raise ValueError('Existing code file exceeds 128 KiB')
        before = path.read_bytes() if path.is_file() else None
        if (digest(before) if before is not None else None) != expected:
            raise ValueError('File changed or create would overwrite: ' + relative)
        text = change['content']
        if not isinstance(text, str) or '\x00' in text:
            raise ValueError('Code content must be UTF-8 text without NUL')
        after = text.encode('utf-8')
        size += len(after)
        if len(after) > MAX_FILE or size > MAX_PATCH:
            raise ValueError('Patch exceeds 128 KiB per file or 512 KiB total')
        old = before.decode('utf-8') if before is not None else ''
        diff = ''.join(difflib.unified_diff(old.splitlines(keepends=True), text.splitlines(keepends=True),
                       fromfile='before/' + relative, tofile='after/' + relative))
        result.append({**change, 'after_sha256': digest(after), 'bytes': len(after), 'diff': diff[:2600],
                       'diff_truncated': len(diff) > 2600})
    return result


def propose(root, arguments):
    if set(arguments) != {'workspace_id', 'changes'}:
        raise ValueError('Coding proposals require workspace_id and changes only')
    with locked(root):
        _, target = load(root, arguments['workspace_id'])
        changes = _changes(target, arguments['changes'])
        pid = str(uuid4())
        value = {'proposal_id': pid, 'workspace_id': arguments['workspace_id'], 'state': 'proposed', 'changes': changes}
        reserve_metadata(root, len(json.dumps(value).encode()))
        folder = base_path(root) / arguments['workspace_id'] / 'proposals'
        folder.mkdir(exist_ok=True)
        _save(folder / (pid + '.json'), value)
        return {'status': 'coding_patch_proposed', 'workspace_id': arguments['workspace_id'], 'proposal_id': pid,
                'files': [{k: c[k] for k in ('relative_path', 'expected_sha256', 'after_sha256', 'bytes', 'diff', 'diff_truncated')}
                          for c in changes], 'applied': False}


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
                    'proposal_id': arguments['proposal_id'], 'reused': True, 'files': plan['files']}
        if plan['state'] != 'proposed':
            raise ValueError('Proposal is not replayable: ' + plan['state'])
        changes = _changes(target, [{k: c[k] for k in ('relative_path', 'expected_sha256', 'content')} for c in plan['changes']])
        backups, staged, installed = {}, [], []
        plan['state'] = 'applying'
        _save(record, plan)
        try:
            for change in changes:
                path = _file(target, change['relative_path'], edit=True)
                backups[path] = path.read_bytes() if path.exists() else None
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = _plain_path(path.with_name('.smelter-patch-' + uuid4().hex))
                with temporary.open('xb') as stream:
                    stream.write(change['content'].encode('utf-8'))
                staged.append((temporary, path, change))
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
        return {'status': 'coding_patch_applied', 'workspace_id': arguments['workspace_id'],
                'proposal_id': plan['proposal_id'], 'files': plan['files'], 'reused': False,
                'source_written': False}


def test_profiles(target):
    folder = target / 'tools/dashboard'
    return [name for name, pattern in [('python', 'test_*.py'), ('node', 'test_*.js')]
            if any(folder.glob(pattern))]


def test(root, arguments):
    if set(arguments) != {'workspace_id', 'profile'} or arguments.get('profile') not in ('python', 'node'):
        raise ValueError('Choose the fixed python or node test profile; no command arguments')
    sid, profile = arguments['workspace_id'], arguments['profile']
    with locked(root):
        _, target = load(root, sid)
        require(target, 'execute', 'tests')
        if profile not in test_profiles(target):
            raise ValueError('No tests exist for this profile')
        files = _scan(target)
        before = tree_digest(files)
        from sandbox import coding_test
        reserve_metadata(root, 3 * 1024 * 1024, 2)
        # The runner takes its own immutable snapshot before releasing this
        # operation lock. Other tool processes cannot race snapshot creation.
        evidence = coding_test(root, target, profile)
        current, _ = load(root, sid)
        current_tree = tree_digest(_scan(target))
        result = {**evidence, 'workspace_id': sid, 'profile': profile, 'tree_sha256': before,
                  'current_tree_matches': current_tree == before}
        folder = base_path(root) / sid / 'test-runs'
        folder.mkdir(exist_ok=True)
        run_id = str(uuid4())
        raw = result.pop('_raw_output')
        output = folder / (run_id + '.log')
        with output.open('xb') as stream:
            stream.write(raw)
        result.update(log_path=str(output), log_sha256=digest(raw))
        log = folder / (run_id + '.json')
        _save(log, result)
        current['tests'][profile] = {'path': str(log), 'tree_sha256': before,
                                    'stage': result['stage'], 'exit_code': result['exit_code']}
        _save(base_path(root) / sid / 'workspace.json', current)
        return {**result, 'evidence_path': str(log),
                'status': 'coding_tests_passed' if result['stage'] == 'GREEN' else 'coding_tests_failed'}


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
        passed = bool(checks) and all(c.get('stage') == 'GREEN' and c['current'] for c in checks)
        return {'status': 'coding_workspace_reviewed', 'workspace_id': arguments['workspace_id'],
                'path': str(target), 'tree_sha256': tree, 'changed_files': changed[:200],
                'changed_files_total': len(changed), 'changes_truncated': len(changed) > 200,
                'required_profiles': profiles, 'checks': checks, 'all_current_tests_passed': passed,
                'coverage': 'not measured', 'visual_inspection': 'not performed',
                'source_written': False, 'message': 'Review the diff and actual tests; model narrative is not verification.'}


def execute(root, grants, name, arguments):
    if not grants.get('coding_workspace'):
        raise ValueError('Coding workspace was not approved for this message')
    handlers = {'prepare_coding_workspace': prepare, 'list_coding_files': list_files, 'read_coding_file': read,
                'propose_coding_patch': propose, 'apply_coding_patch': apply, 'run_coding_tests': test,
                'review_coding_workspace': review}
    if name not in handlers or not isinstance(arguments, dict):
        raise ValueError('Unknown coding operation or invalid arguments')
    return handlers[name](root, arguments)
