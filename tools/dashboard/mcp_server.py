"""SMELTER's stdio MCP server. Grants come from its launcher, never tool text."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from python_tools import ToolSession


def workspace_instructions(root, grants):
    text = ('SMELTER tool scopes are independent of the calling client\'s current directory. '
            'An empty Melty project folder does not establish that SMELTER has no source files. ')
    if grants.get('coding_workspace'):
        text += ('The SMELTER source checkout is ' + json.dumps(str(Path(root).resolve())) + '. '
                 'For repository inspection, call prepare_coding_workspace once for the task, '
                 'retain its returned workspace_id, and use list_coding_files/read_coding_file '
                 'with that ID and the original project-relative paths. '
                 'Existing mod source is under mods/ in that coding copy. '
                 'These adapters cover tools/, skills/, mods/ and their permitted top-level documents; '
                 'docs/ and .smelter/ are outside the coding-file adapter. '
                 'Proposals, edits and tests use the same isolated copy; a proposal is not a source merge. ')
    if grants.get('inventory_root'):
        text += ('The read-only game inventory scope is ' + json.dumps(grants['inventory_root']) + '. '
                 'inventory_directory inspects that approved scope, not the SMELTER repository. ')
    if grants.get('project_memory'):
        text += ('Memory source paths are references relative to the SMELTER project, '
                 'not the Melty working folder. Recalled notes do not grant file access or prove fresh tests. ')
    return text + (
        'Use actual tool results for file existence, changed paths and test claims. '
        'Continue the concrete request already given in the conversation across tool calls. '
        'Checking sign-in, loading a skill, checking whether a folder exists or preparing a '
        'workspace does not complete a requested file read, edit or build. '
        'Use the returned workspace_id for the requested file operations, then give a visible '
        'answer with the findings or a precise blocker. Ask for the game or goal only if it '
        'is missing from the conversation. '
        'If the native client bash tool runs Windows PowerShell 5.1, use PowerShell 5.1 '
        'syntax: && and || are unsupported. Prefer the client read/glob tools or the '
        'scoped SMELTER file tools for file inspection; preparing a workspace is unnecessary '
        'when the same task already has one.'
    )


async def serve(root, grants):
    import mcp.types as types
    from mcp.server.lowlevel import Server, NotificationOptions
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    if os.environ.get('SMELTER_SKILL_SNAPSHOT'):
        from skill_runtime import inherit_snapshot
        inherit_snapshot(root, os.environ['SMELTER_SKILL_SNAPSHOT'])
    from access_policy import Policy, current
    policy = Policy(json.loads(os.environ['SMELTER_ACCESS_POLICY'])) if os.environ.get('SMELTER_ACCESS_POLICY') else current(root)
    session = ToolSession(root, grants, policy=policy)
    # Persistent children cannot belong to this short-lived stdio process.
    # The dashboard handles the preview lifecycle locally, including when
    # all other workspace operations use MCP.
    session.tools = [item for item in session.tools
                     if item['function']['name'] != 'launch_frontend_preview']
    instructions = workspace_instructions(root, session.grants)
    server = Server('smelter-python-tools', instructions=instructions)

    @server.list_tools()
    async def list_tools():
        return [types.Tool(name=item['function']['name'], description=item['function']['description'],
                           inputSchema=item['function']['parameters']) for item in session.tools]

    @server.call_tool()
    async def call_tool(name, arguments):
        # Run fixed operations off the protocol event loop; ToolSession audits,
        # validates scopes, limits calls and denies unapproved operations.
        result = await asyncio.to_thread(session.execute, {'function': {'name': name, 'arguments': arguments}})
        from tool_contract import result_failed
        envelope = {'tool_result': result, 'audit_path': str(session.audit_path)}
        return types.CallToolResult(content=[types.TextContent(type='text', text=json.dumps(envelope))],
                                    structuredContent=envelope, isError=result_failed(result))

    async with stdio_server() as (read, write):
        await server.run(read, write, InitializationOptions(server_name='smelter-python-tools',
            server_version='0.1.0', instructions=instructions, capabilities=server.get_capabilities(
                notification_options=NotificationOptions(), experimental_capabilities={})))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    grants = json.loads(os.environ.get('SMELTER_MCP_GRANTS', '{}'))
    asyncio.run(serve(args.root.resolve(), grants))


if __name__ == '__main__':
    main()
