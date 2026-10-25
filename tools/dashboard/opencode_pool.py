"""One persistent confined OpenCode session per dashboard process.

Starting a container for every task made OpenCode slow and tedious. The pool
keeps one managed container running and reuses it while its key (image, model,
runtime, access policy and bridge tool set) is unchanged; any change, relay
error or failed abort replaces it. Before each task the read-only code snapshot
is refreshed in place and that task's control and tool bridge are attached;
after the task they are detached, so nothing can call host tools between tasks.
Confinement is unchanged: no network, read-only code, session permission rules
per task, approved MCP tools only.
"""
from __future__ import annotations
import hashlib
import json
import threading
import time

LIFETIME = 8 * 3600  # Container server lifetime; tasks keep their own deadlines.
_lock = threading.RLock()
_state = {'client': None, 'key': None, 'status': 'stopped', 'error': None, 'started': None, 'tasks': 0}


def _key(root, configuration, policy, bridge):
    """Anything baked into the container at start; a change requires a new container."""
    from sandbox import config
    tools = json.dumps(bridge.manifest(configuration['runtime']['timeout_seconds']), sort_keys=True) if bridge and bridge.tools else ''
    raw = json.dumps({'image': config(root).get('opencode_image'), 'model': configuration['model'],
                      'runtime': configuration['runtime'], 'policy': getattr(policy, 'revision', None),
                      'tools': hashlib.sha256(tools.encode()).hexdigest()}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _discard():
    client = _state['client']
    if client is not None:
        if not client.close():
            _state.update(status='failed', error='Previous OpenCode container cleanup is pending; inspect Confined runner before retrying')
            return False
        _state.update(client=None, key=None)
    return True


def acquire(root, policy, configuration, control, bridge, factory=None):
    """Return a ready client bound to this task, starting or replacing it if needed."""
    with _lock:
        if _state['status'] == 'busy':
            raise ValueError('An OpenCode task is already using the session; wait for it to finish')
        key = _key(root, configuration, policy, bridge)
        client = _state['client']
        if client is not None and (_state['key'] != key or client.closed or client.error):
            if not _discard():
                raise ValueError(_state['error'])
            client = None
        if client is None:
            _state.update(status='starting', error=None)
            try:
                if factory is None:
                    from opencode_sandbox import ManagedClient as factory
                client = factory(root, policy, configuration, None, allow_inference=True, bridge=bridge, lifetime=LIFETIME)
            except Exception as exc:
                _state.update(status='failed', error=str(exc)[:300])
                raise
            _state.update(client=client, key=key, started=time.time())
        else:
            client.refresh(policy)
        try:
            client.attach(control, bridge)
        except Exception:
            _discard()
            raise
        _state.update(status='busy', error=None)
        _state['tasks'] += 1
        return client


def release(client, healthy=True):
    """Detach the task; keep the session if it is healthy, else remove it.

    Returns the cleanup state reported with the task: True when the session is
    healthy and kept or was removed cleanly, False when removal failed.
    """
    with _lock:
        if client is not _state['client']:
            return client.close()
        if healthy and not client.error and not client.closed:
            # Keep task ownership until the relay and its active fixed tool finish.
            detached = client.detach()
            if detached is not False and not client.error:
                _state['status'] = 'ready'
                return True
        removed = _discard()
        _state.update(status='stopped' if removed else 'failed',
                      error=None if removed else 'Previous OpenCode container was not removed; inspect Confined runner')
        return removed


def start(root, factory=None):
    """Warm the session in the background so the first OpenCode task does not wait for it."""
    from component_controls import require_enabled
    require_enabled(root, 'opencode')
    def run():
        try:
            from access_policy import current
            from task_contract import configuration
            # Create and release under one lock hold so a task cannot attach in between.
            with _lock:
                if _state['status'] != 'starting':
                    return  # A task acquired the client, or Stop ran, before the warm-up worker.
                try:
                    require_enabled(root, 'opencode')
                except ValueError:
                    _state['status'] = 'stopped' if _state['client'] is None else 'ready'
                    return  # Stopped in System status after this warm-up was queued.
                _state['status'] = 'stopped' if _state['client'] is None else 'ready'
                client = acquire(root, current(root), configuration(root), None, None, factory=factory)
                release(client)
        except Exception as exc:  # Reported through status(); the next task retries.
            with _lock:
                _state.update(status='failed', error=str(exc)[:300])
    with _lock:
        if _state['status'] in ('starting', 'busy') or (_state['client'] is not None and _state['status'] == 'ready'):
            return status()
        _state.update(status='starting', error=None)
        starting = status()
    threading.Thread(target=run, daemon=True, name='opencode-pool-start').start()
    return starting


def stop(force=False):
    """Remove the session. Refused while a task runs unless forced (dashboard exit)."""
    with _lock:
        if _state['status'] == 'busy' and not force:
            raise ValueError('An OpenCode task is running; stop it before stopping the session')
        removed = _discard()
        _state.update(status='stopped' if removed else 'failed', error=None if removed else 'OpenCode container was not removed')
        return status()


def status():
    """Pool observation; 'failed' with a container name means cleanup is still pending."""
    with _lock:
        client = _state['client']
        return {'status': _state['status'], 'error': _state['error'], 'tasks': _state['tasks'],
                'uptime_seconds': round(time.time() - _state['started']) if client is not None and _state['started'] else 0,
                'container': getattr(client, 'name', None)}
