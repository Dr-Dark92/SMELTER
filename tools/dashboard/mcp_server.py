"""SMELTER's stdio MCP server. Grants come from its launcher, never tool text."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from python_tools import ToolSession


async def serve(root, grants):
    import mcp.types as types
    from mcp.server.lowlevel import Server, NotificationOptions
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    session = ToolSession(root, grants)
    # Persistent children cannot belong to this short-lived stdio process.
    # The dashboard handles the preview lifecycle locally, including when
    # all other workspace operations use MCP.
    session.tools = [item for item in session.tools
                     if item['function']['name'] != 'launch_frontend_preview']
    server = Server('smelter-python-tools')

    @server.list_tools()
    async def list_tools():
        return [types.Tool(name=item['function']['name'], description=item['function']['description'],
                           inputSchema=item['function']['parameters']) for item in session.tools]

    @server.call_tool()
    async def call_tool(name, arguments):
        # Run fixed operations off the protocol event loop; ToolSession audits,
        # validates scopes, limits calls and denies unapproved operations.
        result = await asyncio.to_thread(session.execute, {'function': {'name': name, 'arguments': arguments}})
        envelope = {'tool_result': result, 'audit_path': str(session.audit_path)}
        return types.CallToolResult(content=[types.TextContent(type='text', text=json.dumps(envelope))],
                                    structuredContent=envelope, isError=result.get('status') == 'error')

    async with stdio_server() as (read, write):
        await server.run(read, write, InitializationOptions(server_name='smelter-python-tools',
            server_version='0.1.0', capabilities=server.get_capabilities(
                notification_options=NotificationOptions(), experimental_capabilities={})))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    grants = json.loads(os.environ.get('SMELTER_MCP_GRANTS', '{}'))
    asyncio.run(serve(args.root.resolve(), grants))


if __name__ == '__main__':
    main()
