# Raptor Aggro System - Cougar Behavior Prototype

## Overview
This module implements the first Raptor aggression prototype for GTA V Enhanced × ARK mashup. It uses simpl ified cougar behavior rules as a baseline placeholder until actual ARK AI data is available.

**⚠️ PLACEHOLDER STATUS:** Current implementation uses simplified canine movement and attack patterns. Real dino behaviors (jump attacks, pack hunting, specific prey detection) require ARK game data integration.

## Files Added

| File | Purpose |
|------|---------|
| `raptor_aggro.lua` | Core aggression logic (detection, chase, attack, cooldown) |
| `engine_adapter.lua` | Replaceable interface for simulation/real_game modes |
| `raptor_system_main.lua` | Main loop integrating all components |
| `raptor_config.json` | Tweakable configuration parameters |

## Key Features

### Target Detection (`detect_targets`)
- Scans for NPCs and entities within detection range (default 500 cm)
- Prioritizes human NPCs over other targets
- Returns sorted list by priority/dist ance

### Chase Logic (`start_chase`, `update_chase`)
- Moves raptor toward active target using smoothed turning
- Implements disengagement when target moves beyond threshold
- Tracks chase duration for timeout behavior

### Attack System (`attempt_attack`)
- Bite attacks at melee range (default 300 cm)
- Configurable damage per hit (default 25)
- Cooldown management between attacks

### State Management
- Idle state: periodic target scanning (~every 2 seconds)
- Chase state: continuous pursuit with distance checks
- Attack state: brief animation followed by cooldown

## Testing Guide

### Simulation Mode (Offline Testing)
1. Run `test_raptor_simulation.lua` to generate test targets at various distances
2. Observe spawn logs: `[RaptorAggro] [SIMULATION] Spawned test instance X`
3. Verify detection thresholds with mock NPCs

### Real ARK Mode (Game Integration)
1. Ensure UE4SS is installed and `LoopInGameThreadWithDelay` API available
2. Launch ARK with GtaArkLink mod enabled
3. Observe logs for `[RaptorAggro] ADAPTER: Real ARK mode active`

## Configuration Parameters

Edit `raptor_config.json` to adjust:
- `detection_range_cm`: Initial target scan distance
- `chase_range_cm`: Maximum pursuit distance before giving up
- `melee_attack_range_cm`: Attack range threshold
- `attack_damage`: Damage per bite hit
- `cooldown_sec`: Time between attacks

## Remaining Runtime Blockers

1. **UE4SS API Compatibility**: Requires ARK game version to support LoopInGameThreadWithDelay with delayed action execution
2. **Dino AI Data**: Real Velociraptor attack patterns (jumps, claws) not implemented - uses generic cougar proxy
3. **Game Reflection**: Finding and tracking actual ArkCharacter_Raptor_C instances needs ARK modding SDK integration

## Next Steps for Live Integration

1. Test with UE4SS v3.0+ installed to verify timer API compatibility
2. Use Unreal Editor to extract Raptor class methods (GetDefaultObject, attack functions)
3. Replace `spawn_actual_raptor()` placeholder with actual ARK dino spawning code
4. Implement pack hunting logic once single-target behavior verified

## License Note
This prototype is part of the GTA V Enhanced × ARK mashup project. Redistribution requires permission from project authors and inclusion of this documentation.
