import hashlib
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import patch

from access_policy import Policy, using
import native_progress as progress
import test_workspace_tracking

SID = 'ses_progress_fixture'


def event(kind, **props):
    return {'type': kind, 'properties': {'sessionID': SID, **props}}


class Metadata:
    def __init__(self, directory): self.directory = directory
    def get(self, path):
        if path == '/session':
            return [{'id': SID, 'directory': self.directory, 'time': {'updated': 1}}]
        return {'id': SID, 'directory': self.directory}


class NativeProgressTests(unittest.TestCase):
    def setUp(self):
        test_workspace_tracking.WorkspaceTrackingTests.setUp(self)
        self.native = Path(self.tmp.name) / 'MeltyProject'; self.native.mkdir()
        self.bridge = progress.Bridge(self.root, Metadata, activity=None)
        with patch.object(self.bridge, '_start'):
            self.bridge.bind({'session_id': SID, 'directory': str(self.native), 'workspace_id': self.sid,
                              'expected_revision': self.bridge.view()['configuration_revision']})
        self.addCleanup(self.bridge.close)

    def tool(self, phase='running', **extra):
        return event('message.part.updated', part={'type': 'tool', 'sessionID': SID,
            'callID': 'call_fixture', 'tool': 'smelter_run_coding_tests', 'state': {'status': phase, **extra}})

    def test_normalizer_discards_reasoning_arguments_results_errors_and_other_sessions(self):
        private = 'private-reasoning-and-credential-fixture'
        tool = self.tool('error', input={'token': private}, output=private, error=private, metadata={'private': private})
        normalized = progress.normalize(tool, SID)
        self.assertEqual(normalized['phase'], 'failed')
        self.assertNotIn(private, json.dumps(normalized))
        for value in (event('message.part.updated', part={'type': 'reasoning', 'text': private}),
                      event('session.next.reasoning.delta', delta=private),
                      event('message.part.delta', field='reasoning', delta=private),
                      {'type': 'session.status', 'properties': {'sessionID': 'ses_other', 'status': {'type': 'busy'}}}):
            self.assertIsNone(progress.normalize(value, SID))
        self.bridge.ingest(tool)
        self.assertNotIn(private, progress._path(self.root).read_text())

    def test_semantic_dedup_handles_both_native_tool_event_versions(self):
        self.assertTrue(self.bridge.ingest(self.tool()))
        self.assertFalse(self.bridge.ingest(event('session.next.tool.called', callID='call_fixture', tool='smelter_run_coding_tests', input={'private': 'excluded'})))
        self.assertTrue(self.bridge.ingest(event('session.next.tool.success', callID='call_fixture', content=[{'text': 'excluded'}])))
        self.assertFalse(self.bridge.ingest(self.tool('completed')))
        value = self.bridge.view()
        self.assertEqual([x['phase'] for x in value['events']], ['running', 'completed'])
        self.assertEqual(value['events'][-1]['tool'], 'smelter_run_coding_tests')

    def test_initial_idle_is_not_completion_and_native_idle_never_claims_test_success(self):
        self.bridge.ingest(event('session.idle')); self.bridge.finish_pending()
        self.assertEqual(self.bridge.view()['completions'], [])
        self.bridge.ingest(self.tool())
        self.bridge.ingest(event('session.idle')); self.bridge.finish_pending()
        value = self.bridge.view()
        self.assertEqual(len(value['completions']), 1)
        snapshot = value['completions'][0]
        self.assertEqual(snapshot['phase'], 'idle')
        self.assertIn('not a test pass', snapshot['verification'])
        self.assertEqual(snapshot['workspace_tracking']['workspace_id'], self.sid)
        self.assertTrue(snapshot['workspace_tracking']['graph']['nodes'])
        self.assertFalse(self.bridge.ingest(event('session.idle')))
        self.bridge.finish_pending(); self.assertEqual(len(self.bridge.view()['completions']), 1)

    def test_observed_cancelled_error_creates_a_cancelled_snapshot_without_error_body(self):
        self.bridge.ingest(event('session.error', error={'name': 'MessageAbortedError', 'message': 'private'}))
        self.bridge.finish_pending()
        self.assertEqual(self.bridge.view()['completions'][0]['phase'], 'cancelled')
        self.assertNotIn('private', progress._path(self.root).read_text())

    def test_persisted_identity_and_gap_survive_process_restart(self):
        self.bridge.ingest(self.tool())
        reloaded = progress.Bridge(self.root, Metadata, activity=None)
        self.assertEqual(reloaded.view()['binding'], self.bridge.view()['binding'])
        self.assertTrue(reloaded.view()['gap'])
        self.assertEqual(reloaded.view()['connection'], 'stopped')
        self.assertFalse(reloaded.ingest(self.tool()))

    def test_a_fresh_task_on_a_healthy_stream_has_its_own_gap_assessment(self):
        self.bridge.value['connection'] = 'connected'
        self.bridge.value['gap'] = True
        self.bridge.ingest(event('session.status', status={'type': 'busy'}))
        self.assertFalse(self.bridge.view()['gap'])
        self.bridge.ingest(event('session.idle')); self.bridge.finish_pending()
        self.assertFalse(self.bridge.view()['completions'][0]['gap'])

    def test_binding_rejects_stale_revision_wrong_directory_and_unknown_workspace(self):
        data = {'session_id': SID, 'directory': str(self.native), 'workspace_id': self.sid,
                'expected_revision': 'stale'}
        with self.assertRaisesRegex(ValueError, 'binding changed'):
            self.bridge.bind(data)
        data['expected_revision'] = self.bridge.view()['configuration_revision']
        with patch.object(self.bridge, 'transport', return_value=Metadata(str(self.root))):
            with self.assertRaisesRegex(ValueError, 'does not match'):
                self.bridge.bind(data)
        data['workspace_id'] = '00000000-0000-0000-0000-000000000000'
        with self.assertRaises(ValueError): self.bridge.bind(data)

    def test_rebinding_archives_prior_activity_and_pause_does_not_control_native_task(self):
        self.bridge.ingest(self.tool())
        self.bridge.control('stop', self.bridge.view()['configuration_revision'])
        before = self.bridge.view()
        self.assertFalse(before['enabled']); self.assertEqual(before['task_state'], 'busy')
        with patch.object(self.bridge, '_start'):
            self.bridge.bind({'session_id': SID, 'directory': str(self.native), 'workspace_id': self.sid,
                              'expected_revision': before['configuration_revision']})
        archives = list((progress._path(self.root).parent / 'archives').glob('*.json'))
        self.assertEqual(len(archives), 1)
        self.assertEqual(json.loads(archives[0].read_text())['events'][0]['phase'], 'running')

    def test_archive_cap_is_cleared_only_by_a_verified_export(self):
        folder = progress._path(self.root).parent / 'archives'; folder.mkdir(parents=True)
        for i in range(10): (folder / f'{i:032x}.json').write_text(json.dumps({'n': i}))
        self.bridge.ingest(self.tool())
        data = lambda: {'session_id': SID, 'directory': str(self.native), 'workspace_id': self.sid,
                        'expected_revision': self.bridge.view()['configuration_revision']}
        with patch.object(self.bridge, '_start'):
            with self.assertRaisesRegex(ValueError, 'export_native_archives'):
                self.bridge.bind(data())
            result = progress.export_archives(self.root)
            self.assertEqual(result['count'], 10); self.assertEqual(list(folder.glob('*.json')), [])
            manifest = json.loads((Path(result['folder']) / 'manifest.json').read_text())
            for row in manifest['files']:
                self.assertEqual(hashlib.sha256((Path(result['folder']) / row['name']).read_bytes()).hexdigest(), row['sha256'])
            self.bridge.bind(data())
        self.assertEqual(len(list(folder.glob('*.json'))), 1)
        self.assertIsNone(progress.export_archives(Path(self.tmp.name) / 'empty'))

    def test_chart_permissions_are_rechecked_after_access_is_narrowed(self):
        self.bridge.ingest(self.tool()); self.bridge.ingest(event('session.idle')); self.bridge.finish_pending()
        policy = json.loads(json.dumps(self.policy.value))
        row = next(row for row in policy['locations'] if Path(row['path']).resolve() == self.target.parent.parent.resolve())
        row['exclusions'].append('coding/'+self.sid+'/mods/demo/tests/test_controller.lua')
        with patch('access_policy.current', return_value=Policy(policy)):
            value = self.bridge.view()
        self.assertNotIn('test_controller.lua', value['completions'][0]['workspace_tracking']['mermaid'])

    def test_failed_index_does_not_hide_native_completion(self):
        self.bridge.ingest(self.tool()); self.bridge.ingest(event('session.idle'))
        with patch('coding_workspace.context', side_effect=OSError('private error body')):
            self.bridge.finish_pending()
        value = self.bridge.view()
        self.assertEqual(value['completions'][0]['phase'], 'idle')
        self.assertEqual(value['completions'][0]['snapshot_error'], 'Workspace snapshot unavailable (OSError)')

    def test_retention_protects_native_bindings_and_archived_charts(self):
        import os
        from uuid import uuid4
        from database import select_database
        from maintenance import plan
        select_database(self.root, str(Path(self.tmp.name) / 'data'))
        path = progress._path(self.root).parent / (str(uuid4())+'.json')
        path.write_text('{}'); os.utime(path, (1, 1))
        self.assertNotIn('native-progress', [row['area'] for row in plan(self.root, 1)['entries']])

    def test_sse_framing_comments_multiline_ids_and_bound(self):
        stopped = threading.Event()
        response = io.BytesIO(b': heartbeat\n\nid: evt_fixture\ndata: {"type": "session.idle",\ndata: "properties": {"sessionID": "ses_progress_fixture"}}\n\n')
        values = list(progress.frames(response, stopped))
        self.assertEqual(values[0][0], 'evt_fixture')
        self.assertEqual(values[0][1]['type'], 'session.idle')
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            list(progress.frames(io.BytesIO(b'data: '+b'x'*(progress.MAX_FRAME+1)), stopped))

    def test_transport_rejects_prompt_control_routes_and_redirects(self):
        client = progress.Transport(str(self.native))
        for path in ('/session/'+SID+'/prompt_async', '/session/'+SID+'/abort', '/config', 'https://other.example'):
            with self.assertRaises(ValueError): client.get(path)
        self.assertIsNone(progress.NoRedirect().redirect_request(None, None, 302, '', {}, 'http://example.com'))

    def test_http_stream_reconnect_reconciles_idle_and_only_performs_gets(self):
        requests = []; attempts = []
        native = str(self.native)
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_GET(self):
                requests.append(('GET', self.path.split('?')[0]))
                path = self.path.split('?')[0]
                if path == '/event':
                    attempts.append(True)
                    payload = (b'data: '+json.dumps(event('session.next.tool.called', callID='call_live', tool='smelter_read_coding_file')).encode()+b'\n\n') if len(attempts)==1 else b': heartbeat\n\n'
                    content_type = 'text/event-stream'
                else:
                    payload = json.dumps(({SID: {'type': 'busy'}} if len(attempts)==1 else {}) if path=='/session/status' else {'id': SID, 'directory': native}).encode()
                    content_type = 'application/json'
                self.send_response(200); self.send_header('Content-Type', content_type); self.send_header('Content-Length', str(len(payload))); self.end_headers(); self.wfile.write(payload)
        server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
        threading.Thread(target=server.serve_forever,daemon=True).start()
        live = progress.Bridge(self.root, activity=None)
        try:
            with patch.object(progress,'BASE','http://127.0.0.1:'+str(server.server_port)):
                live.bind({'session_id': SID, 'directory': native, 'workspace_id': self.sid,
                           'expected_revision': live.view()['configuration_revision']})
                deadline=time.monotonic()+8
                while time.monotonic()<deadline and not live.view()['completions']: time.sleep(.05)
                value=live.view()
                self.assertTrue(value['completions'], value['connection'])
                self.assertTrue(value['completions'][0]['gap'])
                self.assertTrue(all(method=='GET' for method,_ in requests))
                self.assertTrue(all(path in ('/event','/session/status','/session/'+SID) for _,path in requests))
                live.close(); live.thread.join(3)
        finally:
            live.close(); server.shutdown(); server.server_close()


if __name__ == '__main__': unittest.main()
