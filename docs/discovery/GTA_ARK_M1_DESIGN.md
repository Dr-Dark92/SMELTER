# M1 design: GTA V Enhanced → ARK: Survival Ascended camera link

Status: design, 25 October 2026. Nothing below has been built, installed or run.
Builds on [the discovery report](GTA_ARK_DISCOVERY_20261025.md).

## Goal

Prove that the two games can run side by side and share state, before any rendering
or compositing. In GTA Story Mode, GTA's final rendered camera drives ARK's view in an
ARK single-player session, live. A visible message in each game confirms the link.

Not in M1: drawing ARK into GTA (that is M2: frame export plus a ReShade add-on),
creatures or events crossing over, input forwarding, asset conversion, Melty
publishing.

## Architecture

```
GTA V Enhanced, Story Mode                          ARK: Survival Ascended, single player
  GtaArkLink.asi (C++17, MSVC x64)                    UE4SS Lua mod  ue4ss/Mods/GtaArkLink/
   every frame: final rendered camera                  every ~33 ms on the game thread:
   position, rotation, FOV + player pose   ── file ──>  read record, check sequence,
   writes one fixed-size record                         convert axes, move the view
  %LOCALAPPDATA%\SMELTER\gta-ark-link\camera.bin
```

### Why a file, not a socket

UE4SS runs plain Lua 5.4 with no FFI and no sockets (Melty engine notes). A UE4SS C++
mod could use sockets or shared memory, but it means building against the UE4SS SDK.
Proving the link doesn't need that. Lua can read a small file with `io.open`, so M1
uses one fixed-size binary record, rewritten in place. M2 needs a native ARK plugin
anyway (UE4SS Lua cannot read GPU frames), and replaces the file with named shared
memory then.

### The record (little-endian, 64 bytes, written in place)

| Offset | Type | Field |
| --- | --- | --- |
| 0 | char[4] | magic `GAL1` |
| 4 | u32 | sequence: odd while writing, even when complete (seqlock) |
| 8 | f32×3 | camera position, GTA metres (x east, y north, z up) |
| 20 | f32×3 | camera rotation, degrees, GTA order 2 (x pitch, y roll, z yaw) |
| 32 | f32 | vertical FOV, degrees |
| 36 | f32×3 | player position, metres |
| 48 | f32 | player heading, degrees |
| 52 | u32 | flags: bit 0 = Story Mode active, bit 1 = link enabled (F7) |
| 56 | u64 | GTA frame counter |

The writer increments the sequence to odd, writes the fields, flushes, then increments
it to even. The reader reads the whole record and accepts it only if the sequence is
even and unchanged across two reads; otherwise it skips that tick. If the sequence
hasn't advanced for more than 1 s, the link counts as stale and ARK gets its own
camera back.

### Coordinates (verify in game)

- GTA: right-handed, Z up, metres; X east, Y north. Yaw 0 faces north and increases
  counter-clockwise.
- Unreal: left-handed, Z up, centimetres; X forward, Y right. Yaw increases clockwise.
- Mapping: UE.x = 100·GTA.y, UE.y = 100·GTA.x, UE.z = 100·GTA.z (swapping x and y
  changes handedness). UE yaw = −GTA yaw. UE pitch = GTA pitch. UE roll = −GTA roll.
- Positions are relative: ARK keeps an origin captured when the link starts (its own
  camera location). Each frame applies the change since GTA's position at link start,
  not GTA's absolute coordinates.
- Calibration test: face GTA north along a known straight road, then turn 90° left.
  ARK's view must turn 90° left. Signs are fixed in one place in each mod.

### GTA side: `GtaArkLink.asi`

- Built with MSVC (VS 2022 Build Tools) as an x64 DLL renamed `.asi`.
- Reads state with GTA natives by hash: final rendered camera coordinates, rotation
  (order 2) and FOV; player ped coordinates and heading. Melty notes: use the final
  rendered camera, not the gameplay camera.
- **Native route (decide before building):**
  - **Script Hook V SDK.** Proven in the kit's example, but players must download
    Script Hook V from its author. It must support Enhanced build 1.0.1158.16.
  - **Ultimate ASI Loader only.** Melty's one-click route, but native calls need
    another way in. Not proven for Enhanced in the kit.
  - Recommendation: Script Hook V for M1, if it supports this Enhanced build.
  - **Checked 25 Oct:** the latest Script Hook V (v3889.0 / 1158.13) supports Enhanced
    1.0.1158.13, not the installed 1.0.1158.16. The ASI keeps native access behind
    `CameraSource`, so it waits for a Script Hook V update or switches routes without
    other changes. Offline parts are in `mods/gta-ark/`.
