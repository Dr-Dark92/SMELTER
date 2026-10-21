"""Deterministic driver accepts real MCP results, never model success prose."""
import json
import unittest
from smoke_ecc_coding import next_call, tool_results


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


if __name__ == '__main__':unittest.main()
