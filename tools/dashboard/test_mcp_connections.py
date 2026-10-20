import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from mcp_connections import sdk_status, status, load_config, save_config, validate_config, exchange, approved_tools, alias, call
from python_tools import ToolSession
from tool_registry import schemas, execute_builtin


class McpFixture:
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.root = self.base / 'checkout'
        self.root.mkdir()
        self.folder = self.base / 'game'
        self.folder.mkdir()

    def config(self):
        return {'schema_version': 1, 'servers': [{'id': 'fixture', 'command': str(Path(sys.executable).resolve()),
            'args': ['fixture.py'], 'cwd': str(self.root), 'enabled': True, 'allowed_tools': ['echo']}]}


class McpConfigurationTests(McpFixture, unittest.TestCase):
    def test_preview_launch_uses_dashboard_owner_even_in_mcp_mode(self):
        with patch('mcp_connections.sdk_status', return_value={'status':'installed'}):
            session = ToolSession(self.root, {'frontend_workspace':True, 'transport':'mcp'})
        expected = {'status':'workspace_launched','pid':12345,'url':'http://127.0.0.1:8770/#token=fixture'}
        with patch('mcp_connections.call', side_effect=AssertionError('must not launch in transient MCP server')), \
                patch('tool_registry.execute_builtin', return_value=expected) as local:
            result = session.execute({'function':{'name':'launch_frontend_preview','arguments':{}}})
        self.assertEqual(result, expected)
        local.assert_called_once_with(self.root, session.grants, 'launch_frontend_preview', {})
        self.assertEqual(session.events[-1]['transport'], 'python')
        self.assertEqual(session.events[-1]['process_owner'], 'dashboard')

    def test_status_and_save_do_not_start_processes(self):
        with patch('mcp_connections._exchange') as run:
            self.assertEqual(status(self.root)['config']['servers'], [])
            save_config(self.root, self.config())
            self.assertEqual(load_config(self.root), self.config())
            run.assert_not_called()

    def test_bad_configuration_rejected(self):
        for change in ({'id': 'smelter'}, {'command': 'python'}, {'cwd': '../game'},
                       {'enabled': 'yes'}, {'allowed_tools': ['*']}, {'args': 'shell string'}):
            config = self.config()
            config['servers'][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_config(config)

    def test_unknown_names_cannot_fall_through_to_write(self):
        with self.assertRaises(ValueError):
            execute_builtin(self.root, {}, 'invented_tool', {})
        self.assertFalse((self.root / 'diagnostics').exists())

    def test_missing_sdk_is_clear_and_direct_tools_still_work(self):
        with patch('mcp_connections.sdk_status', return_value={'status': 'missing'}):
            with self.assertRaisesRegex(ValueError, 'optional MCP'):
                exchange(self.root)
            with self.assertRaisesRegex(ValueError, 'MCP dependency'):
                ToolSession(self.root, {'write_diagnostics': True, 'transport': 'mcp'})
            session = ToolSession(self.root, {'write_diagnostics': True})
            self.assertEqual(session.tools[0]['function']['name'], 'write_diagnostic_markdown')

    def test_external_selection_allowlist_and_namespacing(self):
        descriptor = {'name': 'echo', 'description': 'Echo', 'input_schema': {'type': 'object'}, 'allowed': True}
        connection = {'tools': [descriptor], 'config_fingerprint': 'fixture'}
        with patch('mcp_connections.exchange', return_value=connection):
            tools = approved_tools(self.root, [{'server': 'fixture', 'name': 'echo'}])
            self.assertEqual(tools[alias('fixture', 'echo')]['descriptor'], descriptor)
            with self.assertRaises(ValueError):
                approved_tools(self.root, [{'server': 'fixture', 'name': 'unapproved'}])
        self.assertNotEqual(alias('one', 'echo'), alias('two', 'echo'))
        with self.assertRaises(ValueError):
            approved_tools(self.root, [{'server': 'smelter', 'name': 'echo'}])

    def test_changed_config_fails_before_process_start(self):
        save_config(self.root, self.config())
        with patch('mcp_connections.sdk_status', return_value={'status': 'installed'}), patch('mcp_connections._exchange') as run:
            with self.assertRaisesRegex(ValueError, 'connection changed'):
                exchange(self.root, 'fixture', name='echo', expected={'config_fingerprint': 'stale'})
            run.assert_not_called()

    def test_mcp_receipt_and_parent_call_deduplication(self):
        session = ToolSession(self.root, {'write_diagnostics': True})
        session.transport = 'mcp'
        result = {'status': 'written', 'path': 'fixture.md', 'bytes': 4, 'sha256': 'fixture', 'mcp_audit_path': 'server.jsonl'}
        with patch('mcp_connections.call', return_value=result) as run:
            request = {'function': {'name': 'write_diagnostic_markdown', 'arguments': {'filename': 'fixture.md', 'content': 'text'}}}
            self.assertEqual(session.execute(request), result)
            self.assertEqual(session.execute(request), result)
            self.assertEqual(run.call_count, 1)
        self.assertIn('[MCP]', session.receipt())
        self.assertTrue(session.events[1]['reused'])


@unittest.skipUnless(sdk_status()['status'] == 'installed', 'Optional pinned MCP SDK is not installed')
class McpIntegrationTests(McpFixture, unittest.TestCase):
    def test_transient_mcp_server_does_not_offer_persistent_preview_launch(self):
        found = exchange(self.root, grants={'frontend_workspace':True}, timeout=15)
        self.assertNotIn('launch_frontend_preview', [item['name'] for item in found['tools']])
        self.assertIn('validate_frontend_workspace', [item['name'] for item in found['tools']])
        with self.assertRaisesRegex(ValueError, 'missing or not in the operator allowlist'):
            exchange(self.root, grants={'frontend_workspace':True}, name='launch_frontend_preview', arguments={}, timeout=15)

    def test_real_stdio_discovery_and_tool_execution(self):
        (self.folder / 'fixture.txt').write_text('fixture')
        grants = {'inventory_root': str(self.folder), 'write_diagnostics': True}
        found = exchange(self.root, grants=grants, timeout=15)
        self.assertEqual(found['status'], 'connected')
        self.assertEqual({x['name'] for x in found['tools']}, {'inventory_directory', 'write_diagnostic_markdown'})
        session = ToolSession(self.root, {**grants, 'transport': 'mcp'})
        inventory = session.execute({'function': {'name': 'inventory_directory', 'arguments': {'relative_path': '.'}}})
        self.assertEqual(inventory['status'], 'inventoried')
        self.assertEqual(inventory['files_observed'], 1)
        request = {'function': {'name': 'write_diagnostic_markdown', 'arguments': {'filename': 'mcp.md', 'content': '# MCP fixture'}}}
        result = session.execute(request)
        self.assertEqual(result['status'], 'written')
        self.assertEqual(Path(result['path']).read_text(), '# MCP fixture')
        self.assertTrue(Path(result['mcp_audit_path']).is_file())
        self.assertEqual(session.execute(request)['path'], result['path'])
        self.assertFalse((self.root / 'diagnostics/mcp_02.md').exists())
        denied = exchange(self.root, grants={}, timeout=15)
        self.assertEqual(denied['tools'], [])
        with self.assertRaisesRegex(ValueError, 'not in the operator allowlist'):
            exchange(self.root, grants={}, name='write_diagnostic_markdown', arguments={'filename': 'denied.md', 'content': 'no'}, timeout=15)
        self.assertFalse((self.root / 'diagnostics/denied.md').exists())

    def test_chat_turn_uses_mcp_and_persists_controller_receipt(self):
        import io
        from database import select_database
        from chats import create_chat, read_chat
        from chat_inference import ask
        select_database(self.root, str(self.base / 'data'))
        cid = create_chat(self.root, 'MCP chat fixture')['id']
        calls = [json.dumps({'message': {'content': '', 'tool_calls': [{'function': {
            'name': 'write_diagnostic_markdown', 'arguments': {'filename': 'chat-mcp.md', 'content': '# Chat MCP'}}}]}}).encode(),
                 b'{"message":{"content":"Completed."}}']
        def opener(*args, **kwargs):
            return io.BytesIO(calls.pop(0))
        result = ask(self.root, cid, 'Write a fixture report', opener=opener,
                     tool_permissions={'write_diagnostics': True, 'transport': 'mcp'})
        self.assertIn('[MCP]', result['reply'])
        record = read_chat(self.root, cid)['messages'][-1]['execution']
        self.assertEqual(record['events'][0]['transport'], 'mcp')
        self.assertEqual(record['events'][0]['result']['status'], 'written')
        self.assertEqual((self.root / 'diagnostics/chat-mcp.md').read_text(), '# Chat MCP')

    def test_saved_glb_inspection_through_real_mcp(self):
        import base64
        import struct
        from database import select_database
        from chats import create_chat
        from model_assets import attach_model, model_path
        select_database(self.root, str(self.base / 'data'))
        cid = create_chat(self.root, 'GLB MCP fixture')['id']
        document = json.dumps({'asset': {'version': '2.0'}, 'nodes': [], 'meshes': [], 'animations': []}).encode()
        document += b' ' * (-len(document) % 4)
        raw = struct.pack('<4sIIII', b'glTF', 2, len(document) + 20, len(document), 0x4e4f534a) + document
        asset = attach_model(self.root, {'conversation_id': cid, 'filename': 'fixture.glb', 'base64': base64.b64encode(raw).decode()})
        session = ToolSession(self.root, {'model_ids': [asset['id']], 'transport': 'mcp'}, cid)
        result = session.execute({'function': {'name': 'inspect_model_attachment', 'arguments': {'attachment_id': asset['id']}}})
        self.assertEqual(result['status'], 'model_inspected')
        self.assertEqual(result['animations'], 0)
        self.assertEqual(result['animation_clips'], [])
        self.assertTrue(Path(result['mcp_audit_path']).is_file())
        self.assertEqual(model_path(self.root, asset['id']).read_bytes(), raw)

    def test_workspace_creation_read_and_edit_over_real_mcp(self):
        from frontend_workspace import target_path
        code = self.root / 'tools/dashboard/dashboard.py'
        code.parent.mkdir(parents=True)
        original = 'HTML = "<style>body{color:red}</style><script>const keep=true;</script>"\n'
        code.write_text(original)
        session = ToolSession(self.root, {'frontend_workspace': True, 'transport': 'mcp'})
        def run(name, arguments):
            result = session.execute({'function': {'name': name, 'arguments': arguments}})
            self.assertNotEqual(result['status'], 'error', result)
            return result
        run('prepare_frontend_workspace', {})
        css = run('read_frontend_file', {})
        run('replace_frontend_css', {'expected_sha256': css['sha256'], 'old_text': 'color:red', 'new_text': 'color:blue'})
        current = run('read_frontend_file', {})
        self.assertIn('color:blue', current['text'])
        self.assertEqual(code.read_text(), original)
        self.assertTrue((target_path(self.root) / 'tools/dashboard/dashboard.py').is_file())
        self.assertEqual(session.call_limit, 24)

    def test_generic_server_discovery_selection_and_chat_dispatch(self):
        fixture = self.base / 'fixture_server.py'
        fixture.write_text('''import json,sys
for line in sys.stdin:
    request=json.loads(line)
    if 'id' not in request: continue
    method=request['method']
    if method=='initialize':
        result={'protocolVersion':request['params']['protocolVersion'],'capabilities':{'tools':{}},'serverInfo':{'name':'fixture','version':'1'}}
    elif method=='tools/list':
        result={'tools':[{'name':name,'description':'Fixture echo','inputSchema':{'type':'object','properties':{'text':{'type':'string'}},'required':['text']}} for name in ['echo','blocked']]}
    elif method=='tools/call':
        value={'echo':request['params']['arguments']['text']}
        result={'content':[{'type':'text','text':json.dumps(value)}],'structuredContent':value,'isError':False}
    else: result={}
    print(json.dumps({'jsonrpc':'2.0','id':request['id'],'result':result}),flush=True)
''', encoding='utf-8')
        config = self.config()
        config['servers'][0]['args'] = [str(fixture)]
        save_config(self.root, config)
        connection = exchange(self.root, 'fixture', timeout=10)
        self.assertEqual({t['name']: t['allowed'] for t in connection['tools']}, {'echo': True, 'blocked': False})
        selected = [{'server': 'fixture', 'name': 'echo'}]
        session = ToolSession(self.root, {'mcp_tools': selected})
        name = session.tools[0]['function']['name']
        result = session.execute({'function': {'name': name, 'arguments': {'text': 'actual MCP'}}})
        self.assertEqual(result['status'], 'mcp_completed')
        self.assertEqual(result['mcp_result']['structuredContent'], {'echo': 'actual MCP'})
        with self.assertRaises(ValueError):
            approved_tools(self.root, [{'server': 'fixture', 'name': 'blocked'}])
        stale = dict(session.external_tools[name])
        stale['descriptor'] = {**stale['descriptor'], 'description': 'old description'}
        with self.assertRaisesRegex(ValueError, 'definition changed'):
            exchange(self.root, 'fixture', name='echo', arguments={'text': 'no'}, expected=stale, timeout=10)
        self.assertEqual(ToolSession(self.root, {}).tools, [])
