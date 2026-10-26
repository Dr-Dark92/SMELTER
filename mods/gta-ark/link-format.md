# GTA → ARK link record (`GAL1`)

Single source of truth for the M1 link. `gta/src/link_record.h`, `tools/gal_link.py`
and `ark/Mods/GtaArkLink/Scripts/gal_link.lua` implement exactly this. Tests check
that all of them agree.

File: `%LOCALAPPDATA%\SMELTER\gta-ark-link\camera.bin`, 64 bytes, rewritten in place
(never truncated or renamed). All values little-endian.

| Offset | Type | Field |
| --- | --- | --- |
| 0 | char[4] | magic `GAL1` |
| 4 | u32 | sequence: odd while writing, even when complete |
| 8 | f32×3 | camera position, GTA metres (x east, y north, z up) |
| 20 | f32×3 | camera rotation, degrees, GTA order 2: x pitch, y roll, z yaw |
| 32 | f32 | vertical field of view, degrees |
| 36 | f32×3 | player position, metres |
| 48 | f32 | player heading, degrees |
| 52 | u32 | flags: bit 0 Story Mode active, bit 1 link enabled |
| 56 | u64 | GTA frame counter |

## Writer (seqlock)

1. Write `sequence + 1` (odd) at offset 4.
2. Write offsets 8–63.
3. Write `sequence + 2` (even) at offset 4.

## Reader

Read all 64 bytes twice. Accept only if the magic matches, the sequence is even, and
both reads are identical. Otherwise skip this tick. A record whose sequence hasn't
changed for the stale limit (about 1 s at 33 ms ticks) means GTA stopped writing:
ARK stops further view mutations and clears the link origin. It does not restore
the previous physical pawn pose. All floating-point fields must be finite, with
FOV strictly between 0 and 180 degrees. The engine adapter requires both flags.

## GTA → Unreal mapping (relative to the link-start origin)

- GTA: right-handed, Z up, metres; X east, Y north. Yaw 0 faces north and increases
  counter-clockwise.
- Unreal: left-handed, Z up, centimetres; X forward, Y right. Yaw increases clockwise.
- Position delta: `ue = (100·dy, 100·dx, 100·dz)`, where `d = gta − gta_at_link_start`;
  added to ARK's pawn location at link start, retaining its existing camera offset.
- Rotation: `ue_pitch = gta_pitch`, `ue_yaw = ue_yaw_at_start − (gta_yaw − gta_yaw_at_start)`,
  `ue_roll = −gta_roll`.

The signs are unverified in the running games. Shared test vectors live in
`tests/vectors.json`. The in-game calibration test is in
`docs/discovery/GTA_ARK_M1_DESIGN.md`.
