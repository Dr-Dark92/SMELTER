"""Operator-only component observations and fixed lifecycle operations.

OpenCode/MCP are enabled on demand. Only this dashboard's Ollama child is
terminated; an existing tray/system service is observed, never adopted by PID.
"""
import atexit
import http.client
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

NAME = 'component_controls.json'
DEFAULT = {'schema_version': 1, 'opencode': True, 'mcp': True}
ACTIONS = ('status', 'start', 'stop', 'reload', 'restart')
_managers = {}
_registry_lock = threading.RLock()


def validate(value):
    if not isinstance(value, dict) or set(value) != set(DEFAULT) or type(value['schema_version']) is not int or value['schema_version'] != 1 or any(type(value[k]) is not bool for k in ('opencode', 'mcp')):
        raise ValueError('Component controls require schema_version=1 and boolean opencode/mcp')


def settings(root):
    from database import chosen_database
    from config_store import load_config
    return load_config(root, NAME) if chosen_database(Path(root)) else dict(DEFAULT)


def require_enabled(root, component):
    if not settings(root)[component]:
        raise ValueError(component + ' is stopped in Settings → System status; Start it before using this route')


def manager(root):
    key = str(Path(root).resolve())
    with _registry_lock:
        if key not in _managers:
            _managers[key] = Components(Path(key))
        return _managers[key]


def check_admission(root, engine, mcp_required=False):
    # Called with Jobs.lock held, paired with the lifecycle changing flag.
    if manager(root).changing:
        raise ValueError('A system component operation is in progress; wait before sending')
    if engine.startswith('opencode'):
        require_enabled(root, 'opencode')
    if mcp_required:
        require_enabled(root, 'mcp')


def enable_agent_components(root):
    """Selecting OpenCode enables its runtime and built-in transport together.

    This changes component availability only, never task tool/path grants.
    """
    from chat_jobs import JOBS
    from job_store import active
    from config_store import save_config
    with JOBS.lock:
        if manager(root).changing:
            raise ValueError('A system component operation is in progress; wait before starting OpenCode')
        flags = settings(root)
        if flags['opencode'] and flags['mcp']:
            return
        if any(j['state'] == 'running' for j in JOBS.jobs.values()) or active(root):
            raise ValueError('Finish or stop the active chat task before enabling OpenCode')
        save_config(root, NAME, {**flags, 'opencode': True, 'mcp': True})


def ollama_request(path, body=None, timeout=2):
    if path not in ('/api/version', '/api/tags', '/api/ps', '/api/generate'):
        raise ValueError('Unsupported component endpoint')
    connection = http.client.HTTPConnection('127.0.0.1', 11434, timeout=timeout)
    try:
        connection.request('POST' if body is not None else 'GET', path,
                           body=json.dumps(body).encode() if body is not None else None,
                           headers={'Content-Type': 'application/json'})
        response = connection.getresponse()
        raw = response.read(256 * 1024 + 1)
        if response.status != 200 or len(raw) > 256 * 1024:
            raise ValueError('Ollama returned an invalid or oversized component response')
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError('Invalid Ollama response')
        return result
    finally:
        connection.close()


