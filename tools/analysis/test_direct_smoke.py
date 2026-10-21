"""Exact-byte acceptance and retained evidence; no live model requests."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from smoke_direct_chat import acceptance, smoke, CONTENT
from chat_jobs import Control
from mcp_connections import sdk_status


def event(raw):
    return {'tool': 'write_diagnostic_markdown', 'executed': True, 'transport': 'mcp',
            'result': {'status': 'written', 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}}


class DirectSmokeTests(unittest.TestCase):
    def test_exact_bytes_and_matching_actual_receipt_are_required(self):
        raw = CONTENT.encode('utf-8')
        self.assertTrue(all(acceptance('completed', [event(raw)], raw).values()))
        for altered in (raw.rstrip(b'\n'), raw + b'\n', CONTENT.replace('\n', '\\n').encode(), b'"' + raw + b'"'):
            with self.subTest(altered=altered):
                checks = acceptance('completed', [event(altered)], altered)
                self.assertFalse(checks['exact_content'])
                self.assertTrue(checks['receipt_hash'])
                self.assertTrue(checks['receipt_bytes'])

    def test_correct_content_does_not_hide_bad_receipt_or_missing_execution(self):
        raw = CONTENT.encode()
        wrong = event(raw)
        wrong['result']['sha256'] = '0' * 64
        self.assertFalse(acceptance('completed', [wrong], raw)['receipt_hash'])
        wrong = event(raw)
        wrong['result']['bytes'] += 1
        self.assertFalse(acceptance('completed', [wrong], raw)['receipt_bytes'])
        wrong = event(raw)
        wrong['executed'] = False
        self.assertFalse(acceptance('completed', [wrong], raw)['one_approved_mcp_write'])
        self.assertFalse(acceptance('completed', [event(raw)], None)['file_present'])
        self.assertFalse(acceptance('error', [event(raw)], raw)['model_completed'])
        self.assertFalse(acceptance('completed', [event(raw), event(raw)], raw)['one_approved_mcp_write'])

    @unittest.skipUnless(sdk_status()['status'] == 'installed', 'Pinned MCP SDK required')
    def test_real_mcp_wrong_model_argument_is_retained_and_still_fails(self):
        self.exercise(CONTENT.rstrip('\n'), 'FAIL')

    @unittest.skipUnless(sdk_status()['status'] == 'installed', 'Pinned MCP SDK required')
    def test_real_mcp_exact_model_argument_passes(self):
        self.exercise(CONTENT, 'PASS')

    def exercise(self, content, expected_status):
        requests = []
        control = Control()
        def infer(body, timeout, maximum):
            requests.append(body)
            if any(message['role'] == 'tool' for message in body['messages']):
                message = {'role': 'assistant', 'content': 'Synthetic final answer.'}
            else:
                message = {'role': 'assistant', 'content': '', 'tool_calls': [{'function': {
                    'name': 'write_diagnostic_markdown', 'arguments': {'filename': 'direct-smoke.md', 'content': content}}}]}
            return json.dumps({'message': message, 'done_reason': 'stop'}).encode()
        control.infer = infer
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / 'evidence'
            result = smoke(destination, control=control)
            self.assertEqual(result['status'], expected_status)
            self.assertFalse(result['live_qwen'])
            self.assertEqual(result['controller_calls'], 1)
            self.assertEqual((destination / 'direct-smoke.md').read_bytes(), content.encode())
            self.assertEqual(result['observed']['bytes'], len(content.encode()))
            self.assertTrue(result['checks']['receipt_hash'])
            self.assertTrue((destination / 'chat-evidence.json').is_file())
            self.assertTrue(list((destination / 'tool-runs').glob('*.jsonl')))
            self.assertEqual(len(requests), 2)
            self.assertEqual(result.get('failed_checks'), ['exact_content'] if expected_status == 'FAIL' else None)


if __name__ == '__main__':
    unittest.main()
