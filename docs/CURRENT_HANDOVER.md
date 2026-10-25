# Continue SMELTER work

Current handover: **25 October 2026**, updated after the engine archive integration.

1. Read the latest [engine archive integration](ENGINE_ARCHIVE_CLI.md), then
   [Universal Modder integration](UNIVERSAL_MODDER.md), followed by
   [review fixes and continuation](REVIEW_FIXES_20261025.md), then
   the earlier [handover](handovers/2026-10-25/HANDOVER.md) for historical context.
2. Check the [progress ledger](handovers/2026-10-25/PROGRESS.md).
3. Continue from the [ordered next steps](handovers/2026-10-25/NEXT_STEPS.md).
4. To assign another agent, use the [continuation prompt](handovers/2026-10-25/SECOND_AGENT_PROMPT.md).

Git checkpoint branch: `feature/agent-stack-game-mods`. Commits `7adb594` and
`cca4ecf` contain the earlier agent stack and lifecycle work; the subsequent
checkpoint includes the tools, prototype mods, review fixes and integration
documented here. Use `git log -1` to identify the exact current commit. Runtime
state/downloads and the unrelated `dw3_decomp-main/` folder are excluded.
Preserve this checkout; earlier checkpoints predate these fixes. Do not reset,
clean or overwrite unrelated local work. Latest continuation notes are in
[REVIEW_FIXES_20261025.md](REVIEW_FIXES_20261025.md).

Reference docs:
- [CLI toolkit and Qwen skills](MODDING_CLI_TOOLKIT.md): engine routes, candidate
  states, requirements and the two new bundled instruction packs;
- [game-mod tools](GAME_MOD_TOOLS.md): `inspect_game_files`, `mods/` coding copy,
  `mods`/`cpp` test profiles, `build_native_mod`;
- [GTA × ARK discovery](discovery/GTA_ARK_DISCOVERY_20261025.md) and
  [M1 design](discovery/GTA_ARK_M1_DESIGN.md);
- [Melty](MELTY_CONNECTOR.md): connector, desktop-app route, context measurements;
- [REA/Ghidra](REA_GHIDRA_INTEGRATION.md);
- [integration status](INTEGRATION_STATUS_20261025.md);
- [System status](SYSTEM_STATUS.md).

Latest integration (25 October, 20:52): Universal Modder GitHub source is pinned
and installed separately from the Melty kit, with a private CLI/runtime, local
knowledge MCP actions and the `universal-modder` Qwen skill. Standalone GTA/ARK
recon and a real Qwen 128K search/read-note task passed. See its integration doc
for exact pins/evidence. Both model routes remain 131,072 context / 8,192 output.
No game was launched/modified. Main remaining gate is game-specific loader/runtime
compatibility and the actual in-game vertical slice.

The earlier Universal Modder GUI refresh is still running (PID 15164, port 8768).
Its catalog includes Universal Modder. Latest launch logs remain
`.smelter/dashboard-um.stdout.log` / `.stderr.log`.

New: repak 0.2.3, retoc 0.1.5 and UnityDataTool 2.4.0 are pinned, installed in
`smelter-engine-cli:1` and exposed through one `inspect_engine_archive` MCP tool
under the inventory-folder grant. The full all-grants manifest fits the existing
32-tool bridge cap. The optional `engine-archive` skill is ready/enabled and its
exact source is installed in native OpenCode alongside the existing three skills.
The native profile now persists the exact registered ARK installation as its
read-only inventory scope; reopen its MCP connection to discover the archive tool.
The backed-up configuration preserves unrelated providers, REA and permissions.

The image ID is `sha256:23456cc5f1a12f70458ba98fe41c649ccd83019068bb8d0ab8e7dc3df6a75a68`.
Setup selection is separate in `.smelter/tooling/engine-cli/selection.json` so the
older running GUI can still read its original sandbox schema. An explicit new
GUI `engine_image` setting takes precedence. No model/runtime limits changed.

Real fixtures and 13 stdio MCP operations passed, including ARK global/optional
IoStore reads. ARK PAKs report version 12 and exceed pinned repak's version-11
support. The tool returns an explicit compatibility limit, not a missing-key claim.
Neither asset extraction/cooking nor a runtime game mod is verified.

GUI refresh is pending: automatic approval review rejected stopping/restarting
the running dashboard. Do not bypass it or kill unrelated Python/game/Melty
processes. The old GUI keeps its compatible image configuration; new native and
standalone MCP processes already load the implementation. A normal backend restart
will expose the new tool in the GUI too. See the engine integration document for
installer, CLI, exact limits and repeatable acceptance commands.

Final verification: **570 dashboard tests, OK (9 skipped)**; **111 setup tests,
OK**; **17 JavaScript tests passed**; **13 real stdio MCP checks passed**. The
Qwen structured acceptance passed at 128K/8K, with exact archive format/path,
task-attributed UE5 identity and explicitly unverified minor/cooking/runtime:
`.smelter/engine-cli-runs/qwen-aa5ebd5a76064105985429f308660092/report.json`.
MCP fixtures/game evidence:
`.smelter/engine-cli-runs/eb1fd06357674a85b7bc436be0f5bfa8/report.json`.
Final limits, native persisted-scope operation and skill-copy verification:
`.smelter/engine-verification.json`. Both saved routes and Ollama's observed
resident model context are 131,072 tokens / 8,192 output where applicable.

Native config backup before persisting the ARK read-only scope:
`~/.config/opencode/opencode.json.bak-smelter-cli-20261025T173834469911Z`.
The configured scope is exactly `D:\SteamLibrary\steamapps\common\ARK Survival Ascended`.
Original GUI sandbox settings before the compatible selection migration are in
`.smelter/tooling/engine-cli/sandbox-before-compatible-selection.json`.
No game files were modified, game processes launched or unrelated changes reset.
