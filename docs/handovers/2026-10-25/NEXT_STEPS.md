> Latest status: use [current handover](../../CURRENT_HANDOVER.md) and [engine archive integration](../../ENGINE_ARCHIVE_CLI.md). This plan is historical. Pinned repak/retoc/UnityDataTool metadata adapters are now implemented. ARK PAK v12 compatibility, actual cooking/runtime integration and refreshing the old GUI remain separate gates. Qwen stays at 128K.

# Ordered next steps (updated 25 Oct, 14:23 Asia/Muscat)

Read [HANDOVER.md](HANDOVER.md) first. Preserve the dirty checkout. Every new tool
or dependency updates requirements and docs in the same change. SMELTER (Qwen
through its tools) does the mod work. The maintaining agent builds and verifies
tools, and changes `mods/` directly only for reference or verification. Ask the
operator before installing into game folders, launching games, publishing, or
changing accounts.

## 1. Establish continuity

- Run `git status --short` and check [MANIFEST.json](MANIFEST.json) (base `982950b`).
- Don't reinstall working tools, repull weights, reauthenticate Melty or recreate
  the database.
- Start the dashboard outside the command sandbox (handover trap 2).
- Confirm GUI → OpenCode ready, Melty connected, and Settings → Confined execution
  showing all four image IDs.

## 2. Coding-copy ergonomics for the local model (platform)

1. **Exact-text edit tool.** Add `propose_coding_edit` (one or more
   `{relative_path, expected_sha256, old_text, new_text}` replacements, each
   `old_text` unique) next to the whole-file proposals. Same apply, rollback and
   audit path. Whole-file patches took about 15 KB of output for a three-file change.
2. **Reviewed merge.** Add an operator-only route that shows a coding copy's
   `mods/<mod>/` diff and applies it to the repo's `mods/<mod>/`. It needs explicit
   approval in the GUI, hash checks against the copy's baseline, and no model
   access. Qwen's two FOV runs live only in `SMELTERV2/coding/…` today.
3. **Lua runner.** Add a confined `lua` profile, a Lua 5.4 image as a catalog step,
   for `mods/<mod>/tests/test_*.lua`. The ARK UE4SS mod's `gal_link.lua` and
   `tests/test_gal_link.lua` are ready but have never run.

Each item needs tests, docs and a SMELTER run proving Qwen can use it.

## 3. M1 through SMELTER (GTA × ARK camera link)

Brief Qwen with [the M1 design](../../discovery/GTA_ARK_M1_DESIGN.md) and the mod's
[README](../../../mods/gta-ark/README.md). Work in the coding copy:
- move testable logic into portable headers, with `cpp` tests (start from Qwen's
  `link_math.h`);
- `tools/install_manifest.py` (plan, apply and remove with a SHA-256 manifest, dry
  run by default) plus `mods` tests;
- keep `native.json` targets building with `build_native_mod`;
- merge reviewed results with step 2.2.

## 4. Unblock the in-game step (needs operator decisions)

- **Script Hook V:** watch for a release supporting GTA Enhanced **1.0.1158.16**
  (latest checked: v3889.0 / 1158.13), or research the Ultimate ASI Loader-only
  native route and report before building.
- **ARK:** choose a UE4SS build for UE 5.5 and confirm ARK's supported single-player
  BattlEye-off option. Prove UE4SS loads before the mod.
- **Before the first modded launches:**
  - back up saves (`um backup`);
  - install from a manifest with a removal script, only with explicit approval;
  - pass GTA `-nobattleye` only as a launch argument;
  - pick Story Mode by hand;
  - ARK single player only.
- **Verify `natives.h` hashes** against alloc8or's native DB.
- **In-game acceptance** (record in `mods/gta-ark/MODLOG.md`): the five checks in
  the M1 design.

## 5. Carry-overs

- **Data copies:** decide which of the two database copies is canonical (handover
  trap 1).
- **Ghidra:** list, archive and remove retained analyses; reassess the 64 MiB limit
  (GTA's exe is 53 MiB but packed; ARK's is 223 MiB).
- **Melty write stages** (validate package, upload an approved artifact, draft,
  test, publish only with explicit approval): only once a real mod artifact exists.
- **Measured tuning:** repeated 35B vs 9B tasks; long-context quality on real
  material.
- **Visual check:** GUI startup, engine switching, grants and the 375 px layout.
- **Commits:** coherent commits for the rest of the work (R06; the earlier stack;
  game-mod tools; docs; `mods/gta-ark`), excluding `dw3_decomp-main/`, when the
  operator asks. R06 can't be separated from the earlier OpenCode startup work.
- **Melty builder:** try a small Melty builder task on the local model (unconfined
  route; Melty lookup is the only SMELTER grant there).
