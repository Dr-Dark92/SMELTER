# Review fixes and continuation

Latest continuation: [engine archive integration](ENGINE_ARCHIVE_CLI.md) and
[current handover](CURRENT_HANDOVER.md) supersede the earlier candidate/install
steps below. Pinned repak, retoc and UnityDataTool metadata adapters now exist;
the actual runtime game integration remains unverified. Qwen stays at 128K.

Updated 25 October 2026, 20:08 Asia/Muscat. Branch `feature/agent-stack-game-mods`,
HEAD `cca4ecf`; this pass is local/uncommitted. Preserve all existing work,
including unrelated `dw3_decomp-main/`. Earlier handovers/checkpoints predate this pass.

## User decisions

- CLI-based modding tools; every installed dependency belongs in requirements/docs.
- Keep Qwen3.5 35B-A3B at **131,072 context tokens (128K)**. Its separate generated
  response ceiling is now 8,192, raised from 2,048; context was not reduced.
- Continue autonomously, with tests along the way. Work is authorized; execution
  sandbox escalation is a separate mechanism, not a need to re-authorize the task.

## Completed

- GAL1 Lua reader: 11 floats / exactly 64 bytes, startup layout assertion and
  shared literal Python/Lua fixture. Added a real confined Lua test profile.
- Model-facing native builds: fixed **MinGW-w64 CLI in no-network Docker**, no
  host MSVC fallback, no execution of generated Windows code. Operator MSVC script
  remains available. Sources, manifest, compiler worker and artifacts have hashes;
  bounded inventory, compilation, artifact transfer and owned cleanup are recorded.
- New pinned `smelter-cpp:2`: g++ 15.2.0-r5, Lua 5.4.8-r0, mingw-w64-gcc 15.2.0-r0,
  pinned Python base digest and recorded resolved transitive package inventory.
  Selected immutable image:
  `sha256:4a16ae11a7c5c1c63a487102710c46efc216de5a84be38b8bedb68db15f272ea`.
  Existing v1 image was preserved.
- Failed native builds now fail MCP/task status. Long build/test operations have
  coordinated 240 s transport deadlines over shorter worker bounds.
- Game inspection checks budgets inside enumeration/header/PE sampling, validates
  truncated PAK footers, rechecks paths and qualifies entropy conclusions.
- OpenCode warm-up survives changed tool grants: empty transport is warmed once,
  task schemas refresh before admission, and task generations/host grants still
  enforce execution. Model/image/runtime/policy changes still replace the container.
- C++ suites over 64 programs return ERROR; no silent truncation. Mod Python tests
  use separate interpreters so same-named helpers do not leak across mods.
- Requirements contain 30 researched CLI entries with integration states. Added
  read-only `modding_tool_catalog` and bundled `game-modding` / `mod-validation`
  instructions. Capability discovery includes mods/cpp/lua/native dependencies.
- Applied tested `tools/setup/configure_melty_cli.py`: native context 131,072,
  output 8,192; persistent grants `melty_read`, `coding_workspace`, `native_build`;
  two skills copied into `~/.config/opencode/skills/`. Other providers, credentials,
  permissions and existing REA registration preserved. Backup:
  `~/.config/opencode/opencode.json.bak-smelter-cli-20261025T152015491910Z`.
  Reproducible derived-tag input: `tools/setup/Modelfile.qwen35b-128k`; existing
  model tag/weights were not recreated/downloaded during this pass.

## Verification

| Check | Result |
| --- | --- |
| Full dashboard suite | 553 tests, OK (9 skipped) |
| Final focused native/Lua/catalog/lifecycle rerun | 74 passed |
| Final catalog/cross-layer checks | 20 passed |
| Setup suite including profile backup/idempotence/context preservation | 104 tests, OK; final configuration regressions also passed (4 tests) |
| Analysis suite | 30 passed |
| JavaScript suite | 24 passed |
| Real Lua | Shared GAL1 fixture and transform tests passed in Docker |
| Real cross-build | ASI, stub-SDK object targets and Windows test EXE built; none executed |
| Host-read boundary | Macro include could not read a host-only fixture or expose its sentinel |
| Real OpenCode transport | Warmed container reused with added/removed grants; refreshed schemas visible; cleanup confirmed |
| Real native-profile stdio MCP | UE5 catalog call returned 15 compatible/general entries; context/output read back as 131,072 / 8,192 |

The full dashboard run predates the final small manifest/capability edits; focused
reruns cover them. Setup/analysis initially hit sandbox-only Windows temporary-file
denials; reruns outside that sandbox passed. These were environmental failures.

Native MCP receipt:
`.smelter/tool-runs/37fbb0fa-1db2-43e0-bfb3-72bc76ccba2a.jsonl`.
Reproduce with `python tools/analysis/smoke_modding_cli.py` and
`python tools/analysis/smoke_modding_cli.py --native-catalog-only`.

## Next work

1. Reload SMELTER and Melty's OpenCode session to discover new code/config/skills.
   No existing interactive application or game was forcibly stopped in this pass.
2. Add pinned installers and fixed read-only adapters for repak PAK list/info,
   retoc IoStore list/info and UnityDataTool JSON metadata. They remain candidates;
   catalog templates are not executable shell grants.
3. Verify skill discovery in the actual Melty builder session, then run a complete
   Qwen-driven mod task at the retained 128K context. This pass verified real tools
   and transports, not a new live-model builder task.
4. GTA/ARK game glue and current loader/build compatibility remain unverified.
   A skeleton ASI/stub compile is not an installable completed mod. No game files
   were installed or game binaries run.
5. Test representative long-task recall/quality at 128K; earlier filler benchmarks
   do not establish that quality. Do not reduce the selected context on assumption.

See [CLI toolkit](MODDING_CLI_TOOLKIT.md), [game tools](GAME_MOD_TOOLS.md),
[Melty](MELTY_CONNECTOR.md), [requirements](../REQUIREMENTS.md).

Final saved-runtime correction: the dashboard read-back was still 16K/2K while
the native Melty configuration was 128K. Both now read **131,072 context / 8,192
output**, with thinking/timeouts preserved. The previous dashboard runtime is
backed up in `.smelter/runtime-before-cli-20261025T160439003909Z.json`.
Repeat `configure_agent_stack.py` setup now preserves an existing saved Qwen
runtime. `configure_melty_cli.py --align-dashboard --apply` reproduces the explicit
alignment, with a backup. Four focused configuration tests passed.
