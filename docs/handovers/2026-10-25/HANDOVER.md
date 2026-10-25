> Latest status: read [review fixes and continuation](../../REVIEW_FIXES_20261025.md) first. This document contains earlier observations; the current native builder is confined MinGW-w64, and Qwen context remains 128K.

# SMELTER agent handover — 25 October 2026

Updated at 14:23 Asia/Muscat (UTC+04:00). It supersedes the 11:13 version of the
same day. This document captures the existing task; it is not authorization to
publish a mod, install into a game folder or change accounts.

## Objective and operator decisions

Build a local workbench where the local model does game-mashup and reverse
engineering work through fixed, grant-gated tools:

```text
User / SMELTER GUI → managed OpenCode (no network) → Ollama → Qwen3.5 35B-A3B (128K)
                            ↓ approved MCP tool calls
                    SMELTER host gateway
                    ├─ REA static tools + fixed Ghidra headless tools
                    ├─ Melty account/game lookup (read-only)
                    ├─ inspect_game_files (archive/executable headers)
                    ├─ coding copy: tools/, skills/, mods/<mod>/ + confined tests (python, node, mods, cpp)
                    └─ build_native_mod (MSVC; built files never run)

Melty desktop app → host OpenCode CLI → same Ollama model + SMELTER MCP (Melty lookup only)
```

Operator requirements (all still in force):
- **Requirements and docs:** every introduced or installed tool is recorded in the
  same change, in `system-requirements.json`, dependency manifests, `REQUIREMENTS.md`
  and the relevant workflow or connector docs.
- **OpenCode startup:** a remembered OpenCode engine loads with the GUI, with no
  repeated enable/check/approval steps. File and tool grants stay separate.
- **Melty sign-in:** use the existing sign-in. Do not ask for sign-in again without
  an observed authentication failure.
- **Melty lookup default:** read-only lookup is on by default and remembered
  (operator request, 25 Oct). All other grants are still per message.
- **Who does mod work:** SMELTER (Qwen through its tools) does the mod work. The
  agent maintaining SMELTER builds and verifies the tools, and acts directly on mods
  only for reference or verification.

**Mashup target (operator decision, 25 Oct):** GTA V Enhanced is the **host**
(Story Mode only) and ARK: Survival Ascended is the **companion** (single player).
The chosen route is Melty's *live passthrough* pattern: both games run side by side
and share state, with no asset conversion. The first milestone, M1, links GTA's
camera to ARK's view. See [discovery](../../discovery/GTA_ARK_DISCOVERY_20261025.md)
and the [M1 design](../../discovery/GTA_ARK_M1_DESIGN.md). Do not assume
`dw3_decomp-main/`, or the DevKit's `DigisoulARK` / `DigiSoul_Codex`, belong to
this mashup.

## Workspace and recovery

| Item | Value |
| --- | --- |
| Workspace | `C:\Users\Dr.Dark92\Documents\ChatGPT\SMELTER` |
| Shell | PowerShell on Windows (Bash also available) |
| Branch | `fix/r07-r08-setup-lifecycle`; `main` is still at base `3f72721` |
| HEAD | `982950b` "Report incomplete installs and bound web-setup children" (R07+R08 only; local, not pushed) |
| Git state | 78 status entries: everything except R07+R08 is uncommitted, including R06 and all new tools, docs and `mods/` |
| Unrelated local work | `dw3_decomp-main/` is operator-owned; preserve it and exclude it from staging and checkpoints |
| Database (non-Codex launches) | `C:\Users\Dr.Dark92\AppData\Local\SMELTER\data\smelter.sqlite3` (copied 25 Oct; see trap 1) |
| Database pointer | `.smelter/database-location.json` |

Start with `git status --short`. **Do not `git reset`, `git clean` or use a
HEAD-only worktree as the current source.**

The source checkpoint `.smelter/handovers/2026-10-25/source-checkpoint.zip` was
regenerated at this update. [MANIFEST.json](MANIFEST.json) lists every file with its
SHA-256 against base `982950b`. It is an overlay of changed and new source (including
`mods/`), not a full repository or a remote backup. It excludes `.git`, `.smelter`
runtime data, databases, credentials, weights, game files and `dw3_decomp-main/`.

## Machine and runtime state (verified 25 Oct)

