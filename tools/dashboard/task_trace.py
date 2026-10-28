"""Bounded, read-only task telemetry. Never reads prompts, reasoning or file contents."""
from contextlib import closing
from datetime import datetime, timezone
import base64
import copy
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import threading
import time
from urllib.parse import urlencode
from urllib.request import Request, build_opener, ProxyHandler

from native_activity import NativeActivity
from native_progress import NoRedirect, same_directory, token

_monitors = {}
_lock = threading.Lock()


def iso(stamp):
    return datetime.fromtimestamp(stamp / 1000, timezone.utc).isoformat() if stamp else None


def visible_path(value, binding, workspace):
    """Allowlisted file metadata, never arbitrary argument strings or shell commands."""
    from python_tools import _plain_path
    from access_policy import require
    if not isinstance(value, str) or not value or len(value) > 1000 or '\x00' in value:
        return None
    try:
        path = Path(value)
        if '..' in path.parts or value.startswith(('\\\\', '//')):
            return None
        path = _plain_path(path if path.is_absolute() else Path(workspace) / path)
        roots = (Path(workspace).resolve(), Path(binding['directory']).resolve())
        if not any(path.resolve().is_relative_to(root) for root in roots):
            return None
        require(path, 'read')
        return str(path)
    except (ValueError, OSError):
        return None


class TraceReader(NativeActivity):
    def read(self, binding, workspace, index=None):
        from python_tools import _plain_path
        _plain_path(self.path)
        sid = token(binding['session_id'], 'ses')
        with closing(sqlite3.connect(self.path.resolve().as_uri() + '?mode=ro', uri=True, timeout=1)) as db:
            db.execute('PRAGMA query_only=ON')
            owner = db.execute('SELECT directory FROM session WHERE id=?', (sid,)).fetchone()
            if not owner or not same_directory(owner[0], binding['directory']):
                raise ValueError('Native session directory mismatch')
            turn = db.execute("SELECT id,time_created FROM message WHERE session_id=? AND json_extract(data,'$.role')='user' ORDER BY time_created DESC,id DESC LIMIT 1", (sid,)).fetchone()
            since = turn[1] if turn else 0
            sessions = db.execute("""WITH RECURSIVE children(id,parent_id,directory,time_created,depth) AS (
                SELECT id,parent_id,directory,time_created,0 FROM session WHERE id=? UNION ALL
                SELECT s.id,s.parent_id,s.directory,s.time_created,c.depth+1 FROM session s JOIN children c
                ON s.parent_id=c.id WHERE c.depth<8 AND s.time_created>=?)
                SELECT id,parent_id,directory FROM children ORDER BY depth,time_created DESC LIMIT 17""", (sid, since)).fetchall()
            records, tools, skills, activity = [], [], set(), since
            for current, parent, folder in sessions[:16]:
                if not same_directory(folder, binding['directory']):
                    continue
                latest = db.execute("""SELECT time_created,time_updated,json_extract(data,'$.time.completed'),
                    json_extract(data,'$.finish'),json_extract(data,'$.error.name'),json_extract(data,'$.modelID'),
                    json_extract(data,'$.providerID'),json_extract(data,'$.agent') FROM message WHERE session_id=?
                    AND time_created>=? AND json_extract(data,'$.role')='assistant' ORDER BY time_created DESC,id DESC LIMIT 1""", (current, since)).fetchone()
                stamp = db.execute('SELECT MAX(time_updated) FROM part WHERE session_id=? AND time_updated>=?', (current, since)).fetchone()[0] or since
                activity = max(activity, stamp, latest[1] if latest else 0)
                phase = 'awaiting_model'
                if latest and latest[4]:
                    phase = 'cancelled' if latest[4] == 'MessageAbortedError' else 'failed'
                elif latest and latest[2] and latest[3] != 'tool-calls':
                    phase = 'completed'
                records.append({'session_id': current, 'parent_id': parent, 'state': phase,
                    'model': latest[5][:160] if latest and isinstance(latest[5], str) else None,
                    'provider': latest[6][:80] if latest and isinstance(latest[6], str) else None,
                    'agent': latest[7][:80] if latest and isinstance(latest[7], str) else None,
                    'last_activity_at': iso(stamp)})
                # Extract named scalars in SQL. Never retrieve state.input/output or message.data.
                rows = db.execute("""SELECT id,time_updated,json_extract(data,'$.tool'),json_extract(data,'$.callID'),
                    json_extract(data,'$.state.status'),json_extract(data,'$.state.time.start'),
                    json_extract(data,'$.state.input.relative_path'),json_extract(data,'$.state.input.filePath'),
                    json_extract(data,'$.state.input.path'),json_extract(data,'$.state.input.workspace_id'),
                    json_extract(data,'$.state.input.name'),CASE
                    WHEN instr(lower(coalesce(json_extract(data,'$.state.error'),'')),'recovery_required')>0
                      OR instr(lower(coalesce(json_extract(data,'$.state.error'),'')),'repeated unchanged')>0 THEN 'recovery_required'
                    WHEN instr(lower(coalesce(json_extract(data,'$.state.error'),'')),'budget')>0 THEN 'tool_budget_exhausted'
                    WHEN instr(lower(coalesce(json_extract(data,'$.state.error'),'')),'permission')>0 THEN 'access_denied'
                    WHEN instr(lower(coalesce(json_extract(data,'$.state.error'),'')),'not found')>0 THEN 'not_found'
                    WHEN json_extract(data,'$.state.status')='error' THEN 'tool_error' ELSE NULL END
                    FROM part WHERE session_id=? AND time_updated>=? AND json_extract(data,'$.type')='tool'
                    ORDER BY time_updated DESC,id DESC LIMIT 33""", (current, since)).fetchall()
                for row in rows[:32]:
                    part, updated, tool, call_id, status, start, relative, filename, path, wid, skill, error = row
                    try:
                        token(tool); token(call_id)
                    except ValueError:
                        continue
                    if status not in ('pending', 'running', 'completed', 'error'):
                        continue
                    file = None
                    if tool in ('read', 'edit', 'write', 'glob', 'grep', 'smelter_read_coding_file'):
                        candidate = (relative if tool == 'smelter_read_coding_file' and wid == binding['workspace_id'] else
                                     filename or path if tool != 'smelter_read_coding_file' else None)
                        file = visible_path(candidate, binding, workspace)
                    entry = {'session_id': current, 'call_id': call_id, 'tool': tool, 'phase': status,
                        'started_at': iso(start) if isinstance(start, (int, float)) else iso(updated),
                        'updated_at': iso(updated), 'file': file, 'error_code': error}
                    if file and index:
                        try:
                            relative_file = Path(file).relative_to(workspace).as_posix()
                            indexed = next((x for x in index.get('files', []) if x['relative_path'] == relative_file), None)
                            if indexed:
                                entry.update(indexed_sha256=indexed.get('sha256'), index_updated_at=index.get('updated_at'))
                        except ValueError:
                            pass
                    tools.append(entry)
                    if tool == 'skill' and status == 'completed' and isinstance(skill, str):
                        try: skills.add(token(skill))
                        except ValueError: pass
                active = [t for t in tools if t['session_id'] == current and t['phase'] in ('running', 'pending')]
                if active and records[-1]['state'] == 'awaiting_model':
                    records[-1]['state'] = 'waiting_child' if all(t['tool'] == 'task' for t in active) else 'using_tool'
        tools.sort(key=lambda x: x['updated_at'], reverse=True)
        return {'native_turn_id': turn[0] if turn else None, 'turn_started_at': iso(since),
            'sessions': records, 'tools': tools[:96], 'skills': sorted(skills)[:32],
            'last_activity_at': iso(activity), 'sessions_truncated': len(sessions) > 16}


