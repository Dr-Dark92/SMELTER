# SMELTER

SMELTER is a local-first development and asset-inspection workbench. Its active interface is the Python dashboard in `tools/dashboard`. The primary agent route is **GUI -> SMELTER -> OpenCode -> Ollama/Qwen**, with selected skill instructions and approved built-in tools connected through MCP. Direct Ollama chat remains selectable. OpenCode's source snapshot stays read-only; approved host tools retain their existing narrow read/write/execute contracts.

The repository also contains older CLI experiments, game-specific research scripts, reusable Blender/asset adapters, and Studio scaffolding. Those components are not automatically connected to the dashboard. Installing a skill provides instructions; it does not install dependencies or grant tools.

## Start on Windows

From the existing checkout:

```powershell
Set-Location C:\SMELTER
python -m unittest discover -s tools/dashboard -p "test_*.py"
if ($LASTEXITCODE -ne 0) { throw "Dashboard tests failed." }
python tools/dashboard/dashboard.py
```

Open the authenticated launch URL printed in that terminal. The dashboard binds to loopback on port **8768** by default. Keep its launch token private. A restart changes the token; use the new URL. On first use, select an absolute SQLite storage directory outside the checkout. Initialization refuses to overwrite an existing database.

The standard dashboard backend uses the Python standard library. Local inference additionally requires a separately running Ollama server at `127.0.0.1:11434` and an installed model. The default reasoning model is `qwen3.5:9b`; the saved reasoning preference controls admitted inference. The OpenCode route additionally requires the managed Docker runtime and pinned MCP SDK. Automated contracts run on native Windows and Linux/Python 3.13. Hardware, drivers and model performance require local validation.

Optional MCP support:

```powershell
python -m pip install -r tools/dashboard/requirements-mcp.txt
```

This installs the pinned MCP SDK, not REA, Blender, model weights, or arbitrary MCP servers. See [requirements](REQUIREMENTS.md) for external tools. On Linux, run the Python commands from the repository root with your available Python executable; the `.ps1` launchers require PowerShell.

## Access and configuration

- **Settings** contains configuration. **Workspaces & Access** registers locations with read, write and registered-execution flags.
- **Review task access** selects permissions for the next message. Skills cannot expand them. Existing adapter restrictions still apply.
- By default the original checkout is readable, its sibling `SMELTERV2` permits registered frontend work/tests/preview, and `diagnostics/` permits new Markdown reports. Unregistered locations are denied. `.git`, `.smelter` and `projects` are excluded from general agent access.
- Policy changes affect new tasks. Each admitted task keeps its policy snapshot. Application-owned database, logs, skill installations and preview bookkeeping are separate from general agent file access.
- Location checks are application policy. Frontend tests/preview and managed OpenCode additionally require the no-network container runner; they have no host fallback. Fixed native inspection adapters remain bounded host processes. Arbitrary external MCP remains blocked; built-in SMELTER MCP is available.

## Current capability boundaries

| Capability | Current behavior |
| --- | --- |
| Direct local chat | Selected reasoning model, bounded context estimate, streaming job progress, cancellation and saved receipts |
| Skills | Shared bounded instruction selection for direct chat/OpenCode; exact OpenCode task hashes; changed/new manifests require dashboard restart |
| Python/MCP tools | Fixed registered operations, per-message grants, audits and application path checks |
| Frontend work | Create/reuse sibling V2; read approved files; **CSS replacement only**; confined fixed tests and temporary small-fixture preview on port 8770 |
| GLB | Browser preview, animation selection, frame/turntable export and stored animation labels; no automatic semantic naming |
| REA | Pinned adapter exposes capabilities and static PE resource inspection, not general native decompilation or game-container extraction |
| OpenCode | Managed no-network container, pinned 1.19.3, selected skills and approved MCP tools; native code snapshot remains read-only; live rig inference still requires validation |
| Workflow planner | Dry-run dependency planning; not an autonomous execution workflow |
| Legacy CLI/core | Shared skill/capability catalog; explicit scoped Registry bridge; other adapters labelled library-only |

An enabled skill, detected executable, open port, successful save, or completed model explanation proves only that specific observation. Tool receipts are evidence of tool results, not independent verification of every AI statement.

## Documentation

See the [agent bridge plan](docs/AGENT_BRIDGE_PLAN.md) and [runtime/smoke instructions](tools/dashboard/OPENCODE_RUNTIME.md) for the current OpenCode/skills/MCP route. General multi-file coding and arbitrary external MCP remain future work.
The [agent bridge handover](docs/AGENT_BRIDGE_HANDOVER_20261021.md) records the verified source, smoke evidence and remaining live-rig checks.

