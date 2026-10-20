import io
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from chat_jobs import Control, Jobs, ChatCancelled, _ResponseSocket
from chat_inference import ask
from chats import create_chat, read_chat
from database import select_database


class ChatJobsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / 'checkout'
        self.root.mkdir()
        select_database(self.root, str(Path(temp.name) / 'data'))
        self.cid = create_chat(self.root, 'Job fixture')['id']

    def test_stream_assembly_and_actual_socket_cancellation(self):
        ready, release = threading.Event(), threading.Event()
        headers_read, sockets = threading.Event(), []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"message":{"content":"Hello"},"done":false}\n')
                self.wfile.flush()
                ready.set()
                release.wait(3)
                try:
                    self.wfile.write(b'{"message":{"content":" world"},"done":true}\n')
                except OSError:
                    pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        import http.client
        real_connection = http.client.HTTPConnection
        class Connection(real_connection):
            def getresponse(self):
                original = self.sock
                response = super().getresponse()
                sockets.append(original)
                headers_read.set()
                return response
        connect = lambda *a, **kw: Connection('127.0.0.1', server.server_port, timeout=3)
        control, finished, errors = Control(), threading.Event(), []
        def run():
            try:
                control.infer({'model': 'fixture'}, 3, 10000)
            except (ChatCancelled, OSError) as exc:
                errors.append(exc)
            finally:
                finished.set()
        with patch('chat_jobs.http.client.HTTPConnection', side_effect=connect):
            thread = threading.Thread(target=run, daemon=True)
            thread.start()
            self.addCleanup(release.set)
            self.assertTrue(ready.wait(2))
            self.assertTrue(headers_read.wait(2))
            # The cancellation handle must survive HTTPConnection releasing its
            # original socket for this HTTP/1.0 connection-close response.
            self.assertIsNot(control.sock, sockets[0])
            self.assertGreaterEqual(control.sock.fileno(), 0)
            # Windows may leave a timed read waiting after shutdown. Reproduce
            # that condition on every platform: cancellation must poll itself.
            with patch('chat_jobs.socket.socket.shutdown', return_value=None):
                control.cancel()
                self.assertTrue(finished.wait(2), 'Stop must unblock the active socket read')
            release.set()
            thread.join(2)
            self.assertTrue(errors)
            # An independent request still works after cancellation.
            response = json.loads(Control().infer({'model': 'fixture'}, 3, 10000))
            self.assertEqual(response['message']['content'], 'Hello world')

    def test_cancel_preserves_completed_tool_receipts_and_skips_next_tool(self):
        control = Control()
        calls = [{'function': {'name': 'write_diagnostic_markdown', 'arguments': {'filename': name, 'content': '# fixture'}}}
                 for name in ('first.md', 'second.md')]
        response = json.dumps({'message': {'content': '', 'tool_calls': calls}}).encode()
        from python_tools import ToolSession
        real_execute = ToolSession.execute
        def execute(session, call):
            result = real_execute(session, call)
            control.cancel()
            return result
        with patch.object(control, 'infer', return_value=response), patch.object(ToolSession, 'execute', execute):
            result = ask(self.root, self.cid, 'Write fixtures', tool_permissions={'write_diagnostics': True}, control=control)
        self.assertTrue((self.root / 'diagnostics/first.md').exists())
        self.assertFalse((self.root / 'diagnostics/second.md').exists())
        self.assertIn('Request stopped', result['reply'])
        self.assertIn('SHA256', result['reply'])
        self.assertEqual(len(read_chat(self.root, self.cid)['messages']), 2)

    def test_jobs_reject_overlap_and_stop_cooperatively(self):
        jobs, entered, release, done = Jobs(), threading.Event(), threading.Event(), threading.Event()
        def worker(*a, control, **kw):
            entered.set()
            release.wait(2)
            try:
                control.check()
            finally:
                done.set()
        job = jobs.start(self.root, {'id': self.cid, 'content': 'fixture'}, worker)
        self.assertTrue(entered.wait(1))
        with self.assertRaises(ValueError):
            jobs.start(self.root, {'id': self.cid, 'content': 'duplicate'}, worker)
        jobs.cancel(job['id'])
        release.set()
        self.assertTrue(done.wait(2))
        self.assertTrue(jobs.jobs[job['id']]['control'].cancelled.is_set())

    def test_completed_request_cannot_be_cancelled_after_commit(self):
        control = Control()
        response = b'{"message":{"content":"Fixture reply"}}'
        with patch.object(control, 'infer', return_value=response):
            ask(self.root, self.cid, 'fixture', control=control)
        self.assertFalse(control.cancel())
        self.assertFalse(control.cancelled.is_set())

    def test_office_context_override(self):
        control = Control()
        with patch.dict('os.environ', {'SMELTER_CONTEXT_LENGTH': '16384'}), patch.object(control, 'infer', return_value=b'{"message":{"content":"fixture"}}') as infer:
            ask(self.root, self.cid, 'fixture', tool_permissions={'write_diagnostics': True}, control=control)
        self.assertEqual(infer.call_args.args[0]['options']['num_ctx'], 16384)

    def test_fragmented_chunked_response_survives_idle_read_intervals(self):
        import http.client
        import socket
        import time
        reader, writer = socket.socketpair()
        self.addCleanup(reader.close)
        self.addCleanup(writer.close)
        payload = '{"message":{"content":"Hello 🌍"},"done":true}\n'.encode()
        wire = b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n' + format(len(payload), 'x').encode() + b'\r\n' + payload + b'\r\n0\r\n\r\n'
        def send():
            try:
                # Delays exceed the raw-read polling interval, including in a
                # partial status line and in the middle of a UTF-8 character.
                split = wire.index('🌍'.encode()) + 1
                for part in (wire[:10], wire[10:split], wire[split:]):
                    writer.sendall(part)
                    time.sleep(0.3)
            except OSError:
                pass
        thread = threading.Thread(target=send, daemon=True)
        thread.start()
        response = http.client.HTTPResponse(_ResponseSocket(reader, Control(), time.monotonic() + 3))
        self.addCleanup(response.close)
        response.begin()
        self.assertEqual(response.read(), payload)
        thread.join(2)

    def test_response_headers_can_be_cancelled_without_socket_shutdown(self):
        import http.client
        import socket
        import time
        reader, writer = socket.socketpair()
        self.addCleanup(reader.close)
        self.addCleanup(writer.close)
        control = Control()
        response = http.client.HTTPResponse(_ResponseSocket(reader, control, time.monotonic() + 3))
        self.addCleanup(response.close)
        timer = threading.Timer(0.1, control.cancel)
        self.addCleanup(timer.cancel)
        timer.start()
        with self.assertRaises(ChatCancelled):
            response.begin()

    def test_stream_tool_batch_uses_controller_budget_and_rejects_excess(self):
        import http.client
        count = [6]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200)
                self.end_headers()
                # Calls arrive across multiple stream messages; the limit must
                # apply to the accumulated batch, not to each individual line.
                for _ in range(count[0]):
                    self.wfile.write(b'{"message":{"tool_calls":[{"function":{"name":"read_frontend_file","arguments":{}}}]},"done":false}\n')
                self.wfile.write(b'{"message":{},"done":true}\n')
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        real_connection = http.client.HTTPConnection
        connect = lambda *a, **kw: real_connection('127.0.0.1', server.server_port, timeout=3)
        with patch('chat_jobs.http.client.HTTPConnection', side_effect=connect):
            for limit, amount, allowed in ((4,6,False),(24,6,True),(5,6,False),(24,25,False)):
                with self.subTest(limit=limit, amount=amount):
                    count[0] = amount
                    control = Control()
                    control.tool_call_limit = limit
                    if allowed:
                        result = json.loads(control.infer({'model':'fixture'}, 3, 20000))
                        self.assertEqual(len(result['message']['tool_calls']), amount)
                    else:
                        with self.assertRaisesRegex(ValueError, 'Excessive'):
                            control.infer({'model':'fixture'}, 3, 20000)
