import json
import unittest
from unittest.mock import patch

import trace_history
import test_workspace_tracking


class TraceHistoryTests(unittest.TestCase):
    def setUp(self):
        test_workspace_tracking.WorkspaceTrackingTests.setUp(self)
        trace_history._last.clear()
        self.addCleanup(trace_history._last.clear)
        self.binding = {'session_id': 'ses_root', 'directory': str(self.root), 'workspace_id': self.sid}

    def snapshot(self, turn='msg_one', phase='using_tool', **extra):
        file = str(self.target / 'mods/demo/tests/fixture.hex')
        value = {'available': True, 'binding': self.binding, 'native_turn_id': turn, 'task_id': turn,
                 'task_id_source': 'Native OpenCode turn (Melty ID not supplied)', 'workspace_root': str(self.target),
                 'status': {'phase': phase, 'task_outcome': 'not_verified' if phase == 'completed' else 'in_progress'},
                 'sessions': [{'session_id': 'ses_root', 'state': phase}],
                 'tools': [{'session_id': 'ses_root', 'call_id': 'call_a', 'tool': 'read', 'phase': 'completed',
                            'file': file, 'indexed_sha256': 'a' * 64, 'index_updated_at': 't'}],
                 'permissions': [], 'validation': [], 'observed_at': '2026-10-27T00:00:00+00:00'}
        value.update(extra)
        return value

    def test_running_turn_is_not_saved_but_its_end_is_saved_once(self):
        self.assertIsNone(trace_history.observe(self.root, self.snapshot()))
        self.assertEqual(trace_history.view(self.root)['charts'], [])
        saved = trace_history.observe(self.root, self.snapshot(phase='completed'))
        self.assertEqual([c['reason'] for c in saved], ['response ended'])
        self.assertIsNone(trace_history.observe(self.root, self.snapshot(phase='completed')))
        charts = trace_history.view(self.root)['charts']
        self.assertEqual(len(charts), 1)
        self.assertEqual(charts[0]['trace']['status']['task_outcome'], 'not_verified')

    def test_later_validation_updates_the_same_turn_chart(self):
        trace_history.observe(self.root, self.snapshot(phase='completed'))
        receipt = [{'profile': 'lua', 'stage': 'RED', 'current': True, 'workspace_tests_stage': 'GREEN', 'acceptance_stage': 'RED'}]
        trace_history.observe(self.root, self.snapshot(phase='completed', validation=receipt))
        charts = trace_history.view(self.root)['charts']
        self.assertEqual(len(charts), 1)
        self.assertEqual(charts[0]['trace']['validation'][0]['acceptance_stage'], 'RED')

    def test_unfinished_turn_is_preserved_when_superseded(self):
        trace_history.observe(self.root, self.snapshot(turn='msg_one'))
        saved = trace_history.observe(self.root, self.snapshot(turn='msg_two'))
        self.assertEqual(saved[0]['reason'], 'superseded before an observed end')
        self.assertEqual(saved[0]['trace']['native_turn_id'], 'msg_one')

    def test_only_allowlisted_fields_are_stored(self):
        trace_history.observe(self.root, self.snapshot(phase='failed', prompt='private-prompt', reasoning='private-thought'))
        raw = trace_history._path(self.root).read_text(encoding='utf-8')
        self.assertNotIn('private-', raw)
        self.assertEqual(json.loads(raw)['charts'][0]['reason'], 'failed')

    def test_paths_are_rechecked_and_redacted_when_access_is_gone(self):
        trace_history.observe(self.root, self.snapshot(phase='completed'))
        self.assertTrue(trace_history.view(self.root)['charts'][0]['trace']['tools'][0]['file'])
        with patch('task_trace.visible_path', return_value=None):
            tool = trace_history.view(self.root)['charts'][0]['trace']['tools'][0]
        self.assertIsNone(tool['file'])
        self.assertNotIn('indexed_sha256', tool)

    def test_store_is_bounded(self):
        for n in range(trace_history.MAX_CHARTS + 5):
            trace_history.observe(self.root, self.snapshot(turn='msg_%d' % n, phase='cancelled'))
        self.assertEqual(len(trace_history.view(self.root)['charts']), trace_history.MAX_CHARTS)

    def test_foreign_store_is_refused(self):
        trace_history.observe(self.root, self.snapshot(phase='completed'))
        path = trace_history._path(self.root)
        value = json.loads(path.read_text(encoding='utf-8'))
        value['source_root'] = 'elsewhere'
        path.write_text(json.dumps(value), encoding='utf-8')
        with self.assertRaises(ValueError):
            trace_history.view(self.root)


if __name__ == '__main__':
    unittest.main()
