# Deep code review — historical baseline and function relationships

**Current review:** [workflow and logic audit](reviews/2026-10-21/workflow-audit/REVIEW.md),
[action plan](reviews/2026-10-21/workflow-audit/ACTION_PLAN.md) and
[progress/evidence](reviews/2026-10-21/workflow-audit/PROGRESS.md). The function
index and graph now pin the current audited application, including the universal
agent bridge and coding path. Counts and unverified-platform claims below belong
to the historical baseline.

> **Superseded defect status:** F01–F11 were addressed in the 2026-10-21 repair. Read [current repair status](REPAIR_STATUS_20261021.md) for implementation, tests and remaining Docker/Windows verification. The following analysis/counts describe the older pinned application, while the graph/function index now describes the repaired application.
>
> **F06 correction:** the baseline already validated top-level JSON objects. Its original finding below overstated the gap. The repair extracts the common boundary and adds real HTTP regression coverage; it does not claim that a previously absent guard was invented.

**Baseline:** `c9e541e9e0d53fcaba109170f8e5a201b500340d`, SMELTERV1. This is a review after the scoped dashboard repair, not a repetition of already fixed findings. Application source is unchanged by this documentation revision. Do not delete functions based only on static graph output.

## Scope and certainty

The pinned snapshot contains **216 scripts / 17,937 source lines**, comprising 160 Python, 12 JavaScript and 44 PowerShell files. Python AST and JavaScript parser indexing found **1,229 declarations/callbacks**, including **653 in files not named as tests** and 576 in test-named files. Some historically named test files are integration programs rather than unit tests. Embedded/generated Python programs passed to Blender or external runtimes are not independently parsed. PowerShell has declaration indexing only; no PowerShell runtime/parser was available.

The graph contains **1,978 static relationship records** and **7,367 unresolved call expressions**. Unresolved includes ordinary standard-library calls, instance dispatch, callbacks, injected dependencies and external APIs. It is not a count of broken links. Same-module lexical calls and self/cls calls have stronger evidence than file-wide imported-alias candidates. Decorators, dynamic code and string dispatch prevent proof of whole-program reachability. Inline JS source lines are approximate.

The [function index](FUNCTION_INDEX.md) lists each declaration. [Graph JSON](graph/system-graph.json) retains per-edge locations, callers/references, unresolved expressions and complexity estimates. [Fixture evidence](graph/review-evidence.json) records three actual reproductions. The source baseline was checked against Git blob hashes before documentation changes; analysis never imported arbitrary source modules just to discover them.

P1 means resolve before expanding execution authority; P2 means material correctness/operational work; P3 means maintainability or clarity. Evidence labels below distinguish reproduced behavior from static reasoning. No real game assets, model inference, Blender, Docker or Windows processes were tested in this review.

## Findings

### F01 · P1 · Working-directory permissions do not confine child processes

**Status: architectural limit, source-confirmed; not a newly demonstrated escape.** `access_policy.Policy.authorize`, `frontend_workspace.validate/launch`, `opencode_runtime.session_rules`, and subprocess adapters gate requested paths/operations. Tests, previews and external runtimes then execute as the current OS user. A chosen cwd and model-tool allowlist cannot prevent arbitrary child code from reading other paths or accessing the network. Low-level MCP helpers are also not an OS sandbox.

**Action:** implement a separate confined worker with explicit mounts/paths, no ambient credentials, a restricted network policy, resource/time limits and process-tree ownership. Keep arbitrary external MCP and general shell/edit authority disabled until that contract is tested. Verify that an intentionally hostile fixture cannot read an unmounted path, write the source tree, inherit secrets, reach a denied network destination or leave descendants behind. Do not present current flags as system-level confinement.

### F02 · P2 · Deleted chats orphan GLB files

**Reproduced.** `model_assets.attach_model/model_path` stores bytes beneath `.smelter/model-assets`, while `chats.delete_chat` deletes SQLite attachment/message rows without removing those bytes. The fixture reports `chat_deleted=true` and `asset_file_still_exists=true`. Remaining bytes cannot be reached through the deleted database attachment, but continue consuming storage.

