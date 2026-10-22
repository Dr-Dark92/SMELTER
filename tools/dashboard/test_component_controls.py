import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace

import component_controls as cc
from database import select_database
from config_store import save_config, load_config


class ComponentControlsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'checkout'
        self.root.mkdir()
        select_database(self.root, str(Path(self.tmp.name) / 'data'))
        self.alive, self.loaded, self.calls = True, True, []
        self.process = None
        self.image = 'sha256:' + 'a' * 64
        save_config(self.root, 'sandbox.json', {'schema_version': 1, 'opencode_image': self.image,
                                                'python_image': None, 'node_image': None})
        from chat_jobs import JOBS
        self.fake_jobs = JOBS
        self.jobs_patch = patch.object(JOBS, 'jobs', {})
        self.jobs_patch.start()
        self.addCleanup(self.jobs_patch.stop)
        self.controls = cc.Components(self.root, request=self.request, finder=lambda name: '/native/' + name + '.exe',
                                      runner=self.runner, popen=self.launch)
        self.addCleanup(self.controls.close)

    def request(self, path, body=None, timeout=2):
        self.calls.append((path, body))
        if self.process is not None and self.process.poll() is not None:
            self.alive = False
        if not self.alive:
            raise OSError('No listener')
        if path == '/api/version': return {'version': '0.40.6'}
        if path == '/api/tags': return {'models': [{'name': 'qwen3.5:9b'}]}
        if path == '/api/ps': return {'models': [{'name': 'qwen3.5:9b'}] if self.loaded else []}
        if path == '/api/generate':
            self.loaded = body['keep_alive'] != 0
            return {'done': True}
        raise AssertionError(path)

    def runner(self, args, **kwargs):
        if 'context' in args: out = 'unix:///local/docker.sock'
        elif 'info' in args: out = json.dumps({'OSType': 'linux', 'ServerVersion': '29.8.2'})
        elif 'image' in args: out = self.image
        elif '--version' in args: out = 'v22.0.0'
        else: raise AssertionError(args)
        return subprocess.CompletedProcess(args, 0, out, '')

    def launch(self, args, **options):
        self.assertEqual(args, ['/native/ollama.exe', 'serve'])
        self.assertFalse(options['shell'])
        # A real owned sleeping child tests cleanup without binding an Ollama port.
        self.process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], **options)
        self.alive = True
        return self.process

    def rows(self):
        return {x['id']: x for x in self.controls.snapshot(True)['components']}

    def test_status_distinguishes_model_residency_provider_and_external_server(self):
        rows = self.rows()
        self.assertEqual(rows['ollama']['ownership'], 'external')
        self.assertFalse(rows['ollama']['actions']['stop']['enabled'])
        self.assertEqual(rows['qwen']['state'], 'loaded')
        self.assertEqual(rows['opencode']['state'], 'on_demand')
        self.assertIsNone(rows['opencode']['version'])  # An image ID is not a verified app version.
        self.assertFalse(rows['python']['actions']['start']['enabled'])
        self.assertIsNone(self.process)

    def test_external_process_is_never_stopped_or_restarted(self):
        for action in ('stop', 'restart'):
            with self.assertRaisesRegex(ValueError, 'started here'):
                self.controls.action('ollama', action)
        self.assertIsNone(self.process)
        self.assertFalse(any(path == '/api/generate' for path, body in self.calls))

    def test_owned_server_start_stop_reaps_real_child(self):
        self.alive = False
        self.controls.action('ollama', 'start')
        process = self.process
        self.assertIsNone(process.poll())
        self.assertTrue(self.controls.owned())
        self.controls.action('ollama', 'stop')
        self.assertIsNotNone(process.poll())
        self.assertFalse(self.controls.owned())

    def test_model_lifecycle_uses_empty_bounded_requests_and_verified_residency(self):
        self.controls.action('qwen', 'stop')
        self.assertFalse(self.loaded)
        self.controls.action('qwen', 'start')
        self.assertTrue(self.loaded)
        self.controls.action('qwen', 'reload')
        bodies = [body for path, body in self.calls if path == '/api/generate']
        self.assertEqual([body['keep_alive'] for body in bodies], [0, 300, 0, 300])
        self.assertTrue(all(body['model'] == 'qwen3.5:9b' and 'prompt' not in body and body['stream'] is False for body in bodies))

    def test_model_success_requires_actual_residency(self):
        original = self.controls.request
        self.controls.request = lambda path, body=None, **kwargs: {'done': True} if path == '/api/generate' else original(path, body, **kwargs)
        with self.assertRaisesRegex(ValueError, 'did not confirm'):
            self.controls.action('qwen', 'stop')

    def test_stop_flags_are_persisted_and_enforced_at_real_entry_points(self):
        self.controls.action('opencode', 'stop')
        self.controls.action('mcp', 'stop')
        self.assertFalse(cc.settings(self.root)['opencode'])
        self.assertFalse(cc.settings(self.root)['mcp'])
        from opencode_runtime import ask
        from mcp_connections import exchange
        with self.assertRaisesRegex(ValueError, 'stopped'):
            ask(self.root, 'unused', 'unused', approval=True)
        with self.assertRaisesRegex(ValueError, 'stopped'):
            exchange(self.root)
        self.assertEqual(self.rows()['opencode']['state'], 'disabled')
        with self.assertRaisesRegex(ValueError, 'mcp is stopped'):
            cc.check_admission(self.root, 'ollama', mcp_required=True)

    def test_probe_failure_restores_stopped_state(self):
        self.controls.action('opencode', 'stop')
        with patch('opencode_runtime.status', side_effect=ValueError('Probe failure')):
            with self.assertRaisesRegex(ValueError, 'Probe failure'):
                self.controls.action('opencode', 'start')
        self.assertFalse(cc.settings(self.root)['opencode'])
        self.assertFalse(self.controls.changing)

    def test_provider_start_verifies_then_closes_inspection_not_persistent_service(self):
        self.controls.action('mcp', 'stop')
        with patch('mcp_connections.exchange', return_value={'status': 'connected'}) as probe:
            result = self.controls.action('mcp', 'start')
        probe.assert_called_once_with(self.root, timeout=20)
        row = next(x for x in result['snapshot']['components'] if x['id'] == 'mcp')
        self.assertEqual(row['state'], 'on_demand')
        self.assertFalse(result['snapshot']['busy'])

    def test_active_job_blocks_mutation_and_changing_components_block_admission(self):
        self.fake_jobs.jobs['id'] = {'state': 'running'}
        with self.assertRaisesRegex(ValueError, 'active chat'):
            self.controls.action('qwen', 'stop')
        self.assertFalse(any(path == '/api/generate' for path, body in self.calls))
        self.controls.changing = True
        with patch.dict(cc._managers, {str(self.root.resolve()): self.controls}):
            with self.assertRaisesRegex(ValueError, 'in progress'):
                cc.check_admission(self.root, 'ollama')

    def test_fixed_schema_rejects_arbitrary_commands_and_invalid_flags(self):
        with self.assertRaises(ValueError): self.controls.action('ollama;cmd', 'start')
        with self.assertRaises(ValueError): self.controls.action('ollama', '--execute')
        with self.assertRaises(ValueError): self.controls.action('python', 'restart')
        with self.assertRaises(ValueError):
            save_config(self.root, cc.NAME, {'schema_version': 1, 'opencode': 'true', 'mcp': True})

    def test_stale_model_selection_is_rejected_before_loading(self):
        with self.assertRaisesRegex(ValueError, 'Selected model changed'):
            self.controls.action('qwen', 'reload', expected_model='other:9b')
        self.assertFalse(any(path == '/api/generate' for path, body in self.calls))
        events = (self.root / '.smelter/component-events.jsonl').read_text().splitlines()
        self.assertEqual(json.loads(events[-1])['status'], 'failed')

    def test_snapshot_cache_does_not_repeat_process_probes(self):
        first = self.controls.snapshot()
        calls = len(self.calls)
        self.assertIs(self.controls.snapshot(), first)
        self.assertEqual(len(self.calls), calls)

    def test_http_auth_and_operator_payload_boundary(self):
        import dashboard
        from http.server import ThreadingHTTPServer
        with patch.object(dashboard, 'ROOT', self.root), patch.object(dashboard, 'component_manager', return_value=self.controls):
            server = ThreadingHTTPServer(('127.0.0.1', 0), dashboard.handler('component-test-token'))
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                def post(body, authorized=True):
                    client = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
                    try:
                        client.request('POST', '/api/system/components', json.dumps(body),
                                       {'X-Smelter-Token': 'component-test-token' if authorized else 'wrong'})
                        response = client.getresponse()
                        return response.status, json.loads(response.read())
                    finally: client.close()
                self.assertEqual(post({'component': 'mcp', 'action': 'stop'}, False)[0], 403)
                self.assertTrue(cc.settings(self.root)['mcp'])
                self.assertEqual(post({'component': 'mcp', 'action': 'stop', 'command': 'arbitrary'})[0], 400)
                status, result = post({'component': 'mcp', 'action': 'stop'})
                self.assertEqual(status, 200)
                self.assertEqual(result['status'], 'completed')
                self.assertFalse(load_config(self.root, cc.NAME)['mcp'])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == '__main__':
    unittest.main()
