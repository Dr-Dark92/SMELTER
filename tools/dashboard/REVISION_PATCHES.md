# Dashboard revision patches — 2026-10-20

This revision addresses the engineering review on SMELTERV1. It changes the existing dashboard; it does not replace the model, install tools, start OpenCode, or redesign the CSS-only frontend editing adapter into a general coding agent.

## Configuration and task access

Open **Settings** for configuration. **Workspaces & Access** is the central list of absolute local locations. **Review task access** shows the controls for the selected engine and the permissions for its next task. Built-in folder selectors contain registered readable locations. Saving a policy affects new tasks; a running task keeps its admission snapshot and records its revision.

| Default location | Read | Write | Registered execution |
| --- | --- | --- | --- |
| Original checkout | Yes | No | None |
| Sibling development workspace, such as C:\SMELTERV2 | Yes | Yes | Tests and preview |
| Original checkout diagnostics directory | Yes | New reports through the existing create-only tool | None |

Other locations are denied. Filesystem roots, UNC locations, traversal, links/reparse paths, and alternate data streams are rejected. The most specific enabled location applies; its exclusions override its flags. Default exclusions include `.git/**`, `.smelter/**`, and `projects/**`. Disabled rows do not establish a denial beneath an enabled parent: leave a row enabled with its flags off to deny that subtree. Operations remain constrained by the existing adapters: write does not create a generic editor, execute does not grant a shell, and delete is not granted.

To inventory a game folder, add that exact folder with **read** enabled, save, then select it under next-task folder inventory. REA additionally requires the existing explicit REA approval and an execution location for its fixed tooling working directory with operation **rea**. Archive/media/Blender inspections retain their explicit approvals and require their registered operation at the original checkout, where those adapters run. Source-write permission is not needed for execution.

The policy applies to agent-facing registered tools, built-in MCP calls, and the OpenCode adapter's read rules. Database storage, audits, approved skill installations, copied runtime dependencies, and preview bookkeeping are application-owned state. Operator configuration and installation endpoints are not generic model tools.

**This is not an OS sandbox.** Tests and previews execute application code as the current OS user. OpenCode permission rules also depend on the external server honoring its contract. Arbitrary external MCP servers cannot enforce SMELTER's path flags, so GUI discovery and execution of those servers are blocked until a confined runner is implemented. Configurations remain saved; the low-level MCP protocol helpers remain available to explicit operator code. Built-in SMELTER MCP remains supported.

## Review changes

| Review issue | Implemented behavior |
| --- | --- |
| R01: SQLite writes, legacy JSON reads | Dashboard readers use authoritative SQLite configuration. New preview copies inherit current model, extension, and runtime settings into an isolated database. |
| R02: saved model ignored | Direct inference uses the saved reasoning model, with the existing Qwen default when unset. Task summary reflects it. |
| R03: OpenCode loses context | Fresh per-turn sessions receive bounded prior user/assistant text. Old receipts and permission grants are not replayed as authority. |
| R04: follow-up failure says done | Durable receipts remain visible; the outcome is partial with the actual error. Failed tool operations also produce partial outcomes. |
| R05: oldest history only | Latest messages load first, with explicit older-page navigation. Receipt/attachment queries are restricted to the returned page. |
| R06: legacy ask bypasses jobs | Both ask/start actions use the same admission, cancellation, and job controller; ask now returns HTTP 202 and a job descriptor. |
| R07: external reads cached | Blanket tool caching removed. Only the explicit create/write/launch deduplication set is cached. External MCP execution is also blocked at GUI task admission. |
| R08: child MCP resets skill baseline | Parent startup fingerprints travel to child MCP processes. Changed/new skill manifests remain unavailable until dashboard restart. |
| R09: multiple active navigation items | Section navigation clears other active items. |
| R10: squeezed composer and scroll layout | Full-width composer, two-column desktop workspace, and bounded mobile conversation/history areas. |
| R11: mixed engine controls and stale status | Task controls depend on the engine; OpenCode approval lives in task access. Live output is displayed for both engines. Unchecked OpenCode service is labeled not checked. |
| R12: failed initialization blocks retry | Legacy configuration is validated before database creation; failed initialization cleans up only files it created. |
| R13: Windows executable assumptions | POSIX native binaries are accepted by inspection adapters. Windows .exe checks remain; shell-script shims are rejected. |
| R14: no context budget | Direct inference estimates prompt costs, drops complete older turns, and rejects an oversized current task explicitly. The estimate is not exact tokenizer accounting. |

Expected disconnected HTTP clients are handled without attempting a second error response. Windows platform tests use the host's concrete Path class while mocking platform behavior.

## Validation and limits

Regression coverage includes real dashboard HTTP configuration round-trips, model selection, latest/older chat pages, durable partial outcomes, policy snapshots/denials, database retry, inherited skill fingerprints, and OpenCode second-turn context. Real stdio MCP integration tests check copied policy exclusions and rejection of changed skills in newly spawned child processes.

Desktop/mobile Chromium checks use a local HTTP OpenCode fixture: server/model verification, task submission, progress/receipt display, approval reset, history reload, settings navigation, access-policy save, and composer width. These verify the bridge and UI; they do not measure Qwen quality or prove behavior of the user's installed Windows OpenCode process.

Local validation commands:

```powershell
Set-Location C:\SMELTER
python -m unittest discover -s tools/dashboard -p "test_*.py"
if ($LASTEXITCODE -ne 0) { throw "Dashboard tests failed." }
python -m unittest discover -s tools/setup -p "test_*.py"
if ($LASTEXITCODE -ne 0) { throw "Setup tests failed." }
node --test tools/dashboard/test_chat_renderer.js tools/dashboard/test_session_auth.js tools/dashboard/test_file_activity.js
if ($LASTEXITCODE -ne 0) { throw "JavaScript tests failed." }
python tools/dashboard/dashboard.py
```

Optional MCP integration tests require the pinned SDK from `requirements-mcp.txt`. Jobs remain in memory and do not resume across server restarts. General OpenCode editing/shell tasks, OS process confinement, full backend modularization, and a unified registry for every legacy CLI are follow-up work. Existing managed V2 copies are preserved, not silently overwritten; updating the original checkout does not update an already prepared V2 copy.