**Action:** define attachment ownership and retention, then implement a reconciler with a dry-run mode, age/grace period and explicit deletion authorization. Handle failed SQL inserts after file creation and interrupted deletions as well. Test shared references, failed transactions and restart recovery. Do not blindly delete every unreferenced file during startup.

### F03 · P2 · OpenCode completion and Stop can disagree

**Reproduced.** `opencode_runtime.ask` checks cancellation during polling, but a final response can finish without another cancellation checkpoint before persistence. A fixture cancels as the final message is returned: Control is cancelled, worker returns completed, and stored execution says cancelled=false. `Jobs._run` consults the flag separately and may label the same task cancelled. OpenCode execution payloads also lack the direct engine's normalized outcome/error fields, leaving failure text as the main historical clue.

**Action:** serialize final cancellation/completion under one controller contract, define which event wins, persist the winning outcome and error for both engines, and make Jobs consume that result. Test Stop before request, during read, while the final response arrives, before persistence and immediately afterward. Preserve completed tool evidence.

### F04 · P2 · Frontend tasks silently override saved runtime settings

**Reproduced.** `chat_inference.ask` raises timeout to at least 900 seconds and output limit to at least 4,096 tokens for `frontend_workspace`. A saved limit of 128 becomes outgoing `num_predict=4096`. `load_runtime` and the Settings view still describe the saved value. This does not increase path permissions, but it makes duration/memory/response controls misleading.

**Action:** calculate an effective task configuration at admission, display overrides before Send, persist it in the execution record, and offer an explicit workload profile instead of silently changing limits. Test exact saved/effective/request agreement. Policy alone is frozen at admission; model/runtime values are currently read later by the worker, so define their snapshot timing too.

### F05 · P2 · Tool stdout limits apply after capture

**Static source finding.** `rea_connection.run_rea`, archive/media/Blender inspections and frontend validation use `subprocess.run(capture_output=True)` or equivalent accumulated logs. Return-value slices and size checks bound the returned receipt after output is already captured. They do not bound peak memory generated by a verbose or malformed tool. Timeout limits duration, not byte count.

**Action:** introduce a shared bounded process runner that streams both stdout/stderr, enforces byte and elapsed limits, terminates the owned process tree, and reports truncation separately from success. Test a fixture producing excessive stdout and stderr concurrently. Preserve exact raw evidence only within an explicit storage quota.

### F06 · P2 · HTTP boundary does not consistently require JSON objects

**Static source finding.** `handler.Handler.do_POST` decodes JSON and then calls `data.get` in route branches. A valid JSON array, number or null can trigger an uncaught AttributeError/TypeError; the handler's exception list does not normalize those cases. Some GET policy/config routes also perform reads outside their local error wrappers.

**Action:** validate top-level request shape immediately, then route-specific fields, and return one structured error envelope. Add actual HTTP tests for null/list/scalar bodies, wrong field types, invalid length, malformed JSON and missing/corrupt state. Keep connection-abort handling separate from validation errors; do not catch everything and label it a client error.

### F07 · P2 · Registries and skill catalogs remain disconnected

**Source-confirmed integration gap.** The dashboard uses `tool_registry.schemas/execute_builtin`, bundled `skills/`, and `.smelter/managed-skills`. `tools/core/smelter_registry.Registry` discovers `.agents/skills` and exposes different capability objects. `agents/skills` is another contract/scaffold location. Importing an instruction, completing an old Blender experiment or starting an MCP server does not bridge these catalogs. `project_contract.inspect_project` has test callers but no production dashboard route/caller in this snapshot.

**Action:** define one capability descriptor and one skill identity model, then implement explicit adapters for existing registries. Preserve operation constraints and policy checks when migrating; do not auto-register callable names from skill text. Either expose project-contract inspection intentionally or mark it a library-only API. Acceptance: one catalog identifies source, dependency, executable adapter, permitted operations and actual availability consistently in GUI, Python and MCP.

