import asyncio
from datetime import timedelta
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

from rea_mcp_gateway import Catalog, definitions, encoded, pointer_get

ROOT = Path(__file__).resolve().parents[2]
HAS_MCP = importlib.util.find_spec('mcp') is not None


class GatewayCatalogTests(unittest.TestCase):
    def test_manifest_is_small_and_does_not_embed_upstream_schemas(self):
        self.assertEqual(len(definitions()), 3)
        self.assertLess(len(encoded(definitions())), 2400)

    def test_json_pointers_handle_escaped_keys_and_reject_invalid_paths(self):
        value = {'a/b': {'~name': [True, 42]}}
        self.assertEqual(pointer_get(value, '/a~1b/~0name/1'), 42)
        for path in ('a', '/a~2b', '/missing', '/a~1b/~0name/-1', '/a~1b/~0name/01'):
            with self.assertRaises(ValueError): pointer_get(value, path)

    def test_large_schema_is_navigable_without_silent_truncation(self):
        catalog = Catalog(None)
        schema = {'type': 'object', 'properties': {'small': {'type': 'integer'},
                  'large': {'enum': ['example' * 20 + str(i) for i in range(500)]}}}
        catalog.tools = {'fixture': SimpleNamespace(name='fixture', description='Fixture', inputSchema=schema)}
        summary = catalog.describe('fixture', max_chars=1000)
        self.assertFalse(summary['complete']); self.assertNotIn('schema', summary)
        self.assertIn('/properties', [child['pointer'] for child in summary['children']])
        part = catalog.describe('fixture', '/properties/small', max_chars=1000)
        self.assertTrue(part['complete']); self.assertEqual(part['schema'], {'type': 'integer'})
        page = catalog.describe('fixture', '/properties/large/enum', max_chars=1000)
        self.assertEqual(page['next_offset'], 30)
        self.assertEqual(catalog.describe('fixture', '/properties/large/enum', max_chars=1000, offset=30)['children'][0]['pointer'], '/properties/large/enum/30')

    def test_catalog_pagination_and_search_keep_every_operation(self):
        class Upstream:
            async def list_tools(self, cursor=None):
                start, end = (0, 100) if cursor is None else (100, 207)
                return SimpleNamespace(tools=[SimpleNamespace(name='tool_' + str(i), description='Ghidra native binary' if i == 206 else 'Other', inputSchema={}) for i in range(start, end)], nextCursor='next' if cursor is None else None)
        async def run():
            catalog = Catalog(Upstream()); await catalog.refresh()
            self.assertEqual(len(catalog.tools), 207)
            result = await catalog.search('Ghidra binary')
            self.assertEqual(result['tools'][0]['name'], 'tool_206')
            self.assertEqual((await catalog.search('', offset=200))['next_offset'], None)
            with self.assertRaisesRegex(ValueError, 'Unknown REA'): catalog.describe('missing')
        asyncio.run(run())

    def test_repeated_catalog_cursor_is_rejected(self):
        class Upstream:
            async def list_tools(self, cursor=None):
                return SimpleNamespace(tools=[], nextCursor='same')
        with self.assertRaisesRegex(ValueError, 'repeated'):
            asyncio.run(Catalog(Upstream()).refresh())

    @unittest.skipUnless(HAS_MCP, 'Optional MCP SDK unavailable')
    def test_invalid_calls_are_rejected_before_reaching_upstream(self):
        class Upstream:
            async def call_tool(self, *args, **kwargs):
                raise AssertionError('Invalid arguments reached the backend')
        catalog = Catalog(Upstream())
        catalog.tools = {'fixture': SimpleNamespace(inputSchema={'type': 'object', 'properties': {'count': {'type': 'integer'}}, 'additionalProperties': False})}
        async def run():
            for args in ('[]', '{"count": "wrong"}', '{"count": NaN}', '{"extra": true}'):
                with self.assertRaises(ValueError): await catalog.invoke('fixture', args)
            with self.assertRaisesRegex(ValueError, 'Unknown REA'): await catalog.invoke('missing', '{}')
        asyncio.run(run())

    @unittest.skipUnless(HAS_MCP, 'Optional MCP SDK unavailable')
    def test_real_stdio_gateway_preserves_arguments_environment_roots_errors_and_progress(self):
        async def run(folder):
            import mcp.types as types
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            async def roots(context):
                return types.ListRootsResult(roots=[types.Root(uri=folder.as_uri())])
            command = [str(Path(__file__).resolve()), '--fixture-backend']
            parameters = StdioServerParameters(command=sys.executable,
                args=[str(ROOT / 'tools/dashboard/rea_mcp_gateway.py'), '--', sys.executable, *command],
                cwd=str(folder), env={**os.environ, 'REA_GATEWAY_FIXTURE': 'preserved', 'REA_GATEWAY_CANCEL_MARKER': str(folder / 'cancelled')})
            async with asyncio.timeout(25):
                async with stdio_client(parameters) as (read, write):
                    async with ClientSession(read, write, list_roots_callback=roots, read_timeout_seconds=timedelta(seconds=10)) as client:
                        initialized = await client.initialize()
                        self.assertIn('Fixture upstream instructions', initialized.instructions)
                        listed = await client.list_tools(); self.assertEqual(len(listed.tools), 3)
                        search = await client.call_tool('search_tools', {'query': 'echo'})
                        self.assertEqual(search.structuredContent['tools'][0]['name'], 'fixture_echo')
                        described = await client.call_tool('describe_tool', {'name': 'fixture_echo'})
                        self.assertTrue(described.structuredContent['complete'])
                        invalid = await client.call_tool('call_tool', {'name': 'fixture_echo', 'arguments_json': '{"field":"bad"}'})
                        self.assertTrue(invalid.isError)
                        progress = []
                        async def onprogress(value, total=None, message=None): progress.append((value, message))
                        result = await client.call_tool('call_tool', {'name': 'fixture_echo', 'arguments_json': '{"field":7}'}, progress_callback=onprogress)
                        self.assertFalse(result.isError)
                        self.assertEqual(result.structuredContent['field'], 7)
                        self.assertEqual(result.structuredContent['marker'], 'preserved')
                        self.assertEqual(Path(result.structuredContent['cwd']), folder)
                        self.assertEqual(result.structuredContent['roots'], [folder.as_uri()])
                        self.assertIn((1, 'Fixture progress'), progress)
                        error = await client.call_tool('call_tool', {'name': 'fixture_fail', 'arguments_json': '{}'})
                        self.assertTrue(error.isError)
                        self.assertEqual(error.structuredContent, {'status': 'fixture_error'})
                        self.assertEqual(error.content[0].text, 'Original fixture error')
                        # The pinned Python SDK does not send protocol cancellation
                        # when a local asyncio waiter is cancelled; emulate the JS client.
                        request_id = client._request_id
                        pending = asyncio.create_task(client.call_tool('call_tool', {'name': 'fixture_wait', 'arguments_json': '{}'}))
                        for _ in range(40):
                            if (folder / 'started').exists(): break
                            await asyncio.sleep(0.05)
                        self.assertTrue((folder / 'started').exists())
                        await client.send_notification(types.ClientNotification(types.CancelledNotification(
                            params=types.CancelledNotificationParams(requestId=request_id, reason='Fixture cancellation'))))
                        from mcp import McpError
                        with self.assertRaises(McpError): await pending
                        for _ in range(40):
                            if (folder / 'cancelled').exists(): break
                            await asyncio.sleep(0.05)
                        self.assertTrue((folder / 'cancelled').exists(), 'Cancellation did not reach the backend')
                        resumed = await client.call_tool('call_tool', {'name': 'fixture_echo', 'arguments_json': '{"field":8}'})
                        self.assertEqual(resumed.structuredContent['field'], 8)
        with tempfile.TemporaryDirectory() as temporary:
            asyncio.run(run(Path(temporary).resolve()))


