import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from access_policy import current, using, Policy
import coding_workspace as coding
import workspace_tracking as tracking


class WorkspaceTrackingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'SMELTER'
        for relative, raw in {
            'tools/dashboard/dashboard.py': b'VALUE=1\n',
            'mods/demo/Mods/Link/Scripts/controller.lua': b'local M = {}\nfunction M.chase() return true end\nreturn M\n',
            'mods/demo/tests/test_controller.lua': b'package.path = "Mods/Link/Scripts/?.lua;" .. package.path\nlocal m=require("controller")\nassert(m.chase())\n',
            'mods/demo/tests/fixture.hex': b'47414c31\n',
        }.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        (self.root / 'skills').mkdir()
        self.policy = current(self.root)
        self.scope = using(self.policy)
        self.scope.__enter__()
        self.addCleanup(self.scope.__exit__, None, None, None)
        ready = coding.prepare(self.root, {})
        self.sid, self.target = ready['workspace_id'], Path(ready['path'])

    def context(self, **kwargs):
        return coding.context(self.root, {'workspace_id': self.sid, 'detail': 'full', **kwargs})

    def test_default_summary_is_compact_and_lists_changed_files_only(self):
        full = self.context()
        summary = coding.context(self.root, {'workspace_id': self.sid})
        self.assertEqual(summary['detail'], 'summary')
        for key in ('graph', 'mermaid', 'history'):
            self.assertNotIn(key, summary)
        self.assertEqual(summary['files'], [])
        self.assertEqual(summary['total_files'], full['total_files'])
        self.assertLess(len(json.dumps(summary)), len(json.dumps(full)) / 2)
        relative = full['files'][0]['relative_path']
        path = self.target / relative
        path.write_bytes(path.read_bytes() + b'\n-- changed\n')
        summary = coding.context(self.root, {'workspace_id': self.sid})
        self.assertEqual([r['relative_path'] for r in summary['changed_files']], [relative])
        self.assertEqual(set(summary['changed_files'][0]), {'relative_path', 'sha256', 'status'})
        searched = coding.context(self.root, {'workspace_id': self.sid, 'query': relative})
        self.assertEqual(searched['files'][0]['relative_path'], relative)
        self.assertNotIn('physical_path', searched['files'][0])
        with self.assertRaisesRegex(ValueError, 'summary or full'):
            coding.context(self.root, {'workspace_id': self.sid, 'detail': 'everything'})

    def test_registry_recovers_id_and_canonical_host_location(self):
        result = coding.context(self.root, {})
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['workspaces'][0]['workspace_id'], self.sid)
        self.assertEqual(result['workspaces'][0]['workspace_root'], str(self.target))
        self.assertEqual(result['workspaces'][0]['storage'], 'host_directory')

    def test_task_finalization_persists_observed_relation_snapshot(self):
        from database import select_database
        from chats import create_chat, read_chat
        from execution_store import finalize
        select_database(self.root, str(Path(self.tmp.name) / 'data'))
        cid = create_chat(self.root, 'Tracking fixture')['id']
        value = self.context()
        execution = {'source': 'controller', 'events': [{'result': {'workspace_id': self.sid}}]}
        finalize(self.root, cid, 'Review fixture', 'Reviewed', execution)
        saved = read_chat(self.root, cid)['messages'][-1]['execution']['workspace_tracking']
        self.assertEqual(saved['revision'], value['revision'])
        self.assertEqual(saved['mermaid'], value['mermaid'])

    def test_query_returns_exact_paths_hashes_and_persistent_index(self):
        result = self.context(query='controller.lua')
        self.assertEqual(result['matching_files'], 2)
        source = next(row for row in result['files'] if '/Scripts/' in row['relative_path'])
        self.assertEqual(source['sha256'], hashlib.sha256((self.target / source['relative_path']).read_bytes()).hexdigest())
        self.assertEqual(source['physical_path'], str(self.target / source['relative_path']))
        self.assertEqual(tracking.cached(self.root, self.sid)['revision'], result['revision'])
        self.assertTrue((coding.base_path(self.root) / self.sid / 'relations.mmd').is_file())

    def test_line_read_is_exact_and_character_mode_is_compatible(self):
        path = 'mods/demo/Mods/Link/Scripts/controller.lua'
        result = coding.read(self.root, {'workspace_id': self.sid, 'relative_path': path, 'start_line': 2, 'line_count': 1})
        self.assertEqual(result['text'], 'function M.chase() return true end\n')
        self.assertEqual(result['pagination_unit'], 'lines')
        self.assertEqual(result['physical_path'], str(self.target / path))
        chars = coding.read(self.root, {'workspace_id': self.sid, 'relative_path': path, 'offset': 1, 'limit': 4})
        self.assertEqual(chars['text'], 'ocal')
        self.assertEqual(chars['pagination_unit'], 'characters')
        mixed = coding.read(self.root, {'workspace_id': self.sid, 'relative_path': path, 'start_line': 2, 'offset': 1})
        self.assertEqual((mixed['pagination_unit'], mixed['start_line']), ('lines', 2))
        self.assertEqual(mixed['ignored_arguments'], ['offset'])

    def test_applied_edits_and_external_deletions_are_tracked(self):
        self.context()
        path = 'mods/demo/Mods/Link/Scripts/controller.lua'
        before = (self.target / path).read_bytes()
        proposal = coding.propose(self.root, {'workspace_id': self.sid, 'changes': [
            {'relative_path': path, 'expected_sha256': coding.digest(before), 'content': 'return {}\n'}]})
        result = coding.apply(self.root, {'workspace_id': self.sid, 'proposal_id': proposal['proposal_id']})
        self.assertNotIn('error', result['tracking'])
        cached = tracking.cached(self.root, self.sid)
        self.assertEqual(next(row for row in cached['files'] if row['relative_path'] == path)['status'], 'modified')
        (self.target / path).unlink()
        refreshed = self.context(query='Scripts/controller.lua')
        self.assertEqual(refreshed['files'][0]['status'], 'missing')
        self.assertIsNone(refreshed['files'][0]['sha256'])
        self.assertEqual(refreshed['history'][-2]['path'], path)

    def test_static_graph_resolves_real_import_without_claiming_behavior_coverage(self):
        result = self.context()
        graph = result['graph']
        by_id = {node['id']: node for node in graph['nodes']}
        imports = [edge for edge in graph['edges'] if edge['kind'] == 'import']
        self.assertTrue(any(by_id[e['source']]['label'].endswith('test_controller.lua') and
                            by_id[e['target']]['label'].endswith('Scripts/controller.lua') for e in imports))
        self.assertTrue(all(e['confidence'] in ('static', 'inferred') for e in imports))
        self.assertIn('flowchart LR', result['mermaid'])
        self.assertIn('not behavior coverage', graph['scope'])

    def test_cached_view_respects_new_file_exclusions(self):
        result = self.context()
        value = json.loads(json.dumps(self.policy.value))
        row = next(row for row in value['locations'] if Path(row['path']).resolve() == self.target.parent.parent.resolve())
        row['exclusions'].append('coding/' + self.sid + '/mods/demo/tests/test_controller.lua')
        with using(Policy(value)):
            visible = tracking.view(tracking.cached(self.root, self.sid))
        self.assertNotIn('mods/demo/tests/test_controller.lua', [r['relative_path'] for r in visible['files']])
        self.assertNotIn('mods/demo/tests/test_controller.lua', visible['mermaid'])

    def test_index_failure_cannot_undo_successful_apply(self):
        from unittest.mock import patch
        path = 'tools/dashboard/dashboard.py'
        before = (self.target / path).read_bytes()
        proposed = coding.propose(self.root, {'workspace_id': self.sid, 'changes': [
            {'relative_path': path, 'expected_sha256': coding.digest(before), 'content': 'VALUE=2\n'}]})
        with patch.object(tracking, 'capture', side_effect=OSError('index disk error')):
            applied = coding.apply(self.root, {'workspace_id': self.sid, 'proposal_id': proposed['proposal_id']})
        self.assertEqual(applied['status'], 'coding_patch_applied')
        self.assertEqual((self.target / path).read_bytes(), b'VALUE=2\n')
        self.assertIn('index disk error', applied['tracking']['error'])

    def test_task_snapshot_uses_index_and_ignores_unowned_or_malformed_ids(self):
        self.context()
        result = tracking.task_snapshot(self.root, {'events': [{'result': {'workspace_id': self.sid}}]})
        self.assertEqual(result['workspace_id'], self.sid)
        self.assertTrue(result['graph']['nodes'])
        self.assertIsNone(tracking.task_snapshot(self.root, {'events': [None, {'result': {'workspace_id': '../outside'}}]}))
        self.assertIsNone(tracking.task_snapshot(self.root, {'events': None}))


if __name__ == '__main__':
    unittest.main()
