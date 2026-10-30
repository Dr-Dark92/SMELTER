# GTA V Enhanced × ARK: Survival Ascended — game handover

Updated 2026-10-28. Read together with
[the SMELTER continuation handover](CLAUDE_CONTINUATION_HANDOVER_20261027.md).
This document consolidates the creator's game vision, actual source architecture,
verified progress and remaining integration work. Historical loader observations
below are dated evidence, not a fresh compatibility check.

**Later managed-Lua checkpoint, 28 October:** A generic C# Lua 5.4 host now passes
the same 128 frozen checks unchanged, plus real-controller/C# fake-provider
movement/attack/cooldown/death-loss tests. This is operator-owned bridge/tooling
work; Qwen's gameplay modules did not change. Setup 168 OK. No RPH runtime,
native GTA provider or game was run. See [the host guide](../MANAGED_LUA_HOST.md)
and [the exact checkpoint](../../diagnostics/MANAGED_LUA_HOST_20261028.json).

**Later native-probe preparation, 28 October:** The RPH authors' Enhanced
release lists build 1158.16 support. A read-only, exact-executable-gated managed
plugin is compiled/staged, with seven fake-callback instrumentation tests and
seven compiler/cache tests. No runtime loader was acquired/installed or run;
this is a candidate route, not a live compatibility result. See
[the probe guide](../GTA_NATIVE_READ_PROBE.md) and
[source/build/test hashes](../../diagnostics/NATIVE_READ_PROBE_20261028.json).
The passive provider/lifecycle milestone remains 128 frozen checks GREEN;
fresh coding-copy Lua 10/10 and mods 14 tests with one C++ sample skip.
No game or ARK runtime claim follows from these offline results.

**Codex continuation, 28 October:** The current six-capability native adapter
design and Lua-host gap are documented in
[GTA predator adapter](../GTA_PREDATOR_ADAPTER.md). A fresh read-only inventory
and current author support check are recorded in
[the range/runtime review](../../diagnostics/PREDATOR_RANGE_REVIEW_20261028.md).
The checked loader paths remain absent; no game was launched or modified.
The controller verifier now has 52 checks after operator-reviewed range-reuse
scenarios. Older 42/48-check results below are historical revisions.

## What the creator wants

GTA V Enhanced Story Mode is the intended host for a GTA × ARK mashup, with ARK:
Survival Ascended supplying the dinosaur/gameplay direction. SMELTER/Qwen should
do the modding and scripting through Melty/OpenCode; the outside coding agent
provides infrastructure, guidelines, diagnosis and verification.

The requested eventual content is:

- Raptors first, then Rex, Carno, Trike, Stego and PT. PT is the user's shorthand;
  confirm the exact creature/profile before selecting assets.
- Creatures can aggro human NPCs, cops and the player; vehicle entities are excluded.
  No extra rule excluding humans occupying vehicles was requested.
- Use GTA cougar behavior as the starting point for aggro/attack experimentation.
- A shop offering a tranquilizer rifle, tranquilizer ammunition, taming meat and
  saddles, alongside the planned dinosaur offering. Prices, stock, UI, persistence
  and species-specific saddle rules have not been defined or implemented.
- Tranq/taming/riding should follow a working first creature. Knockout, feeding,
  ownership, mounting and combat transitions need explicit behavior contracts;
  their detailed mechanics/tuning are not established by the current code.

SMELTER itself must remain universal. Shared policy/controller contracts must
not branch on GTA, ARK, creature names or installation paths. Put native handles,
engine calls, asset IDs and game tuning in adapters and game profiles. CLI/MCP
interfaces are required for AI use. Record every added dependency/tool in the
requirements and documentation, preserving the selected 128K/8K model profile.

## Three related experiments, with different evidence

### M1: two-process camera/state link

GTA and ARK run side by side. GTA's final rendered camera and player pose feed
an ARK-side view-following experiment. This proves a transport/coordinate seam;
it does not place a dinosaur inside GTA or combine the two game engines.

