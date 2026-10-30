# SMELTER V1 — System Requirements

## Bounded native task watchdog

The user-authorized watchdog captures the bound coding prompt privately, waits
for an explicit `finish_coding_task` with verified RED/GREEN, and submits at most three same-session checkpoint
continuations if work stalls without an end flag. Stop, new human input, active
tools, permissions/questions and uncertain delivery prevent duplicate work.
Repeated tool-contract errors and non-improving frozen results hold recovery
for diagnosis rather than replaying the same objective.

Install/start with `python tools/setup/manage_task_watchdog.py install` and
`python tools/setup/manage_task_watchdog.py start`; `activate` loads the new hook
only when the exact native instance is idle. `status`, `disable` and explicit
`adopt` operations are also available. `resume` repairs only legacy automatic-RED
termination without resetting retries or reviving Stop/explicit completion.
Existing Python/OpenCode standard-library
runtimes are reused: no new packages. All files and bounds are declared under
`task_watchdog` in `system-requirements.json`. See [watchdog behavior and private
state](docs/WATCHDOG.md). The trace WebSocket remains read-only.

Focused coding edits use `propose_coding_edit` (one file, one replacement, five
flat string fields); the batch API remains available. Stdio validates the same
advertised schema inside the controller so malformed calls are audited and
budgeted. `tools/dashboard/requirements-mcp.txt` explicitly pins the already
installed `jsonschema==4.26.0` dependency used for validation. No new package
installation was needed. See [coding recovery](docs/RECOVERY_GUARDRAILS.md).

## Managed plugin development (operator build only)

`tools/setup/install_managed_sdk.py --sdk rph` caches the author-owned NuGet
RagePluginHook SDK **1.124.0** from its SHA-256-pinned package in
`tools/setup/managed-sdk-lock.json`. It is a development reference, not a game
loader. The SDK license prohibits redistribution; it stays in ignored
`.smelter/tooling/rph-sdk/` and is never copied into plugin outputs or releases.

`tools/setup/build_managed_mod.py --workspace-id <UUID> --mod <id> --target <name>`
is an **operator-only** fixed C# 5/x64 library compiler for an owned coding copy
and `managed.json`. It uses the installed Windows .NET Framework compiler
(4.7.2+ runtime required), fixed framework references and a pinned SDK. No
MSBuild targets, analyzers, custom flags, SDK execution or output execution.
This is not exposed to the model and is not a host fallback for the confined
native builder. Receipts pin sources/compiler/references/artifact hashes;
compilation does not establish game compatibility. C# source is editable in
coding copies; DLLs and other build outputs remain excluded. Python standard
library only; no new Python package or system compiler was installed.
The CLI preserves its JSON receipt and exits nonzero when its stage is not
`compiled`, so an automated shell cannot mistake a compiler failure for success.

