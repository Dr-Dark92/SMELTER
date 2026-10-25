> Current restriction: GUI discovery and execution of arbitrary external MCP servers are blocked pending process confinement. Built-in SMELTER MCP is supported. External-server configuration/protocol examples below describe low-level operator capabilities, not permission to run them from the GUI. See [current system documentation](../../docs/SYSTEM_DOCUMENTATION.md).

# SMELTER MCP layer (stdio, version 1)

The current host bridge also exposes explicitly granted fixed Ghidra operations
and read-only Melty lookup. See [REA/Ghidra](../../docs/REA_GHIDRA_INTEGRATION.md)
and [Melty](../../docs/MELTY_CONNECTOR.md). Melty HTTPS calls occur on the host;
the OpenCode container remains without network or credentials. Arbitrary
external MCP servers are still blocked.

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

## Saved GLB inspection

Attach a GLB to a titled conversation, then select its **Allow read-only GLB
inspection** checkbox under the next-message permissions (up to eight files).
Select MCP routing to expose `inspect_model_attachment` over the same server.
The model receives the approved attachment IDs and filenames; the tool schema
limits IDs to that selection. The chat backend rejects attachments belonging to
another conversation. Neither discovery nor an enabled skill grants file access.

The inspector reads the saved original bytes without Blender, rendering,
extraction or modification. It returns mesh/material/image/node counts, skin
counts and joint counts, original clip names, saved display labels, and the last
keyframe time as duration. It reads embedded FLOAT/SCALAR time accessors rather
than trusting declared accessor min/max values. Nonfinite or unordered timestamps
are rejected. Unsupported sparse layouts and a bounded 250,000-value timing
budget produce unknown durations, not invented values. Paginate clip lists with
`animation_offset` and `animation_limit` (default 50, maximum 100).

Structural metadata does not identify animation meanings, visually verify the
character, or prove compatibility with an engine. Zero-duration tracks are
reported explicitly. The controller records the inspected GLB's SHA-256.

The connection panel now separates SDK availability, the timestamped last
**discovery snapshot**, and current next-message selections. Changing/resetting
permissions marks built-in discovery results as historical instead of leaving a
misleading current “No tools exposed” claim.

## Isolated frontend development tools

Check **Allow isolated frontend workspace** and MCP routing for the next message.
The original checkout is the source. The fixed sibling destination is the source
folder name plus `V2`: `C:\SMELTER` becomes `C:\SMELTERV2`. Model arguments cannot
choose another source, destination, port, shell command or executable.

The tools are:

- `frontend_workspace_info`: actual paths, capabilities and enabled design skills.
- `read_enabled_design_skill`: an actual enabled skill manifest, selected by ID.
- `prepare_frontend_workspace`: create a new isolated copy, or preserve/reuse an
  existing managed copy. An unmanaged destination is never overwritten.
- `read_frontend_file`: bounded CSS/JavaScript reading from a fixed file allowlist.
- `replace_frontend_css`: exact substring replacement with the full CSS SHA-256.
- `validate_frontend_workspace`: original-source hash checks, backend AST checks,
  identical non-CSS HTML and JavaScript, then fixed Python/JavaScript tests.
- `launch_frontend_preview`: launch only the validated copy on port 8770 and verify
  its authenticated startup response before reporting a URL and process ID.

This version supports **CSS redesign**, not arbitrary code editing. It can change
layout, typography, colors, spacing and component presentation while preserving
all JavaScript, markup outside the style block, Python backend, routes, methods,
request/response contracts and database schemas. Attempts to change those surfaces
block validation/launch. Browser visual inspection is still manual and must not
be reported as an automated pass.

The copy includes code, skill references, local viewer/REA dependencies, and selected
non-secret legacy configuration. It excludes projects, Git metadata, databases,
model weights, runtime logs and agent configuration. Symlinks/junctions are not
copied. The copy is bounded to 20,000 files and 1 GiB. It uses a **fresh independent**
database in `C:\SMELTERV2-Data`; original chat history and assets are not migrated.
Preparation failure may leave that newly initialized data directory for review;
existing directories are never deleted to force a retry.

Workspace permission raises only that message's aggregate tool budget to 24 calls,
with at least a 900-second model-turn timeout and up to 4096 response tokens
(capped at half the configured context). These temporary values do not alter
saved runtime settings or ordinary chat limits. Fixed validation is bounded to
90 seconds total. Stop prevents subsequent calls; an active copy/validation may
finish first. Repeated reads and validations stay fresh after edits.

The preview is a separate process and does not stop the original application.
The dashboard owns preview creation, even when workspace operations use MCP.
Its receipt records `transport: python` and `process_owner: dashboard`. The
short-lived stdio server exposes six workspace operations and deliberately
omits preview launch: Windows MCP cleanup can terminate the server's children.
The chat controller still offers the seventh, dashboard-owned launch operation.
Open its returned URL manually. To stop that preview on Windows, use
`Stop-Process -Id <the returned preview PID>` after verifying the PID in the
receipt. An occupied port blocks launch; tools do not kill an existing listener.
Launch URLs contain a session token and are recorded in local tool receipts/logs.

Suggested prompt (with the workspace permission checked):

```
Use the frontend workspace tools to redesign SMELTER's presentation in its isolated
V2 copy. Call frontend_workspace_info, read up to three actual enabled design
skills, prepare the workspace, and inspect its CSS. Use a coherent design that
improves chat readability, navigation, typography, forms and status visibility.
Apply real hash-checked CSS edits. Preserve all backend, API and JavaScript
behavior. Run validation; launch the validated preview on port 8770. Report only
actual tool results, the skills used and the returned URL. Mark visual inspection
as manual. Do not invent skills or claim completion without saved changes and
successful validation.
```
