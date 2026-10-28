# Trace workbench: implementation report (Claude, 2026-10-27)

This report answers [the live-trace handover](CLAUDE_LIVE_TRACE_HANDOVER_20261027.md).
Design and behaviour are described in [TRACE_WORKBENCH.md](../TRACE_WORKBENCH.md).
At the time of this report, nothing was committed. All work was in the shared working tree, and no Codex-owned
coding, recovery, acceptance or gameplay file was edited.

## Slices

1. **Graph and inspector (first milestone).** `task_trace_graph.js` projects each
   snapshot into stable node IDs and evidence-labelled edges (observed, binding or
   inferred), lays them out in fixed lane slots, and renders a keyed SVG view.
   The view supports pan, zoom, fit, tidy, search, neighbourhood focus and keyboard
   navigation. `task_trace_workbench.js` is the full-screen dialog: identity and
   clock chips, inspector, waits, timeline, files, outcome/tests and saved charts,
   plus JSON, Mermaid and SVG export. It is fed by the existing socket through
   `task_trace_ui.js`.
2. **Saved final task charts.** `trace_history.py` is hooked into
   `Monitor.run` (narrow `try` block). `GET /api/task-trace/charts` serves them,
   and paths are rechecked on every view.
3. **Task artifacts.** `trace_artifacts.py` and `trace_artifacts_ui.js` handle
   registration through an explicit POST. Bytes are served by opaque ID after
   ownership, access and SHA-256 are rechecked. Images preview through one
   blob URL; GLBs go through the existing `SmelterModels`.
4. **Evaluations.** Graphify was rechecked and not installed (see
   [GRAPHIFY_TRACE_PLAN.md](../GRAPHIFY_TRACE_PLAN.md#evaluation-2026-10-27)).
   Melty's MCP tools expose no coding-task identity, so native IDs plus explicit
   correlation remain.

## Shared-file patches

Baseline hashes matched the source manifest before each edit. Each patch is narrow:

| File | Change |
| --- | --- |
| `task_trace.py` | Add `index_revision`/`index_updated_at` to snapshots; call `trace_history.observe` after each sample |
| `dashboard_api.py` | 3 asset routes; `GET /api/task-trace/charts`; `GET/POST /api/task-trace/artifacts`; `GET /api/task-trace/artifacts/<id>` |
| `dashboard.py` | 3 script tags before `task-trace.js` |
| `dashboard_shell.js` | Pass `window, api` to `SmelterTaskTrace.mount` |
| `model_preview.js` | Use `asset.source_url` only if it matches `/api/task-trace/artifacts/<32 hex>` |
| `model_animations.js` | Hide label saving when `asset.labels_read_only` |
| `REQUIREMENTS.md`, `system-requirements.json`, `tools/setup/test_requirements_catalog.py` | Declare `task_trace_workbench` (no new dependencies) |
| `docs/NATIVE_PROGRESS.md`, `docs/ARCHITECTURE.md`, `docs/GRAPHIFY_TRACE_PLAN.md`, `docs/diagrams/live-task-trace.mmd` | Pointers, evaluation and relations |

The socket protocol, authentication, Origin checks, CSP and the existing
grants were not changed.

## Verification evidence

- Full dashboard suite: `Ran 747 tests … OK (skipped=9)`. Setup suite:
  `Ran 141 tests … OK`. All dashboard JS tests: `67 pass, 0 fail`.
- New tests:
  - `test_task_trace_graph.js` (16): projection, concurrency, case/separator
    file identity, stale hashes, frozen RED, bounds, layout stability, Mermaid
    escaping, clocks/waits, export allowlist and artifacts.
  - `test_trace_history.py` (7): terminal/superseded saves, allowlist, path
    redaction, bounds and ownership.
  - `test_trace_artifacts.py` (8): producer evidence, GLB/lineage,
    spoofed/escaping/unsupported paths, changed/deleted/revoked files and
    opaque IDs.
- Browser checks used an isolated preview on its own port with the real
  modules and synthetic fixtures. They covered desktop and 375 px widths,
  selection, arrow keys, neighbourhood focus, saved-chart viewing, SVG export
  parsing, artifact registration and an image preview that survives heartbeats.
- A second check ran the **real** `dashboard.handler` and page on an isolated
  port, with an empty temp ROOT and LOCALAPPDATA (no database, so OpenCode never
  starts) and a patched synthetic trace source, the same approach as
  `test_task_socket.py`. It covered the authenticated same-origin WebSocket
  under the real CSP, the transition to "response ended" with "changes needed"
  shown separately, and a server stop followed by automatic reconnect. No
  chat or session request was sent.
- Screenshots: `trace-workbench-screenshots/01…08`.

Bugs found and fixed during verification:

- Heartbeats reset the inspector forms and previews.
- A banner pushed the layout off-screen.
- The narrow layout collapsed.
- Retries showed "None observed" when the monitor was unbound.
- The observer clock froze while the socket was disconnected.

## Live-feed check after the operator's restart

The user restarted the 8769 dashboard from Codex. It was then opened through its
launch link. The workbench loaded on the real authenticated feed with a real
bound session; the turn was ended and the outcome was "changes needed":

- The lua receipt is RED for both editable tests and frozen acceptance, and the
  mods receipt is GREEN on a stale tree.
- The graph matched the snapshot: 1 session, 7 tool rows grouped into 6 tool
  nodes, and 1 file (`entity_policy.lua`) with its indexed SHA-256 and capture time.
- The backend hook had already saved a real "response ended" chart for that
  turn, and it opened read-only.
- No artifacts were registered, and none were created during the check.
- Retry status read "none observed" from the connected native monitor.
- After the reload, every API request returned 200.

Fix made during this check: the live card's workbench and trace buttons now sit
under the heading instead of at the bottom of the scrolling card. Screenshots
`09…12` show the live run.

## Not verified / remaining gaps

- The running dashboard's live feed has been checked (see above). An in-progress
  task with active tools and waits has not yet been observed live; that was
  covered only with synthetic fixtures.
- The GLB artifact preview was not exercised in a browser; the harness has no
  model-viewer bundle. The code path reuses `SmelterModels` with a validated URL.
- Possible follow-ups:
  - Agent-side artifact registration as a grant-gated SMELTER tool (tool registry
    owners).
  - A versioned event/history layer.
  - Retry attempt/time (not recorded by the native monitor).
  - Melty chat attachments (needs a Melty API).
  - Graphify adoption once a stable release is pinned.
- Edge labels can overlap in dense neighbourhoods. They appear only for the
  selected node and in the inspector.