Implemented source path:

1. GTA `CameraSource` supplies camera/player samples to `GtaArkLink.asi`.
2. The writer updates a fixed 64-byte GAL1 record in a local file.
3. UE4SS Lua in ARK reads a consistent record, checks freshness/flags and maps
   axes/units relative to a captured origin.
4. The current ARK binding moves the local pawn and changes control rotation.

The current transport is **a file**, not a socket or an OS shared-memory block:
`%LOCALAPPDATA%\SMELTER\gta-ark-link\camera.bin`.
Historical model summaries calling it shared memory are imprecise. Native named
shared memory was considered for a later rendering stage, not implemented here.

GAL1 is little-endian: magic/sequence, eleven floating-point camera/player/FOV
values, flags and frame counter, 64 bytes total. The seqlock sequence is odd
during write and even when complete. The reader accepts only identical double
reads with an even sequence and correct magic; invalid/nonfinite values and FOV
outside `(0,180)` reject. Both Story Mode and link-enabled flags are required.

The implemented relative position mapping is
`UE delta = (100*GTA dy, 100*GTA dx, 100*GTA dz)` (metres to centimetres).
Yaw uses the captured Unreal yaw minus GTA yaw change; pitch is retained and roll
negated. Current bindings anchor displacement to the pawn's initial position,
retain camera offset and recapture origins on pawn/controller changes.
These signs/physical camera behavior still need recorded in-game calibration.

At roughly 33 ms ticks, about 30 unchanged reads signal stale data. The reader
then stops further mutations and clears the origin. It does **not** restore the
prior physical pawn pose. FOV is transported but not applied by the current ARK
binding. The old design promise of automatically returning the camera is broader
than the inspected implementation; do not repeat it as completed behavior.

Sources: [record specification](../../mods/gta-ark/link-format.md),
[original M1 design](../discovery/GTA_ARK_M1_DESIGN.md),
[runtime preparation](../GTA_ARK_RUNTIME_WORKFLOW.md).

### M2: visual composition / rendering mashup

The design considered exporting ARK frames through a native component and
compositing through a ReShade add-on, with a faster native transport if needed.
This is a proposed next rendering experiment. No frame exporter, compositor,
depth/occlusion solution, input forwarding, entity replication or finished
single-view GTA/ARK rendering has been verified in this checkpoint.

Camera synchronization alone does not transfer meshes, skeletons, animations,
collision, AI or inventory between RAGE and Unreal. The project must explicitly
choose which later effects use rendering composition and which require native
GTA assets/actors. Do not assume the camera bridge solves both.

### Cougar/Raptor: creature behavior in the GTA host

The creator proposed cougar attacks as the Raptor aggression starting point.
The baseline candidate in the existing design is GTA's `a_c_mtlion`.

Two candidate routes remain distinct:

- Preserve an existing cougar archetype/behavior and provide a compatible Raptor
  appearance. It still needs a verified Enhanced asset-loading path plus correct
  rigging, animations and collision. A cosmetic placeholder is not ARK integration.
- Implement explicit detection, target selection, chase, attack and disengagement
  through a verified native-action adapter. Real actions must return evidence;
  a relationship-group assignment or a state-table mutation alone is insufficient.

Separate the aggro trigger from the executor. Discovery/visibility/damage can
trigger a target decision, while the selected adapter performs movement/attack.
Keep actor and target identities distinct. Test cooldown/range/target loss using
an injected clock; do not issue a new combat command every frame. Specific trigger
rules and numbers should be profiles, not universal engine assumptions.

Raptor import/retargeting, real ARK behavior reuse, GTA attack animation execution,
city spawns and NPC interaction are not established by the current offline tests.
No validated headless ARK-to-Enhanced asset conversion adapter is recorded.

See [the cougar/Raptor design](../../mods/gta-ark/COUGAR_RAPTOR_PROTOTYPE.md).

