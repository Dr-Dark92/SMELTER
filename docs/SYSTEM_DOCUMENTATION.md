# SMELTER system documentation

Application baseline: **SMELTERV1, c9e541e9e0d53fcaba109170f8e5a201b500340d**. This document describes inspected source, not an assurance about installed models, external packages, Windows processes or private game assets. The accompanying review separates reproduced defects, static findings and intentional limits.

## 1. Executables and operating model

| Entry point | Purpose | Dependencies / boundary |
| --- | --- | --- |
| `python tools/dashboard/dashboard.py` | Active local web dashboard | Python standard library; optional integrations separately installed |
| `tools/dashboard/start_dashboard.ps1` | Windows dashboard launcher | PowerShell and Python |
| `python tools/setup/setup_web.py` | Separate vanilla setup UI | Explicit setup actions; not the chat runtime |
| `tools/setup/start_setup.ps1` | Setup launcher | PowerShell |
| `python tools/web/smelter_console.py` | Earlier standalone local console | Separate state/handlers; not a second layer of the active UI |
| `python tools/dashboard/mcp_server.py --root …` | Per-call built-in stdio tool server | Pinned optional MCP SDK; launcher-supplied grants/snapshots |
| `opencode serve …` | External headless agent server | Started separately by operator; dashboard never launches it |
| `tools/bootstraps/*.ps1` | Install/configure/diagnose/probe stages | Script-specific approvals and dependencies; inspect individually |
| `tools/core/test_*.py` | Historical agent/asset integration experiments | Some call Ollama, Blender or Docker; names do not imply offline safety |

### Start and stop

Run from the checkout root. The dashboard creates a launch token and binds to `127.0.0.1:8768`; use its printed URL including the token fragment. The browser authentication helper reads the current fragment and sends the API token header. Do not paste launch URLs into reports. On restart, reconnect using the new token. Stop the owning terminal with Ctrl+C. A browser refresh does not restart the backend or adopt changed startup skill fingerprints.

On first run, initialize a SQLite database outside the checkout. The marker remains inside `.smelter/database-location.json`. Existing database selection is immutable through the initialization endpoint; relocation needs a separate migration. A failed fresh initialization cleans up only files created by that attempt. Legacy extension/model JSON is imported once and preserved.

### External services

| Component | Expected endpoint/version in adapter | Meaning of verification |
| --- | --- | --- |
| Ollama | `http://127.0.0.1:11434`; `/api/chat`, `/api/tags`, `/api/ps` | Model enumeration/allocation and actual request replies are different observations |
| OpenCode | `http://127.0.0.1:4096`; adapter pins 1.19.3 | Health, directory, live permission schema, local provider and echoed session rules checked |
| REA | `rea-agents` 6.7.0 under `.smelter/tooling/rea` | Package presence checked separately from approved live CLI invocation |
| MCP | SDK 1.30.0 in `requirements-mcp.txt` | Installed SDK enables stdio transport; does not install tool servers |
| GLB viewer | model-viewer 4.1.0 local bundle | Browser rendering dependency, independent of model inference |
| 7-Zip / FFprobe / Blender | Discovered executables; adapter-specific checks | Version/dependency checks do not prove content conversion or agent connectivity |

These describe the code's expectations; they are not recommendations to upgrade to unverified current versions.

## 2. Layer responsibilities

