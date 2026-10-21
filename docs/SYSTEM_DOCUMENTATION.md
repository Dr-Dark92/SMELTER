# SMELTER system documentation

This document describes the V1.7 operational repair on SMELTERV1, based on `9ee0f6dbd6c4bd790ef3bf31421f1b6f9573baf3`. The graph manifest pins the exact repaired application commit. Read [repair status](REPAIR_STATUS_20261021.md) for evidence and unverified platform paths. Installed models, Windows processes, container images and game assets are not verified by source review.

## Start and operating model

Run `python tools/dashboard/dashboard.py` from the checkout. The active dashboard binds to `127.0.0.1:8768` and prints an authenticated URL. Keep its token private; use the new URL after restart. Stop its owning terminal with Ctrl+C. A browser refresh does not reload backend code or startup skill fingerprints.

First use initializes SQLite in an absolute directory outside the checkout. `.smelter/database-location.json` selects it. Initialization refuses an existing database and cleans up only its own failed attempt. Current extension, model, runtime, access and sandbox configurations live in SQLite `config_snapshots`. Old JSON configuration is a compatibility/import surface, not dashboard truth.

| Entry point / dependency | Role / boundary |
| --- | --- |
| `tools/dashboard/dashboard.py` | Active standard-library dashboard composition root; optional MCP installed separately |
| `tools/setup/setup_web.py` | Separate explicit setup UI, not the chat controller |
| `tools/web/smelter_console.py` | Older standalone console, not the active dashboard |
| `tools/dashboard/mcp_server.py --root …` | Transient built-in stdio server; pinned SDK 1.30.0 |
| Ollama `127.0.0.1:11434` | Direct/native local-model transport; selected reasoning model, fallback qwen3.5:9b |
| Managed OpenCode 1.19.3 | Container-local 4096; no host port/network; fixed Docker-exec API relay |
| REA rea-agents 6.7.0 | Separate package presence and approved live static PE invocation |
| model-viewer 4.1.0 | Browser rendering dependency, separate from inference |
| 7z / FFprobe / Blender | Fixed approved native inspections with bounded process IO; not arbitrary shell |
| Docker Engine 28+ | Local Linux-container daemon with required resource/seccomp support; reviewed local immutable images, no automatic pull |

Older `test_*` core/bootstrap programs may invoke real models, Blender or Docker. Run only the documented offline suites unless deliberately exercising those integrations.

## Layers and calls

| Owner | Responsibility / next layer |
| --- | --- |
| `dashboard.py` | HTML, auth, HTTP server, injected services; composes `dashboard_api.ApiRoutes` |
| `dashboard_shell.js` | Browser navigation, chat state, task submission/polling, startup |
| `settings_ui.js` | Owns Settings/dialog/task surface before child controls mount; focus restoration |
| `access_ui.js`, `operations_ui.js` | Registered locations, admitted task summary, operator confinement/storage/project controls |
| `chat_jobs.py` | One active task, frozen admission contract, cancellation and live progress |
| `job_store.py` | Cross-controller atomic admission, durable lifecycle, PID identities and interrupted recovery |
| `chat_inference.py`, `ollama_turn.py`, `context_budget.py` | Prompt/skills, bounded model/tool loop, cancellable local transport and context estimate |
| `task_contract.py`, `execution_store.py` | Common configuration revision and atomic saved outcome for both engines |
| `python_tools.py`, `tool_registry.py` | Fixed schemas/dispatch, normalized grants, audits, receipts and explicit deduplication |
| `access_policy.py` | Context-local registered paths, flags, exclusions and immutable task snapshot |
| `mcp_connections.py`, `mcp_server.py` | Built-in stdio transport and parent policy/skill snapshot propagation |
| `opencode_runtime.py`, `opencode_sandbox.py` | Version/schema/session checks, read-only agent task, no-network worker and admitted-model relay |
| `sandbox.py`, `sandbox_preview.py` | Code snapshots, immutable images, limits, labelled ownership/cleanup and loopback preview relay |
| `process_runner.py` | Fixed argv, simultaneous bounded pipe capture, deadlines/cancellation and process-group/Windows-job cleanup |
| `skills_catalog.py`, runtime/context/manager modules | One identity/catalog, startup fingerprints, bounded instructions and explicit install/enable operations |
| `capability_catalog.py`, core `Registry` | Common descriptors; explicitly scoped/audited bridge for registered dashboard tools; other adapters library-only |
| `frontend_workspace.py`, file activity modules | Managed V2, CSS-only exact/hash edits, confined validation/preview, six-card-style file progress |
| `database.py`, `config_store.py`, `chats.py`, `model_assets.py` | SQLite/configuration/transcripts and separately owned attachment bytes |
| `storage_budget.py`, `maintenance.py` | Conservative artifacts quota, reviewed retention, verified backup and offline restore |
| startup/status/resource modules | Host/model observations and timestamped dependency cache; no implied allocation reservation |