## Where the actual files live

| Location | Meaning |
| --- | --- |
| `C:\Users\Dr.Dark92\Documents\ChatGPT\SMELTER` | Main Git checkout; production fixture here is older than the isolated mod work |
| `C:\Users\Dr.Dark92\Documents\ChatGPT\SMELTERV2\coding\897b9243-fd7e-42f4-a46a-d1b814a33a81` | Owned working coding copy; edits persist on host |
| Native Melty/OpenCode project directory | Client CWD, not authority for SMELTER source locations; recover exact current binding |
| `docs/handovers/checkpoint-20261027/current/mods/gta-ark/` | Portable snapshot of the isolated mod source, outside production test discovery |
| `docs/handovers/checkpoint-20261027/reference/` | The two verified reference files, now matching applied working files |
| `.smelter/coding-workspaces/<workspace-id>/` | Local owned metadata, proposals, checkpoints, frozen registration and receipts; not committed |

Docker receives a fresh read-only test snapshot. The files are not being edited
inside a persistent Docker image. Use workspace ID, exact relative path and fresh
full-file SHA. Duplicate basenames must never be selected by guesswork.

Within the isolated/archived mod source:

| Path under `mods/gta-ark/` | Responsibility and limitation |
| --- | --- |
| `gta/src/GtaArkLink.cpp` | ASI writer/F7 loop when the native route is enabled; default skeleton does no native work |
| `gta/src/camera_source.h`, `shv_source.cpp`, `natives.h` | Swappable sampling boundary and gated Script Hook V source; native hashes/ABI require runtime validation |
| `gta/src/link_record.h` | Win32 GAL1 writer/layout |
| `ark/Mods/GtaArkLink/Scripts/gal_link.lua` | GAL1 reader, stale tracking and coordinate conversion |
| `ark/Mods/GtaArkLink/Scripts/main.lua` | ARK camera-link binding; synthetic engine tests are not live reflection proof |
| `Mods/GtaArkLink/Scripts/entity_policy.lua` | Canonical generic policy subject; protected 30/30 now pass |
| `Mods/GtaArkLink/Scripts/raptor_aggro.lua` | Current minimal controller used by offline tests; not a complete native controller |
| `Mods/GtaArkLink/Scripts/engine_adapter.lua` | Simulation/real-mode prototype; contains unimplemented native behavior |
| `Mods/GtaArkLink/Scripts/raptor_system_main.lua` | Entry loop source with unresolved runtime seams; successful import is not successful ticks |
| `ark/Mods/GtaArkLink/Scripts/raptor_*.lua` | Historical alternate copies; do not assume identical signatures or silently swap them in |
| `tests/` | GAL1, runtime-binding fixtures, policy, controller import/state and breakage checks |
| `tools/runtime_workflow.py` | Read-only runtime inspection and source-only packaging, not game installation |

The archived Raptor config uses centimetres and placeholder tuning, while the
universal contract proposes a documented common metre-based boundary. That
normalization is future adapter work, not an already-completed migration.

## Progress: what is verified and what remains

### Verified saved offline result, 2026-10-28

SMELTER applied proposal `b4eb565f-cd2a-4bb3-ae53-d648a37f1c50`. Do not reapply it.
Both latest saved test profiles match tree
`eaff3fa39d33b07d7b7a00f6de754802140c422ec6c892b9411275d04555f79c`:

- Lua: six programs, no failures/errors. Receipt
  `6ee4b5e8-2a0a-49d9-8b6e-d53708e42f36`.
- Frozen generic policy: **30/30**, unchanged verifier
  `b303d3d738ee98a847174e706d15264c091731c23459d2c2ba9a4c59854680ea`.
- Python mods: 14 tests, no failures/errors, one optional C++ writer skip.
  Receipt `f85b25de-e3b4-40a2-ae42-9b03fdb7e58e`.

