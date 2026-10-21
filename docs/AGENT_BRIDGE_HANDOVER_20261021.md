# OpenCode / skills / MCP handover — 2026-10-21

The first bridge milestone is implemented. The GUI now defaults to the explicit
OpenCode agent route, forwarding selected skills and per-message tool grants.
Direct Ollama chat remains selectable. The backend's legacy incoming engine
default remains compatible; new GUI agent requests carry engine=opencode.

Tested application: **0d9950a75e1045a58bfbd90017ee3195d21533d9**.
[CI](https://github.com/Dr-Dark92/SMELTER/actions/runs/39573778988),
[progress](AGENT_BRIDGE_PROGRESS.md), [plan](AGENT_BRIDGE_PLAN.md),
[evidence](agent-bridge-evidence.json),
[runtime instructions](../tools/dashboard/OPENCODE_RUNTIME.md).

## Call path

| Stage / code | Responsibility |
| --- | --- |
| dashboard_shell.js / Send | Collect engine, selected skills, task grants, approval and configuration/policy revisions |
| chat_jobs.Jobs.start | Validate admission, freeze access/configuration and construct AgentBridge before the worker starts |
| skill_context.selected_context | Shared engine selection; load ready enabled startup snapshots and hash actual instruction text |
| agent_bridge.AgentBridge | Own approved descriptors, skill references and the host ToolSession; instructions cannot expand grants |
| opencode_sandbox.ManagedClient | Start owned no-network container with read-only source/proxy assets and local-model relay |
| opencode_runtime.ask | Check API/version/provider and MCP connection, create/verify exact session rules, then submit task |
| opencode_mcp_proxy.mjs | Serve bounded MCP initialize/list/call over stdio; relay calls through the container tmpfs queue |
| ManagedClient._relay / _response | Distinguish admitted model requests from MCP calls; no arbitrary URLs/commands accepted |
| AgentBridge.call -> ToolSession.execute | Revalidate scope, deduplicate fixed writes, apply call limits and collect real controller/file receipts |
| mcp_connections -> mcp_server -> tool_registry | Execute the existing registered Python capabilities over actual MCP |
| ask -> execution_store.finalize | Combine labelled OpenCode activity and controller receipts; atomically save transcript and outcome |

No connector is added for each skill. The bridge exposes the current shared
registered capability schemas. REA, GLB inspection, diagnostic reports and the
existing frontend CSS operations retain their implementation-specific contracts.
Blender instructions still need an actual modeling tool before they can act.

## Verified

- Native Windows/Linux: 371 dashboard tests each; Linux skips 2, Windows skips 3.
- Each OS: 32 setup tests, 4 analysis tests and 15 JavaScript tests passed.
- Real Chromium: selected skills, write grant and OpenCode approval reach the
  outgoing task; consumed approval boxes reset. Responsive/GLB checks also pass.
- Real OpenCode 1.19.3 in the production managed Docker path: selected documentation
  instructions reach the synthetic model; OpenCode discovers and calls the MCP
  tool. Two model fixture requests complete the tool/result loop.
- A 68-byte report is written through the actual Python MCP server. Its saved
  bytes and controller receipt SHA-256 independently match:
  `dfe22aa9e274e9f3b4487c10cc6c3456df909d30d3f8544abb9e8588951054d1`.
- MCP audit and SQLite execution metadata exist. An unapproved write is denied.
- Managed container cleanup is confirmed. No game/user production data is used.
- Changed skills, out-of-scope paths, exclusions, output bounds, cancellation,
  duplicate writes and follow-up failure retention have regressions.

The local browser download was unavailable, so actual browser validation ran in
GitHub Actions. A separate explicit local-process smoke also passed; it was not
used as an automatic production fallback. No live Qwen inference was performed.

## Run and inspect

Stop the old dashboard before updating. Use the new authenticated launch URL.

```fish
cd ~/dev/SMELTER
and git switch SMELTERV1
and git pull --ff-only origin SMELTERV1
and python -m unittest discover -s tools/dashboard -p 'test_agent_bridge.py'
and python tools/dashboard/dashboard.py --no-browser
```

Pinned MCP installation and managed Docker/image prerequisites are documented in
the runtime instructions. The contract command skips actual MCP cases if the
optional SDK is unavailable; inspect the skip count rather than assuming they ran.

For the rig's GUI smoke: create a titled chat, select the documentation skill,
select OpenCode, approve new diagnostic Markdown, check managed OpenCode and
approve one session. Ask it to call smelter_write_diagnostic_markdown to write
agent-bridge-smoke.md with a short explicit marker. Inspect the controller path,
bytes/hash and the actual file. Existing files receive a suffix rather than an
overwrite. This invokes the real model and should wait until rig testing is allowed.

The CLI --image smoke uses real OpenCode/MCP and synthetic model replies. It
requires free fixture port 11434 and refuses to stop an existing service.
The explicit --live variant uses existing local Qwen and performs no model pull.
Both operate on disposable workspace/database state.

## Limits and next milestone

The container source mount remains read-only and native edits, shell, delegation
and external directories remain denied. Host tools use their explicit scopes.
The frontend workspace grant is still CSS-only with fixed validation/preview;
generic multi-file editing was not introduced. Arbitrary external MCP remains
blocked. Image prompts are not forwarded; approved GLBs provide metadata only.

Stop prevents further bridge admission. An active fixed operation may finish
within its existing transport bound; task finalization waits for its receipt in
the worker, while the Stop HTTP handler remains responsive. Unconfirmed cleanup
is reported and must be inspected before more work.

Existing V2 copies are preserved. A stale frontend baseline can still fail
validation; do not delete or reset user changes to bypass it. Next milestones
are confined general patch/test/review support, safe V2 refresh, an external MCP
confinement adapter and real-model task quality/performance measurements.
