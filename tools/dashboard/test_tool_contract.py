"""Transport budgets and authoritative failure classification for mod tools."""
import unittest
from tool_contract import operation_timeout, result_failed, BRIDGE_RELAY_HEADROOM, BRIDGE_RPC_TIMEOUT


class ModToolContractTests(unittest.TestCase):
    def test_native_build_failure_is_not_a_successful_mcp_result(self):
        self.assertTrue(result_failed({'status': 'native_build_failed'}))
        self.assertFalse(result_failed({'status': 'native_build_succeeded'}))

    def test_long_operations_fit_both_transport_envelopes(self):
        for name in ('build_native_mod', 'run_coding_tests'):
            budget = operation_timeout(name)
            self.assertGreater(budget, 200)
            self.assertLess(budget + BRIDGE_RELAY_HEADROOM, BRIDGE_RPC_TIMEOUT)
            self.assertLessEqual(budget + BRIDGE_RELAY_HEADROOM, 440)

    def test_expected_red_remains_evidence(self):
        self.assertFalse(result_failed({'status': 'coding_tests_failed', 'stage': 'RED'}))
        self.assertTrue(result_failed({'status': 'coding_tests_failed', 'stage': 'ERROR'}))
