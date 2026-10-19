# SMELTER Vanilla V1.3.1 dashboard

Launch on Windows from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\dashboard\start_dashboard.ps1
```

The dashboard listens only on `127.0.0.1:8768` by default. API calls require the browser session token. Extension activation is persisted to `.smelter/extensions.json` and does not install packages, launch Blender/FFmpeg/7-Zip, or grant process execution permissions.

Extension health values:

- `ready`: enabled and its executable was verified by the requirements scanner
- `available_disabled`: verified executable, extension not enabled
- `dependency_unavailable`: missing or unverified executable, including an enabled extension whose dependency disappeared

All permissions shown are declarations, **not grants**. Workflow execution and explicit permission approvals are future work.

Run tests:

```powershell
py -3 -m unittest discover -s tools\dashboard -p "test_*.py" -v
```

No AI, bundled optional tools, or network downloads are required for the unit tests.

## Python tools in local Qwen chat

Open **Python tools for the next message** below the chat. Both permissions are
off by default and reset after Send (including a failed Send):

- Enter an absolute folder and check **Allow read-only inventory** to expose
  `inventory_directory`. It lists metadata only, not file contents. It never
  launches the game, extracts archives, or identifies a mesh from file bytes.
- Check **Allow new Markdown reports in diagnostics/** to expose
  `write_diagnostic_markdown`. It creates UTF-8 LF files of at most 32 KiB in
  this checkout's `diagnostics/`. Existing names receive numeric suffixes.

The native Ollama `/api/chat` tool-calling loop has four calls and a 180-second
turn budget. Inventory is limited to depth 8, 3,000 observed entries, 150 listed
entries, and a five-second traversal budget between filesystem operations.
The result declares partial coverage. OS filesystem calls may themselves block;
this is a local application permission boundary, not an OS sandbox against a
hostile local process changing paths concurrently. Links/junctions/reparse points
and inventory roots including `projects/` are rejected. No arbitrary Python,
shell, file-content reader, MCP, REA executable, or Blender execution is added.

Structured calls/results are recorded in `.smelter/tool-runs/*.jsonl`. Chat
history includes controller-generated receipts with the actual saved report
path, byte count and SHA-256, or errors. A failed model follow-up after a tool
action keeps its receipts. Repeated identical requests within a turn reuse the
first successful result instead of writing another file.

Enabled skills still need selection in **Skills Manager** (or supported auto
routing) to enter the prompt. The skill reference budget is 48,000 characters,
at most three skills, and tool/skill chats request a 32,768-token Ollama context.
This can use more model memory than plain chat. Large history is bounded to the
most recent whole messages within 12,000 characters.

First Windows smoke test (not exercised by the offline unit tests):

1. Restart the dashboard and create a new conversation.
2. Approve diagnostic writing for the next message.
3. Send: `Use write_diagnostic_markdown to create python-tool-smoke.md with
   content "# Python tool smoke test". Report the actual saved path and hash.`
4. Confirm a controller receipt and the file in `diagnostics/`.
5. For the game test, approve inventory of `D:\Epic\Darksiders` and diagnostic
   writing. Ask Qwen to inventory the approved folder, write a handover using
   the actual metadata returned, mark partial coverage, and make no extraction
   or game-engine/War mesh identification claims without evidence.
