# Workflow and logic audit — 2026-10-21

Baseline: `c1bef027c0722dea73124c07f748915437c5aeac` on SMELTERV1.
Audit application source: `cee565b24726a9c217eab21c8a75bac88cad8c9c`.
The review includes source tracing, function/call inventory, native contracts,
actual HTTP/MCP/SQLite fixtures, browser interaction and isolated container tests.
Live Qwen, installed native tools and hardware performance require rig acceptance.

## Findings and disposition

| ID | Priority | Trigger and previous behavior | Change / evidence |
| --- | --- | --- | --- |
| W01 | P1 | OpenCode readiness snapshots the checkout, but a plain task snapshots sibling V2. A successful check can be followed by missing/stale V2 failure. | Every managed task uses current source as its immutable reference. Live destinations use approved tools. Native regression captures actual snapshot target; managed report smoke starts without V2. |
| W02 | P1 | Direct Ollama resolves skill selection in the worker, after admission; changes can alter a supposedly frozen task and its saved evidence omits skill hashes. | Validate/freeze direct ToolSession and selected instruction text before the worker. Record exact hashes in both engines. Test disables a selected skill after admission and checks actual outgoing text/hash. |
| W03 | P1 | Coding runner ERROR can be marked successful by direct/OpenCode completion and MCP/UI layers disagree. | Shared controller result semantics; expected assertion RED is evidence, infrastructure ERROR is failure. GUI shows ERROR, expected RED and stale review distinctly. Transcript/MCP/browser regressions. |
| W04 | P1 | Node result parsing depends on default reporter text; finding `ERR_ASSERTION` can misclassify mixed assertion/import failures as RED. | Fixed TAP plus a trusted event reporter; any import/runner error remains ERROR. Host RED/mixed ERROR/GREEN/all-skipped cases and actual container RED/mixed ERROR/GREEN. Windows CI caught and fixed reporter loading with a file URL. |
| W05 | P1 | CSS validation allows two 180s subprocesses through a 120s MCP / 150s RPC path. Receipt delivery can time out while tests continue. | Fixed 420s validation operation, 435s proxy and 450s RPC envelope; normal operations remain 120s/135s. Active cleanup wait follows the admitted operation. Actual CSS validation/preview smoke. |
| W06 | P1 | A cached successful `launch_frontend_preview` result can be returned after another CSS edit, skipping fresh validation. | Launch is not result-cached. Every call rechecks current validation. Native and real preview smoke reject stale launch. |
| W07 | P2 | A catalogue above 256 installed manifests silently omits skills; a new batch can exceed that bound after writing. | Overflow is explicit and fail-closed; unique batch capacity is checked before import. Duplicate skipping is preserved. Discovery 2,048, reviewed batch 40 and installed capacity 256 remain distinct limits. |
| W08 | P2 | A valid database directory containing `#` is inserted unescaped into a SQLite URI and becomes unreadable immediately after selection. | Use encoded file URIs for readiness/integrity and restore validation. Native Windows/Linux and actual HTTP/backup/restore fixture use a hash-containing path. |
| W09 | P2 | Malformed coding function metadata can throw AttributeError in live file activity before normal tool validation. | File-card parser rejects non-object function values without touching files. Shape regressions. |
| W10 | P2 | GitHub skill-file API returns a JSON array; discovery calls `.get` and raises an uncontrolled AttributeError. | Validate packet object shape before metadata access. No install/write occurs. |
| W11 | P2 | Coding tools are absent from capability discovery and legacy read-only classification; installed coding support is difficult to trace. | Catalogue includes all seven coding tools with independent Python/Node readiness. Legacy read/list/review keep read-only classification. No new authority is granted. |
| W12 | P3 | Repeated successful startup/reconnect appends the workflow choices again. | Replace choices before population; actual browser startup-retry check. |
| W13 | P2 | Backup wording implies all new coding state is covered, but coding copies/metadata and MCP JSON are outside the current backup areas. | UI/status/runbook explicitly enumerate exclusions and restore path review. Backup coverage itself is not silently broadened. Complete coding-workspace export remains open. |

The regression file was run before fixes and reproduced incorrect source
selection, saved outcome, URI readiness and malformed-shape behavior. Catalogue
omission was source-confirmed and covered by an added capacity regression. Missing new helper imports in that initial run were test scaffolding,
not separately counted product defects. The first cross-platform run also found
the new reporter's Windows loader issue; it was corrected before rollout.

## Layer coverage and remaining limits