The policy fix removed a surviving unconditional rejection and correctly
distinguished nil maps, malformed scalar maps, disabled boolean entries and
present empty/all-disabled any-maps. One editable test's obsolete reason-code
assertion was aligned to safe rejection; no frozen test was altered.

Earlier native ASI/object/test-EXE builds compiled successfully. That is build
evidence; it does not prove the skeleton has a working native route or that a
Windows cross-build executed in game. Earlier portable FOV-math experiments in
other coding copies are historical work, not automatically adopted here.

### Claude continuation 2026-10-28 (offline evidence only)

- **Promotion.** `Mods/GtaArkLink/Scripts/{entity_policy,raptor_aggro,engine_adapter,raptor_system_main}.lua`
  and the four Lua tests were copied into the main `mods/gta-ark` tree, hash-checked
  (`diagnostics/PROMOTION_20261028.json`). The production README and
  runtime_requirements were kept because they are newer. The `ark/` alternates, the
  `.backup` file and the import-free `test_raptor_basic.lua` were left out. Main
  tree: Lua 6/6 programs, mods 14/14.
- **Generic controller contract.** `predator-controller-v1` defines the universal
  boundary these gaps call for:
  - `new(deps)` takes an injected adapter (`position`, `describe`, `candidates`,
    `move_to`, `attack`, `stop`), `evaluate` and `policy`, a `clock`, and a profile
    (`detect_radius`, `attack_radius`, `lose_radius`, `attack_cooldown`).
  - Its 42 checks cover policy integration, vehicle rejection, actor/target
    identity, a single move request, attack, injected-clock cooldown,
    death/vanish/range loss with `stop`, adapter refusal and throwing, and
    per-actor state.
  - They run against two fake adapters at different unit scales. Game APIs and
    tuning stay in adapters and profiles.
- **Status.** GREEN offline: Qwen's scaffold-based controller (`789c37c8…`) passes
  48/48 and is promoted to the main tree with its finish receipt. This is
  fake-adapter evidence only; it does not show a GTA or ARK actor moving or
  attacking.
- **Not yet wired in.** `raptor_system_main.lua` and `engine_adapter.lua` still
  need a real adapter implementing the six capabilities and a profile in
  game units. Known untested edge: after acquisition, a failing re-describe
  reaches the attack branch.

### Concrete remaining controller/adapter gaps

The inspected canonical controller does not yet import/use `entity_policy`.
Consequently, a passing policy does not prove `start_chase` rejects a vehicle.
Its target discovery fabricates sample records; chase/attack largely mutate
state, and timing still uses `os.time`. It needs the genuine adapter action seam,
normalized inputs, injected clock and meaningful repeated-update tests.

The adapter can silently fall back from failed real initialization to simulation.
Its real spawn branch contains a placeholder and can return true without a
verified actor. Those behaviors must not masquerade as native support.

The entry loop calls `raptor_aggro.spawn_raptor`, which is absent from the
inspected canonical controller, and uses an entity ID as a `table.remove` index.
These runtime paths are not proved by import-only tests. Confirm current bytes
before repairing; archived alternate copies have different interfaces.

Next conformance tests should exercise the same real shared controller with two
different explicit fake adapters, covering actor/target identity, allowed humans,
rejected vehicles, movement/attack requests, cooldowns, loss/death, unsupported
capabilities and failures. Fake-adapter success remains offline evidence.

### User reports versus retained runtime evidence

The creator earlier reported a large leap and that something was working during
Melty testing. Retain that report. The handover checkpoint does not contain a
corresponding live-game loader log, actor capture or camera calibration receipt.
Confirm whether that observation meant the AI/tool chain, simulation, camera
link or a real creature in GTA. Do not turn absence of a retained receipt into
a claim that the creator never observed success, or reinstall/overwrite a working
game setup on the basis of an older README.

## Historical runtime gates: recheck before game testing

