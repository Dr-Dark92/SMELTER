# Repair status and work handover — 2026-10-21

Application repair commit: [`a3e3f854934ed90f36d49478eb336b86dd93948b`](https://github.com/Dr-Dark92/SMELTER/commit/a3e3f854934ed90f36d49478eb336b86dd93948b).

This repair addresses F01–F11 from the review of application commit `c9e541e9e0d53fcaba109170f8e5a201b500340d`. The historical review remains available; it is not the current defect inventory. Source was restored and Git-blob verified against branch head `9ee0f6dbd6c4bd790ef3bf31421f1b6f9573baf3` before editing. User-local files, the Windows rig, game assets and existing V2 were not accessed.

## Office follow-up

Follow-up application commit: `4bd636dbcc04de5d2cb016489c923e3146a611db`. See [offline GUI workflow](OFFICE_GUI_WORKFLOW.md) for the later catalog, atomic job-journal, reconnect and retention fixes. Current follow-up verification: 329 dashboard tests (two opt-in skips), 15 JavaScript, 32 setup and four analysis tests; no live model. The initial repair counts below remain historical.

## Finding disposition

| Finding | Implementation | Verification / limits |
| --- | --- | --- |
| F01: process confinement | New owned Docker worker for frontend tests/preview and managed read-only OpenCode. Read-only code snapshot, no container network, no host secrets/socket mounts, non-root, dropped capabilities, seccomp prerequisite, CPU/memory/PID/log/time budgets. No host fallback. Owner-labelled cleanup and interrupted-container reconciliation. | Flags, unavailable-runner rejection, ownership removal and relay contracts tested. **Real Docker/Windows paths remain locally unverified.** External MCP remains blocked. Fixed trusted native inspection adapters use bounded host processes, not Docker. |
| F02: orphan GLBs | Chat deletion commits metadata deletion, then removes only its attachment files; failures return cleanup-pending IDs. Retention plan can reconcile old unreferenced UUID artifacts. | Actual GLB-byte deletion, locked-file failure, referenced-file protection and changed-file skip tests. |
| F03: Stop/completion disagreement | Shared atomic transcript/outcome finalization for Ollama and OpenCode under the cancellation lock; worker consumes the winning result. Cleanup failure precedes OpenCode finalization. | Final-response cancellation fixture confirms worker and saved execution both cancelled. Stop after committed completion loses consistently. Socket cancellation tests included. |
| F04: hidden runtime overrides | Model/runtime/revision frozen at admission, displayed in task summary and persisted; removed automatic frontend timeout/output increases. OpenCode relay converts to native Ollama with the same context/output limits. | Saved 128-token/30-second fixture agrees with outgoing request; frozen/stale-revision and relay tests. |
| F05: unbounded capture | Shared simultaneous stdout/stderr drain with combined byte ceiling, cancellation, timeout and owned process-tree cleanup. Applied to archive, media, Blender, REA and confined operations. | Real subprocess flood, timeout, cancellation, stdin and nonzero-exit tests on Linux. Windows Job Object code needs rig smoke test. |
| F06: HTTP request shape | Extracted shared HTTP auth/size/JSON-object/error boundary; malformed types consistently return structured 400; SQLite errors return 503. | Actual HTTP tests for null, arrays, scalars, malformed JSON and project checks. **Correction:** the reviewed baseline already had a top-level dict guard; the earlier blanket claim that it lacked one was incorrect. This is consolidation and regression coverage. |
| F07: disconnected catalogs | Unified skill identity/catalog across bundled, managed, legacy and agent-contract locations. Shared capability descriptors identify source, operation, dependencies and availability. Explicit scoped/audited legacy Registry bridge. Added operator project-contract route. | Legacy manifest, policy bridge and project-route fixtures. Library-only adapters remain labelled; no automatic arbitrary callable registration. |
| F08: lifecycle gaps | Durable task_jobs admission/outcomes, PID identity and interrupted-state recovery without replay; artifact quota; reviewed retention; verified SQLite/application-state backup and offline create-only restore. | Cross-controller admission, interrupted recovery, quota rejection, byte-preserving backup/restore, tamper detection and deletion-plan tests. Live chunks remain memory-only. |
| F09: repeated probes | Timestamped 30-second dependency cache with explicit refresh. Cheap DB readiness separated from explicit integrity check. | Probe reuse/refresh and no-quick_check readiness tests. No production-scale performance claim. |
| F10: misleading state | not_checked for unobserved OpenCode; discovery toggle labelled as discovery; lightweight role explicitly configuration-only; admitted model/settings visible; footer identifies host readings and Ollama allocation. | Status/settings regression and browser checks. Model enumeration does not prove a successful inference. |
| F11: settings coupling | Settings component owns its surface before children mount; one skill panel; separate task-access summary; operator maintenance/confinement panels. Extracted browser shell, API routing, inference protocol, finalization and process ownership. | Desktop/mobile Chromium: policy save, settings navigation, maintenance/integrity, capabilities, chat/receipts/Stop/history, no page errors or horizontal overflow. |

## Validation recorded here

- Dashboard with optional MCP SDK: **321 tests run, OK, 2 skipped**. Skips: live vision/model test and explicit real-Docker isolation test.
- Setup: **32 tests passed**. Browser JavaScript: **10 tests passed**. Static-analysis harness: **4 tests passed**.
- Desktop/mobile browser fixture exercised real local HTTP/UI/database flows and actual diagnostic tool receipt persistence. Inference was a synthetic fixture; no model, game, Blender or external agent ran.
- Managed OpenCode model relay tests cover inspection-only denial, model/route allowlists, saved settings, tool-call history/SSE conversion, malformed results, output-limit completion reason and owned-container labels.
- Refreshed graph/function inventory is pinned to the application repair commit; its provenance lives in `docs/graph/source-manifest.json`. Static relationships are not full runtime coverage.

## Rig rollout

1. Stop the old dashboard. Preserve local untracked state; do not run git clean/reset.
2. From `C:\SMELTER`, pull `SMELTERV1` with `--ff-only`, run the dashboard/setup/JS/analysis suites, then launch the dashboard using its new authenticated URL.
3. Existing V2 is intentionally preserved. Archive it and its V2-Data sibling if you need a freshly prepared workspace from this source. Do not overwrite your work. Validation receipts from the old unconfined runner are rejected.
4. For chat/inventory/report operations, Docker is not required. For frontend tests/preview, configure reviewed Python/Node immutable image IDs in **Settings → Confined execution**. For OpenCode, build/configure its separate image. SMELTER neither downloads images nor starts the old host server.
5. Run the opt-in Docker isolation smoke below. Then check the managed OpenCode connection and submit a small explicitly approved read-only README task. Until that passes, its live agent path is **implemented, not deployment-verified**.
6. Create a verified backup in a new directory through **Settings → Storage, recovery & backup** before further experiments. Restore only offline into a fresh checkout/state and new external data directory.

```powershell
Set-Location C:\SMELTER
git pull --ff-only origin SMELTERV1
if ($LASTEXITCODE -ne 0) { throw 'Update failed.' }
python -m unittest discover -s tools/dashboard -p "test_*.py"
if ($LASTEXITCODE -ne 0) { throw 'Dashboard tests failed.' }
python tools/dashboard/dashboard.py
```

Optional container setup is an operator action. Review publishers/base digests first; images must be Linux images available in the local Docker Engine 28+ and must provide the commands shown. Tags are used only during manual acquisition; save the resulting immutable sha256 IDs in Settings.

```powershell
docker pull python:3.12-alpine
docker pull node:22-alpine
docker image inspect --format '{{.Id}}' python:3.12-alpine
docker image inspect --format '{{.Id}}' node:22-alpine
docker build -f tools/dashboard/Dockerfile.opencode -t smelter-opencode:1.19.3 .
docker image inspect --format '{{.Id}}' smelter-opencode:1.19.3

$env:SMELTER_TEST_PYTHON_IMAGE = (docker image inspect --format '{{.Id}}' python:3.12-alpine).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Python image unavailable.' }
$env:SMELTER_TEST_DOCKER = '1'
python -m unittest discover -s tools/dashboard -p "test_defect_repairs.py"
Remove-Item Env:SMELTER_TEST_DOCKER
Remove-Item Env:SMELTER_TEST_PYTHON_IMAGE
```

Check test output/exit codes. The explicit Docker smoke does not build the OpenCode image or prove its provider/agent compatibility. That needs the separate managed connection/task smoke.

## Current intentional limits and remaining verification

- Frontend model editing remains CSS-only. OpenCode is read-only; skills/images/GLBs and SMELTER write grants are not forwarded. This repair does not turn the workbench into an unrestricted coding or decompilation agent.
- Arbitrary external MCP is still blocked. Each future executable adapter needs a reviewed confinement/IO contract, not just a discovered tool name.
- Native approved REA/7z/FFprobe/Blender checks are fixed host processes. Bounded output and Windows jobs are cleanup controls, not filesystem confinement. Treat inspected input/tool dependencies accordingly.
- Container integration, Docker Desktop mounts, OpenCode image startup/offline SDK behavior and Windows process-job semantics have not run in this environment. They fail closed when prerequisites/checks fail. Container escape resistance is not proven.
- Preview uses a no-network container, dashboard-owned loopback relay, temporary state and a one-hour lifetime. Relay request/reply limits are 2 MiB/6 MiB; this is a small-fixture UI preview, not a large-asset transfer service. No host preview database is mounted.
- Backup scope is SQLite, skill-state and **managed** manifests, GLBs, reports, audits and REA evidence. Legacy `.agents`, contract files, source code, installed tools and weights must be preserved/reinstalled separately. Snapshots/containers and running external services are not restored. There is no automatic action replay.
- Full-disk/SQLite failures are surfaced; no system can guarantee durable writes when storage fails. Transcript and admitted-job outcome now share a transaction. If a worker fails before that transaction, a failed terminal metadata save is reported separately and retried on polling/admission after storage repair, without action replay. Live stream chunks are not crash-durable.
- Older CLI/core scaffolds and compatibility JSON APIs remain explicit/library-only. Unused imports were removed from the active composition root; static no-incoming symbols were not blindly deleted.
