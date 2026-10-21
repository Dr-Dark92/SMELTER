"""Deterministic driver accepts real MCP results, never model success prose."""
import json
import hashlib
from pathlib import Path
from types import SimpleNamespace
import tempfile
from unittest.mock import patch
import smoke_ecc_coding as coding_smoke
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

    def test_live_prompt_discloses_the_byte_exact_outputs_before_inference(self):
        """The model must receive the same file contract used by acceptance."""
        reference = '# Synthetic instruction fixture\n'
        with tempfile.TemporaryDirectory() as temporary:
            manifest = Path(temporary) / 'SKILL.md'
            manifest.write_bytes(reference.encode('utf-8'))
            args = SimpleNamespace(skill_manifest=str(manifest), evidence_dir=None,
                                   image='sha256:' + 'a' * 64,
                                   python_image='sha256:' + 'b' * 64, live=True)
            with patch.object(coding_smoke, 'EXPECTED_SKILL', hashlib.sha256(reference.encode()).hexdigest()), \
                 patch.object(coding_smoke, 'AgentBridge'), \
                 patch.object(coding_smoke, 'ask', side_effect=RuntimeError('intercepted before inference')) as ask:
                with self.assertRaisesRegex(RuntimeError, 'intercepted before inference'):
                    coding_smoke.run(args)
            self.assertEqual(ask.call_count, 1)
            prompt = ask.call_args.args[2]
            contract = prompt.split('Exact expected UTF-8 file contents (JSON):\n', 1)[1].split('\n', 1)[0]
            self.assertEqual(json.loads(contract), {
                'tools/dashboard/test_example.py': coding_smoke.TEST,
                'tools/dashboard/example.py': coding_smoke.AFTER})
            self.assertIn('unchanged until actual RED is recorded', prompt)
            self.assertTrue(ask.call_args.kwargs['agent_mode'])
            self.assertEqual(ask.call_args.kwargs['model_key'], 'local/qwen3.5:9b')

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