class Components:
    def __init__(self, root, *, request=None, finder=None, runner=None, popen=None):
        from process_runner import run
        self.root = Path(root)
        self.request = request or ollama_request
        self.finder = finder or shutil.which
        self.runner = runner or run
        self.popen = popen or subprocess.Popen
        self.lock = threading.RLock()
        self.process = None
        self.job = None
        self.changing = False
        self.cache = None
        self.checked = 0

    def owned(self):
        return self.process is not None and self.process.poll() is None

    def row(self, key, name, kind, installation, state, detail, **extra):
        return {'id': key, 'name': name, 'kind': kind, 'installation': installation,
                'state': state, 'detail': detail, 'version': None,
                'actions': {a: {'enabled': a in ('status', 'reload'),
                               'reason': '' if a in ('status', 'reload') else 'This component has no independent managed service'} for a in ACTIONS},
                **extra}

    def snapshot(self, refresh=False):
        with self.lock:
            if self.cache is not None and not refresh and time.monotonic() - self.checked < 15:
                return self.cache
            from database import inspect_database
            from mcp_connections import sdk_status
            from model_assets import viewer_status
            from sandbox import config
            from task_contract import configuration
            flags = settings(self.root)
            try: model = configuration(self.root)['model']
            except (ValueError, OSError):
                from model_preferences import FALLBACK_MODEL
                model = FALLBACK_MODEL
            rows = []
            executable = self.finder('ollama')
            running, version, installed, loaded, api_error = False, None, [], [], ''
            try:
                version = self.request('/api/version').get('version')
                running = isinstance(version, str) and bool(version)
                tags, ps = self.request('/api/tags'), self.request('/api/ps')
                if not isinstance(tags.get('models'), list) or not isinstance(ps.get('models'), list):
                    raise ValueError('Invalid Ollama model lists')
                installed, loaded = tags['models'], ps['models']
            except (ValueError, OSError, http.client.HTTPException) as exc:
                api_error = type(exc).__name__
            row = self.row('ollama', 'Ollama', 'Local model server',
                           'installed' if executable or running else 'missing',
                           'running' if running else 'unhealthy' if self.owned() else 'stopped' if executable else 'missing',
                           '127.0.0.1:11434 · ' + ('Started by this dashboard' if self.owned() else 'Managed outside this dashboard' if running else 'Local server is not responding'),
                           version=version, ownership='dashboard' if self.owned() else 'external' if running else 'none')
            for action in ('start', 'stop', 'restart'):
                allowed = bool(executable) and not running and not self.owned() if action == 'start' else self.owned()
                row['actions'][action] = {'enabled': allowed, 'reason': '' if allowed else 'Stop/restart is available only for the Ollama process started here' if running else 'Install Ollama, then Start'}
            row['actions']['reload']['reason'] = 'Refresh server/model observations; Ollama has no configuration reload API'
            rows.append(row)
            names = lambda items: {x.get('name', x.get('model')) for x in items if isinstance(x, dict)}
            present, resident = model in names(installed), model in names(loaded)
            row = self.row('qwen', model, 'Selected model · not a separate service',
                           'installed' if present else 'unknown' if not running or api_error else 'missing',
                           'loaded' if resident else 'unloaded' if present else 'unavailable',
                           'Start loads into RAM/VRAM; Stop unloads. Reload/Restart unload and load using saved runtime settings. New chats can load it again. No model download.')
            for action in ('start', 'stop', 'reload', 'restart'):
                allowed = running and present and (not resident if action == 'start' else resident if action == 'stop' else True)
                row['actions'][action] = {'enabled': allowed, 'reason': '' if allowed else 'Requires a responding Ollama server and the selected installed model'}
            rows.append(row)
            docker = self.finder('docker')
            docker_running, docker_version, image, image_present = False, None, None, False
            docker_responding, docker_mode = False, None
            try:
                if docker:
                    if os.environ.get('DOCKER_HOST') and not os.environ['DOCKER_HOST'].startswith(('unix://', 'npipe://')):
                        raise ValueError('Only a local Docker daemon is supported')
                    context = self.runner([docker, 'context', 'inspect', '--format', '{{.Endpoints.docker.Host}}'], timeout=3, max_output=4096, text=True, check=True).stdout.strip()
                    if not context.startswith(('unix://', 'npipe://')): raise ValueError('Only a local Docker daemon is supported')
                    info = self.runner([docker, 'info', '--format', '{{json .}}'], timeout=5, max_output=65536, text=True, check=True)
                    info = json.loads(info.stdout)
                    if not isinstance(info, dict): raise ValueError('Invalid Docker status')
                    docker_responding, docker_mode = bool(info.get('ServerVersion')), info.get('OSType')
                    docker_running, docker_version = info.get('OSType') == 'linux', info.get('ServerVersion')
                    image = config(self.root)['opencode_image']
                    if image:
                        actual = self.runner([docker, 'image', 'inspect', '--format', '{{.Id}}', image], timeout=5, max_output=4096, text=True, check=True)
                        image_present = actual.stdout.strip() == image
            except (ValueError, OSError, subprocess.SubprocessError):
                pass
            rows.append(self.row('docker', 'Docker', 'OS-managed Linux container engine',
                                 'installed' if docker else 'missing', 'running' if docker_responding else 'unavailable',
                                 'Manage the shared engine in Docker Desktop or your OS service manager. Linux containers required; observed mode: ' + str(docker_mode or 'unavailable') + '. Status checks never start containers.', version=docker_version))
            for action in ('start', 'stop', 'restart'):
                rows[-1]['actions'][action]['reason'] = 'Shared OS-managed engine; use Docker Desktop or your OS service manager'
            row = self.row('opencode', 'OpenCode', 'Confined runtime · one container per task',
                           'available_image' if image_present else 'cli_only' if self.finder('opencode') else 'missing',
                           'disabled' if not flags['opencode'] else 'on_demand' if image_present and docker_running else 'blocked',
                           'Start enables and checks an isolated session; Stop disables new OpenCode tasks. Reload/Restart recheck the runtime and close the inspection container. Requires a configured image containing OpenCode 1.19.3.', version=getattr(self, 'opencode_version', None))
            for action in ('start', 'stop', 'reload', 'restart'):
                row['actions'][action] = {'enabled': (not flags['opencode'] if action == 'start' else flags['opencode']) and (action == 'stop' or image_present and docker_running),
                                          'reason': 'Requires the configured local OpenCode image and Docker; finish active tasks before changing runtime state'}
            rows.append(row)
            sdk = sdk_status()
            row = self.row('mcp', 'MCP', 'Built-in stdio provider · one process per call',
                           sdk['status'], 'disabled' if not flags['mcp'] else 'on_demand' if sdk['status'] == 'installed' else 'blocked',
                           'Start enables and checks the provider. Stop disables MCP calls. Reload/Restart perform discovery; the check process closes afterwards.', version=sdk.get('version'))
            for action in ('start', 'stop', 'reload', 'restart'):
                row['actions'][action] = {'enabled': (not flags['mcp'] if action == 'start' else flags['mcp']) and (action == 'stop' or sdk['status'] == 'installed'),
                                          'reason': 'Requires the pinned MCP SDK; finish active tasks before changing provider state'}
            rows.append(row)
            rows.append(self.row('python', 'Python', 'Dashboard interpreter', 'installed', 'running', sys.executable, version=sys.version.split()[0]))
            node = self.finder('node')
            node_version = None
            if node:
                try: node_version = self.runner([node, '--version'], timeout=3, max_output=4096, text=True, check=True).stdout.strip()
                except (ValueError, OSError, subprocess.SubprocessError): pass
            rows.append(self.row('node', 'Node.js', 'REA and host tool dependency', 'installed' if node_version else 'unverified' if node else 'missing', 'available' if node_version else 'unavailable', 'Used when a supported tool needs Node; no standing service.', version=node_version))
            db = inspect_database(self.root)
            rows.append(self.row('database', 'SQLite database', 'Local persistent storage', 'installed',
                                 db['status'], db.get('database') or 'Choose a database directory during setup'))
            viewer = viewer_status(self.root)
            rows.append(self.row('viewer', 'GLB viewer', 'Local browser library', viewer['status'],
                                 'available' if viewer['status'] == 'installed' else 'missing', 'Loaded by your browser when opening a 3D preview.'))
            self.cache = {'checked_at': datetime.now(timezone.utc).isoformat(), 'components': rows,
                          'busy': self.changing, 'model': model}
            self.checked = time.monotonic()
            return self.cache

    def _stop_owned(self):
        if self.process is None:
            raise ValueError('Ollama was not started by this dashboard')
        process = self.process
        try:
            if os.name == 'nt':
                if self.job and self.job.handle: self.job.close()
                elif process.poll() is None: process.kill()
            else:
                try:
                    if process.poll() is None: os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError: pass
            process.wait(timeout=5)
        except (OSError, subprocess.SubprocessError) as exc:
            raise ValueError('Owned Ollama termination was not confirmed; ownership is retained for retry') from exc
        finally:
            if process.poll() is not None:
                if self.job: self.job.close()
                self.process = self.job = None

    def close(self):
        with self.lock:
            if self.process is not None: self._stop_owned()

    def _start_ollama(self):
        if self.owned(): return
        if self.process is not None: self._stop_owned()
        executable = self.finder('ollama')
        if not executable or Path(executable).suffix.lower() in ('.cmd', '.bat', '.ps1'):
            raise ValueError('A native Ollama executable is required; shell shims are not executed')
        options = {'creationflags': getattr(subprocess, 'CREATE_NO_WINDOW', 0)} if os.name == 'nt' else {'start_new_session': True}
        self.process = self.popen([executable, 'serve'], stdin=subprocess.DEVNULL,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False, **options)
        try:
            if os.name == 'nt':
                from process_runner import _WindowsJob
                self.job = _WindowsJob(self.process)
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                if self.process.poll() is not None: raise ValueError('Owned Ollama process exited before becoming ready')
                try:
                    if self.request('/api/version').get('version') and self.process.poll() is None: return
                except (ValueError, OSError, http.client.HTTPException): pass
                time.sleep(.15)
            raise ValueError('Ollama did not become ready within its startup deadline')
        except Exception:
            self._stop_owned()
            raise

    def _record(self, component, action, status):
        from python_tools import _plain_path
        folder = _plain_path(self.root / '.smelter')
        folder.mkdir(parents=True, exist_ok=True)
        path = _plain_path(folder / 'component-events.jsonl')
        lines = path.read_text(encoding='utf-8').splitlines()[-199:] if path.is_file() and path.stat().st_size < 256 * 1024 else []
        lines.append(json.dumps({'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                                'source': 'operator', 'component': component, 'action': action, 'status': status}))
        temporary = _plain_path(folder / 'component-events.tmp')
        temporary.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        temporary.replace(path)

    def action(self, component, action, expected_model=None):
        if component not in ('all', 'ollama', 'qwen', 'opencode', 'mcp', 'docker', 'python', 'node', 'database', 'viewer') or action not in ACTIONS or component == 'all' and action != 'status':
            raise ValueError('Unknown component or lifecycle action')
        if not self.lock.acquire(blocking=False):
            raise ValueError('A component operation is already in progress')
        try:
            if action == 'status' or action == 'reload' and component in ('ollama', 'docker', 'python', 'node', 'database', 'viewer'):
                return {'status': 'checked', 'component': component, 'action': action, 'snapshot': self.snapshot(True)}
            from chat_jobs import JOBS
            from job_store import active
            with JOBS.lock:
                if any(j['state'] == 'running' for j in JOBS.jobs.values()) or active(self.root):
                    raise ValueError('Finish or stop the active chat task before changing components')
                self.changing = True
            result = None
            try:
                snapshot = self.snapshot(True)
                row = next(x for x in snapshot['components'] if x['id'] == component)
                if component == 'qwen' and expected_model is not None and expected_model != snapshot['model']:
                    raise ValueError('Selected model changed; refresh System status before changing model residency')
                if not row['actions'][action]['enabled']:
                    raise ValueError(row['actions'][action]['reason'])
                if component == 'ollama':
                    if action in ('stop', 'restart'): self._stop_owned()
                    if action in ('start', 'restart'): self._start_ollama()
                elif component == 'qwen':
                    from task_contract import configuration
                    effective = configuration(self.root)
                    model = effective['model']
                    if model != snapshot['model']: raise ValueError('Model configuration changed during admission; refresh and retry')
                    # Empty request explicitly loads/unloads; never send a user prompt or pull a model.
                    if action in ('stop', 'reload', 'restart'):
                        self.request('/api/generate', {'model': model, 'stream': False, 'keep_alive': 0}, timeout=120)
                    if action in ('start', 'reload', 'restart'):
                        self.request('/api/generate', {'model': model, 'stream': False, 'keep_alive': 300,
                                     'options': {'num_ctx': effective['runtime']['context_tokens']}}, timeout=120)
                    observed = self.request('/api/ps').get('models', [])
                    if not isinstance(observed, list): raise ValueError('Ollama did not return a valid model residency list')
                    loaded = any(isinstance(x, dict) and x.get('name', x.get('model')) == model for x in observed)
                    if loaded != (action != 'stop'): raise ValueError('Ollama did not confirm the requested model residency')
                elif component in ('opencode', 'mcp'):
                    from config_store import save_config
                    flags = settings(self.root)
                    previous = dict(flags)
                    flags[component] = action != 'stop'
                    save_config(self.root, NAME, flags)
                    try:
                        if action != 'stop':
                            if component == 'opencode':
                                from opencode_runtime import status
                                checked = status(self.root)
                                if not checked.get('agent_ready'): raise ValueError(checked.get('reason', 'OpenCode is not ready'))
                                self.opencode_version = checked.get('version')
                            else:
                                from mcp_connections import exchange
                                checked = exchange(self.root, timeout=20)
                                if checked.get('status') != 'connected': raise ValueError('MCP did not confirm discovery')
                    except Exception:
                        save_config(self.root, NAME, previous)
                        raise
                result = {'status': 'completed', 'component': component, 'action': action,
                          'message': ('Provider disabled for new tasks. No standing service process.' if component in ('opencode', 'mcp') and action == 'stop' else 'On-demand provider checked; inspection process closed. New tasks use the current enable state.' if component in ('opencode', 'mcp') else 'Requested component state observed.')}
                self.cache = None
                result['snapshot'] = self.snapshot(True)
                return result
            finally:
                self.changing = False
                if result is None: self.cache = None
                elif self.cache is not None: self.cache['busy'] = False
                try: self._record(component, action, 'completed' if result else 'failed')
                except (ValueError, OSError):
                    if result:
                        result['message'] += ' Local action audit could not be saved.'
                        result['audit_error'] = True
        finally:
            self.lock.release()


def close_all():
    for item in list(_managers.values()):
        item.close()


atexit.register(close_all)
