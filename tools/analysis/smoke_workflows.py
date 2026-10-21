"""Actual loopback HTTP, MCP, SQLite, GLB and recovery smoke without model inference.

All application state is disposable. Only model replies and dependency observations
are synthetic. Retained evidence contains fixture data, never the operator's DB.
"""
import argparse
import base64
from contextlib import ExitStack
import hashlib
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import shutil
import sys
import tempfile
import threading
import time
from unittest.mock import patch
from uuid import uuid4

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools/dashboard'))
from home_demo import create_fixtures


def smoke(directory):
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    checks = []
    report = {'status': 'FAIL', 'mode': 'real HTTP/files/SQLite/MCP; synthetic inference',
              'live_qwen': False, 'docker': False, 'checks': checks}
    def checked(name, condition, detail=None):
        checks.append({'name': name, 'status': 'PASS' if condition else 'FAIL', 'detail': detail})
        if not condition:raise ValueError('Workflow smoke failed: ' + name)
    try:
        import dashboard
        from chat_jobs import Control, Jobs
        from database import select_database, inspect_database
        from access_policy import current
        from skill_runtime import initialize, _monitors
        from model_assets import inspect_attachment, model_path
        from maintenance import restore
        with tempfile.TemporaryDirectory(prefix='smelter-workflow-smoke-') as temporary, ExitStack() as patches:
            base = Path(temporary)
            root = base / 'SMELTER'
            (root / 'tools/dashboard').mkdir(parents=True)
            (root / 'tools/dashboard/dashboard.py').write_text('VALUE=1\n', encoding='utf-8')
            manifest = root / 'skills/fixture/SKILL.md'
            manifest.parent.mkdir(parents=True)
            manifest.write_bytes(b'# Fixture\n\n## Purpose\nVerify WORKFLOW_SKILL_MARKER using receipts.\n')
            select_database(root, str(base / 'data#smoke'))
            fixtures = create_fixtures(base / 'inputs')
            jobs = Jobs()
            entered = threading.Event()
            requests = []
            def infer(control, body, timeout, maximum):
                control.check()
                requests.append(body)
                prompt = next(m['content'] for m in reversed(body['messages']) if m['role'] == 'user')
                if prompt == 'slow fixture':
                    entered.set()
                    if not control.cancelled.wait(5):raise ValueError('Stop fixture was never cancelled')
                    control.check()
                tools = {t['function']['name'] for t in body.get('tools', [])}
                has_result = any(m['role'] == 'tool' for m in body['messages'])
                if prompt == 'report fixture' and not has_result and 'write_diagnostic_markdown' in tools:
                    message = {'content': '', 'tool_calls': [{'function': {'name': 'write_diagnostic_markdown',
                               'arguments': {'filename': 'workflow-smoke.md', 'content': '# Actual fixture report\n'}}}]}
                elif prompt == 'inventory fixture' and not has_result and 'inventory_directory' in tools:
                    message = {'content': '', 'tool_calls': [{'function': {'name': 'inventory_directory',
                               'arguments': {'relative_path': '.'}}}]}
                else:message = {'content': 'Synthetic model reply; inspect actual controller receipts.'}
                return json.dumps({'message': message, 'done_reason': 'stop'}).encode()
            patches.enter_context(patch.object(dashboard, 'ROOT', root))
            patches.enter_context(patch.object(dashboard, 'REPORTS', root / '.smelter/reports'))
            patches.enter_context(patch.object(dashboard, 'JOBS', jobs))
            patches.enter_context(patch.object(dashboard, 'scan', return_value={'tools': []}))
            patches.enter_context(patch.object(dashboard, 'list_models', return_value={'status': 'fixture', 'models': []}))
            patches.enter_context(patch.object(Control, 'infer', infer))
            initialize(root)
            token = secrets.token_urlsafe(32)
            server = ThreadingHTTPServer(('127.0.0.1', 0), dashboard.handler(token))
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            def http(path, body=None, *, authorized=True, expected=200):
                connection = HTTPConnection('127.0.0.1', server.server_port, timeout=20)
                try:
                    headers = {'Content-Type': 'application/json'}
                    if authorized:headers['X-Smelter-Token'] = token
                    connection.request('POST' if body is not None else 'GET', path,
                                       json.dumps(body) if body is not None else None, headers)
                    response = connection.getresponse()
                    raw = response.read()
                    if response.status != expected:
                        raise ValueError(path + ': HTTP ' + str(response.status) + ' ' + raw.decode(errors='replace')[:500])
                    return json.loads(raw)
                finally:connection.close()
            def ask(cid, prompt, **values):
                admitted = http('/api/chats', {'action': 'start', 'id': cid, 'content': prompt,
                                               'engine': 'ollama', **values}, expected=202)
                deadline = time.monotonic() + 25
                while time.monotonic() < deadline:
                    result = http('/api/chat-jobs/' + admitted['id'])
                    if result['state'] != 'running':return result
                    time.sleep(.05)
                raise ValueError('Fixture job did not settle')
            try:
                http('/api/chats', authorized=False, expected=403)
                http('/api/chats', [], expected=400)
                http('/api/chats', {'action': 'create', 'title': ''}, expected=400)
                cid = http('/api/chats', {'action': 'create', 'title': 'Workflow smoke'})['id']
                http('/api/chats', {'action': 'rename', 'id': cid, 'title': 'Renamed smoke'})
                checked('auth, JSON shape, mandatory title and chat CRUD', http('/api/chats/' + cid)['title'] == 'Renamed smoke')
                checked('database hash-path startup and integrity', http('/api/startup')['ready'] and inspect_database(root, integrity=True)['ready'])
                policy = http('/api/access-policy')
                policy_value = {'schema_version': 1, 'locations': policy['locations'] + [{
                    'id': 'inputs', 'name': 'Read-only smoke inputs', 'path': fixtures['inventory']['path'],
                    'read': True, 'write': False, 'execute': False, 'operations': [], 'exclusions': [], 'enabled': True}]}
                applied = http('/api/access-policy', {'policy': policy_value, 'expected_revision': policy['revision']})
                http('/api/access-policy', {'policy': policy_value, 'expected_revision': policy['revision']}, expected=400)
                http('/api/chats', {'action': 'start', 'id': cid, 'content': 'denied', 'engine': 'ollama',
                                   'tool_permissions': {'inventory_root': fixtures['outside']}}, expected=400)
                checked('policy compare-and-swap and unregistered admission denial', len(jobs.jobs) == 0 and applied['revision'] != policy['revision'])
                from urllib.parse import quote
                folders = http('/api/location-browser?path=' + quote(fixtures['inventory']['path'], safe=''))
                checked('operator folder browser lists directories only', [r['name'] for r in folders['directories']] == ['nested'])
                first = ask(cid, 'report fixture', skills=['fixture'], tool_permissions={'write_diagnostics': True, 'transport': 'mcp'})
                transcript = http('/api/chats/' + cid)
                execution = transcript['messages'][-1]['execution']
                receipt = next(e['result'] for e in execution['events'] if e['tool'] == 'write_diagnostic_markdown')
                saved = Path(receipt['path']).read_bytes()
                checked('real MCP write, saved bytes/hash and durable outcome', first['state'] == 'done' and
                        receipt['sha256'] == hashlib.sha256(saved).hexdigest() and saved == b'# Actual fixture report\n')
                checked('admitted skill text and exact hash are recorded', 'WORKFLOW_SKILL_MARKER' in json.dumps(requests) and
                        execution['skill_snapshots'][0]['sha256'] == hashlib.sha256(manifest.read_bytes()).hexdigest())
                second = ask(cid, 'report fixture')
                execution = http('/api/chats/' + cid)['messages'][-1]['execution']
                checked('next task receives no previous tool grants', second['state'] == 'done' and not execution['events'] and
                        not execution['permissions']['write_diagnostics'] and not (root / 'diagnostics/workflow-smoke_01.md').exists())
                inventory_job = ask(cid, 'inventory fixture', tool_permissions={'inventory_root': fixtures['inventory']['path']})
                entry = http('/api/chats/' + cid)['messages'][-1]['execution']['events'][0]['result']
                checked('read-only inventory returns known exact metadata', inventory_job['state'] == 'done' and
                        entry['files_observed'] == 3 and entry['directories_observed'] == 1 and
                        sum(e['bytes'] or 0 for e in entry['entries']) == 26 and entry['scan_complete'])
                job = http('/api/chats', {'action': 'start', 'id': cid, 'content': 'slow fixture'}, expected=202)
                checked('slow task begins', entered.wait(2))
                http('/api/chats', {'action': 'stop', 'job_id': job['id']})
                deadline = time.monotonic() + 3
                while time.monotonic() < deadline and jobs.status(job['id'])['state'] == 'running':time.sleep(.02)
                durable = Jobs().status(job['id'], root=root)
                checked('Stop and independent durable status agree', jobs.status(job['id'])['state'] == durable['state'] == 'cancelled')
                attachment = http('/api/models', {'conversation_id': cid, 'filename': 'two-clips.glb',
                    'base64': base64.b64encode(Path(fixtures['model']['path']).read_bytes()).decode()})
                model = inspect_attachment(root, {'model_ids': [attachment['id']]}, {'attachment_id': attachment['id']})
                http('/api/models', {'action': 'rename_animation', 'id': attachment['id'], 'index': 1, 'label': 'Smoke label'})
                clips = next(m['model_attachment'] for m in http('/api/chats/' + cid)['messages'] if m['model_attachment'])
                checked('GLB structure, embedded durations and persistent labels',
                        [c['duration_seconds'] for c in model['animation_clips']] == [1, 2] and clips['animation_labels']['1'] == 'Smoke label')
                backup = base / 'verified-backup'
                result = http('/api/maintenance', {'action': 'backup', 'directory': str(backup), 'approval': True})
                restored = base / 'RESTORED'
                restored.mkdir()
                restore(backup, restored, base / 'restored-data', True)
                from chats import read_chat
                checked('verified backup and offline restore preserve chat and GLB', result['status'] == 'backed_up' and
                        read_chat(restored, cid)['title'] == 'Renamed smoke' and model_path(restored, attachment['id']).read_bytes() == model_path(root, attachment['id']).read_bytes())
                old = root / '.smelter/reports' / (str(uuid4()) + '.json')
                old.parent.mkdir(exist_ok=True)
                old.write_text('{"fixture":true}', encoding='utf-8')
                os.utime(old, (time.time() - 40 * 86400,) * 2)
                plan = http('/api/maintenance', {'action': 'plan', 'days': 30})
                http('/api/maintenance', {'action': 'prune', 'plan_id': plan['plan_id'], 'approval': False}, expected=400)
                checked('retention preview and denied prune preserve files', old.exists() and plan['files'] == 1)
                removed = http('/api/maintenance', {'action': 'prune', 'plan_id': plan['plan_id'], 'approval': True})
                checked('approved prune removes only the reviewed old artifact', removed['removed'] == 1 and not old.exists() and model_path(root, attachment['id']).is_file())
                http('/api/chats', {'action': 'delete', 'id': cid})
                checked('conversation deletion reconciles attachment bytes', not (root / '.smelter/model-assets' / (attachment['id'] + '.glb')).exists())
                from resource_metrics import cpu_status, memory_status
                report['host_observations'] = {'cpu': cpu_status(), 'memory': memory_status()}
                report.update(status='PASS', synthetic_model_requests=len(requests), cleanup_confirmed=True)
            finally:
                for item in jobs.jobs.values():
                    if item['state'] == 'running':item['control'].cancel()
                server.shutdown()
                server.server_close()
                worker.join(timeout=3)
                _monitors.pop(str(root.resolve()), None)
                for name in ('tool-runs',):
                    source = root / '.smelter' / name
                    if source.is_dir():shutil.copytree(source, directory / name)
    except Exception as exc:
        report['error'] = type(exc).__name__ + ': ' + str(exc)[:1500]
    (directory / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='New evidence directory; never overwrite')
    args = parser.parse_args()
    result = smoke(args.output)
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