| Component | State |
| --- | --- |
| Python | 3.13.15, `C:\Users\Dr.Dark92\AppData\Local\Programs\Python\Python313\python.exe` |
| Node / npm | 24.20.0 / 11.19.0 |
| Docker | Desktop Linux engine 29.8.2 (must be running) |
| Images (immutable IDs in sandbox config) | python `sha256:1b668429…`, node `sha256:ce8d97f7…`, OpenCode 1.19.3 `sha256:c6990350…`, **cpp `smelter-cpp:1` `sha256:bec95471…` (g++ 15.2)** |
| Ollama | 0.40.7 (catalog expects 0.40.10; do not silently upgrade) |
| Models | `qwen3.5:35b-a3b` (`72aac7c28be8`, reasoning); derived `qwen3.5:35b-a3b-128k` (`ef40e0fe4f37`, `num_ctx 131072`, used by host OpenCode); `qwen3.5:9b` (lightweight); `qwen3.5:4b` |
| GPU / RAM | RTX 5080 16 GB / 64 GB |
| MSVC | **VS 2022 Build Tools 17.14.42, MSVC 14.44.35207, Windows SDK 10.0.26100.0** (catalog `msvc`, profile `native_game_mods`) |
| REA / Ghidra / JDK | `rea-agents@6.7.0`; Ghidra 12.1.4 `C:\Tools\Ghidra`; JDK 21 |
| Melty | kit `2026.10.18-739f3496` (hashes verified); MCP `https://melty.gg/api/mcp` connected (protocol 2025-06-18); desktop app 1.0.165 |
| Host OpenCode CLI | 1.19.3 (npm global), config `~/.config/opencode/opencode.json` |

**Saved SMELTER runtime settings:**
- context **131,072** tokens (raised from 16,384 after measurement);
- output **8,192** tokens (raised from 2,048, because whole-file coding patches didn't
  fit);
- timeouts 300 s per model turn and 1,800 s per OpenCode task;
- thinking on. The OpenCode relay turns thinking off when tools are present.

Measured on this GPU: 128K costs about 13% generation speed versus 16K (45.8 vs
52.4 tok/s; 44% CPU / 56% GPU). The full table is in
[MELTY_CONNECTOR.md](../../MELTY_CONNECTOR.md). These are filler-text measurements,
not proof of long-context reasoning quality.

## Changes outside the repository (all made 25 Oct)