The [RPH team's Enhanced release](https://www.lcpdfr.com/downloads/gta5mods/g17media/52970-lspd-first-response-enhanced-preview/)
dated 17 September 2026 lists build 1158.16 support. That supplies a candidate
runtime route separate from Script Hook V; live loading and native reads remain
separate proof gates. No game or security settings are changed by these tools.

The optional `mods/gta-ark/managed.json` target `SmelterNativeProbe` compiles a
read-only RPH diagnostic, with an engine-neutral report/gating harness in
`common/managed/RuntimeProbeHarness.cs`. Its game-specific profile and callbacks
live under `gta/rph/`. It does not implement the six gameplay capabilities or
host Lua. See [probe preparation and evidence](docs/GTA_NATIVE_READ_PROBE.md).
`tools/setup/test_managed_mod_build.py` checks the compiler/cache boundaries;
`tools/setup/test_runtime_probe.py` compiles and runs only a reviewed fake-callback
fixture, without referencing RPH or opening a game. Both reuse the installed
Framework compiler and Python standard library. The real plugin is never run by
the builder or tests, and RPH runtime installation remains separate.

Two operator-only, read-only tools support the supervised run.
`tools/setup/inspect_loader_runtime.py <folder-or-zip>` records each file's
SHA-256 and PE file version under `.smelter/runtime-inventories/`. Zip members are
read in place, never extracted, and nothing is executed.
`tools/setup/verify_runtime_probe.py --profile <expectations.json> --latest --loader-log <log>`
judges the newest probe report against a reviewed per-game profile (GTA:
`mods/gta-ark/gta/rph/read_probe_expectations.json`). It re-hashes the
executable and the profile-selected deployed plugin on disk, and requires the
loader's receipt marker to name the exact report path/run. Windows long/8.3
aliases and slash/case differences are normalized. It writes a verdict under
`.smelter/runtime-probe-verdicts/`. Both use only the Python standard library.
Receipt filenames cannot be selected by malformed report run IDs. These tools
are tested by `tools/setup/test_runtime_probe_verdict.py`, which also judges a
real harness fixture report.

`tools/setup/stage_native_read_probe.py plan|apply|remove` performs the one
game-folder change of that run, reversibly. `extract --archive <author zip>`
copies only the archive's top-level files into `.smelter/native-read-gate/runtime/`.
`plan --runtime-dir <folder>` selects every top-level file plus the staged probe
(RPH's readme: everything except its SDK and Licenses folders) and requires
`RAGEPluginHook.exe`. Anything in a subfolder, such as a bundled LSPDFR's
`plugins/` and `lspdfr/`, is listed as excluded and needs an explicit `--file`. `apply --plan <plan.json>` refuses any existing target, re-hashes the
executable and every source first, and writes an install manifest under
`.smelter/native-read-gate/installs/` before copying. `remove --install <manifest>`
deletes only files whose bytes still match. Pins come from the same expectations
profile. Python standard library only; tested by `tools/setup/test_stage_native_read_probe.py`.

## In-game Lua host probe (operator-only)

`SmelterLuaHostProbe` (`mods/gta-ark/gta/rph/LuaHostProbe.cs` plus the engine-neutral
`common/managed/LuaTickProbe.cs`) is a read-only RPH plugin. It runs four player
reads, each through the managed Lua 5.4 host and one read-only callback, and
records the `lua54.dll` the game process actually loaded. `build_managed_mod.py`
now accepts a list of pinned SDKs per target (`["rph","keralua"]`).
`tools/setup/verify_lua_host_probe.py` applies the read-probe verdict plus the Lua
evidence against `mods/gta-ark/gta/rph/lua_host_probe_expectations.json`.
It independently re-hashes the reported Lua54 and KeraLua files, requires four
integer tick/thread records on the positive host thread ID, and rejects malformed
Lua evidence with a named reason. These checks do not change the deployed probes.
`stage_native_read_probe.py plan --profile … --package …` without `--runtime-dir`
deploys it onto an existing RPH install, including the pinned `KeraLua.dll`,
`lua54.dll` and KeraLua license beside the game executable. Tests:
`test_lua_tick_probe.py` (real pinned Lua 5.4, fake reads) and
`test_verify_lua_host_probe.py`. Python standard library only.

## Optional managed Lua 5.4 host (offline verified)

The independent entity-registry preparation uses
`tools/setup/check_entity_registry.py --workspace-id <UUID> --reviewed-sha256 <hash>`.
After explicit operator source review it compiles/runs only the pure C# fixture
`tools/setup/fixtures/EntityRegistryFixture.cs` with fixed Framework references,
no SDK/game/native provider. The checker is not an MCP tool. It reuses Python
standard library and the installed Framework compiler; no new package is needed.
Source review/hash, bounded snapshots, compiler/test timeouts and receipts are
separate from Lua regression GREEN. Success requires one well-formed summary
with zero failures and a positive check count matching the individual pass
lines; exit zero or an arbitrary success marker is insufficient. Checker tests
cover malformed/inconsistent summaries and compile/review failures. See
[the registry contract](docs/ENTITY_REGISTRY_TASK.md).

The first GTA-specific read slice is checked by
`tools/setup/test_gta_entity_reader.py` with the fixed fake SDK fixture
`tools/setup/fixtures/GtaEntityReaderFixture.cs`, then compiled separately with
the existing `build_managed_mod.py` target `SmelterGtaEntityReader` and the
pinned RPH development SDK. The fixture accepts exact operator-reviewed source
hashes, uses the existing Framework compiler, and bounds compile/run time at
30/10 seconds. It never loads RPH or a game and adds no dependency. Live reader
behavior and the six callbacks remain separate gates. See
[the read-boundary contract](docs/GTA_ENTITY_READER_TASK.md).

`tools/setup/install_managed_sdk.py --sdk keralua` caches **KeraLua 1.4.11**,
its .NET Framework 4.6 binding and Windows x64 `lua54.dll`, using package/member
hashes in `managed-sdk-lock.json`. Its MIT license and Lua's license must be
retained with any future runtime distribution. Nothing is installed into a game.
The existing .NET Framework compiler and Python standard library are reused.

`mods/gta-ark/common/managed/LuaModuleHost.cs` is an engine-neutral host for
reviewed module strings and explicit C# callbacks. It exposes no file loader,
OS libraries or CLR object translator to those modules. It enforces thread
ownership, module/result bounds, explicit failures and a Lua instruction budget.
This is **not a security boundary** for hostile code or blocking CLR callbacks;
callback time overruns are detected after return and fault the host.

`SmelterLuaHost` in `mods/gta-ark/managed.json` selects the pinned `keralua` SDK
for that target. Native DLLs are marked `reference=false` in the lock; the fixed
compiler references only managed assemblies, copies no runtime and executes
no output. Existing `SmelterNativeProbe` still uses the default RPH SDK.

`tools/setup/check_managed_lua.py --workspace-id <UUID>` compiles/runs **only an
operator-reviewed offline fixture**, with fake engine callbacks and the pinned
Lua runtime. It checks all 128 unchanged frozen cases and a missing-attack
mutant. `tools/setup/test_managed_lua.py` tests the bridge independently of GTA;
`test_managed_mod_build.py` tests SDK selection/native-reference exclusion.
The interpreter is not exposed as an MCP host-command fallback. See
[managed Lua host evidence and limitations](docs/MANAGED_LUA_HOST.md).

MoonSharp 2.0.0 was evaluated in a private research fixture and rejected for
this route: it does not supply the Lua 5.4 `utf8` library used by the verifier.
It is not a selected dependency or game runtime; no verifier was weakened to
accommodate it. Its package identity is recorded in the machine catalog.

## Frozen acceptance checks

`tools/dashboard/acceptance_contracts.py` registers reviewed module behavior in
controller metadata outside the model-editable copy. The initial
`entity-policy-v1` verifier uses the existing pinned Lua sandbox and checks 30
engine-neutral entity-policy cases. `predator-controller-v1` (52 checks) verifies
a generic controller against two injected fake adapters: target selection
through the evaluator, movement/attack commands, cooldown and target loss.
`provider-admission-v1` (26 checks) validates an explicit six-function provider,
unchanged read results and command refusals, passive construction and explicit
simulation/provider modes. Admission does not verify game compatibility or supply
a native runtime. Its disposable reference and eight regression mutants are
tested in `tools/dashboard/test_provider_admission.py`. No new packages are required.
`predator-system-v1` adds 20 generic lifecycle checks for passive construction,
explicit provider admission, real policy/controller wiring, actor registration,
refused removal, per-actor errors and fresh state after removal/re-add. It uses
allowlisted sibling modules in the same read-only snapshot; the other three
registered contracts verify those dependencies independently.

For a registered pure Lua contract, the operator can generate an editable
conformance test with `tools/setup/scaffold_acceptance_test.py --workspace-id
<UUID> --contract <id> --destination <project>/tests/test_<name>.lua`. This
creates a hash-checked proposal only; it never applies or registers anything.
It embeds the pinned verifier with the actual subject path relative to the
test working directory. Independent protected acceptance still runs separately.
This uses Python standard library and the existing Lua parser/sandbox.
The subject scaffold also supports `predator-system-v1`: operator-declared
imports and a bounded constructor setup create the real adapter/policy/controller
factory and per-instance state. Actor lifecycle methods remain explicit TODOs
for the model. The scaffold passes 9/20 lifecycle checks; completing its three
methods in a disposable fixture passes 20/20. No new package is needed.

Register a subject explicitly with
`python tools/setup/register_acceptance.py --workspace-id <UUID> --contract entity-policy-v1 --subject <relative-module.lua>`.
The model has no registration or migration tool. After a reviewed verifier
change, re-pin it with `--migrate "<review reason>"` in place of `--subject`. The
change is appended to `acceptance-migrations.jsonl` beside the registry. Failing
checks report what the subject actually returned or raised, and test results
put frozen failures (with the contract text and interface checklist) ahead of
editable-suite errors. Lua validation then requires both its
editable tests and the frozen verifier to pass. Evidence pins subject/verifier
hashes and the executing controller revision. Missing or inconsistent evidence
fails closed. The machine-readable entry is `frozen_acceptance` in
`system-requirements.json`; see [Frozen acceptance](docs/FROZEN_ACCEPTANCE.md).

## Coding recovery and native guardrails

`coding_recovery_context` supplies canonical paths, current hashes, verified
checkpoint references and the first failing stack frame from saved test logs.
Targeted edits handle CRLF/LF differences; the controller blocks repeated failed
calls and unchanged reads. Persistent stdio MCP connections use a renewable
128-call / 15-minute work window, rather than a lifetime 32-call budget. GUI
turn budgets retain their existing limits.

Register the local OpenCode hooks with
`python tools/setup/configure_recovery_guard.py --apply`. Hooks load on the next
OpenCode process and guard only the enabled, exact session/directory binding in
SMELTER's native progress ledger. Native shell/edit/delegation bypasses are
blocked for that task. The installer preserves existing config, makes a backup
and adds missing Ollama request timeout defaults; explicit existing timeouts
remain unchanged. No model turn is submitted or restarted.

This uses the existing Python/OpenCode runtimes and their built-in modules;
there are **no new external packages**. `recovery_guardrails` in
`system-requirements.json` declares the files, limits and setup command. See
[recovery behavior and limitations](docs/RECOVERY_GUARDRAILS.md).

## Exact coding edits and recovery checkpoints

Built-in `coding_workspace.py` now exposes `propose_coding_edits` for unique
old_text/new_text changes; the controller assembles complete files and preserves
unrelated bytes. Existing whole-file proposals remain available, with explicit
line counts and a guard against large accidental truncations. Each confirmed
apply saves hash-verified pre-edit checkpoints, including files created only in
the coding copy. `propose_coding_restore` can select one by `checkpoint_sha256`;
workspace context and apply receipts expose available hashes. This uses Python's
standard library only; no package installation is needed. The machine-readable
entry is `coding_edit_safety` in system-requirements.json. See
[workspace editing and recovery](docs/WORKSPACE_TRACKING.md#safe-targeted-edits-and-checkpoint-recovery).

Proposals that touch `.lua` files are parsed (`luac5.4 -p`, never executed) in the
existing pinned no-network Lua image before they are recorded. A proposal that
would break a file that parses, or create a broken file, is refused with the
line and an excerpt. An already-broken file may still be fixed in steps, and the
proposal then reports the remaining error. If Docker is unavailable, proposals
are not blocked: they carry `lua_syntax.checked=false`, and the test preflight
still applies. No new package is needed (`coding_edit_safety.lua_syntax_gate`).

`coding_workspace_context` returns a compact summary by default: changed files,
receipts, contracts and recent checkpoints. `detail="full"` restores the graph,
history and absolute paths. This is a context-budget change for the 131072-token
profile; no dependency is involved.

`scaffold_contract_subject` (`tools/dashboard/contract_scaffold.py`) proposes a
parseable skeleton for a registered contract subject. It is generated from the
contract's operator-reviewed structured interface. Constructor validation and
method shapes are correct, and behaviour helpers are TODO stubs. The skeleton
is a normal proposal and is never applied automatically. Checkpoint restores
now report how many newer saved versions they would discard. `read_coding_file`
accepts line pagination even when a character offset/limit is also sent; it
reports the ignored arguments instead of rejecting the call. Python standard
library only.

## Universal gameplay implementation slice

The Raptor task is an acceptance case for reusable gameplay logic and project
adapters. Its proposed [shared contract](docs/UNIVERSAL_GAMEPLAY_CONTRACT.md) and
[SMELTER task brief](docs/tasks/RAPTOR_GENERIC_TASK_BRIEF.md) require no additional
external package for the current offline work. Reuse the declared coding MCP,
confined Lua/Python/C++ runners and ECC/gameplay/debugging profiles. This contract
is an implementation specification, not an installed cross-engine runtime.
Add tools only when a concrete engine adapter capability gap requires them, and
declare each actual addition in this file and `system-requirements.json`.

## Native Melty / OpenCode progress

The live task visualization adds `tools/dashboard/task_trace.py`,
`task_socket.py` and `task_trace_ui.js`, using Python's standard library and the
browser's native WebSocket/DOM APIs. No package installation is required. The
same-origin authenticated WebSocket is `/api/task-trace/ws`; a token-protected
HTTP snapshot is `/api/task-trace`. On Windows, existing PowerShell/CIM and TCP
listener metadata discover actual OpenCode ACP processes for read-only pending
access/question inspection. Other platforms retain SQLite task/file telemetry
and explicitly report the ACP permission feed unavailable. Ollama discovery uses
the existing loopback `/api/ps` endpoint. See [live task trace](docs/NATIVE_PROGRESS.md#live-websocket-task-trace).

`task_trace` in `system-requirements.json` declares the modules, sources and
bounds. A supplied Melty task ID can be linked to the exact native binding;
otherwise a native turn ID is labelled as such. No Melty-side task-ID hook is
installed or claimed. The view includes explicit child-session access waits,
budget errors, named file/skill metadata, indexed hashes and quiet-task clues;
it does not submit prompts, grant access, inspect shell contents or restart work.

The trace workbench (`task_trace_graph.js`, `task_trace_workbench.js`,
`trace_artifacts_ui.js`, `trace_history.py`, `trace_artifacts.py`) adds an
interactive relationship graph, inspector, saved final task charts and explicit
task-artifact previews over the same WebSocket feed. It uses the browser's native
SVG/DOM and Python's standard library, and reuses the existing local GLB viewer;
no package is installed. Saved charts (`GET /api/task-trace/charts`) and
artifact registration (`GET/POST /api/task-trace/artifacts`) are bounded files
under `.smelter/task-trace/`. Graphify was evaluated and is **not** installed.
See `task_trace_workbench` in `system-requirements.json` and
[the trace workbench](docs/TRACE_WORKBENCH.md).

The monitor also reads allowlisted lifecycle columns from OpenCode's shared
SQLite metadata in read-only mode. This covers Melty ACP processes whose event
bus differs from the separately running HTTP server. It uses Python's existing
`sqlite3`; no package is installed. Unsupported schemas fail closed and are
reported as unavailable. Message/argument/output/reasoning bodies are excluded.

The built-in `tools/dashboard/native_progress.py` consumes the existing native
OpenCode server's SSE stream at `http://127.0.0.1:4096`. It uses Python's standard
library, the existing dashboard authentication and browser DOM/SVG; no pip/npm
package, WebSocket service, model or external tool is installed. The machine
catalog declares its runtime, endpoint, read-only scope and state location under
`native_progress`. The native server must already be running.

Bind the exact session ID, native directory and owned coding workspace in
**Settings → Debugging → Native task progress**. A saved enabled binding resumes
with the GUI; monitoring never submits prompts or controls the native task.
If native server Basic authentication is configured, its existing process
environment variables `OPENCODE_SERVER_USERNAME` / `OPENCODE_SERVER_PASSWORD`
can authorize these GET requests; credentials are not saved in the progress
ledger. See [operation, privacy and reconnect limits](docs/NATIVE_PROGRESS.md).

## Workspace index, diagrams and native continuity

Setup/profile `workspace_tracking` runs
`python tools/setup/install_workspace_tracking.py` (use `--preview` to inspect).
It enables the bundled `diagrams` skill and bridges it plus compact path/index
instructions to an existing native OpenCode configuration. It downloads nothing,
backs up configuration changes, preserves model/MCP/permission settings and
refuses conflicting native instructions.

Persistent filename/SHA-256 tracking, bounded relationship graphs and the
dashboard SVG viewer use Python's standard library and browser APIs. There is
no new pip/npm dependency, external renderer or WebSocket service. This setup
is included in the Qwen 35B agent profile; its 128K/8K limits remain unchanged.
See [workspace operation and limits](docs/WORKSPACE_TRACKING.md) and
[future SSE/media bridge](docs/NATIVE_PROGRESS_AND_MEDIA_ROADMAP.md).

## ECC coding instruction bridge

The reviewed ECC source is `https://github.com/affaan-m/ECC` at commit
`25278e7d7b6cf6e6a4e7a6c8e10f14ff22f0eb5b` (MIT). The repository includes
11 concise adapted profiles and two SMELTER-authored skills for Windows/Lua
debugging and gameplay logic testing. Original reference text, licenses and
SHA-256 hashes are retained through `tools/setup/ecc-bridge-lock.json`.
`.gitattributes` preserves LF bytes for checksum-verified instructions on Windows,
including when Git's `core.autocrlf` is enabled.
Setup step `ecc_bridge`, the `ecc_coding` profile and `qwen35b_agent` declare it
in `system-requirements.json`.

Preview with `python tools/setup/install_ecc_bridge.py --preview`; install/enable
with `python tools/setup/install_ecc_bridge.py --apply`. The setup queue runs the
same installer. It uses Python's standard library and the vendored sources,
without network downloads. `--no-native` enables only dashboard routes;
`--no-auto-coding` leaves dashboard task selection explicit. Native Qwen's
existing 131072-token context / 8192-token output settings are preserved.

This bridges instruction text to existing SMELTER editing/testing/build tools
and OpenCode's native skill discovery. It does not install ECC's executable
plugin, hooks, model-specific agents, package managers, coverage tools, GoogleTest
or an additional memory layer. Existing pinned Lua/C++/Python/Node runners are
reused. See [the ECC bridge guide](docs/ECC_BRIDGE.md) for profiles, provenance,
activation, validation and limitations.

## Lua module validation for SMELTER-authored mods

The existing pinned `image_cpp` toolchain supplies Lua 5.4.8-r0 for offline
module syntax checks and `run_coding_tests profile=lua`; no host Lua installation
is needed. The Lua profile now compiles every Lua file in each tested mod before
executing test programs, including modules no test imports. It permits up to
512 source files and 64 test programs, within the existing no-network limits.
Syntax errors stop the run with ERROR and zero behavioral tests executed.
Receipts include `source_syntax`, a host runner SHA-256 and explicit validation
scope; older Lua receipts require retesting. Tests still must import the actual
implementation and use failing assertions: syntax success does not prove behavior
or in-game compatibility. See the [Raptor progress review](diagnostics/RAPTOR_PROGRESS_REVIEW_20261026.md).
No new package/image was installed for this validation repair. Additional selected tools still require
version/source/checksum records and documentation before installation.

The existing coding editor also accepts UTF-8 `.hex` fixture text through its
normal propose/apply hash checks. This permits restoring `tests/gal1_fixture.hex`
alongside the original regression tests; it does not execute hex files or permit
binary build outputs. Original fixture/test bytes must be restored from the
checkout rather than replaced with import-only tests bearing the same names.

The built-in `propose_coding_restore` MCP operation restores original source
text through a normal proposal: it reads 1–6 original checkout paths, captures
their bytes/source hashes and the current coding-copy destination hashes, and
returns a proposal ID. `apply_coding_patch` rechecks both original and destination
state before applying. This uses the existing Python standard library and
MCP 1.30.0 dependency; there is no new package, server or executable installer.
Original files, permission scopes, size limits and binary exclusions are preserved.

## Native Qwen tool mode

`python tools/setup/configure_melty_cli.py --native-tool-mode --apply` (preview
first) selects direct answers for native tool work and keeps an explicit
`smelter-thinking` variant. It uses the existing OpenCode/Ollama installations
and Python standard library; no dependency is added. Context/output remain
131,072/8,192. Refresh and verify the running native global configuration cache;
a JSON file change alone does not activate it. See the
[mode, activation and tests](docs/NATIVE_QWEN_TOOL_MODE.md).

## Native REA context gateway

The native Melty/OpenCode profile can wrap its existing REA command with
`python tools/setup/configure_melty_cli.py --compact-rea --apply` (preview first).
`tools/dashboard/rea_mcp_gateway.py` uses the existing pinned MCP 1.30.0 SDK and
its dependencies; no new package is installed. It exposes three discovery/schema/
call tools instead of injecting all 207 REA schemas into each Qwen prompt. The
original backend/Ghidra environment stays in use, with 128K/8K unchanged. See
[configuration, measurements and tests](docs/REA_CONTEXT_GATEWAY.md).

## Shared database paths on Windows

Native Melty/OpenCode and a packaged Codex app must reference the same physical
SQLite file. Database setup now stores its canonical path to avoid Windows
LocalAppData redirection splitting the two environments. Older readable markers
can be repaired with `python tools/setup/canonicalize_database.py --apply` after
preview; the standard-library helper requires idle tasks and backs up the marker
and database before changing the pointer. It installs no dependency and moves no
data. See the [verified Melty repair](docs/MELTY_CONNECTOR.md).
The existing MCP 1.30.0 SDK also carries the source/inventory scope instructions
at initialization; no additional dependency is needed for native workspace
context. The client working directory does not change the approved tool scopes.

## GTA–ARK prototype runtime workflow

The [cougar-based Raptor proposal](mods/gta-ark/COUGAR_RAPTOR_PROTOTYPE.md) records
RageOpenV as an **uninstalled candidate** in `mods/gta-ark/runtime_requirements.json`,
source commit `f742117a5e8ccc359bf3b4644c6bce7dad77cc7a`. Its documented source build
needs CMake 3.17+ and Visual Studio C++; no dependency was installed in this pass.
It is an asset loader, not a native scripting API. Exact 1.0.1158.16 compatibility,
a binary/release checksum and a headless Enhanced asset pipeline remain unverified.
The camera-link preflight continues to use its existing SHV/UE4SS requirements.

The source-only `prototype_workflows.gta_ark` entry points to
`mods/gta-ark/runtime_requirements.json` and its Python CLI. Inspection and source
staging need only the standard library. Confined acceptance reuses the existing
`smelter-cpp:2` Python/Lua image; no new dependency was installed. Script Hook V
and UE4SS remain uninstalled runtime candidates. The dated review finds an exact
GTA Enhanced loader mismatch and unverified ARK APIs; staging is explicitly not
installable. See [commands, sources and evidence](docs/GTA_ARK_RUNTIME_WORKFLOW.md).

## Interactive directory access

The GUI/controller uses Python's standard library and existing JavaScript/Node
MCP bridge for pending folder decisions. No new installed dependency is required.
`request_directory_access` and bounded `read_inventory_file` are built-in tools;
approval grants read-only scope for the task or remembers it for this project.
The bridge supports at most 48 descriptors and a 900-second RPC ceiling; actual
operations keep their fixed execution limits plus a five-minute human-decision
allowance. See [behavior and tests](docs/ACCESS_REQUESTS_AND_MEMORY_ROADMAP.md).
Qwen stays at 131,072 context / 8,192 output tokens.

## Internet and hybrid memory profile

`web_search` adds official SearXNG **2026.10.25-54ca1d9cf**, source revision
`54ca1d9cfb08674f66261d7f351b063558dfcc62`, Linux/amd64 image
`docker.io/searxng/searxng@sha256:a886f6511fd3faf2c9ed921b33a8f0df1c7646e47475b6b309e79cd2887abd9d`.
The lock is `tools/modding/requirements-web.json`; installation is recorded in
`system-requirements.json`. It needs local Docker Linux containers and outbound
internet for public search engines. The private service binds `127.0.0.1:8842`,
has a 512 MiB/two-CPU limit and mounts only its own configuration. No API key,
global executable or Python package is installed.

```powershell
python tools/setup/install_web_search.py --start --enable-docs
python tools/setup/configure_melty_cli.py --enable-knowledge --apply
```

New projects default to internet Off; this checkout uses Documentation domains.
Search queries go to public engines. Fetch uses standard-library HTTPS, with
bounded public-address validation and no ambient authentication. Memory uses
standard-library SQLite **with FTS5** (verified locally with SQLite 3.50.4), JSON
files and an optional 0/16/32/64 MiB estimated RAM cache per process. No embedding
model/service is installed. The existing MCP dependency suffices for native
tools. The bundled `project-knowledge` instruction pack is copied with the
native profile; instructions do not grant permissions. See
[configuration, limits and evidence](docs/INTERNET_AND_PROJECT_MEMORY.md).

## Engine archive CLI profile

`engine_cli` installs optional repak 0.2.3, retoc 0.1.5 and UnityDataTool 2.4.0
from checksum-pinned portable Linux/amd64 releases. Exact download URLs, SHA-256
and the immutable Python/Debian base are in
`tools/modding/requirements-engine-cli.json`. This profile requires local Docker
Linux containers (Engine 28+), with no host .NET SDK, Rust compiler or global PATH
change. The bundled Unity native library determines Unity compatibility.

```powershell
python tools/setup/install_engine_cli.py --select
```

This builds the private `smelter-engine-cli:1` image, verifies actual CLI versions
and selects its immutable `engine_image` after an idle check. The setup page can
build it through the profile; select its reported ID in Settings afterwards.
Versions, lock hash and build log are retained under
`.smelter/tooling/engine-cli/`. Old sandbox configurations remain valid.
The MCP adapter accepts fixed read-only metadata operations on an approved
inventory scope. ARK's PAK version 12 is unsupported by pinned repak; retoc's
global/optional IoStore inspection passed. See [limits and evidence](docs/ENGINE_ARCHIVE_CLI.md).
Both Qwen routes retain the user-selected 131,072 context / 8,192 output profile.

## Qwen 35B and REA/Ghidra integration

The `qwen35b_agent` profile explicitly installs `qwen3.5:35b-a3b`, MCP 1.30.0,
the managed OpenCode image, `rea-agents@6.7.0`, its matching instruction bundle,
and the existing Ghidra/JDK prerequisites. The REA npm installation omits optional
packages and disables lifecycle scripts. `install_rea_skill.py` copies reviewed
instruction text only; it never registers an unrestricted MCP server or changes
native OpenCode/Codex settings. Imported instructions start disabled unless the
operator requests `--enable`.

The 35B model has roughly 22 GB of quantized weights. A 16 GB GPU uses partial
CPU/RAM offload. This rig's measured, user-selected configuration is 128K
context; preserve it. Installing the model does not
replace a saved model automatically. The application uses fixed host-side Ghidra
operations through its approved MCP bridge, without granting arbitrary scripts
or target execution. See [integration status](docs/REA_GHIDRA_INTEGRATION.md).

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/setup/install_missing.ps1 -Profile qwen35b_agent -DryRun
python tools/setup/install_rea_skill.py --enable
python tools/setup/configure_agent_stack.py           # preview only
# After verification, with the dashboard stopped:
python tools/setup/configure_agent_stack.py --apply
```

Melty's optional `melty` profile installs the isolated kit pinned to
`2026.10.18-739f3496`, archive SHA-256
`907ea7f3ed2d4c3443c9f3190f5070db0e77a9c910c50eeaaedf6cd1694f9935`.
The installer verifies every declared file hash and runs no kit code. Its public
download permits only the observed official storage redirect to that exact
archive path. The host-side MCP gateway uses the existing pinned Python MCP SDK
at the fixed `https://melty.gg/api/mcp` endpoint. Credentials remain on the host;
`SMELTER_MELTY_TOKEN` or an explicitly selected existing Melty sign-in supplies
them. Model tasks require a separate `melty_read` grant. Upload/publish/game
launch operations are not exposed. See [Melty connector](docs/MELTY_CONNECTOR.md).

Ghidra 12.1.4 with JDK 21 is the locally verified engine. Its project store is
`%LOCALAPPDATA%/SMELTER/GhidraProjects/<checkout-hash>/<analysis-id>` because
Ghidra forbids project paths containing a dot-prefixed directory. Evidence and
source digests remain in `.smelter/rea-evidence/ghidra`. Preserve both locations
for reusable analyses; current application backups do not include the external
Ghidra projects. Windows launch validates Java and explicitly supplies executable
extensions so the fixed batch launcher runs without an interactive console.

This is the requirements baseline for the `SMELTERV1` branch. Requirements are divided into **vanilla**, **developer**, and **optional extension** categories. Do not install every optional tool by default.

## Vanilla source installation

| Requirement | Baseline | Policy |
| --- | --- | --- |
| Operating system | Windows 10/11 x64, or a supported Linux/macOS installation | Target platforms; compatibility must be validated |
| Python | 3.12 or newer, with `venv` and `pip` | Required to run the current source-based Python backend; Python 3.14 compatibility needs testing |
| Browser | Current Chromium-, Firefox-, or WebKit-based browser | Required for the local web console |
| Network | Loopback (`127.0.0.1`) | No internet required for vanilla operation |
| RAM / disk | To be measured during V1 validation | No unsupported minimum claimed yet |

The vanilla runtime must start without an AI model, external skill package, Node.js, Java, Docker, Blender, or Ghidra. The current Python package requirements are in [`requirements.txt`](requirements.txt), intentionally without third-party dependencies.

## Requirements file

[`system-requirements.json`](system-requirements.json) is the machine-readable source for:

- **tools**: executables, their version checks, winget IDs or pinned npm packages;
- **setup**: project steps that run after the tools are installed (below);
- **profiles**: which tools and setup steps each kind of use needs.

The requirements scanner, the setup wizard's profile preview, the approved winget queue and `install_missing.ps1` all read it. To add or change anything, edit that file; the tables below describe it.

| Setup step | What it does | Needed for |
| --- | --- | --- |
| `mcp_sdk` | `pip install -r tools/dashboard/requirements-mcp.txt` (`mcp==1.30.0`) | Built-in MCP tools, OpenCode |
| `ollama_model` | `ollama pull qwen3.5:9b` (an installed `qwen3.5:4b` also counts) | Chat, OpenCode; the full smoke test expects `9b` |
| `wsl_platform` | Checks Virtual Machine Platform is enabled **and active** (no pending restart) and firmware virtualization is on; if not enabled, runs `wsl --install --no-distribution`. winget's `Microsoft.WSL` installs WSL but does not enable this feature | Docker on Windows |
| `image_python` | `docker pull python:3.12-alpine` | Confined Python tests |
| `image_node` | `docker pull node:22-alpine` | Confined Node tests, CSS preview, OpenCode image base |
| `image_opencode` | `docker build -f tools/dashboard/Dockerfile.opencode -t smelter-opencode:1.19.3 .` | Managed OpenCode; select its `sha256` ID in Settings |
| `glb_viewer` | `npm install --prefix .smelter/tooling/model-viewer @google/model-viewer@4.1.0` | GLB preview and PNG capture |
| `rea` | `npm install --prefix .smelter/tooling/rea rea-agents@6.7.0` | REA analysis |
| `ghidra` | `tools/bootstraps/Setup-Smelter-Ghidra.ps1`: latest official release, SHA-256 checked, into `C:\Tools\Ghidra`; sets user `JAVA_HOME`, `GHIDRA_INSTALL_DIR`, `REA_ANALYSIS_PROVIDER=ghidra`. Needs JDK 21 (Temurin or Microsoft) | Fixed dashboard headless `rea_ghidra_*` adapter and bootstrap scripts; see `docs/REA_GHIDRA_INTEGRATION.md` |
| `playwright`, `chromium` | Playwright 1.56.1 in `.smelter/tooling/browser` plus its Chromium | Full smoke test only |

Profiles: `local_ai`, `opencode_agent`, `media`, `reverse_engineering`, `smoke_test`, `developer`, `game_modding`, `native_game_mods` (Git + Docker and the confined CLI toolchain; host MSVC is optional).

A tool may declare `winget_override`: installer options passed as winget's `--override`, for packages whose default install lacks the needed parts. Visual Studio Build Tools needs it, because without the C++ workload it installs no compiler. The installer stays visible (`--passive`) and agreements are not auto-accepted.

### Hardware profiles and dashboard defaults

The last installer step runs `tools/setup/configure_defaults.py`, which detects the GPU, system RAM, Ollama models, Docker image IDs and installed tools and writes `.smelter/deployment-defaults.json`. The dashboard uses those values **only for settings never saved** in it; saving in the dashboard always wins and re-running deployment cannot override it. Precedence: saved › `SMELTER_CONTEXT_LENGTH` › deployment › built-in.

| Profile | Chosen when | Model | Runtime (context · output · turn / task timeout · thinking) |
| --- | --- | --- | --- |
| `low` | No NVIDIA GPU | `qwen3.5:4b` (3.1 GB) | 16K · 1024 · 600 / 1800 s · off |
| `medium` | GPU up to 6 GB | `qwen3.5:4b` | 32K · 1024 · 300 / 900 s · off — verified on a 4 GB GTX 1050 Ti |
| `high` | GPU over 6 GB up to 16 GB | `qwen3.5:9b` (6.1 GB) | 32K · 2048 · 180 / 900 s · on |
| `extreme` | GPU over 16 GB and at least 30 GB RAM (else `high`) | `qwen3.5:35b-a3b` (20.6 GB MoE, ~3B active) | 64K · 4096 · 300 / 1800 s · on — not yet measured on a rig |
| `custom` | Chosen explicitly | You choose | You choose; deployment seeds only extensions, images and storage |

Deployment also enables the extensions whose tools are installed, saves the three Docker image IDs, suggests the storage folder `%LOCALAPPDATA%\SMELTER\data` on first start-up, warns about NVIDIA drivers older than 531 and reports Ollama version drift. Override detection with:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\setup\install_missing.ps1 -HardwareProfile extreme
python tools\setup\configure_defaults.py --profile custom --dry-run
```

The dashboard's runtime presets are the same Low · Medium · High · Extreme · Custom; it shows Custom when your saved values match no preset.

To install everything that is missing, run from an **administrator** PowerShell in the checkout:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\setup\install_missing.ps1 -DryRun   # show the plan only
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\setup\install_missing.ps1           # run after typing yes
```

`-Profile opencode_agent` limits the run to one profile; `-Only docker,image_opencode` to named tools or steps. The script prints exact commands, marks steps **blocked** when a prerequisite is not ready (for example Docker Desktop not started), asks before changing anything, does not auto-accept agreements, and summarizes each result. Docker steps need Docker Desktop running. After installing WSL or Docker, restart Windows, start Docker Desktop once, open a new PowerShell and run the script again to finish the setup steps.

Optional host integration: to use Melty's desktop app as the front end, the host OpenCode config can point at local Ollama and SMELTER's MCP server. This needs a derived Ollama tag `qwen3.5:35b-a3b-128k` (128K context, measured on an RTX 5080; no download). See [docs/MELTY_CONNECTOR.md](docs/MELTY_CONNECTOR.md) for the exact entries, backup and limits.

After a real run the script checks every selected tool and step again and reports the result. Its exit status is truthful for automation: **0** means the selected profile is complete (a `-DryRun` also exits 0 because it only shows the plan); **1** means an action failed or the plan was cancelled; **2** means nothing failed but the profile is still incomplete, because a tool is missing or a step is blocked or skipped. A tool installed in this run may not be on the current window's PATH yet, so it can report 2 until you rerun it in a new window. `-SummaryPath summary.json` writes the outcome, exit code, actions and recheck as JSON.

## What each dashboard feature needs

| Feature | Needs |
| --- | --- |
| Dashboard | Python 3.12+ and a browser |
| Direct chat | Ollama running at `127.0.0.1:11434` with a model installed (default `qwen3.5:9b`; `qwen3.5:4b` for GPUs with 4 GB or less) |
| Skills | Nothing extra. A skill provides instructions only; it does not install software or require WSL |
| Built-in MCP tools | Pinned MCP SDK: `python -m pip install -r tools/dashboard/requirements-mcp.txt` |
| Managed OpenCode agent | Ollama + model, MCP SDK, **Docker Desktop** (which needs **WSL 2** on Windows) and the pinned OpenCode 1.19.3 container image built per [OPENCODE_RUNTIME.md](tools/dashboard/OPENCODE_RUNTIME.md). The native `opencode` CLI is not used |
| Frontend tests/preview and coding workspace tests | **Docker Desktop** (WSL 2 on Windows). There is no host fallback |
| GPU inference | A current NVIDIA driver. Old drivers can make Ollama fall back to an unstable backend or to the CPU |

## Developer conveniences

| Tool | Purpose | Policy |
| --- | --- | --- |
| Git | Version control and branch management | Recommended for source development |
| GitHub CLI (`gh`) | Authenticated GitHub workflows | Optional |
| PowerShell 7 | Windows automation | Optional; Windows PowerShell may suffice for basic commands |
| Node.js LTS + npm | JavaScript/TypeScript builds and tooling | Optional until a selected frontend/tool requires it |
| C/C++ compiler and build tools | Native game mod builds | Model-facing `build_native_mod` uses confined MinGW-w64 in `smelter-cpp:2`. Optional catalog tool `msvc` remains for operator-run `gta/build.bat`; it is not a model fallback. See [game-mod tools](docs/GAME_MOD_TOOLS.md). |
| WSL 2 | Linux backend for Docker Desktop on Windows | Required for Docker features on Windows; `wsl --install` as administrator, then restart |
| Docker Desktop / Docker Engine | No-network containers for managed OpenCode, frontend tests/preview and coding workspace tests | Required for those features; not needed for the dashboard or direct chat |
| `smelter-cpp:2` image (setup `image_cpp`) | Portable C++ tests, Lua 5.4 tests and Windows x64 cross-compilation | Pinned base digest, g++ 15.2.0-r5, Lua 5.4.8-r0, mingw-w64-gcc 15.2.0-r0 in `Dockerfile.cpp`. Build with `docker build -f tools/dashboard/Dockerfile.cpp -t smelter-cpp:2 .`, then select its immutable ID. No network or host compiler fallback during a task. |

## Extension-dependent runtimes and applications

| Tool | Enabled for | Policy |
| --- | --- | --- |
| Java JDK | Ghidra and Java-based extensions | Optional; match JDK version to the chosen application release |
| Blender | 3D asset conversion, scene and animation automation | Optional |
| Unreal Engine / Unity | Engine-specific workflows | Optional; license and version dependent |
| Ghidra | Reverse engineering | Optional |
| FFmpeg | Audio/video processing | Optional |
| 7-Zip | Archive workflows | Optional |
| Ollama / other local AI runtime | User-selected AI core | Required for chat and OpenCode |
| OpenCode 1.19.3 container image | Managed OpenCode agent route | Required for that route; operator-built, never pulled or built by SMELTER during a task |
| GPU drivers and acceleration libraries | GPU-enabled local inference or graphics | Optional, hardware/model dependent; keep NVIDIA drivers current |
| Playwright and browser binaries | Browser automation/testing | Optional; install only when selected |
| SearXNG / internet search provider | Internet research | Optional; network required |
| MCP adapters or gateway | External tool/agent compatibility | Optional |

## Setup — current source checkout

```powershell
cd C:\SMELTER
git fetch origin
git switch SMELTERV1
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe tools\web\smelter_console.py
```

If the branch is not yet tracked locally, use `git switch --track origin/SMELTERV1` instead of `git switch SMELTERV1`. The commands assume the Python launcher (`py`) is available on Windows. The console is a legacy development entrypoint, not yet the V1 first-run wizard.

## Controlled optional installation queue (V1.2)

The web wizard can now prepare and run a separate, explicitly approved Windows `winget` queue for allowlisted optional tools. This is **opt-in**: selecting a profile does not install anything. The queue displays exact package IDs and commands before approval; execution is sequential and stops on first failure. Each successful command is followed by a requirements rescan to verify the tool is detected.

Supported allowlist (every tool with a `winget` ID in `system-requirements.json`): Git (`Git.Git`), Node LTS (`OpenJS.NodeJS.LTS`), GitHub CLI (`GitHub.cli`), WSL (`Microsoft.WSL`), Docker Desktop (`Docker.DockerDesktop`), Ollama (`Ollama.Ollama`), Blender (`BlenderFoundation.Blender`), FFmpeg (`Gyan.FFmpeg`), 7-Zip (`7zip.7zip`). WSL and Docker Desktop usually need elevation and a restart, so expect to finish them in an administrator terminal. This feature requires Windows and `winget`. It deliberately does **not** use silent mode, automatically accept agreements, elevate privileges, or install dependencies merely because a profile was selected. Some packages may require an interactive prompt or elevation that this browser-driven background process cannot satisfy; those installs may fail and must be completed manually in a terminal. Installation rollback and cancellation are not implemented. Restarting the shell may be needed for PATH updates before verification.

Run all tests with `py -3 -m unittest discover -s tools\setup -p "test_*.py" -v`. Windows integration and actual `winget` installs have not yet been verified.

## Optional profile preview (V1.1)

The local setup wizard now exposes **Developer**, **Local AI**, **OpenCode Agent** (Ollama, WSL, Docker), and **Game Modding** profiles in addition to Vanilla. Profile selection produces a read-only dependency preview using the requirements scanner. Missing or unverified dependencies are marked for manual review. **No optional tool installation commands are generated or executed.** The approved Vanilla setup flow remains independent of preview selections.

Profiles are declared in `system-requirements.json` and resolved by `tools/setup/profiles.py`; their unit tests are in `tools/setup/test_profiles.py`. Re-run all setup tests with:

```powershell
py -3 -m unittest discover -s tools\setup -p 'test_*.py' -v
```

## CLI-launched web setup wizard (V1 preview)

On Windows, from the SMELTER checkout:

```powershell
cd C:\SMELTER
git pull origin SMELTERV1
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\setup\start_setup.ps1
```

The CLI starts a loopback-only web app at `http://127.0.0.1:8767/` and opens a browser with a per-session authorization token. Leave the PowerShell window open while using the wizard. Review the plan and explicitly approve it before the backend runs a fixed sequence: create a local `.venv` if missing, run the requirements scanner, and run setup unit tests. Logs stream into the browser; no second terminal window is required.

Every child the wizard starts (the setup steps above and approved winget queries/installs) runs as an owned process tree: a Windows job object, or a process group elsewhere. Each child has a deadline: winget query 30 s, winget install 30 min, `.venv` 5 min, scanner 2 min, unit tests 15 min. Output is capped at 2 MiB per child, and log lines at 400 characters. **Cancel setup** and **Cancel installation** stop the running child and any descendants, including ones that still hold its output pipe. Closing the wizard with Ctrl+C cancels running work and reaps those processes before exiting. A cancelled run reports `cancelled`, not `failed`. Cancelling an installer mid-way can leave that package partly installed; rerun the plan to check.

This is an initial functional wizard, **not** a package-manager installer: it does not download dependencies or install Node.js, Java, Blender, FFmpeg, 7-Zip, or other optional tools. Do not expose the loopback service through a proxy or port-forward. The wizard and its browser integration require local Windows testing.

## Read-only requirements scanner (implemented; Windows verification pending)

Run the scanner before installing optional tools:

```powershell
.\.venv\Scripts\python.exe tools\setup\check_requirements.py --output diagnostics\requirements-local.json
.\.venv\Scripts\python.exe -m unittest discover -s tools\setup -p test_check_requirements.py -v
```

The scanner uses Python's standard library, checks executable presence and version commands, and writes an explicit JSON report. It performs no installation, network access, or system modifications. The report omits executable paths. Some Windows command shims are marked `detected_unverified` rather than executed. The report should be reviewed before sharing; version output may still include local metadata.

## Planned environment validation (remaining work)

1. Detect OS, architecture, Python version, and available tools without changing the system.
2. Evaluate only the dependencies required by the user's selected extensions.
3. Present exact installation actions and sources for approval.
4. Verify installed executable versions and health checks.
5. Save an environment report, without credentials or private system information.

**Security:** No automatic downloads or execution of third-party installers without user approval. Do not add dependencies solely because a skill mentions them. Pin versions and verify provenance when a dependency is introduced.

## CLI modding candidates and Qwen instructions

The `modding_cli` section of `system-requirements.json` catalogs 31 CLI tools with
engine routes, primary sources, command templates and integration states. Candidate
entries are research recommendations, not installed executables, automatic
installer actions, or execution grants. See [the toolkit](docs/MODDING_CLI_TOOLKIT.md).
`python tools/dashboard/modding_catalog.py --engine unity` lists a filtered view;
the read-only `modding_tool_catalog` MCP tool exposes it with a coding grant.

New bundled instructions `game-modding` and `mod-validation` complement the
existing package-matched REA skill. They install no executable dependencies and
are discovered after a dashboard restart. Installing a future CLI requires a
pinned source/release, checksum, setup/check action and matching documentation.

Optional native Melty profile helper: `python tools/setup/configure_melty_cli.py`
previews changes; `--apply` backs up the existing configuration, installs the two
bundled skills into the native OpenCode skill directory and enables the fixed
SMELTER coding/build grant set. It preserves 131,072 context tokens and sets the
separate output ceiling to 8,192. This helper and the derived-tag Modelfile are
tracked in `modding_cli.native_opencode_profile`. It downloads no tools/models.

For this machine's measured 128K choice, `--align-dashboard --apply` explicitly
aligns the saved dashboard context/output too, with a backup and thinking/timeouts
preserved. Both routes were read back as 131,072 / 8,192. Repeat agent-stack setup
preserves an existing saved Qwen runtime rather than resetting it to 16K.

## Universal Modder (GitHub CLI toolkit)

Profile/setup `universal_modder` installs upstream 0.2.0 at commit
`c1dff21663665dd17af289744a301b66e369605e`, with the source ZIP SHA-256 declared in
`system-requirements.json`. `tools/modding/requirements-universal-modder.txt` pins
Pillow 13.0.0, numpy 2.5.4, PyYAML 6.0.3 and pytest 9.1.1 in a private Python 3.12+
venv. Resolved transitive versions and pip artifact metadata are retained with the
installation. No global Python package, PATH, paid API or game activation occurs.

`python tools/setup/install_universal_modder.py --enable` additionally registers
execution of the fixed local knowledge adapter (`modding` policy operation),
preserving existing rows/denials. `python tools/modding/um.py --help` invokes the
standalone CLI; `universal_modder` MCP status/search/read actions use the existing
coding grant. The `universal-modder` skill complements the pinned REA instructions.
See [integration, standalone examples and verification](docs/UNIVERSAL_MODDER.md).
