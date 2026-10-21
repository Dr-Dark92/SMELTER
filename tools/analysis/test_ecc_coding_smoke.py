"""Deterministic driver accepts real MCP results, never model success prose."""
import json
import http.client
import http.server
import threading
import unittest
from smoke_ecc_coding import next_call, tool_results
from smoke_agent_bridge import port_free


class EccCodingFixtureTests(unittest.TestCase):
    def test_decodes_text_and_list_mcp_envelopes(self):
        result = {'status': 'coding_tests_failed', 'stage': 'RED'}
        encoded = json.dumps({'tool_result': result})
        messages = [{'role': 'assistant', 'content': 'Everything passed'},
                    {'role': 'tool', 'content': [{'type': 'text', 'text': encoded}]}]
        self.assertEqual(tool_results(messages), [result])

    def test_implementation_is_blocked_without_actual_red(self):
        results = [{'workspace_id': 'recorded-id'}, {'sha256': 'actual-hash'}, {}, {}, {'stage': 'ERROR'}]
        with self.assertRaisesRegex(ValueError, 'assertion failure'):
            next_call(results)
        results[-1]['stage'] = 'RED'
        name, arguments = next_call(results)
        self.assertEqual(name, 'propose_coding_patch')
        self.assertEqual(arguments['changes'][0]['expected_sha256'], 'actual-hash')

    def test_final_answer_requires_observed_current_green_review(self):
        with self.assertRaises(ValueError):
            next_call([{'workspace_id': 'id'}, {}, {}, {}, {'stage': 'RED'}, {}, {},
                       {'stage': 'GREEN'}, {'all_current_tests_passed': False}])
        self.assertIsNone(next_call([{'workspace_id': 'id'}, {}, {}, {}, {'stage': 'RED'}, {}, {},
                                    {'stage': 'GREEN'}, {'all_current_tests_passed': True}]))

    def test_consecutive_fixture_checks_reject_a_listener_and_allow_closed_server(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):
                self.send_response(200);self.send_header('Content-Length','2');self.end_headers();self.wfile.write(b'ok')
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        port=server.server_port
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with self.assertRaisesRegex(ValueError,'occupied'):port_free(port)
            client=http.client.HTTPConnection('127.0.0.1',port,timeout=2)
            try:client.request('GET','/');self.assertEqual(client.getresponse().read(),b'ok')
            finally:client.close()
        finally:server.shutdown();server.server_close();thread.join(timeout=2)
        port_free(port)


if __name__ == '__main__':unittest.main()
