# Agent-stack integration status — 25 October 2026

The running dashboard is configured for `qwen3.5:35b-a3b` at 16K context,
2048 output tokens, a 300-second model-turn limit and an 1800-second OpenCode
task limit. The existing 9B lightweight model is preserved. OpenCode starts
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
| Melty service | Fixed `https://melty.gg/api/mcp`, existing host sign-in referenced without copying credentials | Authenticated initialize/account/tool discovery; real `search_games` through built-in MCP; protocol `2025-06-18` |

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
| Dashboard | 505 tests, OK, 9 skipped |
| Setup | 77 tests, OK |
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

Remaining work: game-specific build/asset adapters, explicit Melty upload/test/
publish operations, real-game acceptance, browser/mobile visual review, and the
older installer/web-process lifecycle issues R07–R08. The model has not been
weight-fine-tuned. Current acceptance establishes one generated binary workflow,
not arbitrary game reverse-engineering quality or a complete mashup pipeline.
