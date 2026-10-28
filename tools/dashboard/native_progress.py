"""Read-only, session-bound OpenCode SSE monitor. Never submits or controls work.

Only normalized tool/status metadata is persisted. Prompts, reasoning, tool
arguments, results, error bodies and provider metadata never enter the ledger.
"""
from collections import deque
from datetime import datetime, timezone
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import threading
import time
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from uuid import uuid4
from native_activity import NativeActivity

BASE = 'http://127.0.0.1:4096'
MAX_FRAME = 1024 * 1024
MAX_STORE = 2 * 1024 * 1024
MAX_EVENTS = 300
MAX_COMPLETIONS = 5
_managers = {}
_managers_lock = threading.Lock()


def now():
    return datetime.now(timezone.utc).isoformat()


def token(value, prefix=None):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,160}', value):
        raise ValueError('Invalid native identifier')
    if prefix and not value.startswith(prefix):
        raise ValueError('Invalid native identifier prefix')
    return value


def directory(value):
    from python_tools import _plain_path
    if not isinstance(value, str) or len(value) > 1000 or '\x00' in value:
        raise ValueError('Choose an absolute local native project directory')
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts or value.startswith(('\\\\', '//')):
        raise ValueError('Choose an absolute local native project directory')
    path = _plain_path(path)
    if not path.is_dir():
        raise ValueError('Native project directory does not exist')
    return str(path.resolve())


def same_directory(left, right):
    return os.path.normcase(str(Path(left).resolve())) == os.path.normcase(str(Path(right).resolve()))


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Transport:
    def __init__(self, native_directory):
        self.directory = native_directory
        self.opener = build_opener(ProxyHandler({}), NoRedirect())

    def _open(self, path, *, stream=False, cursor=None):
        # Fixed loopback endpoint and GET-only route allowlist; no agent URL input.
        if path not in ('/event', '/session', '/session/status') and not re.fullmatch(r'/session/ses[A-Za-z0-9_.:-]{1,157}', path):
            raise ValueError('Native monitor supports fixed read-only endpoints')
        headers = {'Accept': 'text/event-stream' if stream else 'application/json'}
        if stream and cursor:
            headers['Last-Event-ID'] = token(cursor)
        password = os.environ.get('OPENCODE_SERVER_PASSWORD')
        if password:
            credentials = os.environ.get('OPENCODE_SERVER_USERNAME', 'opencode') + ':' + password
            headers['Authorization'] = 'Basic ' + base64.b64encode(credentials.encode()).decode()
        return self.opener.open(Request(BASE + path + '?' + urlencode({'directory': self.directory}),
                                        headers=headers, method='GET'), timeout=12 if stream else 5)

    def get(self, path):
        with self._open(path) as response:
            raw = response.read(MAX_FRAME + 1)
        if len(raw) > MAX_FRAME:
            raise ValueError('Native metadata exceeds the bounded response size')
        return json.loads(raw)

    def stream(self, cursor=None):
        response = self._open('/event', stream=True, cursor=cursor)
        if response.headers.get_content_type() != 'text/event-stream':
            response.close()
            raise ValueError('Native server did not return an SSE stream')
        return response


def frames(response, stopped):
    """Bounded SSE framing, including multi-line data and an optional event ID."""
    chunks, size, cursor = [], 0, None
    while not stopped.is_set():
        line = response.readline(MAX_FRAME + 1)
        if not line:
            return
        size += len(line)
        if size > MAX_FRAME:
            raise ValueError('Native event frame exceeds 1 MiB')
        text = line.decode('utf-8').rstrip('\r\n')
        if not text:
            if chunks:
                value = json.loads('\n'.join(chunks))
                if isinstance(value, dict):
                    yield cursor, value
            chunks, size, cursor = [], 0, None
        elif text.startswith('data:'):
            chunks.append(text[5:].lstrip(' '))
        elif text.startswith('id:'):
            candidate = text[3:].strip()
            cursor = token(candidate) if candidate else None


