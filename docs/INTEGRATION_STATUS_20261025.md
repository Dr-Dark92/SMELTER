# Agent-stack integration status — 25 October 2026

26 October update: resumable folder access,
[controlled internet and hybrid project memory](INTERNET_AND_PROJECT_MEMORY.md)
are implemented locally. The refreshed GUI loads these tools; the earlier
restart-pending statements below are historical. Current tests, service state
and continuation instructions are in [CURRENT_HANDOVER.md](CURRENT_HANDOVER.md).

Latest extension: [engine archive CLIs](ENGINE_ARCHIVE_CLI.md) adds pinned repak,
retoc and UnityDataTool with one bounded read-only MCP adapter and Qwen skill.
ARK global/optional IoStore inspection passed; its PAK v12 is unsupported by
repak 0.2.3. Native/standalone MCP loads the new code. The running GUI backend
still needs a restart; automatic approval review blocked that operation.

Updated 25 October, 19:25 Asia/Muscat. Earlier verification rows are historical; latest CLI fixes are recorded below. The running dashboard is configured for
`qwen3.5:35b-a3b` at 128K context (131,072 tokens) and 8,192 output tokens, both
raised on 25 October after measurement, with a 300-second model-turn limit and an
1800-second OpenCode task limit. The existing 9B lightweight model is preserved. OpenCode starts
automatically when it is the browser's saved engine. Engine selection does not
grant target-folder access or host tools.

## Installed, connected and verified

| Component | Installed/configured | Verified behavior |
| --- | --- | --- |
| Qwen3.5 35B-A3B | Ollama tag `qwen3.5:35b-a3b`, ID `72aac7c28be8`, about 22 GB | Real OpenCode tool task completed in 47.1 seconds at 16K context; observed 38% CPU / 62% GPU placement |
| OpenCode | Managed 1.19.3 image, no network, persistent server | Final GUI API reports ready; active task generation and cleanup boundaries repaired |
| REA | Local `rea-agents@6.7.0`, npm install scripts disabled | Real capabilities command returned JSON; matching instruction provenance retained and supported workflow enabled |
| Ghidra | Existing 12.1.4 / JDK 21 | Generated ELF import, function/string search, incoming xrefs, MCP decompilation; no target execution |
| Melty kit | `2026.10.18-739f3496`, pinned archive and all declared file hashes verified | 557 files including metadata installed as data; kit code not executed |
| Melty service | Fixed `https://melty.gg/api/mcp`, existing host sign-in referenced without copying credentials | Authenticated initialize/account/tool discovery; real `search_games` through built-in MCP; protocol `2025-06-18`. Lookup on by default with an automatic GUI check (25 Oct) |
| Melty desktop app route | Host OpenCode 1.19.3 config: `ollama` provider (`qwen3.5:35b-a3b-128k`) and `smelter` MCP (Melty lookup plus isolated coding/catalog/tests/native builds; persistent grants) | Model shown in Melty's dropdown (operator); CLI runs used `smelter_melty_search_games`. Unconfined route |
| MSVC | Existing optional operator compiler | Historical manual build verification; model-facing builds now use confined MinGW-w64. |
| Confined mod CLI toolchain | Image `smelter-cpp:2`, pinned g++/Lua/MinGW-w64 | Real Lua fixture/transform tests, native cross-builds, diagnostics, source-boundary and oversized-suite regression tests. |
| Game-mod tools | `inspect_game_files`, `mods/` coding copy, `mods`/`cpp`/`lua` profiles, confined `build_native_mod`, CLI catalog; existing game-folder policy preserved | Three Qwen SMELTER runs; see [GAME_MOD_TOOLS.md](GAME_MOD_TOOLS.md) |

Melty's callable tools are currently `melty_whoami`, `melty_search_games`, and
`melty_game_info`, gated by the task's read-only Melty grant. Upload, publication,
game launches and mod builds are not implemented by this grant. No public
listing, upload, game binary, game installation or production chat task was
used for acceptance.