## Task admission and outcome

1. Browser consumes next-message approvals and submits conversation, text, optional skills/image and selected engine. It includes the displayed access/config revisions.
2. `Jobs.start` validates grants, rejects stale supplied revisions and overlapping tasks, and freezes policy plus model/runtime. `job_store.admit` atomically checks the external database across controllers.
3. Direct Ollama assembles bounded history/instructions/schemas. Context estimation uses UTF-8 bytes/reserves, not the actual tokenizer. Oversized current work fails explicitly. Saved context/output/timeout values apply without a hidden frontend increase.
4. ToolSession audits before a fixed registered action. Both adapter restrictions and policy apply. Model text cannot grant tools or add executable names. Output/evidence is bounded, and tool actions followed by model failures retain receipts.
5. Stop shuts down the owned local-model socket. Active registered tools finish or hit their own bound; Stop does not roll back completed writes. Each engine finalizes transcript/execution atomically under the cancellation lock. Committed completion wins over a later Stop.
6. Admitted job outcome commits in the same transaction as its transcript/execution. Pre-finalization failures use a separate journal save; persistence warnings are distinct from task outcomes and polling/admission retry metadata only. Restart recovers dead/reused-PID running records as **interrupted**, without replay. A transient browser status failure retains its active task ID and Stop control; explicit Reconnect task polls that ID without resending the prompt. Live chunks/cards are memory-only; saved transcript and audits are the durable evidence.

Execution records include admitted configuration, policy revision, engine, normalized outcome/error/cancelled state and tool results. A successful model explanation is not independent fact-checking of the filesystem.

## Authority and confinement

**Effective operation = registered location policy ∩ next-message grants ∩ fixed adapter contract.** Skills provide instruction text only.

At most 32 absolute local locations, most-specific enabled match, relative exclusions, read/write/registered-execute flags. Whole drives/filesystem roots, UNC, traversal, links/reparse paths and alternate streams are rejected. Disabled rows are ignored; an enabled nested all-false row denies a subtree. Fixed operation names are tests/preview/rea/archive/media/blender. No general shell/editor is exposed.

Default original source is readable, sibling V2 permits registered frontend work/tests/preview, and diagnostics permits new Markdown reports. `.git`, `.smelter` and projects are excluded from general agent access. Dedicated app state operations are separate from model path access.

### Confined execution

Settings accepts only installed immutable `sha256:` image IDs. The runner verifies a local Unix/npipe Docker endpoint, Linux containers, Engine 28+, resource controls and seccomp support. It never downloads/builds images automatically.

Tests/preview/OpenCode get a read-only filtered source snapshot, UID/GID 65534, no network, no host credentials/socket mounts, dropped capabilities, no-new-privileges, bounded tmpfs, memory/CPU/PIDs/logs and internal/host deadlines. There is no native host fallback. Host snapshots have a conservative total budget and ownership records. Cleanup inspects the random container name and matching ownership label; incomplete cleanup is reported and retained for explicit reconciliation.

Frontend tests run fixed Python/JS commands. Preview uses temporary container state and a fixed dashboard-owned relay on loopback 8770, no container published port, one-hour lifetime, request/reply limits 2/6 MiB. It is a small-fixture UI preview; large asset transfers are outside that relay's contract. Old unconfined validation markers cannot launch it. Existing V2 is preserved and must be archived explicitly before preparing a fresh copy after source changes.