class LocalInspector:
    """Discover actual ACP listeners, not the separate HTTP process's event bus."""
    def __init__(self):
        self.ports, self.next_discovery = [], 0
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def ports_now(self):
        if time.monotonic() < self.next_discovery:
            return self.ports
        self.next_discovery = time.monotonic() + 60
        self.ports = []
        if os.name == 'nt':
            command = r'''$tracePids=@(Get-CimInstance Win32_Process -Filter "Name='opencode.exe'" | Where-Object {$_.CommandLine -match '\bacp\b'} | ForEach-Object {$_.ProcessId}); @(Get-NetTCPConnection -State Listen | Where-Object {$_.LocalAddress -eq '127.0.0.1' -and $_.OwningProcess -in $tracePids} | Select-Object -First 4 -ExpandProperty LocalPort) | ConvertTo-Json -Compress'''
            try:
                result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                    capture_output=True, text=True, timeout=6, creationflags=subprocess.CREATE_NO_WINDOW)
                ports = json.loads(result.stdout)
                self.ports = [n for n in (ports if isinstance(ports, list) else [ports]) if type(n) is int and 1 <= n <= 65535][:4]
            except (OSError, ValueError, subprocess.TimeoutExpired):
                pass
        return self.ports

    def get(self, port, route, directory=None):
        if not (route in ('/permission', '/question', '/api/ps') or route.startswith('/session/ses')):
            raise ValueError('Read-only inspection route required')
        headers = {'Accept': 'application/json'}
        if route != '/api/ps' and os.environ.get('OPENCODE_SERVER_PASSWORD'):
            auth = os.environ.get('OPENCODE_SERVER_USERNAME', 'opencode') + ':' + os.environ['OPENCODE_SERVER_PASSWORD']
            headers['Authorization'] = 'Basic ' + base64.b64encode(auth.encode()).decode()
        url = 'http://127.0.0.1:' + str(port) + route
        if directory: url += '?' + urlencode({'directory': directory})
        with self.opener.open(Request(url, headers=headers, method='GET'), timeout=2) as response:
            raw = response.read(256 * 1024 + 1)
        if len(raw) > 256 * 1024: raise ValueError('Inspection response too large')
        return json.loads(raw)

    def inspect(self, binding, sessions, workspace):
        permissions, questions, observed = [], [], False
        ids = {row['session_id'] for row in sessions}
        for port in self.ports_now():
            try:
                owner = self.get(port, '/session/' + token(binding['session_id'], 'ses'), binding['directory'])
                if owner.get('id') != binding['session_id'] or not same_directory(owner.get('directory', ''), binding['directory']):
                    continue
                pending = self.get(port, '/permission', binding['directory'])
                if not isinstance(pending, list): continue
                observed = True
                for item in pending[:64]:
                    if item.get('sessionID') not in ids: continue
                    try: permission_id = token(item.get('id'), 'per')
                    except ValueError: continue
                    patterns = [visible_path(p[:-2] if p.endswith(('/*', '\\*')) else p, binding, workspace)
                                for p in item.get('patterns', [])[:8] if isinstance(p, str)]
                    permissions.append({'id': permission_id, 'session_id': item['sessionID'],
                        'kind': token(item.get('permission', 'permission')), 'paths': [p or '[outside visible scope]' for p in patterns]})
                for item in self.get(port, '/question', binding['directory'])[:64]:
                    if item.get('sessionID') in ids:
                        questions.append({'id': token(item.get('id')), 'session_id': item['sessionID']})
            except (OSError, ValueError, TypeError, KeyError):
                continue
        loaded, ollama = [], 'unavailable'
        try:
            result = self.get(11434, '/api/ps')
            for item in result.get('models', [])[:16]:
                if isinstance(item.get('name'), str):
                    context = item.get('context_length')
                    loaded.append({'name': item['name'][:160], 'context_length': context if type(context) is int else None})
            ollama = 'connected'
        except (OSError, ValueError, TypeError): pass
        return {'permissions': permissions[:32], 'questions': questions[:32], 'permission_source': 'ACP live requests' if observed else 'unavailable',
            'ollama': {'connection': ollama, 'loaded_models': loaded, 'scope': 'host-wide; loaded does not prove this task is generating'}}


