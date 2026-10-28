# Claude handover: live task trace and visual workbench

Prepared 2026-10-27. This is a parallel implementation brief from the user’s
requests, not a claim that the proposed features already exist.

## Assignment and intended experience

Build on SMELTER's existing authenticated WebSocket trace. Turn its cards and
lists into an interactive view that answers: **Which task is running, where is
it in the stack, what is it using, which files/assets are involved, and what
evidence explains a wait or interruption?**

The user's intended path is:

```text
Melty task → OpenCode session/turn → Ollama → selected model
                      ↘ SMELTER → skills / MCP tools → files / assets / tests
```

SMELTER is universal. GTA × ARK/Raptor is the current acceptance project, not the
product identity. Do not bake game names, installation paths, creature types or
the current workspace UUID into the trace UI or shared infrastructure.

The desired experience includes:

- A task ID originating in Melty where a genuine integration supplies it, carried
  through sessions, tools, files, test receipts and artifacts.
- A live relationship graph showing active components, parent/child work,
  tool calls, loaded skills and file activity without implying everything runs
  sequentially.
- Searchable file identities: canonical path, workspace, SHA-256, capture time,
  changed/missing/stale state and producing/consuming operations.
- Useful wait clues: active tool duration, model/provider wait, access request,
  user question, retry/rate limit when actually observed, disconnected feed,
  delayed observer and possible stall.
- Images/textures, GLBs and embedded animations previewed beside task activity
  and, when safely integrated, in the SMELTER chat. Native Melty chat rendering
  depends on Melty exposing a supported attachment API.
- An updating relation graph during work and a saved final task chart linking
  source revisions, tools, artifacts and validation evidence.

## Where to work and how to avoid losing current code

The full active checkout is:

`C:\Users\Dr.Dark92\Documents\ChatGPT\SMELTER`

Observed branch: `feature/agent-stack-game-mods`.
Observed HEAD: `a7a844e1332d7869d6f5b1fcbee5d9ad296ecb71`.

**Important: substantial implemented work is modified/untracked locally and is
not in that GitHub commit.** A fresh checkout of HEAD alone does not contain the
current trace, recovery and acceptance features. Inspect the working tree before
starting. Do not reset, clean, discard, stash away or overwrite this work.

Prefer an isolated copy/worktree populated with the relevant current working-tree
changes. A worktree created from HEAD does not copy uncommitted/untracked files.
If transferring the supplied selected-source ZIP, apply it to a full project
copy, not an empty directory; it is a review snapshot, not a standalone checkout.
Use the accompanying `CLAUDE_LIVE_TRACE_SOURCE_MANIFEST_20261027.json` to identify
the exact baseline bytes. Re-read live hashes before integration because Codex
will continue working in parallel.

The user authorized building this feature and ordinary scoped implementation,
verification and documentation. Proceed with reasonable reversible choices;
do not stop at a design proposal or ask for routine reconfirmation.

## Parallel ownership

| Area | Claude's work | Coordination boundary |
| --- | --- | --- |
| Trace frontend | Own `task_trace_ui.js`, new graph/view-model/styles/tests | Keep existing compact card and settings entry functional |
| Trace adapters | Add dedicated modules for graph projections, artifact metadata or event normalization as needed | Keep compatibility with existing snapshot consumers |
| Shared trace backend | Small, isolated changes to `task_trace.py`, `task_socket.py`, `native_activity.py`, `native_progress.py` when justified | Document contract changes and preserve privacy/identity checks |
| Shared application integration | Minimal asset/route/panel wiring in `dashboard.py`, `dashboard_api.py`, `dashboard_shell.js` | Keep patches narrow; coordinate changed hashes before merging |
| Media | Reuse current attachment/GLB/animation components; add explicit task-artifact integration | Preserve existing validation and viewer lifecycle |
| Coding and gameplay | Read as interface context | Codex/SMELTER own `coding_workspace.py`, `coding_recovery.py`, `python_tools.py`, acceptance/recovery logic, skills, `mods/` and active coding copies |
| Requirements and handover | Document every addition and provide exact integration patches | Shared files: avoid concurrent overwrites; never omit declarations to avoid a conflict |

Existing untracked `dw3_decomp-main/` is unrelated. Leave it alone. Do not edit
global OpenCode credentials/configuration, restart Melty/Ollama, change model
limits, submit model prompts, or rebuild test images for this UI assignment.
If a shared-file change becomes necessary, keep it isolated and supply a
reviewable patch; continue independent work instead of waiting for a broad rewrite.