| Layer / modules | Responsibility | Calls / data boundary |
| --- | --- | --- |
| `dashboard.py` + browser JS | HTML, auth, API routing, UI state, polling, settings | Calls controllers; still contains a large inline script |
| `access_ui.js` | Settings surface, location editor, task-access summary | `/api/access-policy`; existing engine/task controls moved into one dialog |
| `chat_jobs.py` | One active task, admission, cancellation, status and bounded job retention | Chooses direct Ollama or OpenCode worker; keeps state in memory |
| `chat_inference.py`, `context_budget.py` | Prompt/history/skill assembly, bounded model-tool loop, outcome persistence | Local Ollama; ToolSession; SQLite transcripts |
| `python_tools.py`, `tool_registry.py` | Normalize grants, schemas, fixed dispatch, receipts, audits and deduplication | Registered adapters only; no arbitrary shell/editor |
| `access_policy.py` | Registered-location matching, flags, exclusions, immutable revision | Context-local checks around built-in execution; no OS sandbox |
| `mcp_connections.py`, `mcp_server.py` | SDK exchange, stdio lifecycle, descriptors and child snapshot transfer | Built-in calls create transient child processes |
| `opencode_runtime.py` | Existing-server validation, session rules, prompt submission, polling/abort | Separate OpenCode process and its own provider/configuration |
| `database.py`, `config_store.py`, `chats.py` | Bootstrap/readiness, authoritative configuration, paginated transcripts | SQLite plus a filesystem database-location marker |
| `skills_catalog.py`, `skill_manager.py`, `skill_collections.py` | Discover, enable/disable, import approved instruction text | Bundled and managed manifests; state remains JSON |
| `skill_runtime.py`, `skill_context.py`, `skill_router.py` | Startup fingerprints, bounded instruction text, deterministic suggestions | Changed/new manifests require restart; at most three explicit skills |
| `frontend_workspace.py`, `file_activity.py/.js` | Managed V2 copy, CSS-only edits, tests/preview and file cards | Hash/structure checks, isolated preview database, fixed operations |
| `model_assets.py`, preview/animation/turntable JS | GLB validation/storage, local browser preview, clip labels/exports | Saved attachments and SQLite metadata; no animation-meaning inference |
| `execution.py`, `media.py`, `blender.py`, `rea_connection.py` | Fixed explicitly approved inspection processes | Subprocess timeout and argument validation; not general execution tools |
| `resource_metrics.py`, `system_status.py`, `startup.py` | Host counters, Ollama allocation and startup checks | Observations, not CPU/RAM/VRAM reservations |
| `tools/core/smelter_registry.py` and adapters | Older capability registry and asset/material/integrity experiments | Not imported into dashboard tool dispatch automatically |

## 3. Chat execution contracts

### Direct Ollama

1. Browser consumes the next-message approvals and sends `action=start`, conversation ID, text, optional image/skills and tool permissions.
2. `Jobs.start` validates admission, captures the access policy and denies an overlapping active job or unconfined external MCP selection. A worker thread is created.
3. `chat_inference.ask` loads the conversation, saved reasoning model and runtime settings. It selects explicit/suggested skills and creates a ToolSession.
4. Prompt/history, skill text and schemas are bounded. The estimate uses UTF-8 bytes and reserves, not the model's tokenizer. Oversized current work is rejected instead of silently trimming required instructions.
5. `Control.infer` owns a cancellable HTTP transport and assembles Ollama stream chunks. The GUI polls job status for partial content, phase, receipts and file activity.
6. Model tool calls must name an approved schema and use valid arguments. ToolSession writes a request audit before dispatch. Policy checks and adapter restrictions both apply.
7. Tool results are added to the model conversation. The loop has a bounded call budget; repeated create/write/launch calls use an explicit deduplication set.
8. Final user/assistant messages and controller execution data are stored. Tool/model follow-up failures after actions preserve receipts and return partial outcomes. Cancellation does not roll back completed writes.

Legacy `action=ask` now follows the same asynchronous controller and returns HTTP 202/job information. It is no longer a synchronous reply endpoint.

### OpenCode read-only

The operator starts OpenCode from the sibling V2 directory. Check the existing server in **Review task access** while the OpenCode engine is selected, select a verified local model and approve one session. The dashboard checks version, directory, live permission schema and local Ollama provider configuration. A fresh session is created with default-deny rules and a limited read allowlist for README, tools and skills; nested policy exclusions add denials. The server must echo the exact requested permissions and directory before any prompt is sent.

The fresh session receives up to twelve earlier user/assistant texts within a bounded character budget. This preserves useful context while avoiding reuse of prior grants. Skills, images, GLBs, SMELTER MCP grants, shell commands, edits and delegation are not forwarded. Session reuse is not implemented. Polling currently has a fixed five-minute limit and reads the latest fifty external messages. Stop requests abort only the owned session; abort failure is reported. Remaining final-completion/cancellation consistency defects are recorded in the review.

### Built-in MCP

Selecting built-in MCP changes transport, not authority. The launcher transmits normalized grants, the fixed task policy and parent skill fingerprints to the child. Discovery/call connections close afterward. A changed manifest cannot become active just because a fresh child was started. Persistent frontend preview launch is handled by the dashboard owner even when other tools use MCP, so transient-child cleanup does not own the preview lifetime.

Arbitrary external servers are saved configuration only: GUI discovery and task execution are blocked pending confinement. Low-level exchange helpers can still be called by explicit operator Python code; they are not a sandbox for third-party servers.

