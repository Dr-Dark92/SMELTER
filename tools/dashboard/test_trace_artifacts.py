import json
import struct
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import trace_artifacts
import test_workspace_tracking

PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 32


def glb():
    body = json.dumps({'asset': {'version': '2.0'}, 'animations': [{'name': 'Walk', 'samplers': [], 'channels': []}]}).encode()
    body += b' ' * (-len(body) % 4)
    return struct.pack('<4sII', b'glTF', 2, 20 + len(body)) + struct.pack('<II', len(body), 0x4e4f534a) + body


class TraceArtifactTests(unittest.TestCase):
    def setUp(self):
        test_workspace_tracking.WorkspaceTrackingTests.setUp(self)
        (self.target / 'mods/demo/out').mkdir(exist_ok=True)
        (self.target / 'mods/demo/out/icon.png').write_bytes(PNG)
        (self.target / 'mods/demo/out/model.glb').write_bytes(glb())
        (self.target / 'mods/demo/out/notes.txt').write_text('private-notes')
        self.trace = {'available': True, 'binding': {'session_id': 'ses_root', 'directory': str(self.root), 'workspace_id': self.sid},
                      'task_id': 'msg_turn', 'task_id_source': 'Native OpenCode turn (Melty ID not supplied)', 'native_turn_id': 'msg_turn',
                      'index_revision': 'r' * 64,
                      'tools': [{'session_id': 'ses_child', 'call_id': 'call_w', 'tool': 'write', 'phase': 'completed', 'file': str(self.target / 'mods/demo/out/icon.png')},
                                {'session_id': 'ses_child', 'call_id': 'call_r', 'tool': 'read', 'phase': 'completed', 'file': str(self.target / 'mods/demo/out/other.png')}]}
        monitor = SimpleNamespace(view=lambda: self.trace)
        manager = patch('task_trace.manager', return_value=monitor)
        manager.start()
        self.addCleanup(manager.stop)

    def register(self, **data):
        return trace_artifacts.register(self.root, {'action': 'register', **data})

    def test_registers_image_with_observed_producer_and_serves_verified_bytes(self):
        record = self.register(relative_path='mods/demo/out/icon.png', producer_call_id='call_w')
        self.assertEqual((record['kind'], record['mime'], record['state']), ('image', 'image/png', 'current'))
        self.assertEqual(record['producer']['source'], 'observed tool call naming this path')
        self.assertEqual(record['task']['native_turn_id'], 'msg_turn')
        self.assertEqual(record['source_url'], '/api/task-trace/artifacts/' + record['id'])
        raw, mime = trace_artifacts.content(self.root, record['id'])
        self.assertEqual((raw, mime), (PNG, 'image/png'))

    def test_producer_must_be_observed_and_mismatched_paths_are_labelled(self):
        with self.assertRaises(ValueError):
            self.register(relative_path='mods/demo/out/icon.png', producer_call_id='call_missing')
        record = self.register(relative_path='mods/demo/out/icon.png', producer_call_id='call_r')
        self.assertTrue(record['producer']['source'].startswith('declared'))

    def test_glb_reuses_container_validation_and_lineage_must_exist(self):
        image = self.register(relative_path='mods/demo/out/icon.png')
        model = self.register(relative_path='mods/demo/out/model.glb', derived_from=[image['id']])
        self.assertEqual(model['details']['animations'], 1)
        self.assertEqual(model['derived_from'], [image['id']])
        with self.assertRaises(ValueError):
            self.register(relative_path='mods/demo/out/model.glb', derived_from=['f' * 32])

    def test_rejects_unsupported_spoofed_escaping_and_unbound_files(self):
        (self.target / 'mods/demo/out/fake.png').write_bytes(b'not an image')
        for path in ('mods/demo/out/notes.txt', 'mods/demo/out/fake.png', '../outside.png', 'mods/demo/out/missing.png'):
            with self.assertRaises(ValueError, msg=path):
                self.register(relative_path=path)
        with self.assertRaises(ValueError):
            self.register(relative_path='mods/demo/out/icon.png', extra='x')
        self.trace = {'available': False, 'binding': None}
        with self.assertRaises(ValueError):
            self.register(relative_path='mods/demo/out/icon.png')

    def test_changed_or_deleted_files_are_not_served(self):
        record = self.register(relative_path='mods/demo/out/icon.png')
        (self.target / 'mods/demo/out/icon.png').write_bytes(PNG + b'changed')
        self.assertEqual(trace_artifacts.view(self.root)['artifacts'][0]['state'], 'changed')
        with self.assertRaises(ValueError):
            trace_artifacts.content(self.root, record['id'])
        (self.target / 'mods/demo/out/icon.png').unlink()
        self.assertEqual(trace_artifacts.view(self.root)['artifacts'][0]['state'], 'missing')
        self.assertIsNone(trace_artifacts.view(self.root)['artifacts'][0]['source_url'])

    def test_access_revocation_blocks_serving(self):
        record = self.register(relative_path='mods/demo/out/icon.png')
        with patch('coding_workspace.require', side_effect=ValueError('Access denied')):
            self.assertEqual(trace_artifacts.view(self.root)['artifacts'][0]['state'], 'unavailable')
            with self.assertRaises(ValueError):
                trace_artifacts.content(self.root, record['id'])

    def test_opaque_ids_only(self):
        for value in ('../../etc', 'C:/x.png', 'A' * 32, '', None):
            with self.assertRaises(ValueError):
                trace_artifacts.content(self.root, value)

    def test_reregistering_same_bytes_replaces_and_store_is_bounded(self):
        self.register(relative_path='mods/demo/out/icon.png')
        self.register(relative_path='mods/demo/out/icon.png')
        self.assertEqual(len(trace_artifacts.view(self.root)['artifacts']), 1)
        raw = trace_artifacts._path(self.root).read_text(encoding='utf-8')
        self.assertNotIn('private-', raw)


if __name__ == '__main__':
    unittest.main()
