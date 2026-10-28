"""Bounded final task charts derived from sanitized trace snapshots.

A chart is saved when a turn's response ends, is cancelled or fails, and when a
newer turn replaces one that was never seen finishing. Only fields the collector
already sanitized are kept; paths are rechecked against current access on view.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import threading

MAX_CHARTS = 20
MAX_STORE = 1024 * 1024
TERMINAL = ('completed', 'cancelled', 'failed')
KEEP = ('task_id', 'task_id_source', 'native_turn_id', 'turn_started_at', 'sessions', 'tools', 'skills',
        'permissions', 'questions', 'permission_source', 'ollama', 'validation', 'status', 'observed_at',
        'workspace_root', 'index_revision', 'index_updated_at', 'last_activity_at', 'sessions_truncated',
        'configuration_revision')
_lock = threading.Lock()
_last = {}


def _path(root):
    from python_tools import _plain_path
    return _plain_path(Path(root).resolve() / '.smelter/task-trace/charts.json')


def _load(root):
    path = _path(root)
    if not path.is_file():
        return []
    if path.stat().st_size > MAX_STORE:
        raise ValueError('Task chart store exceeds 1 MiB')
    saved = json.loads(path.read_text(encoding='utf-8'))
    if saved.get('schema_version') != 1 or saved.get('source_root') != str(Path(root).resolve()):
        raise ValueError('Task chart store ownership mismatch')
    return saved['charts']


def _store(root, charts):
    from coding_workspace import _save
    from storage_budget import require
    path = _path(root)
    value = {'schema_version': 1, 'source_root': str(Path(root).resolve()), 'charts': charts}
    raw = json.dumps(value).encode()
    while len(raw) > MAX_STORE and len(charts) > 1:
        charts.pop(0)
        raw = json.dumps(value).encode()
    require(root, max(0, len(raw) - (path.stat().st_size if path.exists() else 0)), new_file=not path.exists())
    path.parent.mkdir(parents=True, exist_ok=True)
    _save(path, value)


def chart(snapshot, reason):
    trace = {k: snapshot.get(k) for k in KEEP if k in snapshot}
    binding = snapshot.get('binding') or {}
    trace['binding'] = {k: binding.get(k) for k in ('session_id', 'directory', 'workspace_id', 'melty_task_id')}
    trace['available'] = True
    key = (binding.get('session_id') or '') + ':' + (snapshot.get('native_turn_id') or '')
    return {'id': hashlib.sha256(key.encode()).hexdigest()[:24], 'reason': reason,
            'saved_at': datetime.now(timezone.utc).isoformat(), 'trace': trace,
            'scope': 'Sampled evidence summary; not proof that every operation or in-game behavior ran.'}


def _fingerprint(snapshot):
    status = snapshot.get('status') or {}
    return json.dumps([status.get('phase'), status.get('task_outcome'), snapshot.get('validation'),
                       len(snapshot.get('tools') or []), snapshot.get('index_revision')], sort_keys=True)


def observe(root, snapshot):
    """Called by the collector after each sample; writes only on terminal or superseded turns."""
    if not snapshot or not snapshot.get('available') or not snapshot.get('native_turn_id'):
        return None
    key = str(Path(root).resolve())
    phase = (snapshot.get('status') or {}).get('phase')
    with _lock:
        previous = _last.get(key)
        _last[key] = {'snapshot': snapshot, 'turn': snapshot['native_turn_id'], 'saved': previous.get('saved') if previous and previous['turn'] == snapshot['native_turn_id'] else None}
        record = None
        if previous and previous['turn'] != snapshot['native_turn_id'] and previous['saved'] is None:
            record = chart(previous['snapshot'], 'superseded before an observed end')
        if phase in TERMINAL and _last[key]['saved'] != _fingerprint(snapshot):
            final = chart(snapshot, {'completed': 'response ended', 'cancelled': 'cancelled', 'failed': 'failed'}[phase])
            _last[key]['saved'] = _fingerprint(snapshot)
            record = [record, final] if record else [final]
        elif record:
            record = [record]
        if not record:
            return None
        charts = [c for c in _load(root) if c['id'] not in {r['id'] for r in record}] + record
        _store(root, charts[-MAX_CHARTS:])
        return record


def view(root):
    """Saved charts newest first, with every path rechecked against current access."""
    from access_policy import current, using
    from coding_workspace import load
    from task_trace import visible_path
    charts = list(reversed(_load(root)))
    with using(current(root)):
        for item in charts:
            trace, binding = item['trace'], item['trace']['binding']
            try:
                _, workspace = load(root, binding['workspace_id'])
            except (ValueError, OSError, KeyError, TypeError):
                workspace = None
            check = (lambda p: visible_path(p, binding, workspace)) if workspace else (lambda p: None)
            for tool in trace.get('tools') or []:
                tool['file'] = check(tool.get('file')) if tool.get('file') else None
                if not tool['file']:
                    tool.pop('indexed_sha256', None); tool.pop('index_updated_at', None)
            for permission in trace.get('permissions') or []:
                permission['paths'] = [check(p) or '[outside visible scope]' for p in permission.get('paths', [])]
            if not workspace:
                trace['workspace_root'] = '[workspace unavailable]'
    return {'charts': charts, 'read_only': True,
            'scope': 'Final task charts are sampled evidence summaries. Task outcome remains separate from the response ending.'}
