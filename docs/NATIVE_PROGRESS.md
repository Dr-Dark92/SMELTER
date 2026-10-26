# Native Melty / OpenCode task progress

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
