# Graphify and live task trace: integration assessment

Status: feasible integration proposal, 27 October 2026. No Graphify package,
skill, hook, watcher or frontend dependency has been installed by this review.

## Verified upstream capabilities

The [official repository](https://github.com/Graphify-Labs/graphify) exports a
queryable `graph.json` and an interactive `graph.html`. Its current v8 sources
declare the package name `graphifyy` and a Python 3.10+ requirement; extraction
supports code-only local AST indexing. The installed command is `graphify`.
The reviewed branch's package version is 0.9.96; this is an observation, not a
chosen/pinned release or verification of a published package artifact.

Primary sources inspected:

- [Package manifest](https://github.com/Graphify-Labs/graphify/blob/v8/pyproject.toml): tree-sitter grammars, NetworkX, NumPy and other dependencies; optional watch/MCP/Ollama extras.
- [CLI entry](https://github.com/Graphify-Labs/graphify/blob/v8/graphify/__main__.py): `extract --code-only`, query/export and provider options.
- [Watch implementation](https://github.com/Graphify-Labs/graphify/blob/v8/graphify/watch.py): debounced code-change rebuilds without LLM calls; docs/media changes flag semantic update work separately.
- [JSON export](https://github.com/Graphify-Labs/graphify/blob/v8/graphify/export.py): schema/version metadata and atomic graph writes.
- [HTML exporter](https://github.com/Graphify-Labs/graphify/blob/v8/graphify/exporters/html.py): standalone HTML using CDN-hosted vis-network 9.1.6. This is not an already integrated SMELTER WebSocket widget.

## Proposed boundary

Graphify supplies source structure: files, symbols and source-derived/inferred
relationships. SMELTER's existing trace supplies observed task/turn IDs, tool
calls, file activity, child sessions, access waits and health timers. A small
adapter joins the layers; Graphify does not become the runtime event authority.

Index each approved owned workspace separately. Map exported source paths onto
the existing workspace UUID and canonical project-relative file paths. Retain
graph schema/version and source revision. Use the existing SHA-256 ledger to
label stale relationships; do not treat a graph as proof that current bytes or
test results match. Runtime events can highlight a file observed in a tool call;
they do not prove a static function-call edge executed.

Push bounded graph revisions and activity overlays through the existing
authenticated dashboard WebSocket. Rebuild source relationships after debounced
file changes, not on every heartbeat, token or model-status update. Reconnection
receives current graph revision plus current activity. Keep stable node positions
while activity changes, with search, focused neighborhoods and click-through
file/hash/task details rather than redrawing the entire repository each tick.

Prefer consuming `graph.json` into a locally served renderer. The current
exported HTML's external script cannot be dropped into SMELTER's self-only CSP.
If reusing its renderer, vendor/pin the relevant frontend asset locally and
preserve dependency provenance; do not relax the CSP for a CDN.

## Recommended first slice

1. Resolve and pin a tested release/commit; install in an optional isolated
   tooling environment with locked dependencies. Declare actual additions in
   REQUIREMENTS.md and system-requirements.json.
2. Generate a code-only graph of one selected owned workspace. Exclude unrelated
   checkouts/runtime data and apply the existing path/access policy.
3. Validate graph schema, bounded size, path mapping, revision/staleness and safe
   labels before serving data. Keep observed, extracted and inferred relations
   distinct.
4. Add the dynamic graph overlay to Live task trace and test file highlighting,
   renamed/deleted files, child waits, reconnect and large-graph bounds.
5. Optionally add scoped Graphify query/explain/path operations to the existing
   coding bridge later, so Qwen can locate related files without reading the
   complete graph/report. Semantic docs/media indexing is separate optional work.

This proposal does not change the existing Melty task-ID boundary: a real
Melty-side ID hook remains necessary for automatic Melty-origin correlation.

## Evaluation 2026-10-27

Rechecked PyPI on 27 October 2026: `graphifyy` 0.9.96, `license_expression`
Apache-2.0 (the repository also ships LICENSE-MIT and NOTICE), Python >= 3.10,
required dependencies NetworkX, NumPy, rapidfuzz, PyYAML and about 25 pinned
tree-sitter grammar packages. Releases land several times a day (for example
0.3.21–0.3.25 within one day in April 2026), so no release was identified as
stable enough to pin.

Decision: **not installed.** The trace workbench delivers its graph from the
existing trace and file index without it, and keeps observed, binding and
inferred edges separate, so a source-structure layer can be added later as a
fourth evidence class ("static source relation") without changing runtime
nodes. Before adopting it, pin one tested release and its lock file in an
isolated optional tooling environment, run code-only extraction on one owned
workspace, and feed bounded `graph.json` through a path/revision adapter into
`SmelterTraceGraph`, with no CDN renderer or CSP change.
