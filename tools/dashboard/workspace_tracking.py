"""Derived workspace/file ledger and bounded evidence-based relation graphs.

The filesystem remains authoritative for write admission. This rebuildable cache
never authorizes a patch, executes source, or scans outside a managed copy.
"""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import posixpath
import re

MAX_GRAPH_FILES = 60
MAX_HISTORY = 120
MAX_CACHE = 24 * 1024 * 1024


def _paths(root, sid):
    from coding_workspace import base_path, identifier
    from python_tools import _plain_path
    folder = _plain_path(base_path(root) / identifier(sid))
    return folder / 'file-index.json', folder / 'relations.mmd'


def cached(root, sid):
    from python_tools import _plain_path
    path, _ = _paths(root, sid)
    path = _plain_path(path)
    if not path.is_file():
        return None
    if path.stat().st_size > MAX_CACHE:
        raise ValueError('Workspace index exceeds its bounded cache size')
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('schema_version') != 1 or value.get('workspace_id') != sid or value.get('source_root') != str(Path(root).resolve()):
        raise ValueError('Workspace index ownership mismatch; rebuild it')
    return value


def _kind(relative):
    suffix = Path(relative).suffix.lower()
    if suffix in ('.glb', '.gltf', '.fbx', '.obj', '.blend', '.png', '.jpg', '.jpeg', '.webp', '.dds', '.ktx2'):
        return 'asset'
    if '/tests/' in relative or Path(relative).name.startswith('test_'):
        return 'test'
    return 'file'


