"""Explicit task-artifact registration for trace previews.

Artifacts are never discovered automatically. A registration names an approved
workspace-relative file, records its kind, size, SHA-256 and producing evidence,
and is served only through an opaque ID after ownership, access and hash are
rechecked. Conversions are lineage metadata here; nothing is converted or run.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import threading
from uuid import uuid4

MAX_ARTIFACTS = 200
MAX_STORE = 1024 * 1024
KINDS = {'.png': ('image', 'image/png', 16 * 1024 * 1024), '.jpg': ('image', 'image/jpeg', 16 * 1024 * 1024),
         '.jpeg': ('image', 'image/jpeg', 16 * 1024 * 1024), '.webp': ('image', 'image/webp', 16 * 1024 * 1024),
         '.glb': ('model', 'model/gltf-binary', 25 * 1024 * 1024)}
_lock = threading.RLock()


def _path(root):
    from python_tools import _plain_path
    return _plain_path(Path(root).resolve() / '.smelter/task-trace/artifacts.json')


def _load(root):
    path = _path(root)
    if not path.is_file():
        return []
    if path.stat().st_size > MAX_STORE:
        raise ValueError('Task artifact registry exceeds 1 MiB')
    saved = json.loads(path.read_text(encoding='utf-8'))
    if saved.get('schema_version') != 1 or saved.get('source_root') != str(Path(root).resolve()):
        raise ValueError('Task artifact registry ownership mismatch')
    return saved['artifacts']


def _store(root, artifacts):
    from coding_workspace import _save
    from storage_budget import require
    path = _path(root)
    value = {'schema_version': 1, 'source_root': str(Path(root).resolve()), 'artifacts': artifacts[-MAX_ARTIFACTS:]}
    raw = json.dumps(value).encode()
    if len(raw) > MAX_STORE:
        raise ValueError('Task artifact registry would exceed its bounded size')
    require(root, max(0, len(raw) - (path.stat().st_size if path.exists() else 0)), new_file=not path.exists())
    path.parent.mkdir(parents=True, exist_ok=True)
    _save(path, value)


def _sniff(kind, mime, raw):
    if mime == 'image/png' and not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('File is not a PNG image')
    if mime == 'image/jpeg' and not raw.startswith(b'\xff\xd8\xff'):
        raise ValueError('File is not a JPEG image')
    if mime == 'image/webp' and not (raw[:4] == b'RIFF' and raw[8:12] == b'WEBP'):
        raise ValueError('File is not a WebP image')
    if kind == 'model':
        from model_assets import inspect_glb
        return inspect_glb(raw)
    return {}


def _resolve(root, workspace_id, relative):
    """Workspace ownership, relative-path rules and current read access, as coding tools apply them."""
    from coding_workspace import load, _file
    _, target = load(root, workspace_id)
    path = _file(target, relative)
    if not path.is_file():
        raise ValueError('Artifact file is missing')
    suffix = path.suffix.lower()
    if suffix not in KINDS:
        raise ValueError('Register PNG, JPEG, WebP or GLB files only')
    return target, path, KINDS[suffix]


def _read(path, limit):
    size = path.stat().st_size
    if not 0 < size <= limit:
        raise ValueError('Artifact is empty or exceeds its size limit')
    raw = path.read_bytes()
    if len(raw) != size:
        raise ValueError('Artifact changed while reading')
    return raw


def register(root, data):
    """Explicit registration from the dashboard; the producer is checked against the live trace."""
    from access_policy import current, using
    from task_trace import manager
    allowed = {'action', 'relative_path', 'producer_call_id', 'derived_from'}
    if set(data) - allowed or not isinstance(data.get('relative_path'), str):
        raise ValueError('Use action, relative_path and optional producer_call_id / derived_from')
    trace = manager(root).view()
    if not trace.get('available'):
        raise ValueError('Register artifacts while a bound task trace is available')
    binding = trace['binding']
    with using(current(root)):
        target, path, (kind, mime, limit) = _resolve(root, binding['workspace_id'], data['relative_path'])
        raw = _read(path, limit)
        details = _sniff(kind, mime, raw)
    relative = path.relative_to(target).as_posix()
    producer = {'source': 'declared in dashboard (no observed producing call)'}
    call = data.get('producer_call_id')
    if call is not None:
        match = next((t for t in trace['tools'] if t.get('call_id') == call), None)
        if not match:
            raise ValueError('Producer call is not in the current trace')
        same = match.get('file') and Path(match['file']).resolve() == path.resolve()
        producer = {'source': 'observed tool call naming this path' if same else 'declared; observed call did not name this path',
                    'tool': match['tool'], 'call_id': call, 'session_id': match['session_id'], 'phase': match['phase']}
    with _lock:
        artifacts = _load(root)
        lineage = data.get('derived_from') or []
        if not isinstance(lineage, list) or len(lineage) > 8 or any(not any(a['id'] == x for a in artifacts) for x in lineage):
            raise ValueError('derived_from must list up to eight registered artifact IDs')
        stat = path.stat()
        record = {'id': uuid4().hex, 'registered_at': datetime.now(timezone.utc).isoformat(),
                  'task': {'task_id': trace.get('task_id'), 'task_id_source': trace.get('task_id_source'),
                           'native_turn_id': trace.get('native_turn_id'), 'session_id': binding['session_id']},
                  'workspace_id': binding['workspace_id'], 'relative_path': relative, 'kind': kind, 'mime': mime,
                  'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'mtime_ns': stat.st_mtime_ns,
                  'source_revision': trace.get('index_revision'), 'producer': producer, 'derived_from': lineage,
                  'details': {k: details[k] for k in ('meshes', 'materials', 'images', 'animations', 'animation_clips') if k in details}}
        artifacts = [a for a in artifacts if not (a['workspace_id'] == record['workspace_id'] and a['relative_path'] == relative
                                                  and a['task'] == record['task'] and a['sha256'] == record['sha256'])]
        _store(root, artifacts + [record])
    return public(record, 'current')


def public(record, state):
    out = {k: v for k, v in record.items() if k != 'mtime_ns'}
    out['state'] = state
    out['source_url'] = '/api/task-trace/artifacts/' + record['id'] if state == 'current' else None
    return out


def _state(root, record, verify_hash=False):
    try:
        _, path, (_, _, limit) = _resolve(root, record['workspace_id'], record['relative_path'])
    except ValueError as error:
        message = str(error)
        return ('missing' if 'missing' in message else 'unavailable'), None
    except OSError:
        return 'unavailable', None
    stat = path.stat()
    if not verify_hash and stat.st_size == record['bytes'] and stat.st_mtime_ns == record['mtime_ns']:
        return 'current', path
    raw = _read(path, limit) if stat.st_size <= limit else b''
    return ('current' if hashlib.sha256(raw).hexdigest() == record['sha256'] else 'changed'), path


def view(root):
    from access_policy import current, using
    with using(current(root)):
        artifacts = [public(a, _state(root, a)[0]) for a in reversed(_load(root))]
    return {'artifacts': artifacts, 'read_only_preview': True,
            'scope': 'Explicitly registered task artifacts. A successful preview does not prove game integration.'}


def content(root, artifact_id):
    """Bytes for an opaque ID only after ownership, access and SHA-256 match the registration."""
    from access_policy import current, using
    if not isinstance(artifact_id, str) or len(artifact_id) != 32 or not all(c in '0123456789abcdef' for c in artifact_id):
        raise ValueError('Unknown task artifact')
    record = next((a for a in _load(root) if a['id'] == artifact_id), None)
    if not record:
        raise ValueError('Unknown task artifact')
    with using(current(root)):
        state, path = _state(root, record, verify_hash=True)
        if state != 'current':
            raise ValueError('Task artifact is ' + state + '; register the current file again to preview it')
        raw = _read(path, KINDS[path.suffix.lower()][2])
    if hashlib.sha256(raw).hexdigest() != record['sha256']:
        raise ValueError('Task artifact changed while reading')
    return raw, record['mime']