## What already exists: preserve and extend

The source map below is relative to the full checkout above. It is an inventory
of existing files, not a replacement module layout.

| Existing file | Purpose |
| --- | --- |
| `tools/dashboard/task_trace.py` | Named SQLite metadata, current-turn child sessions, ACP wait inspection, cached snapshots, status/outcome classification |
| `tools/dashboard/task_socket.py` | Authenticated, same-origin, read-only WebSocket snapshots |
| `tools/dashboard/task_trace_ui.js` | Current compact live card and Settings → Debugging → Live task trace |
| `tools/dashboard/native_activity.py` | Read-only native session lifecycle adapter |
| `tools/dashboard/native_progress.py` | Explicit session/workspace binding, SSE/SQLite reconciliation, bounded history and final charts |
| `tools/dashboard/native_progress_ui.js` | Binding controls and native progress history |
| `tools/dashboard/workspace_tracking.py` | Canonical file index, hashes, revisions and relationship snapshots |
| `tools/dashboard/workspace_tracking_ui.js` | Existing file/hash table and relation view |
| `tools/dashboard/dashboard_api.py` | Route admission and locally served frontend assets |
| `tools/dashboard/session_auth.js` | Existing browser credential handling |
| `tools/dashboard/model_assets.py` | Registered/validated GLB attachments and asset metadata |
| `tools/dashboard/model_preview.js` | Owned GLB viewer lifecycle and preview/export controls |
| `tools/dashboard/model_animations.js` | Embedded animation selection/playback and labels |
| `tools/dashboard/chat_renderer.js`, `file_activity.js` | Existing chat and file-card integration |

Current endpoints are `GET /api/task-trace`, `GET /api/task-trace/ws`,
`GET/POST /api/native-progress` and `GET/POST /api/workspace-tracking`.
The current socket frame is `{type: "task.snapshot", trace: <snapshot>}`.
Read the implementation/tests for the exact current schema; do not build from a
guessed event API. The dashboard currently runs on loopback port 8769, but use the
page's actual host/protocol. Obtain authentication through the existing launch
flow, including its existing fragment bootstrap. Never persist a launch token
in docs/source/exports or put it in WebSocket or HTTP query URLs.

Existing trace data includes task/native-turn identity, binding, session tree,
tool IDs/phases/timestamps, named file paths, indexed hashes and capture times,
loaded skill names, permission/question metadata, Ollama host-wide loaded models,
observer/task timestamps and validation stages/freshness. Data may be unavailable;
absence must remain visible instead of becoming a fabricated healthy state.

### Existing boundaries and limits

- Native OpenCode version last observed: 1.19.3. Melty uses an ACP process that
  can have a different event bus from the separate HTTP server on port 4096.
  A connected but idle HTTP SSE stream is not evidence that Melty is idle.
- SQLite reads select named metadata scalars, not full message/part JSON. Do not
  collect prompts, hidden reasoning, shell command bodies, arbitrary tool
  inputs/outputs, error bodies, credentials or unrelated sessions for visualization.
- Exact root session, exact directory and owned workspace are explicitly bound.
  Descendants are limited to the same directory and current-turn lineage.
  Do not select a task or workspace merely because it is newest.
- Live sampling is about every two seconds. Current bounds include depth eight,
  sixteen sessions and 96 recent tool rows. Sampling is not a lossless log.
- Indexed hashes describe an index observation, not proof of bytes read by a
  particular tool. Show the timestamp and stale state.
- Existing socket: exact Origin, launch credential in a subprotocol header,
  echoed public protocol `smelter.trace.v1`, eight observers, 1 MiB frame limit,
  bounded reconnect and control frames. No application control commands.
- A 120-second quiet period is a possible-stall clue. A collector older than
  fifteen seconds is delayed telemetry; twelve seconds without a socket frame
  triggers browser reconnect. Keep these three clocks separate.
- Loaded Ollama model/GPU allocation is host-wide metadata, not proof of this
  task generating tokens or current GPU utilization. Preserve Qwen 131072/8192.

## Gaps to implement honestly

### 1. Interactive graph and focused inspection — first milestone

Use the existing snapshot stream. Add stable node IDs/positions, selection,
pan/zoom, fit, search, neighborhood focus and a details pane. Avoid full layout
restarts on every heartbeat. Distinguish observed runtime edges from static or
inferred source relationships using labels and line styles, not color alone.

