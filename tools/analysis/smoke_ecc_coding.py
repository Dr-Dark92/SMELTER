"""Real confined OpenCode/MCP RED -> fix -> GREEN with pinned ECC instructions.

The default model is a deterministic protocol fixture, not Qwen inference.
--live explicitly uses the existing local Qwen. Only disposable code is edited.
"""
import argparse
import contextlib
import hashlib
import http.server
import json
from pathlib import Path
import sys
import threading
import time

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools/dashboard'))
from agent_bridge import AgentBridge
from access_policy import current
from chat_jobs import Control
from chats import create_chat, read_chat
from config_store import save_config
from database import select_database
from opencode_runtime import ask
from task_contract import configuration
from smoke_agent_bridge import ModelFixture, port_free, smoke_state

EXPECTED_SKILL = '8887afa786ef30de834e7567115d3df71934b343c3d9d849714f8ea43f979ee0'
BEFORE = 'def add(a, b):\n    return a - b\n'
AFTER = 'def add(a, b):\n    return a + b\n'
TEST = ('import unittest\nfrom example import add\n\nclass AddTests(unittest.TestCase):\n'
        '    def test_adds_positive_numbers(self):\n        self.assertEqual(add(2, 3), 5)\n')


def tool_results(messages):
    """Decode OpenCode's returned text blocks without trusting model prose."""
    def find(value, depth=0):
        if depth > 10:return None
        if isinstance(value, str):
            try:return find(json.loads(value), depth + 1)
            except ValueError:return None
        if isinstance(value, list):
            for item in value:
                found = find(item, depth + 1)
                if found:return found
        if isinstance(value, dict):
            if 'tool_result' in value:return value['tool_result']
            for key in ('text', 'content', 'output', 'structuredContent'):
                if key in value:
                    found = find(value[key], depth + 1)
                    if found:return found
        return None
    return [find(item.get('content')) for item in messages if item.get('role') == 'tool']


def next_call(results):
    step = len(results)
    if any(not isinstance(item, dict) for item in results):
        raise ValueError('Missing structured MCP result in model history')
    if step == 0:return 'prepare_coding_workspace', {}
    sid = results[0]['workspace_id']
    if step == 1:return 'read_coding_file', {'workspace_id': sid, 'relative_path': 'tools/dashboard/example.py'}
    if step == 2:return 'propose_coding_patch', {'workspace_id': sid, 'changes': [
        {'relative_path': 'tools/dashboard/test_example.py', 'expected_sha256': None, 'content': TEST}]}
    if step == 3:return 'apply_coding_patch', {'workspace_id': sid, 'proposal_id': results[2]['proposal_id']}
    if step == 4:return 'run_coding_tests', {'workspace_id': sid, 'profile': 'python'}
    if step == 5:
        if results[4].get('stage') != 'RED':raise ValueError('Expected observed assertion failure before implementation')
        return 'propose_coding_patch', {'workspace_id': sid, 'changes': [
            {'relative_path': 'tools/dashboard/example.py', 'expected_sha256': results[1]['sha256'], 'content': AFTER}]}
    if step == 6:return 'apply_coding_patch', {'workspace_id': sid, 'proposal_id': results[5]['proposal_id']}
    if step == 7:return 'run_coding_tests', {'workspace_id': sid, 'profile': 'python'}
    if step == 8:
        if results[7].get('stage') != 'GREEN':raise ValueError('Expected observed passing test after implementation')
        return 'review_coding_workspace', {'workspace_id': sid}
    if step == 9 and results[8].get('all_current_tests_passed'):return None
    raise ValueError('Unexpected or repeated coding tool sequence')


