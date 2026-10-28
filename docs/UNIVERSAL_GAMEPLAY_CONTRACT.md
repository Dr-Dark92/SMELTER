# Universal gameplay logic and adapter contracts

**2026-10-28 update:** The isolated generic policy now passes all 30 frozen
checks, with saved Lua and Python profiles GREEN on the same tree. The earlier
review checkpoint below is historical. Full controller integration, adapter
conformance and in-game behavior are still separate unverified stages. See
[the current game handover](handovers/GTA_ARK_MASHUP_HANDOVER_20261028.md).

Status: implementation specification, 27 October 2026. This is a new contract to
implement and verify, not a description of exports already present in a game mod.
The Raptor prototype is its first acceptance scenario. SMELTER remains a universal
modding workbench; project-specific engine integration belongs in project adapters.

Reviewed implementation checkpoint: a pure `entity_policy.lua` helper now exists
in the owned Raptor coding copy. Its twenty-six checks pass, and the seven prior
operator regression checks now pass unchanged. Two test-local normalizers call
the shared evaluator for one positive case. Six explicit-contract checks still
fail: empty/all-disabled any-maps are accepted, complete entity/optional-map
validation is missing, and any-map validation can short-circuit before a bad
entry. One required rejection assertion was changed to acceptance. Full adapter
conformance, opposite policy outcomes and controller integration remain pending.
See the latest
[forensic review](../diagnostics/RAPTOR_FORENSIC_REVIEW_20261027.md); the broader
controller and adapter contract below is still proposed.

## Ownership and boundaries

SMELTER supplies coding/analysis tools, file identity, requirements, task evidence
and skills. Shared gameplay modules supply reusable state transitions and policy
evaluation. Engine adapters translate native objects, coordinates and actions.
Game profiles supply asset identifiers, tuning and scenario rules. A game-specific
fix may be necessary inside its adapter, with shared invariants tested at the
boundary. Do not hide a native API call behind an engine-neutral filename and
claim that makes it portable.

The operator maintains these contracts and reviews evidence. SMELTER/Qwen authors
the gameplay implementation in the existing owned coding workspace. Do not submit
a native prompt on the user's behalf or move a task into a new copy to bypass
failed tests.

## Proposed shared boundary

The logical operations below are language-neutral. Their concrete names and
signatures must be proposed against the inspected implementation, then applied
consistently to callers and tests. They are not existing `engine_adapter.lua` APIs.

| Responsibility | Shared contract | Adapter or project responsibility |
|---|---|---|
| Identity | Opaque entity ID, separate actor and target IDs | Native handles and lifetime checks |
| Classification | `kind` and normalized trait tags, separate from display name | Class/type inspection and mapping |
| Geometry | Finite `{x,y,z}` positions in metres in a documented common frame | Native vectors, axes and scale conversion |
| Time | Injected monotonic seconds | Engine scheduling and clock implementation |
| Discovery | Query returns actual normalized entities | Native entity enumeration/visibility queries |
| Movement | Request an actor move toward a target/position | Native navigation, game-thread calls |
| Attack | Request an actor attack a valid target | Engine attack/action implementation |
| Spawn | Optional capability with a verified returned entity ID | Loader, asset and spawn APIs |
| Capability | Explicit supported/unsupported state per operation | Build/runtime probing and evidence |
| Result | Success, unsupported or failure with a stable code | Native result validation and diagnostic detail |

Success means the adapter performed or admitted the defined operation and can
provide its specified evidence. A no-op placeholder cannot report success.
Unsupported native mode must remain unsupported; switching to a simulator is an
explicit task decision, not a silent fallback.

The reference logic can use the existing Lua runner. The contract must not assume
every game loads that Lua version or even uses Lua. An engine-specific runtime
bridge, or an equivalent implementation in its supported language, may be needed.

## Shared controller behavior

- Keep controller state per instance/entity. Do not fabricate targets in the
  controller or use native engine globals there.
- Inject entity queries/actions, clock and policy. Avoid direct wall-clock reads
  so cooldown and timeouts can be tested without sleeping.
- Validate IDs, finite positions, alive/valid state, configured ranges and target
  eligibility before mutating state or issuing actions.
- Record the actor receiving movement/attack commands independently from its
  target. Distinguish an admitted request from completed game behavior.
- Define IDLE, CHASING, ATTACKING and disengagement transitions, repeated updates,
  cooldown boundaries and target loss. Preserve useful failure evidence.
- Treat species, game name, installation path, asset ID and role lists as profile
  data. Shared code must not branch on GTA, ARK or a particular creature name.

For the current Raptor scenario, the profile permits human NPCs, cops and the
player and excludes vehicle entities. Test normalized type/traits; never infer
eligibility from names such as `Pawn_...` or `Vehicle_...`. No extra rule excluding
human vehicle occupants was requested.

## Portability acceptance

Execute the same real production controller tests through two explicit fake
adapters with different native-shaped fixtures. One can expose uppercase
centimetre vectors and another a different axis/scale representation; those are
test fixtures, not claims that a real game has been integrated. Normalize both
to the common contract and assert independently chosen positions/distances.

Verify actor/target identity, classification, query results, movement, attack,
cooldown, target loss, invalid/dead targets, unsupported capabilities and adapter
errors. Failed admission must not leave half-created state. Use one assertion
mechanism and a nonzero process exit for every failed assertion. Assert returned
results and resulting actions/state; `pcall` success only proves no exception.

Preserve existing regression fixtures and import the real controller. Do not
mock it, remove a failure, weaken an assertion, or return fabricated success to
obtain GREEN. A disposable fault-injection fixture should demonstrate that
vehicle acceptance and wrong-actor movement are detected.

A passing fake adapter proves the shared boundary and controller behavior only.
Keep native adapter conformance, loader/build compatibility, spawning, assets,
animations and visible in-game behavior as separate evidence stages.

## Tools and skills

The current slice needs no additional external package: the installed coding MCP,
file index, checked proposals, confined Lua/Python/C++ runners and progress monitor
are sufficient. Use `smelter-debugging`, `gameplay-testing` and the relevant ECC
TDD/test-review guidance in small phases. The `diagrams` skill maintains the
relationship handoff. Existing REA/Ghidra is relevant when a native adapter needs
unknown binary/API evidence, not as a remedy for ordinary Lua test defects.

The useful skill enhancement is adapter-contract/conformance guidance attached
to the existing gameplay workflow. Prove this contract before installing another
skill bundle. Any subsequently required tool must have a concrete adapter gap,
CLI interface, verified provenance, declared requirements and installation docs.

See the [SMELTER task brief](tasks/RAPTOR_GENERIC_TASK_BRIEF.md) and
[proposed boundary chart](diagrams/universal-gameplay.mmd).