## Native-launch corrections

The first Windows Ghidra attempt exposed a missing `PATHEXT` in the minimal
process environment, allowing a batch file to open as an external interactive
document. The adapter now sets executable extensions explicitly, validates an
unquoted installed Java home, and uses the hidden bounded process owner. The
old failed help-test console was identified by its exact command and closed.
The later native/MCP and live-model tests completed successfully; the final
process check found no remaining Ghidra help-test console.

Ghidra also rejects projects beneath dot-prefixed directory components. Its
projects now live under `%LOCALAPPDATA%/SMELTER/GhidraProjects`, while input
digests, instruction provenance and JSON evidence remain under `.smelter`.
External Ghidra projects are outside the existing backup/retention scope.

## Repairs and checks

- R01: shared source copies include the mandatory root requirements catalog.
- R02: CI push/PR triggers include `main`.
- R03–R05: active-task generation gates model/tool packets; cleanup retains
  bridge ownership until actions settle; aborted workers are discarded and
  failed removal blocks replacement.
- Automatic OpenCode startup retains the operator's saved engine and removes
  the separate engine-approval step. File/tool grants remain explicit.

| Verification | Result |
| --- | --- |
| Dashboard | 539 tests, OK, 9 skipped (latest, with real MSVC and Docker g++ runs) |
| Setup | 99 tests, OK |
| Analysis | 30 tests, OK |
| JavaScript | 24 tests passed |
| Actual frontend Docker validation/preview | PASS, authenticated isolated preview, CSS verified, stale launch rejected, source unchanged, cleanup confirmed |
| Actual Ghidra + built-in MCP | PASS |
| Actual Qwen35B + OpenCode + Ghidra | PASS with function-search/decompilation controller receipts |
| Actual host Melty auth/discovery + built-in MCP lookup | PASS |

Evidence is retained locally in `.smelter/ghidra-smoke-36911240d5184812b548be1ce5ff1e4b/`,
`.smelter/melty-live-evidence.json`, `.smelter/integration-frontend-smoke/`,
`.smelter/integration-*-final.log`, and `.smelter/agent-stack-configuration.json`.
Launch tokens and credentials are not included in this report.

Requirements and setup are in `system-requirements.json`, `REQUIREMENTS.md`,
and the setup scripts. See [REA/Ghidra](REA_GHIDRA_INTEGRATION.md) and
[Melty](MELTY_CONNECTOR.md) for tool contracts and reproduction commands.

Remaining work:
- coding-copy ergonomics: exact-text edits, reviewed merge, a Lua runner;
- GTA × ARK M1 through SMELTER, then the in-game step, which is blocked on Script
  Hook V support for GTA 1.0.1158.16, a UE4SS choice and install approval;
- Melty upload/test/publish;
- asset adapters, if conversion is ever chosen;
- browser/mobile visual review.

The review's R01–R08 items are fixed (R07+R08 committed as `982950b`). The model has not been
weight-fine-tuned. Current acceptance establishes one generated binary workflow,
not arbitrary game reverse-engineering quality or a complete mashup pipeline.

Current review-fix verification and continuation: [REVIEW_FIXES_20261025.md](REVIEW_FIXES_20261025.md). CLI research and skill selection: [MODDING_CLI_TOOLKIT.md](MODDING_CLI_TOOLKIT.md). Earlier test counts are historical.

## Universal Modder addition (25 October, 20:52)

Pinned GitHub 0.2.0 commit `c1dff21663665dd17af289744a301b66e369605e` is installed
in its own source/runtime, preserving the Melty kit. Standalone read-only scans
reported RAGE for GTA Enhanced and Unreal/IoStore for ARK. New fixed local-KB MCP
status/search/read calls passed. A real Qwen/OpenCode task used search + read_note
and returned a grounded architectural suggestion at the retained 128K context.
Full regression results: dashboard 559 tests / 9 skips; setup 107; upstream 28.
See [the integration](UNIVERSAL_MODDER.md) for scope, launcher and retained evidence.
