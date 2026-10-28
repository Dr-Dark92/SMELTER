# Native Melty / OpenCode task progress

## Live WebSocket task trace

**Settings → Debugging → Live task trace** and the main chat's live card show
the exact bound native task, its current turn, and up to sixteen descendant
sessions. Use **Native task progress** to select the exact directory, session
and owned coding workspace. Nothing is selected by recency. Component cards
show Melty, OpenCode, Ollama/model metadata, SMELTER, loaded skills and tools.
Details include named file activity, indexed SHA-256 identities, child session
IDs and tool failures. Shell commands are not parsed to infer file access. A
skill name means loaded this turn, not proof of execution.

The current native user-message ID is the automatic turn identifier, labelled
**Native OpenCode turn (Melty ID not supplied)**. The available Melty connector
and observed native session metadata do not expose a Melty task-ID event. A real
ID supplied by Melty can be attached with **Link Melty task ID**, without
stopping/rebinding the monitor. The authenticated `POST /api/native-progress`
action is `correlate`, with `melty_task_id` and current `expected_revision`; an
empty ID clears the optional correlation. This is a boundary for a future
Melty-side hook, not a claim that the hook is installed or supplied IDs are
independently verified. Native turn/session/workspace identity remains visible.

The reader selects named metadata scalars from the existing read-only SQLite
store, never full message/part JSON. It follows only root descendants in the
same exact directory, excluding children created before the current turn.
Bounds: depth eight, sixteen sessions and 96 recent tool records. Named file
paths are limited to visible bound-project/owned-workspace paths and rechecked
against current access before delivery. SHA-256 values come from the existing
file index, labelled with its capture time; they are not fresh read receipts.
The trace is a current-turn RAM snapshot, not a lossless transcript. Existing
native lifecycle history/final charts remain available in Native task progress.

On Windows, existing PowerShell/CIM and TCP metadata locate actual OpenCode ACP
listeners: four candidates maximum, rediscovered every sixty seconds. Exact
root session/directory verification precedes GET-only permission/question reads.
A child's pending directory request becomes **Waiting for access**; questions
become **Waiting for answer**. Unsupported discovery is explicitly unavailable;
SQLite telemetry still works. Ollama `/api/ps` shows host-wide loaded models and
context, not proof that this task is generating. Qwen's 128K/8K profile is unchanged.

Other states include using tools, waiting for child/model, tool-budget error,
response ended, cancelled and failed. A completed assistant message is labelled
**Response ended**, not task success. Indexed validation receipts show their
current/stale tree status separately; GREEN still depends on acceptance coverage.
A 120-second quiet interval during pending work
produces **Possible stall**, not proof of deadlock. Aggregate native update times
can show activity without reading text/reasoning. Observer and task timestamps
are separate: a collector older than fifteen seconds becomes **Telemetry delayed**;
twelve seconds without a WebSocket frame reconnects the browser. A stale observer
does not manufacture a task-stall diagnosis.