class CodingFixture(ModelFixture):
    requests = []
    expected_skill = ''
    def do_POST(self):
        try:
            body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            self.requests.append(body)
            if self.path not in ('/v1/chat/completions', '/api/chat') or self.expected_skill not in json.dumps(body):
                raise ValueError('Expected OpenAI-compatible request with the selected ECC reference')
            call = next_call(tool_results(body.get('messages', [])))
            if call:
                name, arguments = call
                name = 'smelter_' + name
                names = [item.get('function', {}).get('name') for item in body.get('tools', [])]
                if name not in names:raise ValueError('Coding MCP tool was not exposed: ' + name)
                message = {'role': 'assistant', 'content': '', 'tool_calls': [{'id': 'call_' + str(len(self.requests)),
                    'type': 'function', 'function': {'name': name, 'arguments': json.dumps(arguments)}}]}
            else:
                message = {'role': 'assistant', 'content': 'Coding smoke completed. Inspect the real RED/GREEN and patch receipts.'}
            if self.path == '/api/chat':
                if call:
                    message['tool_calls'] = [{'function': {'name': name, 'arguments': arguments}}]
                self.respond({'message': message, 'done': True, 'done_reason': 'stop'})
                return
            finish = 'tool_calls' if call else 'stop'
            value = {'id': 'coding-smoke', 'object': 'chat.completion', 'created': int(time.time()), 'model': 'qwen3.5:9b'}
            if body.get('stream'):
                delta = {**message}
                if call:delta['tool_calls'] = [{'index': 0, **message['tool_calls'][0]}]
                first = {**value, 'object': 'chat.completion.chunk', 'choices': [{'index': 0, 'delta': delta, 'finish_reason': None}]}
                last = {**value, 'object': 'chat.completion.chunk', 'choices': [{'index': 0, 'delta': {}, 'finish_reason': finish}]}
                self.respond('data: ' + json.dumps(first) + '\n\ndata: ' + json.dumps(last) + '\n\ndata: [DONE]\n\n', True)
            else:
                self.respond({**value, 'choices': [{'index': 0, 'message': message, 'finish_reason': finish}]})
        except Exception as exc:
            self.send_error(400, str(exc)[:300])


@contextlib.contextmanager
def model_fixture(reference, enabled):
    if not enabled:yield;return
    port_free(11434)
    CodingFixture.requests = []
    CodingFixture.expected_skill = json.dumps(reference)[1:-1]
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 11434), CodingFixture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:yield
    finally:server.shutdown();server.server_close();thread.join(timeout=5)