| File | Contents |
| --- | --- |
| [System documentation](docs/SYSTEM_DOCUMENTATION.md) | Setup, components, APIs, storage, execution sequences, permissions, operations and troubleshooting |
| [Relationship maps](docs/SYSTEM_RELATIONSHIPS.md) | Layer diagrams, edge semantics and graph regeneration |
| [Interactive graph](docs/graph/system-graph.html) | Offline, searchable file/function explorer; download and open locally |
| [Graph JSON](docs/graph/system-graph.json) | Machine-readable files, symbols, call/reference/import candidates and unresolved expressions |
| [Function index](docs/FUNCTION_INDEX.md) | Every indexed application function/callback and script, source links and complexity estimates |
| [Repair status / handover](docs/REPAIR_STATUS_20261021.md) | F01–F11 disposition, evidence, deployment limits and Windows rollout |
| [Deep review](docs/DEEP_CODE_REVIEW.md) | Historical baseline findings, unused candidates and complexity analysis |
| [Changelog](CHANGELOG.md) | Verified revision history and documentation scope |
| [Patch notes](tools/dashboard/REVISION_PATCHES.md) | Configuration/access repair details and rollout constraints |

GitHub shows the graph HTML as source; download it to use the interactive view. The graph is inspired by source-relationship explorers and is generated by the included analysis utilities; Graphify itself was not installed or run.

## Repository layout

| Location | Responsibility |
| --- | --- |
| `tools/dashboard/` | Active dashboard, chat/tool controllers, configuration, asset preview and unit/integration tests |
| `tools/setup/` | Dependency detection, explicit setup operations and setup web interface |
| `tools/core/` | Older reusable capability/asset adapters and opt-in integration experiments |
| `tools/bootstraps/` | Windows configuration/diagnostic launchers and game-specific research stages |
| `tools/web/` | Earlier standalone console; separate from the active dashboard |
| `tools/analysis/` | Static graph generation, review reproductions and analysis tests |
| `skills/` | Bundled dashboard skills and declarative skill policy |
| `agents/skills/` | Agent contracts/scaffolding; namespaced manifest discovery in the shared catalog, disabled until reviewed/enabled |
| `studio/` | Frontend/backend scaffolding, not the active dashboard |
| `automation/` | Repository state helper and workflow/handover scaffolding |
| `diagnostics/` | Committed historical evidence and locally created reports |
| `projects/` | Reserved project area; not implicitly granted to the agent |

## Validation

```powershell
python -m unittest discover -s tools/dashboard -p "test_*.py"
python -m unittest discover -s tools/setup -p "test_*.py"
python -m unittest discover -s tools/analysis -p "test_*.py"
node --test tools/dashboard/test_chat_renderer.js tools/dashboard/test_session_auth.js tools/dashboard/test_file_activity.js tools/dashboard/test_operations_ui.js
```

Check each exit code before continuing. Some scripts named `test_*` under `tools/core` and `tools/bootstraps` are opt-in model/Docker/Blender experiments, not ordinary offline unit tests; do not run all repository scripts indiscriminately.

Do not commit credentials, launch tokens, game binaries, extracted game assets, model weights, local databases or generated workspaces. Existing managed V2 copies are preserved; pulling this branch does not update an already prepared V2 copy. Read the repair handover for container setup, backup/restore, preserved V2 copies and platform verification requirements.

## GUI revision

Settings now uses a navigation rail, a selectable skills table with expandable collections and a single + attachment menu. Reviewed imports skip existing IDs/content and import unique skills disabled. See [GUI and import behavior](docs/GUI_SKILLS_AND_ATTACHMENTS.md).

## Operational repair (V1.7)

Settings now includes confined execution, storage/recovery/backup and capabilities/project checks. Tasks keep an admitted model/settings/policy snapshot and durable lifecycle record; interrupted work is reported without replay. Artifact storage has conservative quotas and an explicitly reviewed retention plan. Database integrity checks are operator-triggered; dependency probes have a short timestamped cache.

**Docker is optional for ordinary chat and existing fixed native inspections, but mandatory for frontend tests/preview and managed OpenCode.** There is no automatic image pull or unconfined fallback. Live Docker/Windows execution remains to be validated on the rig. See the [repair handover](docs/REPAIR_STATUS_20261021.md).

## Office GUI work without Qwen

Run `python tools/analysis/offline_gui_fixture.py` from the checkout and open its printed launch URL. It serves the actual GUI with synthetic replies and temporary SQLite/report state on port 18771. No live Ollama/OpenCode/Docker service is used. Ctrl+C removes fixture state. See [office GUI workflow](docs/OFFICE_GUI_WORKFLOW.md) for fish commands and checks.

Registered locations now use a staged permission table with folder browsing and atomic Apply. See [location controls](docs/REGISTERED_LOCATIONS.md).

The [historical runtime review](docs/reviews/2026-10-21/REVIEW.md) records seven reproduced defects. They are implemented and regression checked in the [UI/UX overhaul](docs/UI_UX_OVERHAUL.md), with current [progress](docs/reviews/2026-10-21/PROGRESS.md) and [handover](docs/OVERHAUL_HANDOVER_20261021.md).

The workbench now has grouped searchable Settings, a responsive conversation drawer, an integrated composer and explicit permission/resource context. See the [design system](design-system/smelter/MASTER.md) and [rollout guide](docs/UI_UX_OVERHAUL.md) before refreshing an existing V2 workspace.
