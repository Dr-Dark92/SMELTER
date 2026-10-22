# System status and component controls

Open Settings → System status, or use the footer's System details button. The
component table separates installation from runtime, shows versions when actually
observed, and provides Status / Start / Stop / Reload / Restart where supported.
Check timestamps identify cached observations. Refresh all statuses forces a new
bounded check. Footer telemetry updates do not replace or reset the table.

| Component | Installation/runtime evidence | Controls |
| --- | --- | --- |
| Ollama | Native executable and fixed loopback version/model APIs | Start a hidden dashboard-owned server; Stop/Restart that owned process; Reload refreshes observations |
| Selected Qwen/model | Installed tags versus actually loaded models | Start loads installed model; Stop unloads; Reload/Restart unload then load with saved context settings |
| OpenCode | Configured local immutable image versus optional host CLI; app version only after successful inspection | Start enables and checks a confined session; Stop disables new sessions; Reload/Restart verify and close the inspection container |
| MCP | Exact Python SDK version, enabled state and explicit discovery check | Start enables/checks; Stop disables MCP calls; Reload/Restart rediscover and close the check process |
| Docker | Local context, engine response/version and Linux/Windows mode | Status/Reload observations; shared engine lifecycle remains in Docker Desktop/OS service manager |
| Python | Interpreter running the dashboard | Status/Reload; no separate service |
| Node.js | Native version probe | Status/Reload; dependency, no standing service |
| SQLite | Selected database readiness/path | Status/Reload; embedded storage |
| GLB viewer | Local installed browser library | Status/Reload; browser dependency |

OpenCode and MCP remain on demand. Enabling them does not imply a persistent
service, a live model test, broad coding competence or fresh per-task permissions.
Their Stop controls persist locally in SQLite and are enforced at task admission
and runtime entry points. The existing MCP Connections screen also shows when
MCP has been stopped globally. Existing per-message tool approvals still apply.

An Ollama instance started outside this dashboard is labelled external. It is
not adopted by PID, killed by process name or stopped through an unrelated OS
service. Stop that instance using its owning application/service manager before
starting a dashboard-owned instance. Closing the dashboard closes its owned
Ollama child/process group/job. Reopening a dashboard does not adopt old PIDs.

Model Stop changes current memory residency; a later chat can load the model
again. It does not delete installed weights. Load/unload uses the existing local
Ollama empty-request API and never pulls a model or sends a user prompt. See the
[official Ollama FAQ](https://docs.ollama.com/faq) for model residency semantics.

Lifecycle changes are rejected while a dashboard task is active, including a
recorded task still owned by a live process. New chat admission is rejected while
a lifecycle mutation is in progress. A stale selected-model identity is rejected
before load/unload. Concurrent control requests are rejected rather than queued
for duplicate execution. Finish/Stop the chat first, then use component controls.

The authenticated operator-only API is GET/POST `/api/system/components`. POST
accepts a fixed component and action; Qwen mutations also require the model name
observed by the GUI. It accepts no commands, paths, ports or executable arguments
and is not exposed as a model tool. Lifecycle changes retain a bounded local operator log
at `.smelter/component-events.jsonl`; audit failure is reported separately from
an operation that already completed. An unconfirmed state remains an error.

## Verification

Focused regressions cover real owned child cleanup, rejection of external
process stop, exact empty load/unload requests and residency confirmation,
persistent runtime stops, entry-point enforcement, rollback on failed enable,
active-chat/interleaved admission guards, stale model denial, caching and actual
HTTP authentication/payload rejection. Browser coverage checks table rendering,
operator Stop, disabled non-service controls, telemetry preservation and 375px
layout. Model operations in tests use controlled responses; desktop Ollama and
GPU behavior require the operator's live acceptance.

## Verified build and desktop acceptance

Source 33f4fd323095d60187f456edc6e63021b479c3e8 passed all four jobs in
[CI 39707087492](https://github.com/Dr-Dark92/SMELTER/actions/runs/39707087492):
422 dashboard, 32 setup, 30 analysis and 16 JS tests per native platform, actual
browser/GLB checks, and confined OpenCode/MCP/CSS/ECC checks. Dashboard skips were
2 on Linux and 3 on Windows. CI inference was synthetic. A separate local real
MCP provider Stop/Start passed. See [progress and evidence](reviews/2026-10-22/system-status/PROGRESS.md).

On the desktop, stop the old dashboard with Ctrl+C, update SMELTERV1 and relaunch.
Use the newly printed authenticated URL. Open Settings → System status and click
Refresh all statuses. Compare installed versus running/loaded states. The first
live model Start/Stop and dashboard-owned Ollama lifecycle remain desktop
acceptance; those operations were simulated in automated tests. Finish active
chat work before trying them. Model Stop unloads memory; later chats can load it
again. Reload an enabled MCP/OpenCode provider to run an actual connection check.
