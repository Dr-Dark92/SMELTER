# Raptor acceptance case for universal gameplay logic

**2026-10-28 checkpoint:** The standalone policy now passes 30/30 protected
checks and the saved Lua/mods profiles are GREEN. The dated hashes and test
defects below are historical observations, not fresh file identities. The
canonical controller still needs policy integration and actual adapter/action
coverage. Begin with [the current game handover](../handovers/GTA_ARK_MASHUP_HANDOVER_20261028.md)
and recover live hashes before selecting a new bounded behavior task.

Prepared for the user to pass to SMELTER/Qwen. No native prompt was submitted.
The shared controller and conformance contract are to remain engine-neutral.
Game-specific objects/assets/units belong in a project adapter/profile.

## Recover the actual task

Reuse workspace `897b9243-fd7e-42f4-a46a-d1b814a33a81`. Recover its canonical host
root and search by exact filename with `smelter_coding_workspace_context` before
reading or editing. The task's `mods/gta-ark` directory is a project, not the
identity of SMELTER. Duplicate basenames must be distinguished by their indexed
relative paths and current SHA-256. Docker runs read-only snapshots of host files.

Latest inspected paths and hashes, 27 October 2026:

| Relative path | SHA-256 |
|---|---|
| `mods/gta-ark/Mods/GtaArkLink/Scripts/raptor_aggro.lua` | `165a5e79ca8e5f6bf467fa9a5aa03105fbad0f4dd5ceb2a1fff2ed867c164c17` |
| `mods/gta-ark/Mods/GtaArkLink/Scripts/engine_adapter.lua` | `a22c0d6be09ba5dff8a9a0b27ec3d540f8df329b319d5fb90c42c7abad660410` |
| `mods/gta-ark/tests/test_raptor_behavior.lua` | `a5229f9093f3169ce6f7bf3acbddcce220e31f5a0fcbe9e2a894d911926ca059` |

These are inspection evidence, not permission to overwrite later edits. Re-read
current destination hashes before proposing changes. Preserve the six original
GAL1/runtime regression fixtures and their existing assertions.

## Current defects to demonstrate

The current behavior test calls the dot-defined `start_chase` with `:` (line 60),
inserting an unintended `self`. It counts `pcall` success without asserting the
returned boolean, refers to undefined `checks_failed` (line 96), maintains
inconsistent failure counters and does not assert vehicle rejection (lines
118–126). A thrown exception is not evidence of correct rejection.

The current controller fabricates sample targets (lines 34–41), reads `os.time`
directly and lacks a shared normalized eligibility boundary. Its existing-state
chase branch also needs an actual state/action test. The current adapter's real
spawn branch contains a placeholder but returns success; initialization can
silently fall back to simulation. Those limitations must be reported honestly.

These observations supersede earlier handover assumptions about the original
line-95 method-call defect. The inspected controller has since been replaced by
a smaller implementation. Diagnose the bytes currently on disk.

## Work sequence for SMELTER

1. Load the current relevant debugging/gameplay skills and inspect actual exports,
   signatures and callers. Do not invent APIs from a previous response.
2. Repair the test harness semantics and restore consistent assertion accounting.
   Obtain a meaningful failing behavior receipt before changing production logic.
3. Propose the reusable boundary from `docs/UNIVERSAL_GAMEPLAY_CONTRACT.md`:
   normalized opaque entity IDs, type/traits, finite metre-based positions,
   injected monotonic clock, capability discovery and explicit action results.
   These are new design requirements, not claimed existing exports.
4. Implement the smallest shared controller and project adapter seam required by
   this slice. Preserve necessary public wrappers and update traced callers.
   Avoid a broad migration or renaming every file just to remove game names.
5. Execute the same controller behavior suite with two different fake adapters.
   Cover allowed human NPC/cop/player targets and rejected vehicle entities,
   actor versus target identity, chase/attack, range/cooldown, target loss and
   unsupported/error paths. Do not add an occupant exclusion policy.
6. Use disposable mutations to prove relevant tests reject vehicle acceptance and
   movement issued to the target instead of the controlled actor.
7. Run Lua and original Python/mod regressions on the final tree through SMELTER.
   Save receipt IDs, exact tree hash, applied proposal IDs and the final relation
   chart. Keep in-game/native compatibility explicitly unverified until tested.

Only SMELTER/Qwen authors the gameplay implementation. The operator supplies
this contract and reviews evidence. No extra tool package is required for this
offline slice. Keep Qwen's selected 131072/8192 context/output limits.