## 4. Access model and tool catalog

**Effective authority = registered location policy ∩ per-message grants ∩ adapter's fixed operation contract.** An enabled skill is instruction text and cannot add authority.

Policies allow at most 32 locations. Local absolute paths are required; whole filesystem/drive roots, UNC, traversal, reparse/symlink paths and alternate streams are rejected. Most-specific enabled matching location wins. Relative exclusions deny access within that row. A disabled nested row is ignored; an enabled row with all flags off denies the subtree. Execute selects from `tests`, `preview`, `rea`, `archive`, `media`, `blender`, not arbitrary executable names or arguments.

| Exposed model tool | Extra restriction |
| --- | --- |
| `inventory_directory` | Approved registered folder; bounded metadata traversal, no file-content reads |
| `write_diagnostic_markdown` | New plain `.md` basename in diagnostics; no overwrite; saved-byte digest |
| `rea_capabilities` | Explicit process approval, enabled REA skill and registered REA execution directory |
| `rea_inspect_pe_resources` | Same plus approved readable folder, relative `.exe/.dll`, MZ signature and 64 MiB limit |
| `frontend_workspace_info` | Fixed original/sibling locations and actual supported surface |
| `prepare_frontend_workspace` | Refuses unmanaged existing target; isolated database; checks copied source/destination paths |
| `read_enabled_design_skill` | Actual enabled design-skill ID and active manifest snapshot |
| `read_frontend_file` | Listed readable files; dashboard CSS only; bounded pagination |
| `replace_frontend_css` | Exact substring and CSS SHA-256; original/backend/HTML/JS preserved |
| `validate_frontend_workspace` | Registered tests operation; fixed test commands; no model-chosen shell |
| `launch_frontend_preview` | Registered preview operation, validated current content, fixed port and startup health check |
| `inspect_model_attachment` | Explicit saved-attachment ID; bounded metadata/clip timing inspection |

Application-owned database, audits, installed skill text/runtime dependencies, uploaded attachments and preview bookkeeping are handled by dedicated application operations. Path policy does not grant general access to `.smelter`. Operator configuration/installation APIs are distinct from model tools. Executed tests/previews still run as the OS user: permitted working directories do not confine child code's filesystem or network access.

## 5. API map

All active dashboard APIs require the launch token. Static page/assets are served separately. The paths below are source contracts, not a second independent public service specification.

| Method / path | Operations / implementation |
| --- | --- |
| GET `/api/startup` | Database/configuration/dependency startup report |
| POST `/api/database/select` | First database selection/initialization |
| GET `/api/system/status` | CPU/RAM/disk, database, Ollama model allocation |
| GET `/api/extensions`; POST same | Catalog / enable state in SQLite |
| GET `/api/ollama/models` | Installed model discovery, gated by extension/dependency state |
| GET `/api/ollama/preferences`; POST same | Read/save installed reasoning or lightweight model preference |
| GET `/api/runtime` | Effective direct-chat settings and source attribution |
| POST `/api/chats`, `action=runtime_settings` | Save runtime settings; does not reload a model |
| GET `/api/chats`; GET `/api/chats/{id}` | Conversation list / latest or `before` message page |
| POST `/api/chats` | Create, note, rename, delete, ask/start or stop; action dispatch in handler |
| GET `/api/chat-jobs/{id}` | In-memory task progress/outcome; restart loses these jobs |
| GET/POST `/api/access-policy` | Effective policy/model summary / save operator policy |
| GET `/api/skills`, `/api/skills/status`, `/api/skills/review/{id}` | Catalog, active/restart status, current manifest review |
| POST `/api/skills/manage` | Explicit add/enable/disable/remove managed instruction operations |
| POST `/api/skills/discover`, `/api/skills/discover-repository`, `/api/skills/collection-preview` | Preview-only GitHub manifest discovery / collection review |
| GET `/api/mcp/status`; POST `/api/mcp` | SDK/config status, save/probe/discover with current gates |
| GET `/api/rea/status` | Package/launcher status; not live target analysis |
| GET `/api/opencode/status`, `/api/opencode/provider-preview`, `/api/opencode/validate` | Detection, in-memory config preview, offline staged validation |
| POST `/api/opencode/deploy` | Explicit create-only isolated config staging; no server launch |
| GET `/api/opencode/agent` | Live read-only bridge compatibility check |
| GET `/api/models/status`; GET `/api/models/{id}` | Viewer dependency status / saved attachment bytes |
| POST `/api/models` | GLB attachment or animation-label operation |
| GET `/api/workflows`, `/api/workflows/reports` | Dry-run definitions / recent report view |
| POST `/api/workflows/plan` | Dry-run dependency/input checks and report write |
| POST `/api/archive/inspect`, `/api/media/inspect`, `/api/blender/inspect` | Fixed explicitly approved inspection processes |
| POST `/api/aero/classify` | Deterministic aerodynamic classification helper; not part of agent execution |

