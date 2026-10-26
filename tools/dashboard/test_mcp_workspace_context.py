import asyncio
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import timedelta

from mcp_server import workspace_instructions
from database import select_database

ROOT = Path(__file__).resolve().parents[2]


class WorkspaceContextTests(unittest.TestCase):
    def test_instructions_distinguish_source_inventory_and_memory_references(self):
        source = Path.cwd() / 'fixture-source'; game = str(Path.cwd() / 'fixture-game')
        value = workspace_instructions(source, {'coding_workspace': True, 'inventory_root': game, 'project_memory': True})
        self.assertIn(json.dumps(str(source.resolve())), value)
        self.assertIn(json.dumps(game), value)
        self.assertIn('prepare_coding_workspace', value); self.assertIn('read_coding_file', value)
        self.assertIn('workspace_id', value); self.assertIn('not the Melty working folder', value)

    def test_ungranted_repository_is_not_advertised_as_a_readable_scope(self):
        value = workspace_instructions(Path.cwd() / 'private-source', {})
        self.assertNotIn('private-source', value)
        self.assertNotIn('prepare_coding_workspace', value)
        self.assertNotIn('inventory_directory', value)

    @unittest.skipUnless(importlib.util.find_spec('mcp'), 'Optional MCP SDK unavailable')
    def test_real_initialize_from_empty_client_directory_can_route_to_existing_mod(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); source = base / 'SMELTER'; caller = base / 'Melty-project'
            caller.mkdir(); (source / 'tools/dashboard').mkdir(parents=True); (source / 'skills').mkdir()
            (source / 'tools/dashboard/dashboard.py').write_text('VALUE=1\n')
            mod = source / 'mods/gta-ark/README.md'; mod.parent.mkdir(parents=True)
            mod.write_text('Existing prototype fixture; game runtime unverified.\n')
            select_database(source, str(base / 'data'))
            async def run():
                from mcp import ClientSession, StdioServerParameters
                from mcp.client.stdio import stdio_client
                parameters = StdioServerParameters(command=sys.executable,
                    args=[str(ROOT / 'tools/dashboard/mcp_server.py'), '--root', str(source)], cwd=str(caller),
                    env={**os.environ, 'SMELTER_MCP_GRANTS': json.dumps({'coding_workspace': True})})
                async with asyncio.timeout(30):
                    async with stdio_client(parameters) as (read, write):
                        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=15)) as client:
                            initialized = await client.initialize()
                            self.assertIn('prepare_coding_workspace', initialized.instructions)
                            self.assertIn(json.dumps(str(source.resolve())), initialized.instructions)
                            prepared = await client.call_tool('prepare_coding_workspace', {})
                            workspace = prepared.structuredContent['tool_result']
                            self.assertEqual(workspace['status'], 'coding_workspace_ready')
                            actual = await client.call_tool('read_coding_file', {
                                'workspace_id': workspace['workspace_id'], 'relative_path': 'mods/gta-ark/README.md'})
                            result = actual.structuredContent['tool_result']
                            self.assertEqual(result['status'], 'coding_file_read')
                            self.assertIn('Existing prototype fixture', result['text'])
            asyncio.run(run())
            self.assertEqual(list(caller.iterdir()), [])
            self.assertIn('Existing prototype fixture', mod.read_text())


if __name__ == '__main__': unittest.main()
