# Bounded task watchdog

The user explicitly authorized automatic recovery on 2026-10-27: capture the
prompt, wait for RED/GREEN, and retry stalled work up to three times without
asking for confirmation. This supersedes the earlier no-auto-prompt boundary
for this separate, scoped controller. The live trace/WebSocket remains read-only.

## Two automatic exit conditions

1. An **explicit, verified RED or GREEN end flag** ends the current task's watch.
   The agent calls `finish_coding_task` only when it intends to finish. A RED
   test receipt alone is intermediate validation and does not end observation.
   An explicit final RED is terminal; it does not cause another repair loop.
2. An incomplete stalled task can receive **three recovery continuations**, then
   its watch ends as exhausted. That is one original attempt plus at most three
   retries. The durable counter is not reset by reconnects, MCP refreshes,
   watchdog restarts, compaction or the watchdog's own messages.

Stop/cancellation and a new human objective override recovery. Disabling or
changing the binding prevents dispatch. Pending access/questions and active
tools/children are waits, not permission to replay work.

## Installation and operation

```powershell
python tools/setup/manage_task_watchdog.py install
python tools/setup/manage_task_watchdog.py start
python tools/setup/manage_task_watchdog.py activate
python tools/setup/manage_task_watchdog.py status
```

Installation preserves and backs up existing OpenCode config, registering a
local capture plugin and the approved Python executable. No dependency is
downloaded. Capture code is installed as a SHA-named immutable local module
under `.smelter/watchdog/plugins/`, bounded to sixteen revisions. This avoids
stale native module caches after an update without restarting Melty.
`activate` reloads only the verified idle native project instance;
it defers if work or human requests are active. Existing conversation history
is retained. The plugin otherwise loads on the next native instance startup.

The plugin ensures the hidden service is running when a bound human prompt
arrives. `start` is idempotent and uses a process-identity check plus an exclusive
leader lock. It starts no visible terminal. The service remains ready for the
next human prompt after an individual watch terminates.

`adopt` explicitly captures just the latest human prompt from the currently
bound native session. It does not search unrelated sessions or copy assistant
reasoning. Normal capture comes from OpenCode's `chat.message` hook. Disable
with `python tools/setup/manage_task_watchdog.py disable`; this stops observation
and future submissions without killing the model or replaying anything.

`resume` is an operator migration for a watch stopped by the former automatic
RED rule. It verifies the same current human prompt/backend, refuses explicit
completion, Stop, new input or active/human-waiting work, and restores only that
original prompt. The existing task ID, attempts and three-retry budget survive.
It is not a general way to resurrect ended or exhausted tasks.

## Capture, state and identity

The separate Python process and loopback capture endpoint own the recovery state.
The endpoint requires a private bearer credential, rejects browser Origins and
accepts only bounded capture/cancellation messages. It exposes no arbitrary
URL, command, model-selection, directory-grant or task-control API.

Only the enabled exact native session/directory/owned workspace is admitted.
Original provider/model, agent, variant and available per-message tool/system/
format constraints are retained. The originating ACP process creation identity
and listening port are recorded. Dispatch uses that exact source, never the
separate idle HTTP server or whichever session was most recently active.

Initial support is text-only coding prompts up to 32 KiB. Attachments/subtasks
are explicitly rejected for recovery instead of silently disappearing from a
replayed request. Synthetic compaction messages do not arm a new watch.
No-reply context messages do not start model work: a real original assistant
execution must first have been observed.

Private state is under `.smelter/watchdog/`: configuration, process runtime
credential, a bounded SQLite task/attempt journal and a metadata-only public
status file. Raw prompt/options remain private and are cleared from active task
records at terminal/superseded states. They never enter trace frames, ordinary
logs, screenshots or public status. The native application retains its own chat
history independently. Limits are 128 task records and an 8 MiB database check;
capacity failure requires operator inspection, not automatic loss of history.

The capture and dispatcher code use the existing Python/OpenCode runtimes and
their standard libraries. Current real ACP discovery/activation targets Windows;
portable unit tests use explicit native fixtures. Requirements declare every
new component under `task_watchdog` in `system-requirements.json`.

## Evidence and end flags

