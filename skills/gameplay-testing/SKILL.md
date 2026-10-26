---
name: gameplay-testing
description: Implement and test game AI/controller state transitions through real production modules and a simulated engine boundary, including targeting, chase, attacks, cooldown and target loss.
---
# Test gameplay logic behind an adapter

Record the intended host game/build and current slice. Define inputs, observable outputs, state transitions, units and timing before implementing. Keep the controller independent of engine globals; pass a narrow adapter and controllable clock. Fake engine queries/actions, not the controller itself.

Import and execute the real implementation in tests. Check normal transitions and relevant boundaries: no target, invalid/dead target, range/visibility changes, target loss, attack cooldown, repeated updates and adapter errors. Use explicit assertions that fail the process. Distances and times need independent expected values rather than duplicated implementation formulas.

For an aggression controller, verify the actor receiving movement/attack commands is the creature, targeting uses the intended NPC population, cooldown cannot be bypassed and disengagement clears the target. Add tame/unconscious/owner exclusions only when that behavior is in the current task. Preserve requested species and host; a cougar placeholder proves only its demonstrated behavior.

Lua tests run from the mod directory: adjust `package.path` to the canonical module folder before requiring it, or execute the chunk returned by `loadfile`. Keep one authoritative implementation and trace its import path. Do not silently skip missing modules or accept their exported names as behavior proof.

Report offline controller evidence separately from native build, loader compatibility, game launch and visible in-game behavior. A passing simulation does not establish an engine API or working Raptor asset/animation integration.