| Where | Change | Undo |
| --- | --- | --- |
| `C:\Users\Dr.Dark92\AppData\Local\SMELTER\` | Copy of the Codex-virtualized data folder (DB + Ghidra projects), SHA-256 verified | Original kept in the Codex package store |
| Access policy (DB) | Added `msvc_runtime` (execute-only, operation `native_build`); `game_grand_theft_auto_v_enhanced` and `game_ark_survival_ascended` (read-only). No write rows | Settings → Access & locations |
| Sandbox config (DB) | `cpp_image` = `sha256:bec95471…` | Settings → Confined execution |
| Runtime settings (DB) | context 131,072, output 8,192 | Settings → Runtime |
| `~/.config/opencode/opencode.json` | `ollama` provider (`qwen3.5:35b-a3b-128k`) and `smelter` MCP server (`SMELTER_MCP_GRANTS={"melty_read":true}`); existing unrestricted `rea` entry untouched | Backups `opencode.json.bak-20261025-smelter` (original) and `.bak-20261025-16k` |
| Ollama | Tag `qwen3.5:35b-a3b-128k` (16K tag created, then removed) | `ollama rm qwen3.5:35b-a3b-128k` |
| Windows | VS 2022 Build Tools with the C++ workload (winget) | Visual Studio Installer |
| Docker | Image `smelter-cpp:1` | `docker rmi smelter-cpp:1` |
| Browser profile (built-in pane) | Saved engine OpenCode; Melty lookup preference | — |
| Chat history | Test chats: Melty connection test, 128K context test, SMELTER tests 1–3 | Delete in GUI |

Nothing was installed into or launched from either game folder.

## Authentication and application data

- `.smelter/melty-connection.json` holds a **reference only**
  (`existing-codex-melty` → the `melty` entry in `~/.codex/config.toml`). Never
  copy the credential anywhere.
- The dashboard launch URL has a session token that changes on restart. Read it
  from `.smelter/dashboard.stdout.log`; never write it into documents.
- The GUI binds `127.0.0.1:8768` only.
- Ghidra projects live under `%LOCALAPPDATA%/SMELTER/GhidraProjects`, and evidence
  under `.smelter/rea-evidence/ghidra`.

## What was done on 25 Oct (session 2)

- **Review findings R06–R08 fixed:**
  - R06: one lifecycle owner for the persistent OpenCode pool, live verified with
    real Docker.
  - R07: `install_missing.ps1` exit codes 0/1/2 with a recheck and `-SummaryPath`.
  - R08: `setup_web.py` children owned, bounded and cancellable.
  - R07 and R08 are committed as `982950b`.
- **Codex MSIX data:** found and copied (trap 1).
- **Melty:**
  - lookup on by default with an automatic startup check, live verified through
    an OpenCode task;
  - Melty's desktop app wired to the local model and SMELTER MCP; the operator
    confirmed the model appears in Melty's dropdown.
- **Context and output:** measured context sizes (16K–256K) and set 128K for both
  routes; output raised to 8,192.
- **GTA × ARK:** read-only discovery, MSVC installed, M1 designed, and the offline M1
  parts built in `mods/gta-ark/`. The C++ writer and skeleton ASI build cleanly,
  Python tests pass 7/7, the offline round trip works, and the Lua mod is untested.
- **SMELTER game-mod tools:**
  - `inspect_game_files`;
  - the coding copy now covers `mods/`, with `mods` and `cpp` test profiles;
  - `build_native_mod`;
  - `configure_native_build.py`;
  - full reference in [GAME_MOD_TOOLS.md](../../GAME_MOD_TOOLS.md).
- **Qwen ran three SMELTER tests:**
  1. discovery: correct;
  2. Python/C++ edit: GREEN plus a native build, but a C++ logic bug compiled
     undetected, which led to the new `cpp` profile;
  3. portable C++: `cpp` GREEN plus a native build in 114.7 s, with correct code.

## Implementation map (new or changed this session)

| Area | Files |
| --- | --- |
| OpenCode lifecycle (R06) | `component_controls.py` (`_opencode_row`, `_opencode`, `warm_opencode`), `opencode_pool.py`, `dashboard_api.py` session route, `system_components.js` |
| Installer (R07) | `tools/setup/install_missing.ps1` (`Get-InstallOutcome`, `Complete-Install`, `winget_override`), `test_install_missing.py` |
| Web setup (R08) | `tools/setup/setup_web.py` (`_Supervised`, `_Lines`), `test_setup_web.py` |
| Requirements | `system-requirements.json` (`msvc` + `winget_override`, `native_game_mods`, `image_cpp`, `cpp_image`), `requirements_catalog.py`, `check_requirements.py` (vswhere, empty output = unverified), `install_actions.py` |
| Melty default | `dashboard_shell.js` (remembered grant, auto check) |
| Game file inspection | `tools/dashboard/game_files.py`, `test_game_files.py` |
| Mods in coding copy | `coding_workspace.py` (`mods/` paths, editable C/C++/Lua, protected scripts and outputs), `frontend_workspace._source_files(extra)`, `access_policy.check_grants`, `test_mod_workspace.py` |
| Confined test profiles | `sandbox.py` (`CODING_MODS`, `CODING_CPP`, exec-able `/build` only for cpp, `cpp_image` migration), `Dockerfile.cpp`, `operations_ui.js`, `deployment_defaults.py`, `test_cpp_profile.py` |
| Native builds | `tools/dashboard/native_build.py`, `test_native_build.py`, policy operation `native_build`, `tools/setup/configure_native_build.py` |
| Tool wiring | `tool_registry.py`, `python_tools.py` (grant `native_build`, receipts), `capability_catalog.py`, `access_ui.js` |
| Mod | `mods/gta-ark/` (spec, MODLOG, C++/Python/Lua, `native.json`, tests) |

## Current callable boundaries

- **Read-only:** inventory and `inspect_game_files` in approved read locations;
  Melty lookup; REA/Ghidra on approved PE/ELF up to 64 MiB.
- **Coding copy (`SMELTERV2/coding/<uuid>`):**
  - edits `tools/`, `skills/` and `mods/<mod>/` (`.py .js .css .html .json .md .toml
    .yaml .c .cpp .h .hpp .lua .txt`), whole-file proposals only;
  - scripts are read-only and build outputs are excluded;
  - test profiles `python`, `node`, `mods`, `cpp`, all in no-network Docker;
  - **no merge back into the repo.**
- **`build_native_mod`:**
  - MSVC with fixed flags (`/W4 /WX`) and an allowlisted `native.json`;
  - built files are **never run**;
  - compiling proves only that the code compiles.
- **Not provided:** installing into game folders, launching games, running native
  code on the host, a Lua runner, asset readers or converters, Melty upload/publish,
  Git operations.

## Validation (latest)

- Dashboard **539** OK (9 skips; real MSVC compiles and real Docker g++ runs
  included); setup **99** OK; analysis 30 OK (not rerun this session); JS **24**
  passed.
- Live checks this session:
  - R06 pool start/stop/restart with real Docker;
  - Melty auto-check and an OpenCode Melty task;
  - 128K GUI task;
  - host OpenCode CLI runs through `smelter` MCP;
  - SMELTER tests 1–3.
- Mod `mods/gta-ark`:
  - `gta/build.bat` OK, and `build_native_mod` builds all 3 targets;
  - Python 7/7 (6 + 1 skip in the container);
  - offline writer/reader round trip;
  - Lua and in-game behaviour unverified.

## Known traps

1. **Codex MSIX virtualization.** The earlier session ran inside the Codex desktop
   app, so its `%LOCALAPPDATA%\SMELTER` is really under
   `%LOCALAPPDATA%\Packages\OpenAI.Codex_2p2nqsd0c76g0\LocalCache\Local\SMELTER`.
   There are now **two independent copies** (Codex launches vs everything else).
   Pick one before relying on saved data. Never choose a new database on a
   `database_missing` screen.
2. **Launching from Claude Code.** Start the dashboard **outside the command
   sandbox** (it must see the real AppData and Docker). Use `--no-browser` with
   stdout/stderr redirected to `.smelter/dashboard.*.log`. To restart gracefully,
   POST `/api/opencode/session {"action":"stop"}` first (this also disables OpenCode;
   the next GUI load re-enables it), then stop the PID.
3. **Shell quirks on this machine:**
   - executables are not found in the current folder (`NoDefaultCurrentDirectoryInExePath`),
     so call built programs by full path;
   - the short temp path `C:\Users\DR1319~1.DAR\…` fails with `Set-Location`, so use
     `%USERPROFILE%\AppData\Local\Temp\…`;
   - PowerShell `>` writes UTF-16;
   - long inline Python or heredocs with quotes break Bash, so write a script file;
   - for `cmd /c call vcvars64.bat`, pass the path as a separate argument.
4. **Whole-file patches** cost output tokens (about 15 KB for three files). Keep
   output at 8,192, or add an exact-text edit tool.
5. **Compile ≠ correct.** Put testable C++ logic in portable headers (no
   `<windows.h>`) with `tests/cpp/test_*.cpp`; Win32 glue stays compile-only.
6. **Script Hook V** (latest v3889.0 / 1158.13) does not support the installed GTA
   Enhanced **1.0.1158.16** yet.
7. **GTA safety (Melty):**
   - Story Mode only, with `-nobattleye` only as a launch argument, never in
     `commandline.txt` or `args.txt`;
   - leave Script Hook V's `bin/args.txt` out of releases;
   - pick Story Mode by hand; never automate the landing page;
   - ARK single player only, with BattlEye off only through ARK's own supported
     option.
8. **Melty's app route is unconfined.** Host OpenCode has network, shell and file
   access, and the `smelter` MCP grant is permanent. Keep it to Melty lookup. The
   unrestricted `rea` MCP entry in the same config predates this session.
9. **Earlier traps still apply:** Windows Ghidra `PATHEXT` handling; Ghidra projects
   outside dot-folders; Ghidra receipts use `ghidra_version`; start Docker Desktop
   after a reboot; skill changes need a dashboard restart; the review report
   `diagnostics/REVIEW_20261024.md` predates the fixes (R01–R08 are now fixed).

Next steps: [NEXT_STEPS.md](NEXT_STEPS.md). Ledger: [PROGRESS.md](PROGRESS.md).
For another agent: [SECOND_AGENT_PROMPT.md](SECOND_AGENT_PROMPT.md).
