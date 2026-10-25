"""Verify warm OpenCode reuse across MCP grants without model/game execution.

Uses a fresh project/database under .smelter and removes only its own container.
Optional --activate-toolchain selects the already-built image in the real project.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/dashboard'))


def native_catalog():
    """Exercise the native profile's exact grant set through the real stdio MCP server."""
    from mcp_connections import exchange
    path = Path.home() / '.config/opencode/opencode.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    model = data['provider']['ollama']['models']['qwen3.5:35b-a3b-128k']
    if model['limit']['context'] != 131072 or model['limit']['output'] != 8192:
        raise AssertionError('Native context/output configuration differs from the selected profile')
    grants = json.loads(data['mcp']['smelter']['environment']['SMELTER_MCP_GRANTS'])
    result = exchange(ROOT, grants=grants, name='modding_tool_catalog', arguments={'engine':'ue5'}, timeout=30)
    envelope = result.get('structuredContent', {})
    tool = envelope.get('tool_result', {})
    if result.get('isError') or tool.get('status') != 'modding_catalog_read':
        raise AssertionError('Native MCP catalog call did not complete')
    names = {t['id'] for t in tool['tools']}
    if not {'repak', 'retoc', 'ghidra'} <= names:
        raise AssertionError('Native MCP engine routing did not return the expected tools')
    return {'status':'passed', 'native_context_tokens':131072, 'native_output_tokens':8192,
            'real_mcp_catalog_call':True, 'ue5_tools_returned':len(names),
            'audit_path':envelope.get('audit_path'), 'candidate_tools_executed':False}


def smoke(activate=False):
    from database import select_database
    from config_store import save_config
    from access_policy import current
    from task_contract import configuration
    from agent_bridge import AgentBridge
    from process_runner import run
    import opencode_pool
    import shutil
    docker = shutil.which('docker')
    if not docker:
        raise ValueError('Docker is required')
    images = {key: run([docker, 'image', 'inspect', '--format', '{{.Id}}', tag], timeout=5, text=True, check=True).stdout.strip()
              for key, tag in [('python_image', 'python:3.12-alpine'), ('node_image', 'node:22-alpine'),
                               ('opencode_image', 'smelter-opencode:1.19.3'), ('cpp_image', 'smelter-cpp:2')]}
    if activate:
        sys.path.insert(0, str(ROOT / 'tools/setup'))
        from configure_native_build import configure
        configure(ROOT, image_id=images['cpp_image'], apply=True)
    base = ROOT / '.smelter'; base.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='cli-smoke-', dir=base) as tmp:
        root = Path(tmp) / 'project'; root.mkdir()
        (root / 'README.md').write_text('Isolated OpenCode warm transport smoke fixture.\n')
        (root / 'tools/dashboard').mkdir(parents=True)
        (root / 'tools/dashboard/dashboard.py').write_text('# Source snapshot fixture; never executed.\n')
        select_database(root, str(Path(tmp) / 'data'))
        save_config(root, 'sandbox.json', {'schema_version':1, **images})
        conf, policy = configuration(root), current(root)
        first = opencode_pool.acquire(root, policy, conf, None, None)
        name = first.name
        try:
            opencode_pool.release(first)
            bridge = AgentBridge(root, None, 'CLI catalog inspection', grants={'coding_workspace':True}, policy=policy)
            second = opencode_pool.acquire(root, policy, conf, None, bridge)
            if first is not second or second.name != name:
                raise AssertionError('Tool-enabled task replaced the warmed container')
            if second.request('/mcp').get('smelter', {}).get('status') != 'connected':
                raise AssertionError('Refreshed MCP server is not connected')
            requests = '\n'.join(json.dumps(x) for x in (
                {'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18'}},
                {'jsonrpc':'2.0','id':2,'method':'tools/list'})) + '\n'
            listed = run([docker, 'exec', '-i', name, 'node', '/opt/smelter-bridge/proxy.mjs'],
                         input=requests.encode(), timeout=10, max_output=65536, text=True, check=True)
            rows = [json.loads(line) for line in listed.stdout.splitlines()]
            tools = next(row['result']['tools'] for row in rows if row.get('id') == 2)
            if 'modding_tool_catalog' not in {t['name'] for t in tools}:
                raise AssertionError('New task tool schemas were not published')
            opencode_pool.release(second)
            third = opencode_pool.acquire(root, policy, conf, None, None)
            if third is not first:
                raise AssertionError('Removing grants replaced the warmed container')
            opencode_pool.release(third)
            return {'status':'passed', 'container_reused':True, 'task_schemas_refreshed':True,
                    'toolchain_image':images['cpp_image'], 'real_project_image_selected':activate,
                    'model_inference':False, 'game_execution':False}
        finally:
            state = opencode_pool.stop(force=True)
            if state['status'] != 'stopped':
                raise ValueError('Owned smoke container cleanup was not confirmed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activate-toolchain', action='store_true')
    parser.add_argument('--native-catalog-only', action='store_true')
    args = parser.parse_args()
    print(json.dumps(native_catalog() if args.native_catalog_only else smoke(args.activate_toolchain), indent=2))
