# SMELTER

SMELTER is a local-first development and asset-inspection workbench. Its active interface is the Python dashboard in `tools/dashboard`, with local Ollama chat, registered Python tools, optional built-in MCP transport, and an OpenCode **read-only** source-inspection adapter.

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

The standard dashboard backend uses the Python standard library. Local inference additionally requires a separately running Ollama server at `127.0.0.1:11434` and an installed model. The fallback reasoning model is `qwen3.5:9b`; the saved reasoning preference controls direct inference. Python 3.13 is the user's Windows environment; current automated verification here used Linux/Python 3.12. Hardware, drivers and model performance require local validation.

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
- These checks are **not an OS sandbox**. External MCP discovery/execution from the GUI is blocked until a confined runner exists. Built-in SMELTER MCP remains available.

## Current capability boundaries

| Capability | Current behavior |
| --- | --- |
| Direct local chat | Selected reasoning model, bounded context estimate, streaming job progress, cancellation and saved receipts |
| Skills | Bounded manifest instructions; startup fingerprints; changed/new manifests require dashboard restart |
| Python/MCP tools | Fixed registered operations, per-message grants, audits and application path checks |
| Frontend work | Create/reuse sibling V2; read approved files; **CSS replacement only**; fixed tests and preview on port 8770 |
| GLB | Browser preview, animation selection, frame/turntable export and stored animation labels; no automatic semantic naming |
| REA | Pinned adapter exposes capabilities and static PE resource inspection, not general native decompilation or game-container extraction |
| OpenCode | Existing local server on 4096, validated version 1.19.3 and provider, fresh read-only session with bounded conversation text |
| Workflow planner | Dry-run dependency planning; not an autonomous execution workflow |
| Legacy CLI/core | Separate experiments and registries; no implicit GUI bridge |

An enabled skill, detected executable, open port, successful save, or completed model explanation proves only that specific observation. Tool receipts are evidence of tool results, not independent verification of every AI statement.

## Documentation

| File | Contents |
| --- | --- |
| [System documentation](docs/SYSTEM_DOCUMENTATION.md) | Setup, components, APIs, storage, execution sequences, permissions, operations and troubleshooting |
| [Relationship maps](docs/SYSTEM_RELATIONSHIPS.md) | Layer diagrams, edge semantics and graph regeneration |
| [Interactive graph](docs/graph/system-graph.html) | Offline, searchable file/function explorer; download and open locally |
| [Graph JSON](docs/graph/system-graph.json) | Machine-readable files, symbols, call/reference/import candidates and unresolved expressions |
| [Function index](docs/FUNCTION_INDEX.md) | Every indexed application function/callback and script, source links and complexity estimates |
| [Deep review](docs/DEEP_CODE_REVIEW.md) | Remaining defects, unused candidates, complexity hotspots and prioritized follow-up work |
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
| `agents/skills/` | Agent contracts/scaffolding; distinct from dashboard's managed catalog and legacy `.agents/skills` |
| `studio/` | Frontend/backend scaffolding, not the active dashboard |
| `automation/` | Repository state helper and workflow/handover scaffolding |
| `diagnostics/` | Committed historical evidence and locally created reports |
| `projects/` | Reserved project area; not implicitly granted to the agent |

## Validation

```powershell
python -m unittest discover -s tools/dashboard -p "test_*.py"
python -m unittest discover -s tools/setup -p "test_*.py"
python -m unittest discover -s tools/analysis -p "test_*.py"
node --test tools/dashboard/test_chat_renderer.js tools/dashboard/test_session_auth.js tools/dashboard/test_file_activity.js
```

Check each exit code before continuing. Some scripts named `test_*` under `tools/core` and `tools/bootstraps` are opt-in model/Docker/Blender experiments, not ordinary offline unit tests; do not run all repository scripts indiscriminately.

Do not commit credentials, launch tokens, game binaries, extracted game assets, model weights, local databases or generated workspaces. Existing managed V2 copies are preserved; pulling this branch does not update an already prepared V2 copy. Read the deep review before treating the application as a general coding or reverse-engineering agent.