def classify(data, current=None):
    """Timers are clues, never a fabricated diagnosis of deadlock or model thought."""
    current = current or datetime.now(timezone.utc)
    root = next((s for s in data.get('sessions', []) if s['session_id'] == data['binding']['session_id']), {})
    phase = root.get('state', 'unknown')
    pending = {p['session_id'] for p in data.get('permissions', [])}
    active = [x for x in data.get('tools', []) if x['phase'] in ('running', 'pending')]
    if phase not in ('completed', 'cancelled', 'failed'):
        if pending: phase = 'waiting_access'
        elif data.get('questions'): phase = 'waiting_answer'
        elif active: phase = 'waiting_child' if all(x['tool'] == 'task' for x in active) else 'using_tool'
        elif data.get('tools') and data['tools'][0].get('error_code') == 'tool_budget_exhausted': phase = 'tool_budget_exhausted'
    last = data.get('last_activity_at')
    age = max(0, int((current - datetime.fromisoformat(last)).total_seconds())) if last else None
    waiting = phase in ('using_tool', 'waiting_child', 'awaiting_model', 'tool_budget_exhausted')
    redirected = bool(data.get('tools') and data['tools'][0].get('error_code') == 'recovery_required')
    validation=data.get('validation',[])
    failed=[v for v in validation if v.get('current') and v.get('stage') in ('RED','ERROR')]
    outcome='in_progress'
    outcome_hint=''
    if phase=='completed':
        if failed:
            outcome='changes_needed'
            outcome_hint=('Frozen acceptance failed; passing editable tests do not complete this task.' if any(v.get('acceptance_stage') in ('RED','ERROR') for v in failed) else 'Current validation failed. The response ended, but changes are still required.')
        elif not validation or any(not v.get('current') or v.get('stage')!='GREEN' for v in validation):
            outcome='not_verified';outcome_hint='Current validation is incomplete or stale; task completion is not verified.'
        else:
            outcome='checks_passed';outcome_hint='Current required checks passed within their recorded scope; in-game behavior remains separate.'
    return {'phase': phase, 'quiet_seconds': age, 'task_outcome':outcome, 'outcome_hint':outcome_hint,
        'recovery_redirect': redirected,
        'recovery_hint': 'A repeated call was blocked. The agent should use its saved workspace recovery context and change its approach.' if redirected else '',
        'possible_stall': bool(waiting and age is not None and age >= 120),
        'stall_threshold_seconds': 120,
        'hint': ('Waiting for an access decision in the native client.' if phase == 'waiting_access' else
                 'Waiting for an answer in the native client.' if phase == 'waiting_answer' else
                 'SMELTER reported its tool-call budget exhausted.' if phase == 'tool_budget_exhausted' else
                 'No visible progress for at least two minutes; this does not prove a deadlock.' if waiting and age is not None and age >= 120 else
                 'Waiting for a delegated task.' if phase == 'waiting_child' else
                 'Waiting for model/provider activity.' if phase == 'awaiting_model' else '')}