OpenCode is also a managed container. Only its read-only snapshot is visible. Host polls a tmpfs queue through fixed Docker exec commands; only admitted local-model requests reach fixed loopback Ollama. Native translation enforces context/output settings and tool-call/packet limits. Check sessions cannot prompt a model. No shell/edit/delegation grants, skills, images, GLBs or SMELTER write permissions are forwarded. Session rules are default-deny and must be echoed before prompt submission. Prior conversation is bounded; sessions are fresh. Source directory checks alone are not the OS boundary.

**Not all host processes are confined.** Fixed native REA/7z/FFprobe/Blender checks remain trusted approved host processes, with bounded output and owned process cleanup. Built-in MCP is app-controlled transport. Arbitrary external MCP remains blocked. Low-level explicitly invoked library helpers are not a third-party sandbox. See repair status for unverified Docker/Windows paths.

## Catalog and model tools

Bundled `skills/`, managed `.smelter/managed-skills`, legacy `.agents/skills` and contract `agents/skills` share namespaced identities. Legacy/contract entries start disabled until reviewed/enabled. Duplicate identities fail closed. Only SKILL.md and optional declarative smelter.json enter fingerprinted context; skill code is not auto-run. Changed/new text requires a dashboard restart. Dependencies found on PATH are observations, not proof of working adapters.

| Model tool group | Fixed contract |
| --- | --- |
| inventory_directory | Approved registered folder, bounded metadata, no general content reader |
| write_diagnostic_markdown | New plain basename in diagnostics, no overwrite, byte digest |
| rea_capabilities / rea_inspect_pe_resources | Explicit process approval, enabled skill, registered scope; relative bounded MZ PE files for inspection |
| frontend workspace/info/prepare/read/skill | Fixed source/sibling, managed copy, bounded source reads, actual enabled fingerprinted design skill |
| replace_frontend_css | Exact substring + current SHA; CSS-only, preserves backend/HTML/JS |
| validate_frontend_workspace / launch_frontend_preview | Current-content checks plus registered execution and confined runner prerequisites |
| inspect_model_attachment | Saved attachment ID, bounded metadata/clip timing; no semantic animation inference |

Capability descriptors identify actual adapter/schema, source, dependency, availability, permitted operations and transport. `Registry.connect_dashboard` is an explicit bridge into the same policy/audit ToolSession. Other legacy capability adapters remain library-only. Project-contract inspection is operator-only and applies read policy to the project and required files.

## HTTP contracts

All API calls require the launch token. Static page/assets are separate allowlisted files. POST requires bounded JSON objects; malformed input gets structured 400, database failures 503. State mutations serialize through the composition-root RLock. Disconnected-client writes do not trigger a second response.

| API | Contract |
| --- | --- |
| GET startup/system/status/runtime | Cheap readiness, cached dependency observations, host/model metrics, effective settings |
| POST database/select | First create-only external DB initialization |
| GET/POST access-policy | Location policy and effective model/config revision / save |
| GET/POST chats; GET chats/{id} | List, create/title, rename/delete/note/start/stop/runtime; paginated latest transcript |
| GET chat-jobs/{id} | Live state or durable historical/interrupted record |
| GET skills/status/review; POST skills/manage/discover/collection-preview | Shared catalog, activation/review, explicit instruction management/discovery |
| GET capabilities; POST project-contract | Common descriptors / policy-checked project documentation inspection |
| GET/POST sandbox | Observational prerequisite checks, operator image config, stop owned preview |
| GET/POST maintenance | Quota/jobs/ownership status, retention plan/apply, new backup, explicit integrity/reconcile |
| GET/POST mcp | Built-in SDK/config/discovery with gates; external execution blocked |
| GET opencode/agent | Managed read-only connection check, no prompt; runtime version/schema/provider checks |
| GET opencode/status/provider-preview/validate; POST deploy | Legacy installation/config staging helpers; not managed container activation |
| GET/POST ollama preferences/models; extensions | Saved roles/discovery controls; lightweight remains configuration-only |
| GET models/status or models/{id}; POST models | Viewer readiness, stored GLB, upload/animation-label operation |
| GET workflows/reports; POST workflows/plan | Dry-run plans / bounded report listing |
| POST archive/media/blender inspect | Fixed approved host inspections |
| POST aero/classify | Deterministic classification helper, outside agent loop |

