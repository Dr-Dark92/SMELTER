"""Non-destructive review reproductions. Uses temporary fixtures and mocks only."""
import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools/dashboard'))
import access_policy
import opencode_pool as pool
from opencode_sandbox import ManagedClient
from frontend_workspace import _source_files, DASHBOARD

results = []
def record(name, **data):
    results.append({'probe': name, **data})

class FakeClient:
    created = []
    def __init__(self, *args, **kwargs):
        self.closed = False
        self.error = None
        self.control = None
        self.bridge = kwargs.get('bridge')
        self.close_had_bridge = None
        self.cleanup = False
        self.created.append(self)
    def attach(self, control, bridge): self.control, self.bridge = control, bridge
    def detach(self): self.control = self.bridge = None
    def close(self):
        self.close_had_bridge = self.bridge is not None
        self.closed = True
        return self.cleanup
    def refresh(self, policy): pass

def reset():
    pool._state.update(client=None, key=None, status='stopped', error=None, started=None, tasks=0)

with tempfile.TemporaryDirectory(prefix='smelter-review-') as temporary:
    root = Path(temporary) / 'SMELTER'
    root.mkdir()
    policy = access_policy.Policy(access_policy.defaults(root))
    denied = root / 'tools/Private'
    denied.mkdir(parents=True)
    secret = denied / 'fixture.txt'
    secret.write_text('fixture only', encoding='utf-8')
    value = access_policy.defaults(root)
    value['locations'][0]['exclusions'].append('tools/Private/**')
    scoped = access_policy.Policy(value)
    def allowed(path):
        try: scoped.authorize(path, 'read'); return True
        except ValueError: return False
    record('windows_exclusion_case', exact_allowed=allowed(secret),
           alternate_case_allowed=allowed(root / 'tools/private/fixture.txt'),
           same_file=(root / 'tools/private/fixture.txt').is_file())

    config = {'model': 'fixture', 'runtime': {'timeout_seconds': 30}}
    with patch.object(pool, '_key', side_effect=lambda root, conf, policy, bridge: conf['model']):
        reset()
        first = pool.acquire(root, policy, config, None, object(), factory=FakeClient)
        pool.release(first)
        second = pool.acquire(root, policy, {**config, 'model':'changed'}, None, None, factory=FakeClient)
        record('replacement_after_failed_cleanup', old_cleanup=False,
               new_client_created=second is not first, pool_status=pool.status()['status'])
        reset()
        client = pool.acquire(root, policy, config, None, object(), factory=FakeClient)
        pool.release(client, healthy=False)
        record('bridge_detached_before_close', close_had_bridge=client.close_had_bridge)
        reset()
        with patch('access_policy.current', return_value=policy), \
             patch('task_contract.configuration', return_value=config), \
             patch('component_controls.require_enabled', side_effect=ValueError('disabled')) as gate:
            pool.start(root, factory=FakeClient)
            for _ in range(100):
                if pool.status()['status'] != 'starting': break
                threading.Event().wait(.01)
            record('pool_start_component_gate', status=pool.status()['status'], gate_calls=gate.call_count)
        reset()

    idle = object.__new__(ManagedClient)
    idle.allow_inference = True
    idle.control = None
    idle.bridge = None
    idle.model = 'fixture'
    idle.model_calls = 0
    idle.settings = {'max_output_tokens': 10}
    idle._native_response = lambda body: {'fixture_inference_admitted': True}
    packet = {'method':'POST', 'path':'/v1/chat/completions',
              'body':base64.b64encode(json.dumps({'model':'fixture','messages':[]}).encode()).decode()}
    record('idle_model_relay', response=idle._response(packet))

    code = root / DASHBOARD
    code.parent.mkdir(parents=True, exist_ok=True)
    code.write_text('HTML="fixture"', encoding='utf-8')
    (root/'skills').mkdir()
    (root/'system-requirements.json').write_text('{}', encoding='utf-8')
    (root/'tools/setup').mkdir()
    for name in ('requirements_catalog.py', 'check_requirements.py'):
        (root/'tools/setup'/name).write_bytes((ROOT/'tools/setup'/name).read_bytes())
    files = _source_files(root)
    destination = Path(temporary)/'copy'
    for relative, source in files.items():
        out = destination/relative
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(source.read_bytes())
    result = subprocess.run([sys.executable, str(destination/'tools/setup/check_requirements.py'), '--json'],
                            capture_output=True, text=True, timeout=10)
    record('snapshot_missing_catalog', catalog_copied='system-requirements.json' in files,
           copied_scanner_exit=result.returncode,
           missing_catalog_error='FileNotFoundError' in result.stderr and 'system-requirements.json' in result.stderr)

print(json.dumps(results, indent=2))