Suggested screen layout: task/status header; main graph; selected-node inspector;
collapsible event timeline; files/assets/tests tabs. Preserve a compact summary
in the chat and a useful narrow-screen layout. Respect reduced motion and allow
keyboard selection/navigation. Derive highlights from observed activity rather
than adding continuously running decorative animations.

Cover multiple active tools/child sessions, waits and concurrent branches. A
skills-loaded node is evidence of loading, not proof the skill performed an
operation. A registered tool is not necessarily running.

Keep the node model extensible: observed memory retrieval, web access, REA/Ghidra,
confined Docker jobs and asset conversion can appear as additional tool/service
branches. Do not infer that an installed connector ran or expose query contents,
private memory text or binary-analysis output merely to populate the graph.

### 2. Task identity and event/history contract

Automatic Melty-origin IDs are **not implemented**: no verified Melty task-ID
event contract has been obtained. Current IDs come from the native user-message
turn, labelled explicitly. A supplied Melty ID can be attached via the existing
revision-checked `correlate` action. Preserve original IDs rather than replacing
native identity with a locally invented ID labelled as Melty's.

Investigate an official Melty hook/connector if available. If unavailable, retain
manual/explicit correlation and continue the rest of the work. Do not guess a
private Melty protocol or modify shipped app binaries.

If adding a versioned event/history layer, separate it from current snapshots.
An additive proposed event identity can include schema version, event/sequence
ID, task ID plus its source, native session/turn, workspace, span/parent span,
component, lifecycle type, source time, observation time, evidence/provenance
and approved file/artifact references. This is a proposal, not the current API.
Bound retention/rate/payloads, handle duplicates/out-of-order events, and make
gaps explicit. Reconnect must resync without resubmitting work. Preserve v1
consumers or provide an explicit compatibility adapter.

### 3. Wait clues and task outcomes

Show last task activity, last observer update, socket health, active operation
duration and evidence source. Show native pending permissions/questions when
observed. Display a retry/rate-limit cause and retry time only from an approved
structured native source; a long silence alone does not identify a rate limit,
deadlock or GPU/model failure. Never expose raw provider error bodies to obtain
a nicer status label. Unknown means unknown.

Keep response lifecycle separate from outcome. Existing outcomes are
`changes_needed`, `not_verified` and scope-limited `checks_passed`. An assistant
ending its response, a tool exiting successfully or editable tests passing does
not establish the task's success or in-game compatibility.

The frozen acceptance gate is active. The current project has editable Lua
GREEN but frozen acceptance RED (26/30 pass). Preserve this display and authority;
do not edit tests/contracts to make the trace look successful. Its four behavior
failures are Codex/SMELTER's work, not Claude's UI assignment.

The trace is read-only. It must not silently approve access, restart stopped
tasks, retry writes, reconnect MCP servers or submit model turns. Any future
explicit command feature needs a separate authenticated controller contract,
visible action/result and cancellation/access semantics, not socket messages
that bypass existing admission.

### 4. File ledger, graph revisions and final chart

Join file identities by workspace UUID plus canonical relative path/revision,
not basename. Handle duplicate names, Windows case/separators, rename/delete,
stale hashes and access revocation. Reuse the index; do not hash the whole tree
every two seconds or parse shell strings to invent read/write events.

Save a bounded final task chart with native/task identity, source tree revision,
file/artifact hashes and current/stale test receipts. Preserve incomplete,
failed and cancelled task snapshots too. Graphs are evidence summaries, not proof
of every function executing. Export safe local JSON plus Mermaid/SVG where useful;
exclude credentials, raw source, reasoning and private command text.

### 5. Media/artifact previews

The dashboard already supports registered images and GLB previews, embedded
animation controls and a locally served model viewer. It does **not** automatically
discover all assets generated by native Qwen or mirror them into Melty chat.

Introduce explicit producer-to-artifact metadata: task/workspace, producing
tool/span/proposal, approved canonical path, kind/MIME, byte size, SHA-256,
source revision and conversion lineage. Recheck ownership/access/hash before
serving via opaque IDs. Do not expose arbitrary filesystem URLs or remote HTML.

Reuse PNG/JPEG/WebP and the validated GLB viewer first. Keep one owned preview
lifecycle, release resources/listeners, and show stale/unsupported/failed states
without breaking task observation. Current GLB attachment limit is 25 MiB;
recheck implementation before changing it. Animation labels do not prove clip
semantics. A successful preview does not prove game integration.