Words such as “GREEN” in model prose and ordinary test outcomes are not end
flags. The agent must successfully call `finish_coding_task` with the owned
workspace, intended final RED/GREEN and all relevant profiles. The watchdog
matches this intent against test receipts emitted by actual native SMELTER test
calls created during this logical task. It checks the receipt path/ownership,
current source tree, log hash, normal runner revision, snapshot proof and frozen
acceptance revision. Both local and protected stages must support a GREEN flag.

Required scopes include registered frozen profiles and every valid test profile
actually invoked during the task. Missing, stale, malformed, unowned or ERROR
receipts cannot become a RED/GREEN flag. The explicit finish proof must match
the current tree, profiles and receipt hashes; later validation invalidates an
older finish declaration. The root turn must end and related tools/children
must drain before completion is accepted. An ended turn that merely says it will
keep working remains eligible for bounded recovery. End flags remain scope-limited;
they do not prove in-game behavior or unexpressed requirements.

## Stall and recovery behavior

A tool-contract failure is not a transient stall. Three recognized protocol
errors among the last twelve task tool calls cause `wait_tool_contract` before
another automatic continuation. A separate `wait_validation_progress` hold
detects three hash-verified RED results from the same frozen verifier revision
and check counts when the newest failure count is no better than the best of
the prior two. Editable-suite counts cannot trigger this trend check. These
holds spend no retry, manufacture no completion flag and do not change the
three-retry limit. An explicit verified finish still ends observation.

The watchdog does not abort active work on those holds. The operator stopped
the diagnosed runaway repair turn on 2026-10-27 after all three retries were
spent. Saved files and the original journal were retained; no fourth
continuation was submitted. A new human task is required to start new work.

The worker polls at five seconds. An ended turn without a valid end flag gets a
30-second idle grace period. Native retries/rate-limit waits are allowed to
finish. A 300-second quiet interval marks a stalled wait; a busy native engine
or active tool is never overlapped with another model turn. Existing native
provider deadlines and fixed tool deadlines drain such operations first. The
watchdog does not force-kill a stuck process or bypass an access decision.
Automatic continuation is limited to the known coding/read/validation tool
domains. Unknown external side-effect domains hold for inspection instead of
automatically repeating a publication, upload or other external action.
An exact pre-execution rejection from SMELTER's native shell/edit guard is
recognized as blocked work; it does not imply that a shell action executed.
Executed or otherwise failed native shell calls still hold for inspection.

When the exact backend is verified idle, it reserves a unique retry message ID
and spends one retry **before** making the asynchronous same-session request.
The continuation includes the original objective, original settings and the
same workspace, plus a controller instruction to recover current context and
avoid repeating applied changes. Backoff is 30/60/120 seconds between retries.
It does not restart the workspace, roll back files or replay individual writes.

A second lifecycle check immediately precedes reservation. The capture hook
also rejects a recovery message whose reservation is no longer current. A newer
human objective supersedes the old watch, while a recognized recovery message
does not create a new task or reset its budget.

If a POST times out or the service crashes during delivery, the reserved message
ID is reconciled against native metadata. The same ambiguous submission is never
blindly sent twice. If delivery remains uncertain, recovery holds for inspection;
it does not manufacture an end flag or consume unlimited model calls. Runtime
loss similarly waits for the original source rather than resurrecting work in
another process. These are safety holds, not additional automatic exit rules.

## Integration with Claude's trace work

Claude owns the graph/workbench frontend. This implementation does not modify
its trace files or socket control boundary. The trace may consume the safe
`.smelter/watchdog/public.json` projection through an authenticated backend
adapter later, showing task ID, origin ID/hash, state, retries/max, wait reason,
end flag/receipt and observation time. Never serve `runtime.json`, the SQLite
journal, raw prompt or copied request options to the browser.

Main modules: `watchdog_store.py`, `watchdog_native.py`, `task_watchdog.py` and
`watchdog_capture_plugin.mjs`. Operator tool: `manage_task_watchdog.py`.
Tests: `test_task_watchdog.py`, `test_watchdog_capture.mjs` and
`test_manage_task_watchdog.py`. Native fixtures submit only to a local fake server;
they do not call Qwen or send real user messages.

See [watchdog state relationships](diagrams/task-watchdog.mmd).