### F08 · P2 · No recovery, retention or complete backup lifecycle

**Source-confirmed.** Jobs live only in `Jobs.jobs`; a restart loses task visibility. Tool/REA/report evidence has no automatic retention quota. `list_reports(limit=…)` limits the returned view, not disk file count; `MAX_REPORTS` does not implement cleanup. Attachment deletion has F02. Database selection, JSON skill state, stored artifacts and audit files are separate resources without a complete backup/restore transaction.

**Action:** persist minimal job lifecycle/revision/owned-process information, mark interrupted work explicitly after restart, and add operator-controlled retention/backup/reconcile workflows. Recovery must report observed state rather than automatically replaying writes. Test full disk and process death between file write, audit write and SQL commit.

### F09 · P2 · Dependency scanning and database integrity checks are on frequent paths

**Static performance finding; no timing claim.** `check_requirements.scan` sequentially probes executables with up to five seconds per probe and is called by multiple dashboard reads/operations. `config_store._db` calls `inspect_database`, which performs `PRAGMA quick_check`; configuration and transcript paths repeatedly request readiness. These checks are useful but may create repeated request work on slow disks or broken tool installations. No production-scale benchmark was run.

**Action:** use an explicit refresh plus short-lived dependency cache with timestamps, and separate cheap readiness from scheduled/on-demand integrity verification. Do not cache mutable file/tool outputs as if they were immutable evidence. Benchmark startup/settings/footer paths before and after, including unavailable executable fixtures.

### F10 · P3 · Status and feature semantics are still uneven

**Source-confirmed.** `system_status` now says OpenCode not_checked, but `startup_report` still labels it not_started without probing whether an independently started server exists. Model configuration stores reasoning/lightweight roles while direct chat consumes reasoning; no direct lightweight routing is present. The Ollama extension gates model discovery checks, while direct `chat_inference.ask` submits to the local endpoint without consulting that enable flag. OpenCode settings are staged independently from the running external server.

**Action:** label observations by scope: detected, configured, checked, connected, permitted and executed. Define whether extension toggles are discovery preferences or execution switches, and enforce/document that choice. Hide unsupported lightweight-routing promises. Do not imply that saving provider JSON activates a running server.

### F11 · P3 · Settings consolidation is incomplete at the component level

**Source-confirmed maintainability/UX finding.** `access_ui.mount` moves existing DOM nodes into one Settings dialog after the old shell mounts. This provides one visible home, but several older configuration panels, the Skills Manager and skill overview remain distinct implementations. Large inline handlers retain DOM/global coupling. The footer reports host/model observations and can still be mistaken for task allocation.

**Action:** create explicit Settings and TaskAccess components with owned state rather than moving already-mounted nodes. Keep one skill detail/catalog model, one effective-task summary and engine-specific controls. Test keyboard focus, mobile scroll and return from Settings during a running task. Label resource readings as host/model observations.

## Unused code: classified, not guessed

The static graph has 281 non-test symbols with no recorded incoming static call/reference. Many are external entry points, HTTP hooks, callbacks or dynamically invoked methods. This number is not a deletion list.

| Candidate | Evidence / classification | Recommendation |
| --- | --- | --- |
| `extensions.load_state`, `save_state` | No production call/reference found after SQLite migration; tests still use them; dashboard imports them but does not load their names | Legacy compatibility helpers; migrate tests/consumers and deprecate before removal |
| `model_preferences.configure_model` | No production call/reference found; older JSON save/load path; tests exercise it | Compatibility API, not the current dashboard model save path |
| `model_preferences.load_preferences/save_preferences` | Called by that legacy helper; not globally unreferenced | Remove only as part of the legacy configuration API migration |
| `project_contract.inspect_project` | Test callers; no current production route/caller found | Unconnected product feature or intentional library API; choose explicitly |
| `dashboard` imports `load_state`, `save_state`, `load_preferences`, `configure_model`, `inspect_database`, `ask`, `catalog_skills`, `add_skill` | AST Name-load check found no Python use in this module | Cleanup candidates; verify mock patch paths and public imports before removal |
| `os` in system_status/reports/opencode_deploy, `tempfile` in reports/opencode_deploy, `re` in skills_catalog, `Path` in skill_collections | Imported names have no AST Name-load references | Low-risk import cleanup after test verification |
| `reports.MAX_REPORTS` | Defined without retention enforcement | Implement explicit quota or remove misleading unused constant |
| `Handler.do_GET/do_POST`, `_NoRedirect.redirect_request` | Framework dispatch, not ordinary direct calls | Keep; static absence is expected |
| `main`, argparse programs and PowerShell launchers | Executed externally or behind main guards | Keep as entry points; document supported/legacy status |
| Core adapter operations passed to capability registration | Callback/function references and registry dispatch | Keep until their actual integrations are migrated |