class Monitor:
    def __init__(self, root, reader=TraceReader, inspector=LocalInspector):
        self.root = Path(root).resolve(); self.reader = reader(); self.inspector = inspector()
        self.lock = threading.RLock(); self.stop = threading.Event(); self.value = None
        self.thread = threading.Thread(target=self.run, daemon=True, name='smelter-task-trace'); self.thread.start()

    def collect(self):
        from native_progress import manager as native_manager
        from coding_workspace import load
        from workspace_tracking import cached
        from access_policy import current, using
        native = native_manager(self.root).view(); binding = native['binding']
        if not binding or not native['enabled']:
            return {'binding': binding, 'enabled': native['enabled'], 'available': False, 'reason': 'Bind and enable Native task progress to watch this task.'}
        with using(current(self.root)):
            _, workspace = load(self.root, binding['workspace_id'])
            index = cached(self.root, binding['workspace_id'])
            data = self.reader.read(binding, workspace, index)
            data.update(self.inspector.inspect(binding, data['sessions'], workspace))
            data['validation'] = [{'profile': t['profile'], 'stage': t['stage'], 'current': t['current'],
                                  'workspace_tests_stage':t.get('workspace_tests_stage'),'acceptance_stage':t.get('acceptance_stage')}
                                  for t in (index or {}).get('tests', [])[:16]]
        data.update(index_revision=(index or {}).get('revision'), index_updated_at=(index or {}).get('updated_at'))
        data.update(binding=binding, enabled=True, available=True, workspace_root=str(workspace),
            observed_at=datetime.now(timezone.utc).isoformat(), configuration_revision=native['configuration_revision'])
        # Native turn IDs identify real turns; never pretend they originated in Melty.
        data['task_id'] = binding.get('melty_task_id') or data['native_turn_id']
        data['task_id_source'] = 'Melty ID supplied in binding' if binding.get('melty_task_id') else 'Native OpenCode turn (Melty ID not supplied)'
        data['status'] = classify(data)
        return data

    def run(self):
        while not self.stop.is_set():
            try: value = self.collect()
            except (OSError, ValueError, sqlite3.Error, KeyError, TypeError) as error:
                value = {'available': False, 'reason': 'Task telemetry unavailable (' + type(error).__name__ + ')', 'binding': None}
            with self.lock: self.value = value
            try:
                from trace_history import observe
                observe(self.root, value)  # Saves final/superseded turn charts only.
            except (OSError, ValueError, KeyError, TypeError):
                pass
            self.stop.wait(2)

    def view(self):
        # Recheck access and binding on every delivery, including WebSocket frames.
        from native_progress import manager as native_manager
        from access_policy import current, using
        from coding_workspace import load
        native = native_manager(self.root).view()
        with self.lock: value = copy.deepcopy(self.value)
        if value and not value.get('available') and not value.get('binding') and native['enabled']:
            return {**value, 'binding': native['binding']}
        if not value or value.get('binding') != native['binding'] or not native['enabled']:
            return {'available': False, 'binding': native['binding'], 'reason': 'Monitor paused or synchronizing binding.'}
        if value.get('available'):
            with using(current(self.root)):
                _, workspace = load(self.root, native['binding']['workspace_id'])
                for tool in value['tools']:
                    tool['file'] = visible_path(tool.get('file'), native['binding'], workspace)
                    if not tool['file']:
                        tool.pop('indexed_sha256', None); tool.pop('index_updated_at', None)
                for permission in value['permissions']:
                    permission['paths'] = [visible_path(p, native['binding'], workspace) or '[outside visible scope]' for p in permission['paths']]
            value['status'] = classify(value)
            observer_age = max(0, int((datetime.now(timezone.utc) - datetime.fromisoformat(value['observed_at'])).total_seconds()))
            value['observer_age_seconds'] = observer_age
            value['observations_stale'] = observer_age > 15
            if value['observations_stale']:
                value['status'].update(phase='telemetry_delayed', possible_stall=False,
                    hint='Observer has not refreshed; current task activity is unknown.')
        return value


def manager(root):
    key = str(Path(root).resolve())
    with _lock:
        if key not in _monitors: _monitors[key] = Monitor(root)
        return _monitors[key]


def close_all():
    with _lock:
        for monitor in _monitors.values(): monitor.stop.set()
