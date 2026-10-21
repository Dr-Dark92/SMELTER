"""Real MCP + Python/Node no-network container profiles; no model inference.

Exercise RED, GREEN, mixed assertion/import ERROR and current-tree invalidation.
Requires existing immutable images. No pull, installation or host execution fallback.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools/dashboard'))

PY_RED = 'import unittest\nclass Check(unittest.TestCase):\n def test_one(self): self.assertEqual(1,2)\n'
NODE_RED = "const {test}=require('node:test'),assert=require('node:assert/strict');test('one',()=>assert.equal(1,2));\n"


def smoke(directory, python_image, node_image):
    from database import select_database
    from config_store import save_config
    from python_tools import ToolSession
    from sandbox import owned_runs
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    report = {'status': 'FAIL', 'live_qwen': False, 'transport': 'actual Python MCP',
              'boundary': 'real no-network Python and Node containers', 'cases': []}
    with tempfile.TemporaryDirectory(prefix='smelter-profile-smoke-') as temporary:
        root = Path(temporary) / 'SMELTER'
        folder = root / 'tools/dashboard'
        folder.mkdir(parents=True)
        (root / 'skills').mkdir()
        (folder / 'dashboard.py').write_bytes(b'VALUE=1\n')
        (folder / 'test_profile.py').write_bytes(PY_RED.encode())
        (folder / 'test_profile.js').write_bytes(NODE_RED.encode())
        original = {p.name: p.read_bytes() for p in folder.iterdir()}
        select_database(root, str(Path(temporary) / 'data'))
        save_config(root, 'sandbox.json', {'schema_version': 1, 'python_image': python_image,
                                         'node_image': node_image, 'opencode_image': None})
        session = ToolSession(root, {'coding_workspace': True, 'transport': 'mcp'})
        def call(name, arguments):
            value = session.execute({'function': {'name': name, 'arguments': arguments}})
            if value.get('status') == 'error':raise ValueError(name + ': ' + value.get('error', 'unknown error'))
            return value
        try:
            ready = call('prepare_coding_workspace', {})
            sid, target = ready['workspace_id'], Path(ready['path'])
            def change(changes):
                rows = []
                for name, content in changes.items():
                    path = target / 'tools/dashboard' / name
                    rows.append({'relative_path': 'tools/dashboard/' + name, 'content': content,
                                 'expected_sha256': hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None})
                proposed = call('propose_coding_patch', {'workspace_id': sid, 'changes': rows})
                call('apply_coding_patch', {'workspace_id': sid, 'proposal_id': proposed['proposal_id']})
            def test(profile, expected):
                result = call('run_coding_tests', {'workspace_id': sid, 'profile': profile})
                report['cases'].append({k: result.get(k) for k in ('profile', 'stage', 'counts', 'exit_code',
                                        'cleanup_confirmed', 'tree_sha256', 'log_sha256', 'image')})
                if result.get('stage') != expected or result.get('cleanup_confirmed') is not True:
                    raise ValueError(profile + ' expected ' + expected + ': ' + json.dumps(result))
            test('python', 'RED')
            test('node', 'RED')
            change({'test_profile.py': PY_RED.replace('1,2', '1,1'), 'test_profile.js': NODE_RED.replace('1,2', '1,1')})
            test('python', 'GREEN')
            test('node', 'GREEN')
            green = call('review_coding_workspace', {'workspace_id': sid})
            if not green['all_current_tests_passed']:raise ValueError('Both current GREEN results were not recognized')
            change({'test_profile.js': NODE_RED, 'test_broken.js': "require('./deliberately-missing');\n"})
            test('node', 'ERROR')
            change({'test_profile.py': PY_RED, 'test_broken.py': 'import deliberately_missing_smelter_fixture\n'})
            test('python', 'ERROR')
            stale = call('review_coding_workspace', {'workspace_id': sid})
            if stale['all_current_tests_passed']:raise ValueError('Edits did not invalidate GREEN')
            if any(p.read_bytes() != original[p.name] for p in folder.iterdir()):raise ValueError('Original source changed')
            if owned_runs(root):raise ValueError('Owned containers/snapshots were left behind')
            report.update(status='PASS', current_green_review=green['all_current_tests_passed'],
                          stale_green_rejected=not stale['all_current_tests_passed'],
                          source_unchanged=True, cleanup_confirmed=True, tool_calls=len(session.events))
        except Exception as exc:
            report['error'] = str(exc)[:3000]
        finally:
            for name in ('tool-runs', 'coding-workspaces'):
                source = root / '.smelter' / name
                if source.is_dir():shutil.copytree(source, directory / name)
    (directory / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--python-image', required=True)
    parser.add_argument('--node-image', required=True)
    args = parser.parse_args()
    report = smoke(args.output, args.python_image, args.node_image)
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
