# Trace workbench

Status: implemented 2026-10-27 (Claude, live-trace assignment). Builds on the
[live WebSocket task trace](NATIVE_PROGRESS.md#live-websocket-task-trace); the
socket contract (`smelter.trace.v1`, `{type: "task.snapshot", trace}`) is unchanged.

Open it from the live task card in the chat (**Open trace workbench**) or from
**Settings → Debugging → Live task trace**. The compact card and the settings
panel keep working as before; one socket feeds all three views.

## What it shows

- **Identity chips:** task ID and its source, native turn, bound session and
  workspace. A Melty task ID appears only when one was explicitly supplied.
- **Response lifecycle and task outcome as separate chips.** "Response ended"
  never implies success; frozen acceptance RED shows "Changes needed" even when
  editable tests are GREEN.
- **Relationship graph** in five lanes (task identity → agent runtime →
  services & skills → operations → files & evidence) covering Melty, OpenCode,
  sessions and child sessions, Ollama, observed models, SMELTER, loaded skills,
  tool groups, access/question waits, workspace, files, tests and registered
  artifacts.
- **Edge evidence classes**, by line style and label rather than colour alone:
  solid = observed at runtime, long dash = explicit binding/configuration,
  dotted = inferred (tool-name prefix or expected provider path).
- **Inspector:** every identity, timestamp, hash, freshness note and
  relationship of the selected node, plus individual calls of a tool group.
- **Waits & clocks:** three separate clocks (last native activity, observer
  refresh, last socket frame), access requests, pending questions, model/provider
  waits, possible stalls, delayed observer and disconnected feed. A provider
  retry is shown only when a bound, connected native monitor reports the
  `retry` session status; otherwise retries are "cannot be observed".
- **Timeline, Files, Outcome & tests, Saved charts** tabs.

Node states use a coloured bar plus a text label (`active`, `waiting`, `error`,
`stale`, `finished`, `unknown`). After the root response ends, a child session's
last non-final state is shown as `unknown`, not `active`.

## Interaction

Click or Tab + Enter selects a node; arrow keys move to the nearest node in that
direction; Esc clears. Drag to pan, wheel or +/− to zoom, **Fit**, **Tidy layout**
(re-pack slots) and **Focus neighbourhood** (dim everything except the selection
and its neighbours). Search matches labels, IDs, paths and hashes.

Node positions are stable: each node keeps its lane slot across heartbeats and
is only re-packed on Tidy or when the task (session + native turn) changes. The
DOM is reconciled by node ID, so focus, selection and an open preview survive
updates. No animation runs; the only transition is disabled under
`prefers-reduced-motion`. Under 900 px the layout stacks vertically and chips
scroll horizontally.

## Saved final task charts

`trace_history.py` is called by the collector after each sample. It saves a
bounded chart (20 charts, 1 MiB, `.smelter/task-trace/charts.json`) when a
turn's response ends, is cancelled or fails, updates it if receipts change
afterwards, and saves an unfinished turn as "superseded before an observed end"
when a newer turn replaces it. Only already-sanitized snapshot fields are kept.
`GET /api/task-trace/charts` rechecks every path against current access and
redacts paths (and their hashes) for workspaces that are gone or no longer
visible. Charts open read-only in the same graph.

**Export JSON / Mermaid / SVG** write the current (live or saved) graph from an
allowlist: identities, states, paths, hashes, receipts and edges. No prompts,
arguments, outputs or reasoning exist in the snapshot to export.

## Task artifacts

Artifacts are never discovered automatically. Selecting a PNG, JPEG, WebP or GLB
file node inside the bound workspace offers **Register as task artifact** with
an optional producing call (only calls in the current trace that wrote or named
that path) and optional conversion lineage (another registered artifact).

`trace_artifacts.py` validates the path with the coding workspace's own
ownership, relative-path and access rules, checks magic bytes (GLB through the
existing `inspect_glb`), and records task/workspace identity, kind/MIME, size,
SHA-256, source index revision, producer evidence and lineage (200 records,
1 MiB, `.smelter/task-trace/artifacts.json`). A producer call that did not name
the path is labelled "declared", not observed.

`GET /api/task-trace/artifacts/<32-hex id>` serves bytes only after workspace
ownership, current read access and SHA-256 match the registration; changed,
missing or revoked files show their state and are not served. Images preview
through one owned blob URL; GLBs reuse `SmelterModels` (one owned viewer,
existing 25 MiB limit) with clip labels read-only. Nothing is converted, copied
or published, and a successful preview does not prove game integration.

## Not implemented / boundaries

- **Automatic Melty task IDs:** Melty's MCP tools (publishing, tests, Melty Net
  sessions) expose no coding-task or turn identity, and no supported Melty hook
  was found. Native turn IDs remain the identity; a supplied Melty ID still
  attaches through the existing revision-checked `correlate` action.
- **Native Melty chat attachments:** require a supported Melty attachment API.
- **Retry attempt/time:** the native monitor records only the `retry` status.
- **Event/history layer:** charts are sampled snapshots, not a lossless log; the
  proposed versioned event contract in the handover remains a proposal.
- **Graphify:** evaluated, not installed (see
  [Graphify assessment](GRAPHIFY_TRACE_PLAN.md#evaluation-2026-10-27)).
- **Agent-side registration:** Qwen cannot register artifacts yet; exposing it
  as a SMELTER tool belongs to the grant-gated tool registry.

Relations: [diagrams/live-task-trace.mmd](diagrams/live-task-trace.mmd).