See `handler.Handler.do_GET` and `do_POST` in the function index for exact action names, schemas and error handling. The review identifies the lack of a uniform JSON-object validation boundary. Some invalid top-level request types currently yield an uncaught error instead of a consistent JSON 400.

## 6. Persistent and transient state

| State | Location | Ownership/lifecycle |
| --- | --- | --- |
| SQLite selection | `.smelter/database-location.json` | Path marker; do not manually relocate without migration |
| Metadata/configuration | External `smelter.sqlite3`: metadata, config_snapshots | Extensions, models, runtime settings and access policy authoritative here |
| Transcripts | conversations, messages, message_execution | Execution JSON contains engine/tool evidence; narrative not independently fact-checked |
| GLB attachment records | model_attachments | References message plus metadata, original clip names and user labels |
| GLB bytes | `.smelter/model-assets/{id}.glb` | Separate disk storage; chat deletion currently leaves orphan files |
| Skill state | `.smelter/skill-state.json`, managed-skills/collections | Separate JSON/instruction storage, not SQLite config snapshots |
| Skill startup baseline | SkillMonitor in memory | Dashboard restart required to activate changed/new manifest text |
| Tool audits | `.smelter/tool-runs/*.jsonl` | Request/result evidence; sensitive local data and launch URLs may occur |
| REA evidence | `.smelter/rea-evidence/*.json` | Retained raw output and digest; no automatic retention policy |
| Workflow reports | `.smelter/reports/` | Create-only reports; returned list bounded, total disk files are not |
| Preview workspace | Sibling V2 and V2-Data, managed marker in destination | Preserved/reused, not reset by source updates |
| Runtime jobs | `Jobs.jobs`, Control and file-activity objects | Memory only; no crash recovery/resume |
| Resource counters | In-memory sample and live `/api/ps` | Measurements; no enforced allocation budget |

Back up the selected SQLite database and required application-owned state together using a consistent database backup procedure. A copy of the repository alone does not include conversation storage or managed skills. No automated complete-backup/restore transaction exists. Do not publish raw audits without reviewing tokens, paths and sensitive content.

## 7. Verification and troubleshooting

Run offline dashboard/setup/analysis unit suites and JavaScript tests from the root; commands are in README. With the optional SDK installed, stdio integration tests start only fixture/built-in processes. The recorded application suite had 294 tests with one skip, setup 32 and JavaScript 10. Documentation-analysis tests are separate. This is component verification, not proof that every feature or external service works on Windows.

| Symptom | First evidence to inspect |
| --- | --- |
| No UI / wrong port | Owning terminal's current launch URL and process; active dashboard 8768, preview 8770, OpenCode 4096 are different |
| Unauthorized after restart | Current fragment/token; database initialization does not repair authentication |
| Skill enabled but no tool | Actual ToolSession schema and grants; a manifest does not install executables or register capabilities |
| Skill changes ignored | Skills status/review and restart-required baseline |
| Tool denied | Registered location, most-specific row, exclusions, operation and next-message approval; inspect receipt |
| Config saved but OpenCode unchanged | Staging is separate from the independently running server's effective config |
| Slow/empty model response | Runtime settings, context estimate, actual Ollama logs/allocation; GPU allocation is not utilization |
| Preview unchanged | Existing V2 is preserved; source and destination are different trees; inspect CSS hash and validation receipt |
| Task says partial | Read tool receipts and follow-up error; successful file writes remain real even if explanation failed |
| Stop disagrees with OpenCode transcript | Known final-completion race; inspect external session/audit before relying on completion state |

## 8. Maintenance direction

Prioritize lifecycle correctness and access-policy contract tests before adding broad execution tools. Then split the dashboard HTTP router and inline script, extract the inference loop into explicit phases, and normalize job results across engines. Introduce a confined runner before exposing arbitrary MCP or general editing/commands. Retain compatibility adapters until their consumers are migrated. Full findings and proposed acceptance checks are in the deep review.