`task_trace.py` supplies shared snapshots about every two seconds.
`task_socket.py` pushes them on `GET /api/task-trace/ws`; authenticated
`GET /api/task-trace` provides the same diagnostic snapshot. Reconnection uses
bounded backoff and resynchronizes current state. This is the dashboard feed;
OpenCode's upstream SSE/SQLite transports remain unchanged. See the
[OpenCode server API](https://opencode.ai/docs/server/).

The socket requires the exact dashboard Origin and its existing launch
credential in a WebSocket subprotocol header, never a URL/query string. Only
`smelter.trace.v1` is echoed. Eight concurrent observers, 1 MiB frames, masked
final client control frames, ping/pong/close and bounded reads are supported.
Application messages cannot issue task commands; extensions/compression are not
negotiated. Framing follows [RFC 6455](https://www.rfc-editor.org/rfc/rfc6455).
No prompts, reasoning, file contents, shell commands, arbitrary tool arguments,
outputs, error bodies or credentials are mirrored. Only explicitly named
file/workspace/skill input metadata is exposed; the legacy ledger retains its
stricter lifecycle-only contract. Observation never submits prompts, approves
access, resets connections or aborts tasks.

No dependencies were installed. Requirements declare the standard-library/native
browser implementation under `task_trace` in `system-requirements.json`. See the
[task-flow source](diagrams/live-task-trace.mmd). The interactive graph, inspector, saved final charts and explicit task
artifacts are described in [the trace workbench](TRACE_WORKBENCH.md).

## ACP and HTTP process coverage

The real Melty run exposed a separate ACP OpenCode process and an HTTP server
with independent event buses. Both use the same native session store. A connected
HTTP stream can therefore be idle while Melty works. The monitor now supplements
SSE with a read-only `native_activity.py` adapter for the exact bound session and
directory. It selects only tool names/IDs/statuses and message lifecycle fields
using SQL; it never selects full message/part JSON into the application.

The observed OpenCode 1.19.3 schema is supported. The default store is
`~/.local/share/opencode/opencode.db` (or under `XDG_DATA_HOME`). Schema/identity
failures make this source unavailable. It does not modify the native database.
Once shared lifecycle observations are available, an idle report from the other
HTTP process cannot prematurely finish the ACP task.

Public tool updates are read in batches of 16 every two seconds, with a persisted
timestamp/ID cursor. Existing bindings can recover activity since their last
observation; new bindings do not replay old completed tasks. The UI marks catch-up
and identifies its activity source. Sampling can miss intermediate phases; this
is lifecycle evidence, not a complete event transcript. Assistant turns ending
with `tool-calls` stay busy; a final completed response, error or cancellation is
handled separately. Final charts still use the explicitly bound coding workspace,
even if a model created other copies against the task instructions.

SMELTER can watch an existing native OpenCode session through its documented SSE
event stream. This is a read-only monitor of the session used by Melty. It never
creates a session, submits a prompt, restarts work, acknowledges permissions or
sends an abort command. It does not call the model or change Qwen's 128K/8K profile.

## Operation

Open **Settings → Debugging → Native task progress**. Enter the absolute directory
used by the native Melty project, choose **Find sessions**, and select the exact
session ID belonging to the task. Choose its SMELTER coding workspace and press
**Bind and watch**. Discovery shows IDs and timestamps, does not choose by recency,
and filters results against the exact directory. Session metadata must confirm
the directory, and the workspace must have a valid SMELTER ownership marker.

An enabled binding resumes when the dashboard starts. **Pause monitor** stops
only observation. **Resume monitor** reconnects the same verified binding.
Pause and allow the old connection to close before choosing another session.
Control requests carry the current configuration revision to reject stale tabs.

The main conversation page shows a separate native progress card. The settings
panel shows more history. Both display tool names and lifecycle states, session
busy/retry/idle, failures/cancellation, transport state and event gaps. Tool
completion is not a controller-verified test pass; the actual workspace receipt
and tree hash determine whether tests are current.

After observed work transitions to idle, failure or cancellation, the monitor
refreshes the bound workspace index and saves a final relation chart with the
current/stale test receipts. The native progress card displays that chart. An
initial idle snapshot does not fabricate completion of an unseen historical task.
Failure to build a chart preserves the observed completion with a separate
snapshot error. Normal SMELTER file/test calls continue updating the workspace
index during work.

## Transport and privacy

The endpoint is fixed to `http://127.0.0.1:4096`. Only GET `/session`,
`/session/<verified ID>`, `/session/status` and `/event` are supported. No arbitrary
URL input, redirects or proxy environment are used. The directory query scopes
the connection; incoming events are additionally filtered by the exact session
ID. Current builds' `message.part.updated` tool states and
`session.next.tool.*` events normalize into the same lifecycle record.
[Official server API](https://opencode.ai/docs/server/).

The ledger excludes reasoning, prompts, message text/deltas, tool arguments,
raw outputs, error bodies, provider metadata, attachments and environment values.
It stores only allowlisted event types, bounded identifiers, tool names, phases,
local observation timestamps, sequence and final workspace graph metadata.
Raw event frames exist transiently in the SSE parser and are never logged.
If the server requires Basic auth, use its existing process environment variables;
the monitor never persists authentication headers or values. The dashboard API
requires its existing token and same-origin checks. Historical chart nodes are
filtered again against current workspace access policy before being returned.

## Reconnect and bounds

The worker opens the stream before checking status, so new transitions can queue
while status is read. Disconnects use bounded exponential backoff and revalidate
session/directory identity. A saved event ID is sent as `Last-Event-ID` when
available, but OpenCode's documentation does not guarantee replay. The UI marks
gaps and reconciles session status; it does not promise a complete transcript.
An idle state observed after a gap creates an explicitly marked snapshot when
the monitor had previously observed the task working. A newly observed task on
a healthy connection starts a fresh gap assessment.

The worker admits at most 100 normalized transitions per ten seconds, bounds
each SSE frame/metadata response to 1 MiB, retains 300 recent transitions and
1,024 deduplication keys, and keeps up to five completion charts within a 2 MiB
ledger. Repeat native event versions coalesce by call ID and lifecycle phase.
Rebinding archives the prior binding before starting a new ledger; ten archives
are allowed before review is required. Nothing is deleted by rebinding. Ordinary
retention plans protect native progress state; backups include it.

State lives at `.smelter/native-progress/state.json`; prior binding archives live
under `archives/` in that directory. Polling the dashboard reads cached metadata
and rechecks access; it does not ask the model for progress or rehash the tree.
Finalization does a bounded coding-workspace refresh. Stop/rebind is immediate
at the API; the old read-only stream may take its 12-second socket timeout to
close. An in-progress metadata read or workspace snapshot must also finish before
rebinding. Monitoring threads are daemonized and stopped on normal GUI exit.

## API

- `GET /api/native-progress`: cached binding, lifecycle events and completion charts.
- `POST` with `action: "sessions"` and `directory`: discover exact-directory IDs.
- `POST` with `action: "bind"`, `session_id`, `directory`, `workspace_id` and
  `expected_revision`: verify and watch that mapping.
- `POST` with `action: "start"` or `"stop"` and `expected_revision`: resume/pause
  the monitor. These do not start or stop native AI work.

No additional third-party runtime is installed. Requirements are declared under
`native_progress` in `system-requirements.json` and explained in `REQUIREMENTS.md`.

## Verification and remaining acceptance

Offline tests exercise identity checks, stale configuration, reasoning/content
exclusion, both tool-event formats, deduplication, SSE framing/size bounds,
disconnect/reconnect over a local HTTP fixture, GET-only requests, final chart
persistence, permissions, snapshot failure, protected retention and authenticated
API controls. JavaScript tests cover safe rendering, gaps and RED/stale receipts.
An actual user-run Melty task is still required to verify the complete live
busy → tools → idle path on this machine. No model prompt is submitted to obtain
that acceptance automatically.

Generated textures, GLB models and animations still need the separate registered
asset ingestion described in [the media roadmap](NATIVE_PROGRESS_AND_MEDIA_ROADMAP.md).

## Recovery integration

The trace shows a Recovery checkpoint hint for observed repeated-call redirects.
The optional registered local OpenCode recovery hook adds per-inference and
compaction guidance and blocks native shell/edit/delegation bypasses only for
the enabled exact bound task. Details and limitations are in
[RECOVERY_GUARDRAILS.md](RECOVERY_GUARDRAILS.md). Read-only WebSocket observations
do not restart tasks, submit prompts or approve access. Provider deadlines and
native retries are distinct from the trace observer's quiet-activity warning.

## Response lifecycle and task outcome

See [FROZEN_ACCEPTANCE.md](FROZEN_ACCEPTANCE.md) for the operator-registered,
separately isolated acceptance gate. Overall GREEN requires local tests and
frozen acceptance to pass. The live trace derives changes-needed, not-verified
and scope-limited checks-passed outcomes separately from an ended response.

## Parallel visual workbench handover

See [Claude live-trace assignment](handovers/CLAUDE_LIVE_TRACE_HANDOVER_20261027.md)
for the requested interactive graph, task/file/asset inspection, reliable wait
clues, media previews and optional Graphify source layer. It distinguishes
implemented functionality from proposed integration and defines parallel file
ownership while controller/gameplay work continues.