| Layer / primary entry points | Review and verification | Remaining limitation |
| --- | --- | --- |
| GUI: dashboard_shell, settings/access/locations/skills, chat/file renderers | DOM flow, outgoing request/revision/grant checks; real Chromium, responsive layouts and reload/Stop | Global DOM coupling and compressed handlers remain; proposal cards appear when real tool arguments arrive, not artificial token-by-token typing |
| HTTP: dashboard.handler, ApiRoutes | Authentication, route/schema/error boundary, narrow mutation locks, actual loopback requests | No service-wide thread/concurrency admission or read deadline on every HTTP body; loopback token is not an OS sandbox |
| Jobs/configuration: Jobs.start/_run/_finish, task_contract, runtime_settings | Both engine admission paths, policy/config/skill snapshots, atomic terminal persistence, no action replay | “Completed” means request/controller completion; semantic deliverable acceptance still requires actual review/tests |
| Direct model: OllamaTurn, Control.infer, bounded | Native NDJSON shape/limits, stream completion/output limit, real socket cancellation, context estimate | Exact tokenizer/vision accounting is not measured; live Qwen quality/latency remains pending |
| OpenCode: status/ask, ManagedClient | Version/API/provider/permission checks, source snapshot, native relay translation, no-network container, owned cleanup | Fixed pinned 1.19.3; native shell/edits/delegation remain denied; Docker/runtime dependency is intentional |
| Skills: catalogue, monitor, selected_context, importer/router | Four source identities, duplicate handling, digest/restart checks, reviewed imports, capacity and malformed packets | Instruction-only SKILL.md import; linked scripts/dependencies/hooks are not installed. Automatic routing only recognizes the bundled documentation/diagram keyword rules |
| MCP: AgentBridge, proxy, connections/server, ToolSession | Shared descriptors, grants, audit, bounded call/response transport, frozen policy/manifest fingerprints, active-call settlement | Built-in stdio only for production agent actions; arbitrary external MCP still blocked |
| Coding: prepare/read/propose/apply/test/review | UUID ownership, portable paths, hashes, staged rollback, replay protection, immutable test tree, both profile outcomes | tools/skills and selected documents only; no delete/install/general build/merge/Git/coverage. Ten copies and fixed metadata quotas need an export/retention lifecycle |
| CSS workbench: prepare/_check/replace/validate/launch | Original/backend/HTML/JS preservation, exact CSS edits, real container tests and preview, stale launch denial | Existing V2 baseline is preserved and may be stale; no safe automatic refresh/rebase. Preview is a temporary no-network environment |
| GLB: inspect_glb/inspect_attachment, preview/animations/turntable | URI/decoder policy, embedded time bounds, labels/DB, browser rendering, lifecycle, PNG/WebM, cancellation/reload | Container/resource policy checks are not a full glTF semantic validator; decoder-dependent compression and animation meaning inference unsupported |
| Storage: database, execution_store, job_store, maintenance, quotas | SQLite/file readiness, URI correctness, atomic transcript/job commit, interrupted recovery, actual backup/restore/prune | Coding metadata/copies and MCP JSON excluded from backup; restored absolute policy/image paths need review; quotas are conservative application controls |
| Native inspections: REA/archive/media/Blender | Fixed command construction, path/approval checks, bounded process runner and existing contract fixtures | Actual REA/Blender/FFprobe/7z installations not exercised here. REA is static PE resource inspection; Blender GUI action is version check only |
| Setup: requirement scan, profiles/install actions/setup_web | Source and 32 native contract checks; no installation attempted | Separate setup wizard still uses older unbounded streaming Popen lifecycle for operator installers; needs timeout/cancellation/child ownership improvements |
| Core/legacy/web/game research | Static syntax/function/call inventory; core bridge traced to shared ToolSession; adapters labelled library-only | Host-capable experiments are not ordinary unit tests or dashboard capabilities; game/Blender/model-dependent scripts were not executed |
| CI/docs/graph | Immutable tested source, native Windows/Linux, actual browser/container artifacts, updated .mjs/.cjs and analysis inventory | Fixed upstream package versions still use mutable base-image tags at explicit build time; supply-chain digests/lock refresh should be a separate planned change |

## Architectural judgment

The main weakness was disagreement between layers, not absence of MCP or the
skill text: a ready connection did not imply the same workspace, ERROR was not
consistently failure, and a prior preview URL could masquerade as current output.
These contracts now have direct reproductions and cross-layer checks. ECC can
guide the model through tools that actually exist; installing more instructions
cannot provide missing execution, coverage, memory or reverse-engineering tools.

The next important product distinction is **request completion versus accepted
deliverable**. A model can end its answer without creating a requested patch or
obtaining current GREEN. Receipts reveal this, and the smoke asserts it, but a
general task-specific acceptance contract is not yet enforced for every GUI task.

## Function/call review and complexity

The regenerated [function index](../../../FUNCTION_INDEX.md) and
[graph](../../../graph/system-graph.html) enumerate the pinned source. The graph
includes active, legacy, test and analysis scripts, including the MCP .mjs proxy.
It does not execute analyzed modules. Static calls/references are candidates;
framework routes, callbacks, injected fixtures, shell entry points and generated
programs require manual tracing. No no-caller function is deleted on that basis.

| Hotspot | Branch estimate / span in reviewed source | Recommended boundary |
| --- | --- | --- |
| opencode_runtime.ask | 71 / 145 lines | Session admission, polling, abort/cleanup and outcome finalization |
| home_smoke.execute | 65 / 123 lines | Explicit phase plan, prerequisite gate and evidence/report writer |
| model_assets.inspect_glb | 48 / 63 lines | Header/chunk, resource policy and structural summary validators |
| ManagedClient._native_response | 47 / 58 lines | SDK history normalization, budgeted native request and response mapping |
| process_runner.run | 47 / 67 lines | Keep process ownership, drainage and termination invariants together; do not remove input checks to lower a metric |
| dashboard_shell.executionCards | 46 / 18 compressed lines | Explicit result view model and small rendering helpers |
| skills_catalog.catalog_skills | 43 / 92 lines | Bounded source enumeration, manifest record and identity merge |

Metrics count lexical branches/boolean terms; they are not formal McCabe scores
or a reason to remove validation. Historical JSON configuration helpers still
have compatibility/test callers. Core library adapters, main programs, HTTP hooks
and registry callbacks require a migration/consumer decision before removal.

See [action plan](ACTION_PLAN.md), [progress](PROGRESS.md), [handover](HANDOVER.md),
[evidence](evidence.json) and the [full smoke runbook](../../../FULL_SMOKE_TEST.md).