def run(args):
    reference = Path(args.skill_manifest).read_text(encoding='utf-8')
    if hashlib.sha256(reference.encode()).hexdigest() != EXPECTED_SKILL:
        raise ValueError('ECC TDD instruction integrity mismatch')
    with smoke_state(args.evidence_dir) as base:
        root = base / 'SMELTER'
        folder = root / 'tools/dashboard'
        folder.mkdir(parents=True)
        (folder / 'dashboard.py').write_bytes(b'VALUE=0\n')
        (folder / 'example.py').write_bytes(BEFORE.encode())
        skill = root / 'skills/ecc-tdd-workflow'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_bytes(reference.encode())
        select_database(root, str(base / 'data'))
        save_config(root, 'sandbox.json', {'schema_version': 1, 'opencode_image': args.image,
                                          'python_image': args.python_image, 'node_image': None})
        save_config(root, 'runtime_settings.json', {'schema_version': 1, 'settings': {
            'context_tokens': 32768, 'max_output_tokens': 1024, 'timeout_seconds': 300, 'thinking': False}})
        cid = create_chat(root, 'ECC coding RED GREEN smoke')['id']
        control = Control()
        control.access_policy = current(root)
        control.configuration = configuration(root)
        prompt = ('Use the selected ECC TDD instructions with the approved MCP coding tools only. '
                  'Prepare one coding copy. Read tools/dashboard/example.py. Propose/apply a new unittest in '
                  'tools/dashboard/test_example.py asserting add(2,3)==5, then run the fixed python tests and observe RED. '
                  'Propose/apply the minimal fix from subtraction to addition. Run python tests again for GREEN and '
                  'review the workspace. Do not use shell, installs, coverage, Git, delegation, or modify original files. '
                  'Report actual RED/GREEN and saved hashes without claiming coverage or a source merge.')
        bridge = AgentBridge(root, cid, prompt, skills=['ecc-tdd-workflow'], grants={'coding_workspace': True},
                             policy=control.access_policy, control=control)
        with model_fixture(reference, not args.live):
            result = ask(root, cid, prompt, model_key='local/qwen3.5:9b', approval=True,
                         control=control, agent_mode=True, bridge=bridge)
        if result['status'] != 'completed':raise ValueError('Coding agent did not complete: ' + result['reply'])
        execution = read_chat(root, cid)['messages'][-1]['execution']
        events = [e for e in execution['events'] if e.get('source') == 'controller']
        tests = [e['result'] for e in events if e['tool'] == 'run_coding_tests']
        if [r.get('stage') for r in tests] != ['RED', 'GREEN']:
            raise ValueError('Missing actual RED followed by GREEN evidence')
        if tests[0]['counts']['failures'] != 1 or tests[0]['counts']['errors'] != 0 or tests[1]['counts']['tests'] != 1:
            raise ValueError('Test counts do not establish the expected assertion failure/fix')
        reviews = [e['result'] for e in events if e['tool'] == 'review_coding_workspace']
        if not reviews or not reviews[-1]['all_current_tests_passed'] or reviews[-1]['changed_files_total'] != 2:
            raise ValueError('Final review did not verify the current two-file change')
        target = Path(reviews[-1]['path'])
        if (target / 'tools/dashboard/example.py').read_bytes() != AFTER.encode():raise ValueError('Saved fix bytes differ')
        if (target / 'tools/dashboard/test_example.py').read_bytes() != TEST.encode():raise ValueError('Saved test bytes differ')
        if (folder / 'example.py').read_bytes() != BEFORE.encode() or (folder / 'test_example.py').exists():
            raise ValueError('Original source was changed')
        if not all(Path(e['result']['mcp_audit_path']).is_file() for e in events):raise ValueError('Missing actual MCP audits')
        if not execution['cleanup_confirmed'] or not all(t['cleanup_confirmed'] for t in tests):
            raise ValueError('Owned container cleanup was not confirmed')
        cards = execution.get('files', [])
        return {'status': 'passed', 'model': 'live qwen3.5:9b' if args.live else 'synthetic protocol fixture; no Qwen inference',
                'selected_skill_sha256': EXPECTED_SKILL, 'boundary': 'managed no-network OpenCode and Python test containers',
                'controller_tool_calls': len(events), 'test_stages': ['RED', 'GREEN'], 'red_counts': tests[0]['counts'],
                'green_counts': tests[1]['counts'], 'changed_files': reviews[-1]['changed_files'],
                'all_current_tests_passed': True, 'coverage': 'not measured', 'source_unchanged': True,
                'mcp_audits_checked': True, 'cleanup_confirmed': True, 'fixture_model_requests': len(CodingFixture.requests) if not args.live else None,
                'file_cards': len(cards), 'evidence_directory': str(Path(args.evidence_dir).resolve()) if args.evidence_dir else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True, help='Existing immutable OpenCode image ID')
    parser.add_argument('--python-image', required=True, help='Existing immutable Python test image ID')
    parser.add_argument('--skill-manifest', required=True, help='Reviewed pinned ECC tdd-workflow SKILL.md')
    parser.add_argument('--evidence-dir', help='New retained evidence directory; no overwrite')
    parser.add_argument('--live', action='store_true', help='Explicit real Qwen inference, never automatic')
    args = parser.parse_args()
    try:result = run(args)
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'error': str(exc)}, indent=2));return 1
    print(json.dumps(result, indent=2));return 0


if __name__ == '__main__':raise SystemExit(main())
