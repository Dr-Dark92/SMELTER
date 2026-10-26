# Cougar-based Raptor aggression prototype

Status: proposed design, 26 October 2026. No gameplay code, assets or loaders
were installed or run. The creator suggested using the cougar attack as the
aggro trigger. GTA Story Mode remains the intended host.

## Current target policy

The creator's latest requirement is to make human NPCs, cops and the player
eligible targets, while excluding vehicle entities. Classification must be
explicit at the adapter boundary: a vehicle with a valid position method is
still ineligible. Include each human category and a vehicle in offline fixtures;
selection and direct chase initiation must reject a vehicle. This requirement
does not add a separate rule about human occupants of vehicles.

The immediate behavior task remains offline in workspace
`897b9243-fd7e-42f4-a46a-d1b814a33a81`. Its new test currently fails in setup:
`init_simulation()` sets adapter mode and returns nothing. The actual API is
`engine_adapter.simulate_targets(position)`, which returns an array of records
with `.pawn`. Calls use dot syntax. Access controller state through its existing
`raptor_states[id]` map. There is no existing set_clock, get_state or init_raptor
API. Keep assertions on actual fields (`chase_start_time`, `last_attack_time`)
and do not add invented interfaces just to make the mistaken test run. Once
setup is corrected, the previously reproduced double-GetActorLocation defect
is a real behavioral RED; engine callbacks are not required to reproduce it.

## Work ownership and next SMELTER brief

The creator wants SMELTER (Qwen through Melty/OpenCode) to implement the mod,
including scripting where needed. The operator and Codex provide guidelines,
review changed files/test receipts and maintain SMELTER's infrastructure. This
document records design guidance; it is not a gameplay implementation. Preserve
the current operator-driven Melty testing flow unless they explicitly delegate
prompt submission.

Suggested next brief for SMELTER:

> Implement the first bounded Raptor aggression prototype in the existing
> isolated workspace, keeping GTA Story Mode as the host. Use GTA cougar behavior
> as the baseline. Use scripting/native code where needed for controlled spawning,
> nearby human-NPC target selection, chase, attack and disengagement. A cougar
> placeholder may prove behavior while Raptor rigging is unresolved; label it
> clearly and do not claim ARK integration from the placeholder. First establish
> what the installed GTA runtime actually supports. If live integration is
> blocked, implement the runtime-independent aggro controller behind an adapter
> and test its range/visibility, target-loss and cooldown behavior offline. Use
> the supported language/toolchain for the selected GTA route. Record every new
> tool in requirements and documentation. Return changed files, actual test/build
> receipts and remaining unverified game behavior.

The initial slice excludes the remaining dinosaurs and shop/taming expansion;
they follow a reviewed first implementation. CLI-based tools remain required.

## First playable experiment

Use GTA's existing mountain lion (`a_c_mtlion`) as the behavior baseline for the
first Raptor. First establish ordinary cougar pursuit/attack in the target GTA
build; then test a Raptor appearance with compatible rigging, attack animations
and collision. Assigning a relationship group alone does not provide those
assets or prove that an arbitrary dinosaur model can execute cougar attacks.

Separate the aggro trigger from the attack executor:

- Trigger: a valid target enters the configured detection range/visibility, or
  the creature takes damage. Retain/lose targets with a cooldown and hysteresis
  rather than issuing a combat task every frame.
- Executor: reuse compatible GTA animal pursuit/attack behavior. Cfx documents
  `TASK_COMBAT_PED` for directing a ped at a target and per-ped relationship-group
  assignment. These references do not verify those calls in Enhanced 1.0.1158.16.
- Later gameplay: tranquilization clears combat; unconscious creatures cannot
  aggro; a tamed creature excludes its owner from hostile targets. Species-specific
  movement and attacks remain separate work for Rex, Carno, Trike, Stego and PT.

Prefer a mod-owned relationship group for scripted creatures. Do not globally
change the behavior of every vanilla cougar just to control the prototype.

## Two candidate implementation routes

1. **Asset replacement first:** retain the original cougar archetype/AI while
   supplying a compatible Raptor appearance. This is a possible way to demonstrate
   inherited aggression without custom Script Hook V combat code. It still needs
   a verified Enhanced asset-loading route and a compatible rig/animation pipeline.
   Natural cougar spawning/target selection also does not prove controllable city
   spawns or hostility toward every desired NPC. This is a hypothesis to test.
2. **Scripted creature controller:** own the detection/targeting state machine,
   spawning and attack tasks through a verified GTA native-access adapter. This
   remains subject to the Script Hook V compatibility gate or a separately
   verified alternative. Asset loaders do not supply that native scripting API.

`RageOpenV` is an uninstalled, source-identified asset-loader candidate; its README
advertises both Legacy and Enhanced support and ASI-loader integration. Exact
1.0.1158.16 compatibility has not been established. It is recorded as a candidate
in `runtime_requirements.json`, not selected by the existing camera-link preflight.
Its source build is CLI-driven (CMake/MSVC); no build or asset-conversion CLI was
validated here. Sollumz documents Enhanced asset conversion through CodeWalker,
but its GUI tutorial is not an implemented headless SMELTER conversion adapter.

Tranqs, taming, saddles and shop inventory need additional gameplay work. The
existing GAL1 camera-link experiment does not implement these features. A
cougar-only placeholder is not proof that ARK content is integrated.

## Corrections to the preceding model research

- Script Hook RDR2 is documented for RDR2 natives, not a verified GTA V runtime.
- No source establishes the proposed 3–7-day Script Hook V update ETA.
- An unlisted game build is outside the author's listed support; a refusal was
  not tested here because the runtime was not installed/launched.
- ARK single-player is not GTA Story Mode. Keep the intended host in GTA.
- Modifying a version check would not establish binary/API compatibility.

## Evidence before adoption

Require exact-build loader and Enhanced asset-format evidence, an AI-usable CLI
asset workflow, visible pursuit/attack against the intended target, matching
attack animations/hit detection, and reversible package manifests before treating
this route as ready. Offline state-machine tests can validate target selection,
cooldowns and the tame/unconscious transitions while runtime access is unresolved.
No tool was installed during this design pass.

Sources:
[Cfx ped models](https://docs.fivem.net/docs/game-references/ped-models/),
[combat task](https://github.com/citizenfx/natives/blob/master/TASK/TaskCombatPed.md),
[per-ped relationship group](https://github.com/citizenfx/natives/blob/master/PED/SetPedRelationshipGroupHash.md),
[RageOpenV source](https://github.com/Chiheb-Bacha/RageOpenV/tree/f742117a5e8ccc359bf3b4644c6bce7dad77cc7a),
[Enhanced conversion guide](https://github.com/PlebMasters/sollumz-wiki/blob/main/tutorials/asset-conversion-for-gtav-enhanced.md),
[Script Hook V author](https://www.dev-c.com/gtav/scripthookv/),
[Script Hook RDR2 author](https://www.dev-c.com/rdr2/scripthookrdr2/).