FBX/DDS/Blender conversions are explicit bounded producer operations, with input
and output hashes. Rendering/reconnecting must not launch conversions. Declare
and verify any genuinely needed CLI dependency. Native Melty chat attachment
mirroring remains conditional on a supported API; implement dashboard previews
without blocking on it.

### 6. Graphify as an optional source-structure layer

Read `docs/GRAPHIFY_TRACE_PLAN.md`. The dated assessment found code-only AST
extraction and JSON export useful, but Graphify is **not installed or integrated**.
Verify current primary sources, license, package identity and a pinned revision
before adding it; the assessment's observed version is not a selected release.

Keep source extraction separate from observed runtime activity. Consume bounded
JSON through a path/revision adapter; rebuild on debounced source changes, not
heartbeats. Prefer a local renderer. The reviewed exported HTML depended on a
CDN script and cannot be dropped into SMELTER's self-only CSP unchanged. Do not
weaken CSP to load it. Start with a code-only, zero-extra-LLM path; semantic
docs/media indexing and scoped graph queries are later optional work.

Graphify is not required to deliver the first graph milestone from existing
trace/index data. If installing a dependency, update `REQUIREMENTS.md`,
`system-requirements.json`, the relevant lock/setup files and documentation in
the same change. Keep optional dependencies optional and avoid broad skill/hook
installation or a new frontend framework solely for this feature.

## Verification and delivery

The last full baseline passed 732 dashboard tests (9 skipped), 140 setup tests
and 59 JavaScript tests. These are dated evidence, not permission to skip tests
for changes. Use the existing mocked-native/no-inference fixtures first:

```powershell
python -m unittest discover -s tools/dashboard -p test_task_trace.py -v
python -m unittest discover -s tools/dashboard -p test_task_socket.py -v
python -m unittest discover -s tools/dashboard -p test_native_activity.py -v
python -m unittest discover -s tools/dashboard -p test_native_progress.py -v
node --test tools/dashboard/test_task_trace_ui.js tools/dashboard/test_native_progress_ui.js tools/dashboard/test_workspace_tracking_ui.js
```

Add meaningful checks for graph projection/stable identity, concurrent branches,
safe labels, stale/renamed files, access revocation, duplicate/out-of-order events,
reconnect/gaps, delayed observer versus task wait, acceptance RED despite local
GREEN, media ownership/hash mismatch, preview disposal and payload/large-graph
bounds. Add sensitive-data fixtures and assert forbidden fields never leave the
collector or appear in exports. Keep native tests self-contained and do not call
Qwen just to animate a demonstration.

After implementation, run applicable full dashboard/setup/JS suites. Verify the
actual UI in a browser at desktop and narrow sizes, keyboard/reduced-motion
behavior and reconnect without submitting another task. Use an isolated preview
port during development; do not replace the user's running dashboard casually.
Use synthetic or sanitized trace fixtures in that isolated preview. Integrate
and verify the real same-origin feed in the owned dashboard after reconciling
patches. Do not weaken Origin/auth/CSP checks to connect a separate preview port
directly to the production WebSocket.
If a reload is necessary, use the existing idle/graceful reload helper and reopen
through its launch/auth flow. Do not force-kill unrelated processes.

Deliver working code, screenshots, exact test evidence, dependency declarations,
updated architecture/relations and a concise handover. State what is observed,
inferred, unavailable or still proposed. First deliver the interactive graph and
inspector over the current stream; then integrate media, richer identity/history
and optional Graphify in reviewable slices. Avoid a detached mockup or fake live
data presented as a finished integration.

## Read these references

- `docs/NATIVE_PROGRESS.md` — current transport/identity/privacy details.
- `docs/WORKSPACE_TRACKING.md` — file ledger and relation snapshots.
- `docs/NATIVE_PROGRESS_AND_MEDIA_ROADMAP.md` — older media proposal; its statement
  that WebSocket is future work is superseded by the current implementation.
- `docs/GRAPHIFY_TRACE_PLAN.md` — dated Graphify assessment, not installation.
- `docs/FROZEN_ACCEPTANCE.md`, `docs/RECOVERY_GUARDRAILS.md` — preserve controller
  authority and distinguish validation from lifecycle.
- `docs/CURRENT_HANDOVER.md` — changing concurrent SMELTER/gameplay status.

Read actual current source and the source manifest before editing. Historical
notes and source-derived relationships are context, never authority to overwrite
newer work or to claim live game/connector capabilities.