def normalize(event, session_id):
    """Return only public lifecycle metadata; raw strings cannot become UI text."""
    props = event.get('properties')
    if not isinstance(props, dict):
        return None
    part = props.get('part', {})
    if not isinstance(part, dict):
        part = {}
    sid = props.get('sessionID', part.get('sessionID'))
    if sid != session_id or part.get('sessionID', sid) != session_id:
        return None
    kind = event.get('type')
    record = {'event_type': kind}
    try:
        if isinstance(event.get('id'), str):
            record['source_event_id'] = token(event['id'])
        if kind == 'message.part.updated' and part.get('type') == 'tool':
            state = part.get('state', {})
            phase = state.get('status') if isinstance(state, dict) else None
            if phase not in ('pending', 'running', 'completed', 'error'):
                return None
            record.update(kind='tool', call_id=token(part.get('callID')), tool=token(part.get('tool')),
                          phase={'completed': 'completed', 'error': 'failed'}.get(phase, phase))
        elif kind in ('session.next.tool.called', 'session.next.tool.progress',
                      'session.next.tool.success', 'session.next.tool.failed'):
            record.update(kind='tool', call_id=token(props.get('callID')),
                          phase={'called': 'running', 'progress': 'running', 'success': 'completed',
                                 'failed': 'failed'}[kind.rsplit('.', 1)[1]])
            if 'tool' in props:
                record['tool'] = token(props['tool'])
        elif kind in ('session.status', 'session.idle'):
            status = props.get('status', {})
            phase = 'idle' if kind == 'session.idle' else status.get('type') if isinstance(status, dict) else None
            if phase not in ('idle', 'busy', 'retry'):
                return None
            record.update(kind='session', phase=phase)
        elif kind == 'session.error':
            error = props.get('error', {})
            name = error.get('name') if isinstance(error, dict) else None
            record.update(kind='session', phase='cancelled' if name == 'MessageAbortedError' else 'failed')
        elif kind == 'session.next.prompted':
            record.update(kind='session', phase='busy')
        else:
            return None
        return record
    except ValueError:
        return None


def _path(root):
    from python_tools import _plain_path
    return _plain_path(Path(root).resolve() / '.smelter/native-progress/state.json')


def _empty():
    return {'schema_version': 1, 'configuration_revision': uuid4().hex, 'binding': None,
            'enabled': False, 'connection': 'stopped', 'task_state': 'unknown',
            'cycle': 0, 'completed_cycle': 0, 'sequence': 0, 'events': [], 'seen': [],
            'completions': [], 'cursor': None, 'gap': False, 'last_observed_at': None}


