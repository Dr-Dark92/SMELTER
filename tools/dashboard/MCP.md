# SMELTER MCP layer (stdio, version 1)

SMELTER now acts as an MCP host/client and ships a local Python MCP server.
The model remains Qwen through Ollama. No weight training is involved.

## Install and run

The optional SDK is pinned to MCP Python SDK 1.30.0 (the v1 API).
Install it into the same Python interpreter that runs the dashboard:

```powershell
python -m pip install -r tools/dashboard/requirements-mcp.txt
python -m unittest discover -s tools/dashboard -p "test_*.py"
python tools/dashboard/dashboard.py
```

On Arch/CachyOS, use a virtual environment rather than modifying system Python:

```fish
python -m venv .smelter/dashboard-venv
.smelter/dashboard-venv/bin/python -m pip install -r tools/dashboard/requirements-mcp.txt
.smelter/dashboard-venv/bin/python tools/dashboard/dashboard.py
```

The dashboard and direct Python tools still work without the optional SDK.
SDK integration tests skip when that dependency is unavailable or incompatible.

## Built-in tools over MCP

1. Open **Tools & Integrations → MCP Connections**.
2. Select folder inventory, diagnostics, or REA permissions in the chat's tool controls.
3. Click **Start server and discover tools** with server `smelter` selected.
   Discovery starts a temporary process and lists only permitted tools. It does
   not call an inventory, write, or REA operation.
4. Check **Route built-in tools through MCP for the next message** and Send.
5. Inspect the controller's result, `[MCP]` transport label and audit paths.

The shared `tool_registry.py` defines the built-in tool schemas and exact
handlers. Both transports use the same registry. The MCP server delegates to
ToolSession, including scope checks, call limits, deduplication and disk audit.
The parent chat turn retains its own aggregate call limit and deduplication.
Permission checkboxes reset on Send. REA still requires its enabled skill and
installed runtime. MCP does not install REA or interpret skill Markdown as code.

## Additional local servers

Use the configuration editor to save this shape. Replace the example executable,
script, working directory and tool name with values for a server you trust:

```json
{
  "schema_version": 1,
  "servers": [
    {
      "id": "asset-tools",
      "command": "C:\\Tools\\Python\\python.exe",
      "args": ["C:\\Tools\\asset-tools\\server.py"],
      "cwd": "C:\\Tools\\asset-tools",
      "enabled": true,
      "allowed_tools": ["inspect_asset"]
    }
  ]
}
```

Configuration lives in `.smelter/mcp-servers.json`. Saving starts no process.
Command/cwd must exist and be absolute, without symlinks, junctions or traversal.
Use the executable's real resolved path on Linux. There is no automatic `npx`,
`uvx`, package install or shell interpolation. Arguments are passed as an array.
Keep credentials out of command arguments. Custom environment variables and
network transports are not supported by this first version.

After saving, explicitly discover the server. Tools outside `allowed_tools` are
shown as blocked. Allowed tools get **next message** checkboxes in the chat's
permission controls. No tools are automatically granted because a server or
skill exists. At message start SMELTER discovers selected tools; calls verify
that the connection configuration and tool definition still match that turn's
snapshot. Model-facing aliases include a stable server/tool hash to avoid name
collisions. Results and their originating server/tool are recorded separately
from model prose. A missing SDK/server is an error; there is no silent fallback.

## Boundaries and lifecycle

- Local **stdio only**, using the official SDK's initialize/list/call flow.
- A fresh process per discovery or call, with SDK-managed cleanup. This is
  intentionally stateless: do not depend on a previous call's in-memory state.
- External servers execute as the OS user. Tool allowlists and chat checkboxes
  are application permissions, **not an OS sandbox**. Built-in folder grants do
  not constrain arbitrary third-party server code or its startup actions.
- Up to 12 configured servers, 128 tools per server, 16 selected external tools
  per message, and 4 actual tool requests per turn (shared with built-in tools).
- Discovery: 20 seconds; calls: 120 seconds including startup. Stop prevents
  later calls; an active tool may continue until it returns or reaches its
  bound. A timeout does not prove that a side effect was rolled back.
- Results above 256 KiB are rejected; an action may already have completed.
  The child's built-in audit and parent requested/result audit remain distinct.
- No persistent daemon, remote HTTP/SSE transport, server resource/prompt browser,
  custom credentials, automatic skill-to-tool generation, or OS isolation yet.

## Standalone use

Other MCP clients may launch `python tools/dashboard/mcp_server.py --root C:\\SMELTER`.
The default grant is empty: no tools. Trusted launchers can set
`SMELTER_MCP_GRANTS` to a JSON object with the existing built-in permission keys
(`inventory_root`, `write_diagnostics`, `rea_root`, `rea_analysis`). The server
never accepts a tool call that changes those grants.