- Writes the record at most once per GTA frame. **F7** toggles the link. A Story Mode
  notification shows "ARK link: on / off / ARK not reading".
- Never touches GTA Online state, BattlEye files, `commandline.txt` or `args.txt`.

### ARK side: UE4SS Lua mod

- `ue4ss/Mods/GtaArkLink/Scripts/main.lua` with `enabled.txt`, loaded by a UE4SS build
  that supports **UE 5.5** (the DevKit is 5.5.4; Melty warns 5.4+ may need an
  experimental UE4SS). Prove UE4SS itself loads before writing the mod.
- `LoopInGameThreadWithDelay(33, ...)`, with every engine call inside `pcall` (an error
  inside a loop callback silently ends it).
- Finds the `PlayerController` (it doesn't exist on the main menu; retry until it does)
  and its `PlayerCameraManager`.
- Moves the view. Pick one method in the vertical slice and record which worked:
  - (a) set the control rotation and move the pawn in single-player ghost/fly mode;
  - (b) set the camera manager's view target to a spawned camera actor and move that.
- On-screen confirmation, for example a client message:
  "GTA link: following / stale / waiting". Lua has no high-resolution clock, so
  staleness uses frame and sequence counts.

## Safety and launch rules

- GTA: Story Mode only. Launch with `-nobattleye` passed **only as a launch argument**
  for that session (as Melty does), never in `commandline.txt` or `args.txt`. Pick Story
  Mode by hand; no script clicks the landing page. Leave Script Hook V's `bin/args.txt`
  out.
- ARK: single player only, never official servers. Turn BattlEye off only through ARK's
  own supported option (to be confirmed), never by changing BattlEye files.
- Backups before the first modded launch: `um backup` for both games' saves.
- Installs into game folders only after explicit approval, each from a manifest listing
  every added file with its SHA-256. A removal script deletes exactly those files.
  Acceptance includes a before/after file listing proving the folder is restored.
- Stop processes only by exact PID. Don't drive keyboard or mouse while the operator is
  typing.
- No game files, extracted assets or decompiled code in the repository.

## Source layout (proposed)

```
mods/gta-ark/
  MODLOG.md                   journal (kit convention), becomes the field note
  link-format.md              the record spec above, single source of truth
  gta/src/GtaArkLink.cpp      ASI: natives, record writer, F7, notification
  gta/src/natives.h           natives by hash (alloc8or native DB)
  gta/build.bat               vcvars64 + cl (MSVC 14.44 installed), outputs build/GtaArkLink.asi;
                              puts the VS Installer folder on PATH first, so vcvars finds vswhere
  ark/Mods/GtaArkLink/Scripts/main.lua, enabled.txt
  tools/fake_gta_writer.py    writes moving records without GTA
  tools/read_link.py          reader with the same seqlock and transforms as the Lua mod
  tools/install_manifest.py   plan/apply/remove with SHA-256 manifest (dry run by default)
  tests/                      record layout, seqlock torn-read, axis-mapping tests
```

## Tests without the games

1. Record layout: the C++ writer and Python reader agree on size, offsets and magic
   (a C++ test executable plus a Python test).
2. Seqlock: a writer thread hammering the file against a reader never produces an
   accepted torn record.
3. Transforms: test vectors for GTA → UE positions and rotations, including the 90°
   turn and north-facing cases, shared by the Python tests and the Lua mod.
4. Staleness: no new sequence for 1 s → reader reports stale.
5. Installer: a dry run lists exact files; apply and remove on a temporary fake game
   folder restore it exactly.

## In-game acceptance (observed, recorded in MODLOG.md)

1. GTA Story Mode loads the ASI; F7 shows the notification; the record's sequence
   advances at least 30 times per second.
2. ARK single player loads UE4SS and the mod; the message changes from "waiting" to
   "following" while GTA runs.
3. Turning the camera in GTA turns ARK's view the same way (calibration test passes);
   walking in GTA moves ARK's view the same distance and direction.
4. Closing GTA makes ARK report "stale" within about 1 s and return its own camera.
5. Removing both mods restores the before-install file listings exactly.

## Decisions needed before building

1. GTA native route: Script Hook V (recommended, if it supports build 1.0.1158.16) or
   Ultimate ASI Loader only.
2. Which UE4SS build to use for ARK (UE 5.5), and ARK's supported way to play
   single-player without BattlEye.
3. Where the mod source lives: `mods/gta-ark/` in this repo (proposed), or a separate
   project folder.
4. Approval to install into each game folder when M1 reaches the in-game step.