No application function is deleted by this review. A safe removal should demonstrate absent internal, external, registration and test consumers; preserve a deprecation path where applicable.

## Complexity hotspots and proposed boundaries

Metric: one plus counted branches/boolean terms/comprehensions in each lexical body, excluding nested function bodies. It is an estimate, not formal cyclomatic complexity. Validation code naturally scores high; removing input checks to reduce a number would be a regression. Lines refer to the pinned snapshot, not a reformatted future file.

| Function | Lines | Branch estimate | Appropriate decomposition |
| --- | ---: | ---: | --- |
| `chat_inference.ask` | 178 | 66 | Admission/effective config; context builder; model transport; tool loop; outcome/persistence |
| `handler.Handler.do_GET` | 154 | 62 | Route table and typed per-resource handlers; shared auth/error boundary |
| `handler.Handler.do_POST` | 157 | 57 | Same, plus operation request validators and controller calls |
| `model_assets.inspect_glb` | 63 | 48 | Container/header validation; document/reference validation; metadata extraction |
| `python_tools.inventory` | 98 | 42 | Traversal/budget iterator; policy filtering; aggregate summary; bounded response builder |
| `model_assets.inspect_attachment` | 100 | 40 | Attachment authority; accessor/time decoding; clip pagination; result contract |
| Inline JS `executionCards` | 16 | 40 | Expand compressed statements; explicit renderer helpers and status mapping |
| `access_policy.validate` | 32 | 39 | Small named field/path/exclusion validators; preserve fail-closed behavior |
| `mcp_connections.validate_config` | 32 | 38 | Connection identity, command/cwd, allowed-tool validators |
| `opencode_runtime.ask` | 104 | 37 | Session contract; external polling; finalization/cancellation; persistence adapter |
| `rea_connection.run_rea` | 84 | 37 | Approved target resolver; fixed command builder; bounded runner; evidence writer |

`ToolSession._execute` is another important orchestration seam even if its branch count is lower: authorization, pre-action audit, file cards, transport selection, caching and result recording coexist. Extract interfaces around those responsibilities, not one helper per trivial line. `dashboard.py` is still a 100+ KiB mixed Python/HTML/JS/CSS file, making layer changes unnecessarily coupled.

## Suggested implementation order

1. **Correctness:** unified outcomes/Stop contract, attachment reconciliation, explicit effective runtime settings and HTTP request-shape checks. Tests must cover both engines and durable history.
2. **Execution boundary:** confined worker and bounded subprocess runner before external MCP/general coding tools.
3. **Structure:** route handlers, explicit chat phases, common outcome/persistence schema and component-owned Settings state; preserve public API behavior or version deliberate changes.
4. **Integration:** one capability/skill catalog through adapters, not a fresh registry that leaves both existing registries alive.
5. **Operations:** recover interrupted jobs, retention, consistent backups, dependency-scan caching and readiness/integrity separation.
6. **Cleanup:** deprecate legacy JSON helpers, remove confirmed unused imports/constants, archive experimental launchers with supported entry points documented.

For each stage, use behavior-level checks: actual outgoing request configuration, real fixture HTTP/stdio receipts, final stored outcome, policy denial before process start, no source overwrite, and orphan/restart reconciliation. Unit count alone is insufficient evidence that the complete local agent works.
