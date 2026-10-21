"""R01-R07 regressions: disposable files/HTTP only, no live inference or Docker."""
import io
import json
import os
import tempfile
import threading
import time
import unittest
from contextlib import ExitStack
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from access_policy import Policy, defaults, using
from chat_inference import ask
from chat_jobs import Control, Jobs
from chats import create_chat, read_chat
from database import select_database
from frontend_workspace import prepare, _source_files
from python_tools import ToolSession
from task_contract import OUTPUT_LIMIT_ERROR

class OverhaulRepairs(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.root = self.base / 'SMELTER'
        self.root.mkdir()
        select_database(self.root, str(self.base / 'data'))
        self.cid = create_chat(self.root, 'Repair fixture')['id']

    def source(self):
        folder = self.root / 'tools/dashboard'
        folder.mkdir(parents=True)
        (folder / 'dashboard.py').write_text('HTML="<style>body{}</style>"', encoding='utf-8')
        (self.root / 'README.md').write_text('Private fixture README', encoding='utf-8')

    def test_report_final_path_and_suffix_denials_in_both_transports(self):
        from mcp_connections import sdk_status
        transports = ['python'] + (['mcp'] if sdk_status()['status'] == 'installed' else [])
        folder = self.root / 'diagnostics'; folder.mkdir()
        (folder / 'allowed.md').write_text('existing', encoding='utf-8')
        value = defaults(self.root); value['locations'][2]['exclusions'] = ['blocked*.md', 'allowed_01.md']
        for transport in transports:
            for name in ['blocked-report.md', 'allowed.md']:
                with self.subTest(transport=transport, name=name):
                    session = ToolSession(self.root, {'write_diagnostics':True, 'transport':transport}, self.cid, policy=Policy(value))
                    result = session.execute({'function':{'name':'write_diagnostic_markdown','arguments':{'filename':name,'content':'Denied fixture'}}})
                    self.assertEqual(result['status'], 'error')
                    self.assertIn('Access denied', result['error'])
        self.assertFalse((folder / 'blocked-report.md').exists())
        self.assertFalse((folder / 'allowed_01.md').exists())
        self.assertEqual((folder / 'allowed.md').read_text(encoding='utf-8'), 'existing')

    def test_denied_readme_cannot_enter_workspace_copy(self):
        self.source(); value = defaults(self.root)
        value['locations'][0]['exclusions'].append('README.md')
        with using(Policy(value)), self.assertRaisesRegex(ValueError, 'Access denied'):
            _source_files(self.root)
        self.assertFalse(self.root.with_name('SMELTERV2').exists())

    def test_preparation_failure_rolls_back_its_own_data_then_retries(self):
        self.source(); original = Path.write_text
        def fail_marker(path, *args, **kwargs):
            if path.name == 'frontend-workspace.json':
                raise OSError('Injected marker failure')
            return original(path, *args, **kwargs)
        with using(Policy(defaults(self.root))), patch.object(Path, 'write_text', fail_marker):
            with self.assertRaisesRegex(OSError, 'Injected'):
                prepare(self.root, {})
        self.assertFalse(self.root.with_name('SMELTERV2').exists())
        self.assertFalse(self.root.with_name('SMELTERV2-Data').exists())
        with using(Policy(defaults(self.root))):
            self.assertEqual(prepare(self.root, {})['status'], 'workspace_ready')

    def test_preexisting_data_is_never_rollback_owned(self):
        self.source(); data = self.root.with_name('SMELTERV2-Data')
        data.mkdir(); (data / 'keep.txt').write_text('keep', encoding='utf-8')
        with using(Policy(defaults(self.root))), self.assertRaisesRegex(ValueError, 'already exists'):
            prepare(self.root, {})
        self.assertEqual((data / 'keep.txt').read_text(encoding='utf-8'), 'keep')
        self.assertFalse(self.root.with_name('SMELTERV2').exists())

    def test_direct_length_is_persisted_as_partial_without_tool_execution(self):
        response = {'message':{'content':'Partial fixture text','tool_calls':[{'function':{'name':'write_diagnostic_markdown','arguments':{'filename':'must-not-write.md','content':'x'}}}]}, 'done_reason':'length'}
        result = ask(self.root, self.cid, 'Fixture', tool_permissions={'write_diagnostics':True}, opener=lambda *a,**k:io.BytesIO(json.dumps(response).encode()))
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['error'], OUTPUT_LIMIT_ERROR)
        self.assertFalse(result['tools_executed'])
        self.assertFalse((self.root / 'diagnostics/must-not-write.md').exists())
        self.assertEqual(read_chat(self.root, self.cid)['messages'][-1]['execution']['outcome'], 'partial')

    def test_opencode_length_finishes_immediately_as_partial(self):
        from opencode_runtime import ask as agent_ask
        from test_opencode_runtime import Fixture
        target = self.root.with_name('SMELTERV2'); target.mkdir()
        client = Fixture(target)
        client.frames = [[{'info':{'role':'assistant','finish':'length','time':{'completed':1}},'parts':[{'type':'text','text':'Partial agent text'}]}]]
        result = agent_ask(self.root, self.cid, 'Fixture', approval=True, model_key='local/qwen3.5:9b', client=client)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['error'], OUTPUT_LIMIT_ERROR)
        self.assertEqual(sum(path.endswith('/message?limit=50') for path,_,_ in client.calls), 1)
        self.assertFalse(any(path.endswith('/abort') for path,_,_ in client.calls))

    def stream_server(self, packets):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args): pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200); self.end_headers()
                for packet in packets:
                    self.wfile.write(json.dumps(packet).encode() + b'\n')
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        self.addCleanup(thread.join, 3); self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        return server

    def test_stream_packet_shapes_raise_protocol_errors(self):
        for packet in [[], None, 1, {'done':'false'}, {'done':True,'done_reason':[]}, {'message':[]}]:
            with self.subTest(packet=packet):
                server = self.stream_server([packet])
                with patch('chat_jobs.http.client.HTTPConnection', side_effect=lambda *a,**k:HTTPConnection('127.0.0.1', server.server_port, timeout=2)):
                    with self.assertRaises(ValueError):
                        Control().infer({'model':'fixture'}, 2, 4096)

    def test_malformed_followup_keeps_completed_action_in_transcript(self):
        server = self.stream_server([[]])
        control = Control(); actual = control.infer; calls = []
        def infer(body, timeout, maximum):
            calls.append(body)
            if len(calls) == 1:
                return json.dumps({'message':{'content':'','tool_calls':[{'function':{'name':'write_diagnostic_markdown','arguments':{'filename':'saved.md','content':'Actual fixture bytes'}}}]},'done_reason':'stop'}).encode()
            return actual(body, timeout, maximum)
        with patch.object(control, 'infer', side_effect=infer), patch('chat_jobs.http.client.HTTPConnection', side_effect=lambda *a,**k:HTTPConnection('127.0.0.1', server.server_port, timeout=2)):
            result = ask(self.root, self.cid, 'Fixture report', tool_permissions={'write_diagnostics':True}, control=control)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual((self.root / 'diagnostics/saved.md').read_text(encoding='utf-8'), 'Actual fixture bytes')
        messages = read_chat(self.root, self.cid)['messages']
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[-1]['execution']['events'][0]['result']['status'], 'written')

    def test_partial_text_survives_protocol_failure_without_tools(self):
        server = self.stream_server([{'message':{'content':'Observed partial text'},'done':False}, []])
        with patch('chat_jobs.http.client.HTTPConnection', side_effect=lambda *a,**k:HTTPConnection('127.0.0.1', server.server_port, timeout=2)):
            result = ask(self.root, self.cid, 'Fixture text', control=Control())
        self.assertEqual(result['status'], 'partial')
        self.assertFalse(result['tools_executed'])
        messages = read_chat(self.root, self.cid)['messages']
        self.assertEqual(len(messages), 2)
        self.assertIn('Observed partial text', messages[-1]['content'])
        self.assertEqual(messages[-1]['execution']['outcome'], 'partial')

    @unittest.skipIf(os.name == 'nt', 'Case-distinct directory fixture is Linux-specific')
    def test_linux_case_distinct_locations(self):
        value = defaults(self.root)
        first = self.base / 'Case'; second = self.base / 'case'
        first.mkdir(); second.mkdir()
        if first.samefile(second): self.skipTest('Filesystem is case-insensitive')
        value['locations'] = [{**value['locations'][0], 'id':'upper', 'path':str(first)}, {**value['locations'][0], 'id':'lower', 'path':str(second)}]
        self.assertEqual(len(Policy(value).value['locations']), 2)

    def test_resolved_duplicate_locations_still_rejected(self):
        value = defaults(self.root)
        value['locations'].append({**value['locations'][0], 'id':'duplicate'})
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            Policy(value)

    def test_stop_http_bypasses_long_probe_and_global_state_lock(self):
        import dashboard
        jobs = Jobs(); finish = threading.Event(); entered = threading.Event(); release = threading.Event()
        def worker(*args, **kwargs):
            finish.wait(5); kwargs['control'].check(); return {'status':'completed'}
        job = jobs.start(self.root, {'id':self.cid,'content':'Fixture'}, worker=worker)
        def probe(*args, **kwargs):
            entered.set(); release.wait(4); return {'status':'fixture'}
        with ExitStack() as stack:
            for name,value in [('ROOT',self.root),('JOBS',jobs),('mcp_exchange',probe),('validate_tool_permissions',lambda *a:{})]:
                stack.enter_context(patch.object(dashboard, name, value))
            server = ThreadingHTTPServer(('127.0.0.1',0), dashboard.handler('fixture-token'))
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            def post(path, body):
                connection = HTTPConnection('127.0.0.1',server.server_port,timeout=5)
                try:
                    connection.request('POST',path,json.dumps(body),{'Content-Type':'application/json','X-Smelter-Token':'fixture-token'})
                    response=connection.getresponse(); status=response.status; response.read(); return status
                finally: connection.close()
            errors = []
            def probing():
                try: post('/api/mcp', {'action':'probe','server':'smelter','permissions':{}})
                except Exception as exc: errors.append(exc)
            probing_thread=threading.Thread(target=probing); probing_thread.start()
            try:
                self.assertTrue(entered.wait(2))
                # A different operator mutation holding the configuration lock
                # must not serialize delivery of Stop.
                with dashboard.STATE_LOCK:
                    self.assertEqual(post('/api/chats',{'action':'stop','job_id':job['id']}),200)
                self.assertTrue(jobs.jobs[job['id']]['control'].cancelled.is_set())
                self.assertFalse(release.is_set())
            finally:
                release.set(); finish.set(); probing_thread.join(5)
                deadline=time.monotonic()+3
                while jobs.jobs[job['id']]['state']=='running' and time.monotonic()<deadline:time.sleep(.01)
                server.shutdown(); server.server_close(); thread.join(3)
            self.assertEqual(errors, [])
