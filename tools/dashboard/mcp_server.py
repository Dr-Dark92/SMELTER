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
                 'For repository inspection, recover an existing task workspace first; if none exists, call prepare_coding_workspace once, '
                 'retain its returned workspace_id, and use list_coding_files/read_coding_file '
                 'with that ID and the original project-relative paths. '
                 'Existing mod source is under mods/ in that coding copy. '
                 'These adapters cover tools/, skills/, mods/ and their permitted top-level documents; '
                 'docs/ and .smelter/ are outside the coding-file adapter. '
                 'Use propose_coding_restore for missing or altered baseline files: supply the workspace ID '
                 'and original relative paths; the controller captures original bytes and current destination hashes. '
                 'Review and apply its proposal with apply_coding_patch; no manual hash calculation is needed. '
                 'Proposals, edits and tests use the same isolated copy; a proposal is not a source merge. ')
        text += ('Recover forgotten locations with coding_workspace_context: omit its workspace_id to list '
                 'managed copies, or pass the existing ID and filename query to refresh the file index. '
                 'read_coding_file supports start_line/line_count, or character offset/limit; do not mix them. ')
        text += ('For focused fixes prefer propose_coding_edit: five flat string arguments workspace_id, relative_path, expected_sha256, old_text, new_text. '
                 'For a batch use propose_coding_edits with a real changes array and UNIQUE file paths; group a file\'s replacements in one edits array. '
                 'the controller preserves all unrelated bytes. propose_coding_patch.content replaces the ENTIRE file, '
                 'never just a snippet or diff. Review before_lines/after_lines and the diff before apply. '
                 'Large accidental truncations are rejected. Apply receipts and workspace context expose saved '
                 'pre-edit checkpoint hashes. To recover workspace-only files use propose_coding_restore with one '
                 'relative_path in relative_paths plus checkpoint_sha256; the checkout baseline cannot restore a '
                 'file that exists only in the coding copy. ')
        text += ('coding_workspace_context and coding_recovery_context expose operator-frozen acceptance contracts. '
                 'These verifiers are outside the editable copy and run automatically with their profile. Overall GREEN requires both workspace tests and frozen acceptance. '
                 'Never relax strict validation to match a comment or incidental reason-code assertion in an editable test; preserve the frozen behavior and report the contradiction. ')
        text += ('A test RED is intermediate validation, not a task end. Continue the requested fix. '
                 'Only when actually finished, call finish_coding_task with the existing workspace_id, '
                 'outcome GREEN or a final unsuccessful RED, and every relevant test profile. '
                 'The controller verifies current receipts before accepting this explicit end flag. ')
        text += ('If an edit fails or you lose the task location, use coding_recovery_context with the existing workspace ID. '
                 'It returns current hashes, canonical paths, verified checkpoints and the first failing test frame. '
                 'CRLF/LF contexts are matched by the controller; do not repeatedly re-read a file to guess line endings. '
                 'Two identical failed calls or four identical unchanged reads trigger a recovery redirect. '
                 'Read the cause before its callers; a runtime error is not a syntax error. Preserve frozen acceptance '
                 'criteria and regression fixtures, and never bypass a rejected proposal with native shell/edit. '
                 'Recover within this task; do not restart the workspace, weaken tests, approve access or resume cancelled tasks. ')
        text += ('Load the diagrams skill for task relationships. Refresh the exact workspace context after changes '
                 'and tests and at task completion; its SHA-256 ledger and relations.mmd preserve the handoff. '
                 'Static/inferred imports and snapshot test receipts do not establish in-game behavior. ')
        text += ('Each test invocation copies current source into a NEW read-only bind-mounted snapshot. '
                 'The pinned Docker image supplies the runtime/toolchain, not cached project source; do not rebuild it '
                 'or create a new workspace to refresh edits. Lua receipts expose source_snapshot hashes, test_programs '
                 'working directories and actual standard-loader import paths. profile=mods runs Python tests; '
                 'profile=lua runs Lua tests from mods/<project>. A:B(x) inserts A as argument one, '
                 'whereas A.B(x) does not. Inspect the declared signature and returned value before blaming caching. ')
        try:
            from access_policy import current, using
            from workspace_tracking import registry
            with using(current(root)):
                copies = registry(root)['workspaces']
            if copies:
                text += 'Known HOST coding directories: ' + json.dumps([
                    {'workspace_id': row['workspace_id'], 'host_directory': row['workspace_root']} for row in copies]) + '. '
        except (ValueError, OSError):
            pass
        from coding_profiles import automatic_coding_enabled
        if automatic_coding_enabled(root):
            text += ('The ECC instruction bridge is enabled. In native OpenCode, load the task-relevant '
                     'skill profiles before coding: ecc-tdd-workflow/ecc-verification-loop for implementation, '
                     'smelter-debugging for syntax/path failures, gameplay-testing for controller behavior, '
                     'or ecc-cpp-standards/ecc-cpp-testing for native code. Load only two or three profiles. '
                     'These instructions do not install ECC hooks or grant tools. ')
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
    from recovery_guard import PersistentBudget
    session.persistent_budget = PersistentBudget()
    session.validate_tool_arguments = True
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

    @server.call_tool(validate_input=False)
    async def call_tool(name, arguments):
        # ToolSession validates the SAME advertised schema before execution so
        # malformed calls enter budgets, guards and audits instead of bypassing
        # them in the SDK's verbose, unaudited pre-handler error path.
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