async def fixture_backend():
    import mcp.types as types
    from mcp.server.lowlevel import Server, NotificationOptions
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    server = Server('fixture', instructions='Fixture upstream instructions')
    @server.list_tools()
    async def list_tools():
        return [types.Tool(name='fixture_echo', description='Echo fixture and check roots', inputSchema={
            'type': 'object', 'properties': {'field': {'type': 'integer'}}, 'required': ['field'], 'additionalProperties': False}),
            types.Tool(name='fixture_fail', description='Return fixture error', inputSchema={'type': 'object', 'properties': {}, 'additionalProperties': False}),
            types.Tool(name='fixture_wait', description='Wait for fixture cancellation', inputSchema={'type': 'object', 'properties': {}, 'additionalProperties': False})]
    @server.call_tool()
    async def call_tool(name, arguments):
        if name == 'fixture_wait':
            marker = Path(os.environ['REA_GATEWAY_CANCEL_MARKER'])
            marker.with_name('started').write_text('started')
            try:
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                marker.write_text('cancelled')
                raise
        if name == 'fixture_fail':
            return types.CallToolResult(isError=True, structuredContent={'status': 'fixture_error'},
                content=[types.TextContent(type='text', text='Original fixture error')])
        context = server.request_context
        if context.meta and context.meta.progressToken is not None:
            await context.session.send_progress_notification(context.meta.progressToken, 1, 1, 'Fixture progress')
        roots = await context.session.list_roots()
        return {'field': arguments['field'], 'marker': os.environ.get('REA_GATEWAY_FIXTURE'),
                'cwd': str(Path.cwd()), 'roots': [str(root.uri) for root in roots.roots]}
    async with stdio_server() as (read, write):
        await server.run(read, write, InitializationOptions(server_name='fixture', server_version='1',
            instructions='Fixture upstream instructions', capabilities=server.get_capabilities(NotificationOptions(), {})))


if __name__ == '__main__':
    if sys.argv[1:] == ['--fixture-backend']:
        asyncio.run(fixture_backend())
    else:
        unittest.main()