Full route paths/action names live in `dashboard_api.ApiRoutes` and the generated function index. Legacy `action=ask` uses the asynchronous job controller, returning 202 rather than a synchronous model reply.

## Storage, maintenance and recovery

| State | Ownership / lifecycle |
| --- | --- |
| External SQLite | Config, conversations/messages/execution, GLB metadata/labels, task_jobs |
| `.smelter/model-assets` | UUID GLBs; deleting chat removes its bytes after SQL commit; failures reported |
| skill-state + managed manifests | Explicit instruction management; JSON/files separate from SQLite |
| tool-runs / rea-evidence / reports | Bounded evidence; conservative total 1 GiB/10,000-file artifact budget before writes |
| sandbox-runs | Filtered code snapshots and ownership/PID/image records; bounded staging; explicit interrupted cleanup |
| V2 + V2-Data | Managed frontend copy and initial isolated DB, preserved across pulls; container preview uses temporary state instead |
| In-memory streams/skill baselines/metrics | Lost on restart; restart adopts reviewed current skill text |

Retention previews server-side hash/size/mtime plans, expires after ten minutes and requires explicit approval. It protects referenced GLBs, skips changed files and targets recognized UUID artifacts only. No blanket startup deletion. Newest 100 workflow reports are retained unless older age policy selects them. Backup/retention/reconcile require idle recorded jobs.

Backup uses SQLite.backup plus verified managed manifests, skill-state, GLBs, reports, audits and REA evidence. It rejects existing destinations and concurrent observed changes. A manifest records byte hashes. Source, legacy skill directories, dependencies, weights and running containers are outside this backup. Restore is offline/create-only, verifies hashes/paths/schema/integrity, and never replays actions.

```powershell
python tools/dashboard/maintenance.py status --root C:\SMELTER
python tools/dashboard/maintenance.py integrity --root C:\SMELTER
python tools/dashboard/maintenance.py backup --root C:\SMELTER --directory D:\SMELTER-Backup-New --approve
# Offline: fresh checkout has no .smelter; external data destination must not exist.
python tools/dashboard/maintenance.py restore --root C:\SMELTER-Restored --directory D:\SMELTER-Backup-New --data-directory D:\SMELTER-Restored-Data --approve
# Dry-run only; Settings supports reviewing then applying the same expiring plan.
python tools/dashboard/maintenance.py prune --root C:\SMELTER --days 30
```

## Validation and troubleshooting

See README for offline suites and the repair handover for counts, image setup and explicit real-container smoke. Current verification used Linux/Python 3.12, MCP fixtures and Chromium; it did not establish Windows/Docker Desktop/OpenCode-image/live-model correctness.

| Symptom | Inspect |
| --- | --- |
| Wrong page / unauthorized | Current launch URL/token; dashboard 8768 differs from preview 8770 |
| Skill enabled but unavailable | Shared catalog identity, restart fingerprint, actual dependency/adapter/grant |
| Tool unavailable | Fixed exposed schema, admitted policy and next-message grant; MCP does not invent adapters |
| Preview/tests/agent blocked | Confined execution status, local immutable images/engine; no host fallback |
| Stale V2 after pull | Preserve/archive old V2/V2-Data, then prepare from updated source |
| Interrupted task / cleanup pending | Maintenance task and ownership records, receipts; reconcile after process/storage repair; do not replay writes blindly |
| Model slow / context rejected | Admitted model/context/output/timeout and actual Ollama logs; host GPU metrics are observations |
| Quota reached | Preview retention/backup; nothing is silently deleted |
| DB corruption concern | Explicit integrity operation; cheap readiness does not run quick_check on every read |

Do not publish raw audits, databases, credentials, launch tokens or game assets. AI narrative, saved file bytes, successful tool receipts and independent content verification are different claims.

## Offline office harness

`python tools/analysis/offline_gui_fixture.py` serves the real browser UI with synthetic replies, disposable state and stubbed services on loopback 18771. It never calls a live model. See [office workflow](OFFICE_GUI_WORKFLOW.md). Retention plans now remain disabled after consumption/failure/expiry and are invalidated when age changes.