class Bridge:
    def __init__(self, root, transport=Transport, activity=NativeActivity):
        self.root = Path(root).resolve()
        self.transport = transport
        self.activity = activity
        self.lock = threading.RLock()
        self.stopped = threading.Event()
        self.thread = None
        self.activity_thread = None
        path = _path(root)
        self.value = _empty()
        if path.is_file():
            if path.stat().st_size > MAX_STORE:
                raise ValueError('Native progress ledger exceeds 2 MiB')
            saved = json.loads(path.read_text(encoding='utf-8'))
            if saved.get('schema_version') != 1 or saved.get('source_root') != str(self.root):
                raise ValueError('Native progress ledger ownership mismatch')
            self.value.update(saved)
            self.value['connection'] = 'stopped'
            if self.value['enabled']:
                self.value['gap'] = True  # Process downtime has no guaranteed replay contract.
        self.value['activity_connection'] = 'stopped'
        self.rate = deque()

    def _save(self):
        from coding_workspace import _save
        from storage_budget import require
        value = {**self.value, 'source_root': str(self.root)}
        raw = json.dumps(value).encode()
        while len(raw) > MAX_STORE and len(self.value['completions']) > 1:
            self.value['completions'].pop(0)
            value = {**self.value, 'source_root': str(self.root)}
            raw = json.dumps(value).encode()
        if len(raw) > MAX_STORE:
            raise ValueError('Native progress ledger exceeds its bounded size')
        path = _path(self.root)
        require(self.root, max(0, len(raw) - (path.stat().st_size if path.exists() else 0)), new_file=not path.exists())
        path.parent.mkdir(parents=True, exist_ok=True)
        _save(path, value)

    def _revision(self, expected):
        if expected != self.value['configuration_revision']:
            raise ValueError('Native progress binding changed; reload before updating it')

    def _archive(self):
        if not self.value['binding']:
            return
        from python_tools import _plain_path
        from coding_workspace import _save
        from storage_budget import require
        folder = _plain_path(_path(self.root).parent / 'archives')
        if folder.is_dir() and len(list(folder.glob('*.json'))) >= 10:
            raise ValueError('Ten native binding archives exist; preserve/review them before rebinding')
        archived = {**self.value, 'source_root': str(self.root)}
        raw = json.dumps(archived).encode()
        require(self.root, len(raw))
        folder.mkdir(parents=True, exist_ok=True)
        _save(folder / (uuid4().hex + '.json'), archived)

    def _verify(self, binding):
        from access_policy import current, using
        from coding_workspace import load
        with using(current(self.root)):
            load(self.root, binding['workspace_id'])
        metadata = self.transport(binding['directory']).get('/session/' + quote(binding['session_id'], safe=''))
        if not isinstance(metadata, dict) or metadata.get('id') != binding['session_id'] or not isinstance(metadata.get('directory'), str) or not same_directory(metadata['directory'], binding['directory']):
            raise ValueError('Native session directory does not match the selected binding')
        return metadata

    def discover(self, native_directory):
        selected = directory(native_directory)
        rows = self.transport(selected).get('/session')
        if not isinstance(rows, list):
            raise ValueError('Native server returned invalid session metadata')
        result = []
        for row in rows[:200]:
            if not isinstance(row, dict) or not isinstance(row.get('directory'), str) or not same_directory(row['directory'], selected):
                continue
            try:
                result.append({'session_id': token(row.get('id'), 'ses'), 'directory': selected,
                               'updated': row.get('time', {}).get('updated')})
            except (ValueError, AttributeError):
                continue
        return {'directory': selected, 'sessions': result[:50],
                'selection': 'Select the exact task session; no session is chosen by recency.'}

    def bind(self, data):
        from coding_workspace import identifier
        binding = {'session_id': token(data.get('session_id'), 'ses'),
                   'directory': directory(data.get('directory')),
                   'workspace_id': identifier(data.get('workspace_id'))}
        if data.get('melty_task_id'):
            binding['melty_task_id'] = token(data['melty_task_id'])
        self._verify(binding)
        with self.lock:
            self._revision(data.get('expected_revision'))
            if self._alive():
                raise ValueError('Stop the existing monitor and wait for it to disconnect before rebinding')
            self._archive()
            self.value = {**_empty(), 'binding': binding, 'enabled': True, 'activity_since': now()}
            self._save()
            self._start()
        return self.view()

    def control(self, action, expected):
        with self.lock:
            self._revision(expected)
            if action == 'stop':
                self.value['enabled'] = False
                self.stopped.set()
                self.value['connection'] = 'stopping' if self._alive() else 'stopped'
            elif action == 'start':
                if not self.value['binding']:
                    raise ValueError('Bind an exact native session first')
                if self._alive() and self.stopped.is_set():
                    raise ValueError('Previous monitor is stopping; retry after it disconnects')
                self._verify(self.value['binding'])
                self.value['enabled'] = True
                self._start()
            else:
                raise ValueError('Use start or stop for the read-only native monitor')
            self.value['configuration_revision'] = uuid4().hex
            self._save()
        return self.view()

    def correlate(self, melty_task_id, expected):
        """Attach a supplied Melty ID without restarting or reselecting the task."""
        identifier = token(melty_task_id) if melty_task_id else None
        with self.lock:
            self._revision(expected)
            if not self.value['binding']:
                raise ValueError('Bind an exact native session first')
            self.value['binding'] = dict(self.value['binding'])
            if identifier: self.value['binding']['melty_task_id'] = identifier
            else: self.value['binding'].pop('melty_task_id', None)
            self.value['configuration_revision'] = uuid4().hex
            self._save()
        return self.view()

    def _start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stopped = threading.Event()
        self.value['connection'] = 'connecting'
        if self.activity:
            self.activity_thread = threading.Thread(target=self._activity_run, daemon=True, name='smelter-native-activity')
            self.activity_thread.start()
        self.thread = threading.Thread(target=self._run, daemon=True, name='smelter-native-progress')
        self.thread.start()

    def _alive(self):
        return any(thread and thread.is_alive() for thread in (self.thread,self.activity_thread))

    def resume(self):
        with self.lock:
            if self.value['enabled'] and self.value['binding']:
                self._start()

    def close(self):
        self.stopped.set()  # Leaves the saved binding/enabled preference for normal startup.

    def view(self):
        with self.lock:
            # Return a detached copy; transport and authentication never leave this module.
            value = json.loads(json.dumps({k: v for k, v in self.value.items() if k not in ('seen', 'cursor', 'pending','activity_cursor')}))
            value['finalizing_snapshot'] = bool(self.value.get('pending'))
            value['event_connection'] = value['connection']
            if value.get('activity_connection') == 'connected':
                value['connection'] = 'connected' if value['enabled'] else value['connection']
                value['status_source'] = 'shared native lifecycle metadata (HTTP + ACP)'
                if value.get('catching_up'):
                    value['task_state'] = value.get('activity_task_state',value['task_state'])
            else:
                value['status_source'] = 'Shared lifecycle metadata unavailable; HTTP process observations only'
        from access_policy import current, using
        from coding_workspace import load
        binding = value['binding']
        if binding:
            with using(current(self.root)):
                load(self.root, binding['workspace_id'])
                from workspace_tracking import view as tracking_view
                for item in value['completions']:
                    snapshot = item.get('workspace_tracking')
                    if snapshot:
                        # Recheck current path permissions even for historical chart nodes.
                        visible = tracking_view(snapshot, limit=1)
                        item['workspace_tracking'] = {k: visible[k] for k in ('workspace_id', 'revision', 'updated_at', 'graph', 'mermaid', 'tests')}
        return {**value, 'source': 'OpenCode native public lifecycle metadata',
                'read_only': True, 'raw_content_mirrored': False,
                'scope': 'Idle is a session observation, not proof that code or in-game behavior passed.'}

    def ingest(self, event, cursor=None, source='event_stream'):
        """Deterministic admission used by the worker and disposable transport tests."""
        binding = self.value['binding']
        if not binding:
            return False
        record = normalize(event, binding['session_id'])
        if not record:
            return False
        record['source'] = source
        with self.lock:
            if record['kind'] == 'tool':
                if 'tool' not in record:
                    record['tool'] = next((e['tool'] for e in reversed(self.value['events'])
                                           if e.get('call_id') == record['call_id'] and e.get('tool')), 'tool')
                key = 'tool:' + record['call_id'] + ':' + record['phase']
            else:
                key = record.get('source_event_id') or 'session:' + str(self.value['cycle']) + ':' + record['phase']
                if self.value['task_state'] == record['phase']:
                    return False
            key = hashlib.sha256(key.encode()).hexdigest()
            if key in self.value['seen']:
                return False
            tick = time.monotonic()
            while self.rate and tick - self.rate[0] > 10:
                self.rate.popleft()
            if len(self.rate) >= 100:
                self.value['gap'] = True
                return False
            self.rate.append(tick)
            self.value['seen'] = (self.value['seen'] + [key])[-1024:]
            phase = record['phase']
            if record['kind'] == 'tool' and self.value['task_state'] not in ('busy', 'retry'):
                self.value['cycle'] += 1
                self.value['gap'] = self.value['connection'] != 'connected' or bool(self.value.get('catching_up'))
                self.value['task_state'] = 'busy'
            elif record['kind'] == 'session':
                previous = self.value['task_state']
                if phase in ('busy', 'retry') and previous not in ('busy', 'retry'):
                    self.value['cycle'] += 1
                    self.value['gap'] = self.value['connection'] != 'connected'
                elif phase in ('failed', 'cancelled') and self.value['cycle'] == self.value['completed_cycle']:
                    self.value['cycle'] += 1
                # A stream's initial idle does not complete an unseen historical task.
                if phase in ('idle', 'failed', 'cancelled') and self.value['cycle'] > self.value['completed_cycle']:
                    self.value['pending'] = {'cycle': self.value['cycle'], 'phase': phase,
                                             'gap': self.value['gap'], 'observed_at': now()}
                self.value['task_state'] = phase
            self.value['sequence'] += 1
            self.value['last_observed_at'] = now()
            self.value['events'] = (self.value['events'] + [{**record, 'sequence': self.value['sequence'],
                'observed_at': self.value['last_observed_at']}])[-MAX_EVENTS:]
            if cursor:
                self.value['cursor'] = token(cursor)
            self._save()
            return True

    def finish_pending(self):
        with self.lock:
            pending = self.value.get('pending')
            binding = self.value['binding']
            if not pending:
                return
            pending = dict(pending)
        from access_policy import current, using
        from coding_workspace import context
        try:
            with using(current(self.root)):
                snapshot = context(self.root, {'workspace_id': binding['workspace_id'], 'limit': 1})
            # Retain only graph metadata, not a duplicate of the complete file index.
            full = {k: snapshot[k] for k in ('workspace_id', 'source_root', 'workspace_root', 'storage',
                'tests_use', 'updated_at', 'revision', 'operation', 'tests', 'graph', 'mermaid')}
            full.update(files=[], history=[])
            result = {**pending, 'tree_sha256': snapshot['revision'], 'workspace_tracking': full,
                      'verification': 'Observed final workspace snapshot; native idle is not a test pass.'}
        except (ValueError, OSError, TypeError, sqlite3.Error) as error:
            result = {**pending, 'snapshot_error': 'Workspace snapshot unavailable (' + type(error).__name__ + ')'}
        with self.lock:
            if self.value.get('pending') != pending:
                return
            self.value['completions'] = (self.value['completions'] + [result])[-MAX_COMPLETIONS:]
            self.value['completed_cycle'] = pending['cycle']
            self.value.pop('pending', None)
            self._save()

    def _run(self):
        delay = 1
        try:
            while not self.stopped.is_set():
                try:
                    binding = self.value['binding']
                    self._verify(binding)
                    transport = self.transport(binding['directory'])
                    with transport.stream(self.value['cursor']) as response:
                        # Subscribe before the status read: subsequent transitions queue on the stream.
                        statuses = transport.get('/session/status')
                        if not isinstance(statuses, dict):
                            raise ValueError('Invalid native session status response')
                        if not self.value.get('activity_authoritative'):
                            self.ingest({'type': 'session.status', 'properties': {'sessionID': binding['session_id'],
                                'status': statuses.get(binding['session_id'], {'type': 'idle'})}})
                        self.finish_pending()
                        with self.lock:
                            self.value['connection'] = 'connected'
                            self.value.pop('connection_error', None)
                            self._save()
                        delay = 1
                        for cursor, event in frames(response, self.stopped):
                            if self.stopped.is_set():
                                break
                            public=normalize(event,binding['session_id'])
                            if not self.value.get('activity_authoritative') or public and public['kind']=='tool':
                                self.ingest(event, cursor or event.get('id'))
                            self.finish_pending()
                        if not self.stopped.is_set():
                            raise OSError('Native event stream ended')
                except Exception as error:
                    # Never reflect HTTP bodies, remote errors, headers or credentials.
                    with self.lock:
                        self.value['connection'] = 'reconnecting'
                        self.value['gap'] = True
                        self.value['connection_error'] = 'Native monitor disconnected (' + type(error).__name__ + ')'
                        try:
                            self._save()
                        except (ValueError, OSError):
                            pass
                    if self.stopped.wait(delay):
                        break
                    delay = min(delay * 2, 30)
        finally:
            with self.lock:
                self.value['connection'] = 'stopped'

    def _activity_run(self):
        client=self.activity()
        try:
            while not self.stopped.is_set():
                try:
                    binding=self.value['binding']
                    since=self.value.get('activity_since') or self.value.get('last_observed_at') or now()
                    observed=client.poll(binding,self.value.get('activity_cursor'),since)
                    with self.lock:
                        changed=(self.value.get('activity_connection')!='connected' or
                                 self.value.get('activity_cursor')!=observed['cursor'] or
                                 self.value.get('activity_task_state')!=observed['phase'] or
                                 self.value.get('catching_up')!=observed['has_more'])
                        self.value.update(activity_connection='connected',activity_task_state=observed['phase'],
                                          activity_authoritative=True,catching_up=observed['has_more'])
                    for event in observed['events']:
                        changed=self.ingest(event,source='native_database') or changed
                    with self.lock:
                        self.value['activity_cursor']=observed['cursor']
                    if not observed['has_more']:
                        historical=(not observed['events'] and self.value['cycle']==0 and
                                    observed['phase'] in ('failed','cancelled') and
                                    observed['status_time']<int(datetime.fromisoformat(since).timestamp()*1000))
                        if historical:
                            with self.lock:self.value['task_state']=observed['phase']
                        else:
                            changed=self.ingest(observed['status_event'],source='native_database') or changed
                        self.finish_pending()
                    if changed:
                        with self.lock:self._save()
                except (ValueError,OSError,sqlite3.Error,KeyError,TypeError):
                    with self.lock:self.value['activity_connection']='unavailable'
                if self.stopped.wait(2):break
        finally:
            with self.lock:self.value['activity_connection']='stopped'


def manager(root):
    key = str(Path(root).resolve())
    with _managers_lock:
        if key not in _managers:
            _managers[key] = Bridge(root)
        return _managers[key]


def close_all():
    with _managers_lock:
        for bridge in _managers.values():
            bridge.close()