The 25–26 October discovery recorded GTA Enhanced build `1.0.1158.16`, while the
then-reviewed Script Hook V snapshot listed `1.0.1158.13`. Loader files were not
found in the checked locations then. ARK client loader/API support was not
verified, and the executable did not expose a readable minor-version resource.
DevKit version is not proof of the installed shipped client's exact UE version.

These are **historical observations**, not claims about today's latest releases
or the user's current installations. Re-read the exact executable hashes/builds,
loader files and actual logs, and verify current official support before selecting
a runtime. Preserve any later user-installed working setup.

UE4SS must actually expose the required `LoopInGameThreadWithDelay` and reflected
objects in this ARK client. A development documentation page or a present DLL does
not prove it loaded. The current adapter expects a local standalone session.
The GTA ASI built without `GAL_WITH_SHV` has only a no-op `DllMain`; installation
would not create a native camera or creature API. Notifications alone are not a
reader acknowledgement.

`RageOpenV` was recorded as an uninstalled asset-loader candidate in the main
requirements snapshot, not as a verified native scripting or asset-conversion
solution. The isolated archive's older requirements snapshot may omit it. Resolve
the dated snapshots explicitly; do not replace a native-action API with an asset
loader. Earlier suggestions about Script Hook RDR2 as a GTA solution and a fixed
3–7-day update ETA had no verified support and must not be reused as facts.

The read-only `runtime_workflow.py inspect` reports versions/hashes/loaders;
successful inspection is not runtime readiness. `package --stage` creates an
`installable:false` source package of the camera-link Lua files, not a creature
installer. Review exact install/removal manifests and saved-game backups under
the user's existing authorization. Use GTA Story Mode and ARK single player;
do not repurpose this work for online sessions or patch version checks to claim
compatibility.

## Ordered continuation and playable acceptance

1. Verify the saved GREEN copy and promote reviewed changes into the intended
   source tree. Repair the current native-session/completion record separately;
   its old process ended, and no successful final marker was recorded. Do not
   replay the already-applied repair or reset its watchdog journal.
2. Implement/test the generic policy-to-controller-to-adapter boundary. Preserve
   existing protocol fixtures and tests. Make unsupported native operations
   explicit; a simulator is a deliberate test mode.
3. Inventory the real current game setup and reconcile the creator's earlier
   working report. Verify one supported native route and one controlled actor
   spawn/action in the selected host before broad asset work.
4. For the cougar/Raptor slice, show one actor acquiring an eligible NPC/cop/player,
   issuing movement/attack to the actor rather than the target, rejecting vehicle
   entities, disengaging, and respecting cooldown/loss. Record logs/capture and
   exact loader/build/source hashes. A cougar placeholder must be labelled.
5. Verify compatible Raptor asset/rig/animation/collision integration before
   describing it as an ARK creature working in GTA. Expand species only after that.
6. Implement shop, tranqs, taming and saddles as separately tested gameplay slices.
   Define tuning, ownership, persistence and UI explicitly with the creator's intent.
7. Pursue M1 live camera calibration and M2 rendering/compositing as separately
   evidenced milestones. A camera-follow demo is not a completed visual mashup;
   a local Raptor demo is not proof of two-engine rendering.

Useful project guidance: `smelter-debugging`, `gameplay-testing`, `game-modding`,
`mod-validation`, relevant ECC testing/review skills and `diagrams`. Confirm what
is actually loaded in the chosen OpenCode agent; installed does not mean used.
REA/Ghidra is for concrete native/API or binary evidence gaps, not a substitute
for reading ordinary Lua source. No additional tool is needed for the current
offline controller slice. Any future asset/runtime tool needs a real capability
gap, CLI interface, verified provenance, declared requirements and documentation.

Relationship chart: [GTA–ARK mashup map](../diagrams/gta-ark-mashup.mmd).
Broader reusable boundary: [universal gameplay contract](../UNIVERSAL_GAMEPLAY_CONTRACT.md).