def _references(path, text):
    """Literal source references only; these do not prove runtime behavior."""
    if path.suffix == '.lua':
        return [(m.group(1), 'import') for m in re.finditer(r'\brequire\s*\(?\s*[\"\']([^\"\']+)[\"\']', text)]
    if path.suffix == '.py':
        try:
            result = []
            for node in ast.walk(ast.parse(text)):
                if isinstance(node, ast.Import):
                    result += [(x.name, 'import') for x in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    result.append((node.module, 'import'))
            return result
        except SyntaxError:
            return []
    if path.suffix in ('.js', '.mjs', '.cjs'):
        return [(m.group(1), 'import') for m in re.finditer(r'(?:\bfrom\s*|\brequire\s*\(|\bimport\s*)[\"\']([^\"\']+)[\"\']', text)]
    return []


def _resolve(relative, token, text, known):
    path = Path(relative)
    suffix = path.suffix
    module = token.replace('.', '/') if not token.startswith('.') else token
    extensions = ('.lua',) if suffix == '.lua' else ('.py', '/__init__.py') if suffix == '.py' else ('', '.js', '.mjs', '/index.js')
    candidates = [(path.parent / (module + ext)).as_posix() for ext in extensions]
    mod_root = Path(*path.parts[:2]) if path.parts[0] == 'mods' else Path('.')
    if suffix == '.lua':
        for match in re.finditer(r'[\"\']([^\"\']*\?\.lua[^\"\']*)[\"\']', text):
            for template in match.group(1).split(';'):
                if '?' in template:
                    candidates.append((mod_root / template.replace('?', module)).as_posix())
    candidates += [module + ext for ext in extensions]
    exact = sorted({posixpath.normpath(x) for x in candidates if posixpath.normpath(x) in known})
    if exact:
        return exact, 'static'
    # A unique same-mod filename is an inferred candidate, not verified import resolution.
    stem = Path(token).stem if suffix in ('.js', '.mjs', '.cjs') else token.split('.')[-1].split('/')[-1]
    prefix = mod_root.as_posix() + '/' if path.parts[0] == 'mods' else ''
    matches = sorted(x for x in known if x.startswith(prefix) and Path(x).stem == stem and x != relative)
    return matches[:3], 'inferred'


def graph(root, target, rows, tests, revision):
    from access_policy import require
    from python_tools import _plain_path
    available = {row['relative_path']: row for row in rows if row['sha256'] is not None}
    changed = [r for r in rows if r['status'] != 'unchanged']
    selected = sorted(changed or rows, key=lambda r: r['relative_path'])[:MAX_GRAPH_FILES]
    chosen = {r['relative_path']: r for r in selected}
    edges = []
    for row in list(selected):
        relative = row['relative_path']
        if row['sha256'] is None:
            continue
        path = _plain_path(target / relative)
        if path.suffix not in ('.py', '.lua', '.js', '.mjs', '.cjs') or path.stat().st_size > 128 * 1024:
            continue
        require(path, 'read')
        try:
            text = path.read_bytes().decode('utf-8')
        except UnicodeError:
            continue
        for token, relation in _references(path, text):
            destinations, confidence = _resolve(relative, token, text, available)
            for destination in destinations:
                if destination not in chosen and len(chosen) < MAX_GRAPH_FILES:
                    chosen[destination] = available[destination]
                if destination in chosen and destination != relative:
                    edges.append({'source_path': relative, 'target_path': destination,
                                  'kind': relation, 'confidence': confidence})
    identity = lambda path: 'f' + hashlib.sha256(path.encode()).hexdigest()[:14]
    nodes = [{'id': 'workspace', 'label': 'Coding copy ' + revision[:10], 'kind': 'workspace'}]
    result_edges = []
    for relative, row in sorted(chosen.items()):
        nodes.append({'id': identity(relative), 'label': relative, 'kind': _kind(relative),
                      'sha256': row['sha256'], 'status': row['status']})
        result_edges.append({'source': 'workspace', 'target': identity(relative), 'kind': 'contains', 'confidence': 'observed'})
    for edge in edges[:120]:
        result_edges.append({'source': identity(edge['source_path']), 'target': identity(edge['target_path']),
                             'kind': edge['kind'], 'confidence': edge['confidence']})
    for test in tests:
        node = 'test_' + test['profile']
        nodes.append({'id': node, 'kind': 'receipt', 'label': test['profile'] + ' ' + test['stage'] + (' current' if test['current'] else ' stale')})
        if test['current']:
            result_edges.append({'source': node, 'target': 'workspace', 'kind': 'tested snapshot', 'confidence': 'observed'})
    return {'nodes': nodes, 'edges': result_edges, 'truncated': len(changed or rows) > MAX_GRAPH_FILES,
            'scope': 'Observed files and snapshot receipts; static/inferred imports are not behavior coverage.'}


def mermaid(value):
    clean = lambda text: str(text).replace('&', '&amp;').replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', ' ')
    lines = ['flowchart LR']
    for node in value['nodes']:
        lines.append('  ' + node['id'] + '["' + clean(node['label']) + '"]')
    for edge in value['edges']:
        arrow = '-.->' if edge['confidence'] in ('static', 'inferred') else '-->'
        lines.append('  ' + edge['source'] + ' ' + arrow + '|"' + clean(edge['kind'] + ' / ' + edge['confidence']) + '"| ' + edge['target'])
    return '\n'.join(lines) + '\n'


def capture(root, metadata, target, files, operation='indexed'):
    from coding_workspace import _save, digest, tree_digest, reserve_metadata
    from python_tools import _plain_path
    sid = metadata['workspace_id']
    previous = cached(root, sid)
    old = {row['relative_path']: row for row in previous['files']} if previous else {}
    now = datetime.now(timezone.utc).isoformat()
    known = set(metadata['baseline']) | set(files) | set(old)
    if len(known) > 40000:
        raise ValueError('Workspace history exceeds 40,000 indexed paths')
    rows, changes = [], []
    for relative in sorted(known):
        sha, baseline = files.get(relative), metadata['baseline'].get(relative)
        path = _plain_path(target / relative)
        status = 'missing' if sha is None else 'created' if baseline is None else 'unchanged' if sha == baseline else 'modified'
        row = {'relative_path': relative, 'name': Path(relative).name, 'physical_path': str(path),
               'source_path': str(Path(root).resolve() / relative), 'sha256': sha, 'baseline_sha256': baseline,
               'status': status, 'bytes': path.stat().st_size if sha is not None else None, 'kind': _kind(relative)}
        rows.append(row)
        if previous and old.get(relative, {}).get('sha256') != sha:
            changes.append({'time': now, 'path': relative, 'before_sha256': old.get(relative, {}).get('sha256'), 'sha256': sha, 'status': status})
    revision = tree_digest(files)
    tests = []
    for profile, result in metadata.get('tests', {}).items():
        current = result.get('tree_sha256') == revision
        from acceptance_contracts import fresh
        current = current and fresh(root,sid,target,profile,result)
        if profile == 'lua':
            from sandbox import lua_runner_sha256
            current = current and result.get('runner_sha256') == lua_runner_sha256()
        tests.append({'profile': profile, 'stage': result.get('stage', 'UNKNOWN'),
                      'workspace_tests_stage':result.get('workspace_tests_stage'), 'acceptance_stage':result.get('acceptance_stage'),
                      'tree_sha256': result.get('tree_sha256'), 'current': current})
    relation = graph(root, target, rows, tests, revision)
    history = ((previous or {}).get('history', []) + changes + [{'time': now, 'operation': operation, 'tree_sha256': revision}])[-MAX_HISTORY:]
    value = {'schema_version': 1, 'workspace_id': sid, 'source_root': str(Path(root).resolve()),
             'workspace_root': str(target), 'storage': 'host_directory',
             'tests_use': 'read-only Docker snapshots; tests execute from each mod directory',
             'updated_at': now, 'revision': revision, 'operation': operation, 'files': rows,
             'tests': tests, 'history': history, 'graph': relation, 'mermaid': mermaid(relation)}
    raw = json.dumps(value).encode()
    if len(raw) > MAX_CACHE:
        raise ValueError('Workspace index exceeds its bounded cache size')
    path, diagram = _paths(root, sid)
    reserve_metadata(root, max(0, len(raw) - (path.stat().st_size if path.exists() else 0)) + len(value['mermaid']), 0 if path.exists() else 2)
    _save(path, value)
    _plain_path(diagram)
    temporary = diagram.with_name('relations.' + digest(raw)[:16] + '.tmp')
    _plain_path(temporary)
    try:
        with temporary.open('x', encoding='utf-8', newline='\n') as stream:
            stream.write(value['mermaid'])
        temporary.replace(diagram)
    finally:
        temporary.unlink(missing_ok=True)
    return value


def observe(root, metadata, target, files, operation):
    """Tracking failure cannot turn an already applied edit into a false failure."""
    try:
        if files is None:
            from coding_workspace import _scan
            files = _scan(target)
        value = capture(root, metadata, target, files, operation)
        return {'revision': value['revision'], 'updated_at': value['updated_at'],
                'workspace_root': value['workspace_root'], 'storage': value['storage']}
    except (ValueError, OSError, UnicodeError) as error:
        return {'error': str(error)[:300], 'rebuild_with': 'coding_workspace_context'}


def view(value, query='', offset=0, limit=50):
    if not isinstance(query, str) or len(query) > 200 or type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('Use a bounded text query and pagination (limit 1-100)')
    from access_policy import allowed
    can_read = lambda relative: allowed(Path(value['workspace_root']) / relative, 'read')
    rows = [row for row in value['files'] if query.casefold() in row['relative_path'].casefold() and can_read(row['relative_path'])]
    nodes = [node for node in value['graph']['nodes'] if node['kind'] in ('workspace', 'receipt') or can_read(node['label'])]
    ids = {node['id'] for node in nodes}
    relation = {**value['graph'], 'nodes': nodes, 'edges': [edge for edge in value['graph']['edges'] if edge['source'] in ids and edge['target'] in ids]}
    result = {**{k: value[k] for k in ('workspace_id', 'source_root', 'workspace_root', 'storage', 'tests_use', 'updated_at', 'revision', 'operation', 'tests')},
            'history': [event for event in value['history'] if 'path' not in event or can_read(event['path'])][-20:],
            'graph': relation, 'mermaid': mermaid(relation),
            'query': query, 'files': rows[offset:offset + limit], 'offset': offset,
            'total_files': len(value['files']), 'matching_files': len(rows), 'has_more': offset + limit < len(rows)}
    while result['files'] and len(json.dumps(result).encode()) > 192 * 1024:
        result['files'].pop()
        result['has_more'] = True
    return result


def registry(root):
    from coding_workspace import base_path, load
    result = []
    for marker in sorted(base_path(root).glob('*/workspace.json'))[:10]:
        try:
            metadata, target = load(root, marker.parent.name)
            value = cached(root, metadata['workspace_id'])
            result.append({'workspace_id': metadata['workspace_id'], 'source_root': metadata['source'],
                           'workspace_root': str(target), 'storage': 'host_directory',
                           'indexed': value is not None, 'updated_at': value['updated_at'] if value else None,
                           'revision': value['revision'] if value else None})
        except (ValueError, OSError):
            continue
    return {'workspaces': result, 'count': len(result), 'selection': 'Use the existing task workspace_id; no workspace is selected by recency.'}


def task_snapshot(root, execution):
    """Attach the final indexed graph to managed/direct task history, without scanning."""
    from coding_workspace import load
    from access_policy import using, current
    events = execution.get('events', [])
    if not isinstance(events, list):
        return None
    for event in reversed(events):
        if not isinstance(event, dict):
            continue
        result = event.get('result', {})
        sid = result.get('workspace_id') if isinstance(result, dict) else None
        if not sid:
            continue
        try:
            with using(current(root)):
                load(root, sid)
                value = cached(root, sid)
                if value:
                    visible = view(value, limit=1)
                    return {k: visible[k] for k in ('workspace_id', 'revision', 'updated_at', 'graph', 'mermaid', 'tests')}
        except (ValueError, OSError, KeyError, TypeError):
            continue
    return None
