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
- **Relationship graph**, a layered top-down hierarchy (task and Melty →
  OpenCode → sessions, services and workspace → tools and models → files, tests
  and artifacts) covering Melty, OpenCode, sessions and child sessions, Ollama,
  observed models, SMELTER, loaded skills, tool groups, access/question waits,
  workspace, files, tests and registered artifacts. See
  [Graph layout](#graph-layout).
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
(re-run the full crossing optimisation), **Focus neighbourhood** (dim everything
except the selection and its neighbours) and **Containment edges** (draw the
workspace → file binding edges; see below). Search matches labels, IDs, paths
and hashes. Selecting a node shows the relation labels of its edges.

The DOM is reconciled by node ID, so focus, selection and an open preview survive
updates. No animation runs; the only transition is disabled under
`prefers-reduced-motion`. Under 900 px the layout stacks vertically and chips
scroll horizontally.

## Graph layout

`layout()` in `task_trace_graph.js` is a deterministic layered (Sugiyama-style)
layout in plain JS/SVG, with no dependency. It was chosen over a force-directed
network, arc or chord view because the trace is mostly a hierarchy (who
started whom, which tool touched which file), like an org or relationship chart:

1. **Direction.** Edges point down. A wait hangs below the session it blocks
   (its arrow points up into the session), and any cycle is broken by
   reversing depth-first back edges.
2. **Layers.** Longest-path layering from the roots. A layer with more than
   seven nodes wraps by pushing leaves (and their successors) one layer down.
   On a heartbeat, wrapping prefers nodes that were lower last time and new
   nodes, so rows do not reshuffle.
3. **Long edges** get a narrow placeholder on every layer they cross, so a
   connector only passes through free columns. Long edges from one source with
   one evidence class share a trunk (a bus, as in an org chart) and branch at
   the target's layer.
4. **Ordering.** Barycentre sweeps followed by adjacent transposes minimise
   crossings. The first layout and **Tidy layout** optimise freely. On later
   heartbeats only new nodes and placeholders move, and nodes already on screen
   keep their left-to-right order.
5. **Placement and routing.** Order-preserving placement aligns nodes with
   their neighbours. Connectors are orthogonal with rounded corners: they leave
   a node's bottom edge, run horizontally on their own track in the channel
   between two layers, and enter the target's top edge. Ports are spread along
   each box edge in the order of the other end. A port is nudged off any other
   connector's column, so two connectors never share a stretch of line (except
   the trunk of one bus). Each connector has a background-coloured casing, so a
   crossing reads as one line passing over another.

The left gutter labels each layer with the kinds on it. Each layer is colour
coded: a faintly tinted band with a solid stripe at its left edge, and the
outline of every node on that row in the same colour. Six hues
(`LAYER_COLOURS`) cycle by row and are chosen to stay distinct from the state
bar and evidence colours, so state still reads from the node's left bar and
evidence from the line. Exported SVGs keep the colours. Layout is recomputed
on every snapshot (a few milliseconds at 60 nodes). Evidence keeps its line style
(solid observed, long dash binding, dotted inferred), and arrowheads take the
evidence colour. All colours are theme tokens, so the graph follows the
dashboard theme; the exported SVG uses a fixed dark palette.

**Workspace containment.** Every file inside the bound workspace has an
`inside bound workspace` binding edge from the workspace. On a typical Qwen run
these are a third of all edges, so the view draws them only when **Containment
edges** is pressed. Otherwise the workspace node reads `contains N files`. The
edges stay in the graph data: the inspector, neighbourhood focus and the
JSON/Mermaid exports always include them.

`test_task_trace_graph.js` checks the layout on Qwen-sized fixtures (13–57
nodes):
- no two node boxes come within 8 px of each other;
- every connector is orthogonal, starts and ends on its own boxes and never
  enters another box;
- no two connectors overlap, except within a same-source, same-evidence bus;
- layers run top-down and no layer exceeds seven nodes;
- the result is deterministic, and a tree has zero crossings;
- adding a node on a heartbeat keeps the existing order.

The node `lane` field from `project()` is kept for compatibility but no longer
drives placement.

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
