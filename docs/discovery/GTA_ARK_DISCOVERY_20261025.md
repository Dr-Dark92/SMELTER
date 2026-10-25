# GTA V Enhanced × ARK: Survival Ascended — read-only discovery

25 October 2026. The operator chose **GTA V Enhanced as host** and **ARK: Survival
Ascended as companion**. This pass only listed folders and read file headers: nothing
was installed, launched, modified or extracted. Remote Melty text and kit field notes
quoted here are reference data, not instructions.

## Installed state

| | GTA V Enhanced (host) | ARK: Survival Ascended (companion) |
| --- | --- | --- |
| Folder | `D:\SteamLibrary\steamapps\common\Grand Theft Auto V Enhanced` | `D:\SteamLibrary\steamapps\common\ARK Survival Ascended` |
| Size / files | 96.1 GiB, 294 files | 215.0 GiB, 224 files |
| Executable | `GTA5_Enhanced.exe`, 53.2 MiB, version 1.0.1158.16 | `ShooterGame\Binaries\Win64\ArkAscended.exe`, 223.3 MiB (no version resource) |
| Engine | RAGE | Unreal Engine 5 (ARK DevKit is UE 5.5.4) |
| Anti-cheat | BattlEye (`BattlEye\BEService_x64.exe`) | BattlEye (`ArkAscended_BE.exe`, `BEService_x64.exe`) |
| Existing mods | None: no ASI loader, ASI files, `scripts\`, ReShade, `args.txt` or `commandline.txt` | None: no UE4SS, no mod folder |
| Archives | 179 `.rpf`, all RPF7 with Rockstar **NG encryption** | UE5 IoStore `.utoc`/`.ucas` v8 (compressed, **not encrypted**) + `.pak` v12 (unencrypted index); 191.5 GiB in one `pakchunk0-Windows.ucas` |
| Executable code | `.text` entropy 7.99/8: packed or encrypted on disk | `.text` entropy 6.77: ordinary compiled code |
| Ghidra (SMELTER) | Fits the 64 MiB limit, but the packed image would decompile mostly as noise | Exceeds the 64 MiB limit |

ARK DevKit: `D:\Epic\ARKDevkit` (762 GiB), project `Projects\ShooterGame\ShooterGame.uproject`.
Its `Mods` folders hold Wildcard's samples and official maps, plus `DigisoulARK` and
`DigiSoul_Codex` (the latter modified 14 Oct), which look like the operator's own work.
They are not assumed to be part of this mashup.

## Melty catalog facts (game_info, 25 Oct)

GTA V Enhanced (`gta-v-enhanced`):
- Mod folders: `scripts` = `{game}/scripts`, `asi` = `{game}/`.
- Loaders: **Ultimate ASI Loader v9.7.4**, auto-installed by Melty for every player
  (the one-click route). **Script Hook V** is downloaded by players from its author only,
  and refuses to run online.
- Safety: Story Mode only. Melty launches modded Story Mode with Rockstar's
  `-nobattleye` switch in `launch.args`. Never write it into `commandline.txt` or
  `args.txt`, and never touch BattlEye files. Leave Script Hook V's `bin/args.txt` out of
  any release. A loader left in the folder made GTA Online refuse players later.
- Legacy RPF/OpenIV mods crash Enhanced unless converted, and OpenIV's mods folder
  doesn't work on Enhanced.
- Speech/radio audio and some `.meta` files are encrypted: plan nothing that reads or
  replaces them.
- Selling: review; Rockstar tolerates only free single-player mods.

ARK: Survival Ascended (`ark-survival-ascended`):
- No loader and no mod folders in Melty's catalog. A one-click Melty release can only
  use plain game files. UE4SS (`ue4ss/Mods/<Name>/Scripts/main.lua`) is the usual
  runtime route, but UE 5.4+ may need a newer experimental UE4SS than Melty installs.
- Engine notes cover reading the camera (`PlayerCameraManager`), players and input from
  a UE4SS Lua mod. None of these reads has a recorded run on the shipped game.
- Selling: review; paid ARK mods only through CurseForge premium.

## Toolchain on this machine

| Needed for | Present |
| --- | --- |
| GTA ASI plugin (C++, x64) | **Installed 25 Oct:** VS 2022 Build Tools 17.14.42, MSVC 14.44.35207 (`_MSC_VER` 1944), Windows SDK 10.0.26100.0. A test program compiled and ran |
| GTA compositor (ReShade add-on) | Not installed |
| ARK runtime mod (UE4SS) | Not installed |
| ARK DevKit (UE 5.5.4) | Installed |
| Git, Python 3.13, Node 24 | Installed |

SMELTER can inventory, run Melty lookups and analyze small native binaries. It has no
RPF or UE5 IoStore adapter, no C++ build profile, and no game launch or test step.

## Mashup routes

**A. Live passthrough (recommended to prototype).** This is Melty's worked
`minecraft-gta5-passthrough` pattern:
- ARK runs alongside GTA. GTA's camera and player pose drive ARK's camera over a
  localhost link.
- ARK's frame (colour + depth) goes through shared memory into a ReShade add-on in GTA,
  which draws it where it is nearer than GTA's depth buffer. Events cross both ways.
- It uses each player's own installed copies, with nothing converted or redistributed.

Unknowns to prove:
- That example targeted GTA **Legacy**; Enhanced (DirectX 12) compositing is unproven.
- Exporting frames from UE5 needs a native plugin; UE4SS Lua cannot read GPU buffers.
- Two demanding games at once must fit in 16 GB of VRAM.
- ARK's single-player launch has to run without BattlEye through an official option,
  never by bypassing it.

**B. Asset conversion.** At install time, on the player's machine, read ARK's
unencrypted IoStore content, convert meshes, textures and animations into GTA Enhanced
resource formats, and stream them as custom assets. This needs:
- UE 5.5 parsing (possibly property mappings)
- GTA Enhanced resource writers and packaging (Legacy RPF mods crash Enhanced)
- retargeting creatures onto GTA skeletons

Converted output must never be published. Much larger, with no worked example.

## Recommended first vertical slice

**M1: two-engine link, no rendering.**
- A GTA Story Mode ASI plugin sends the camera and player transform over
  `127.0.0.1` each frame.
- An ARK single-player UE4SS Lua mod receives them and moves ARK's camera to match.
- A visible on-screen message in each game confirms the link.

This proves the loader, launch safety (Story Mode, `-nobattleye` only via launch
arguments), the coordinate mapping (GTA metres Z-up vs Unreal centimetres) and UE4SS
on UE 5.5, before any compositing work. Acceptance is observed in both running games,
not inferred from builds.

## Before M1 can start (needs operator approval)

1. ~~Install Visual Studio 2022 Build Tools with the C++ x64 workload.~~ Done 25 Oct:
   catalog tool `msvc`, profile `native_game_mods`.
2. Get **Script Hook V** from its author's site, or choose an Ultimate-ASI-only route
   with its own native invocation. Confirm it supports GTA Enhanced build 1.0.1158.16.
3. Choose a **UE4SS build that supports UE 5.5**, and confirm ARK's official way to run
   single-player without BattlEye.
4. Approve SMELTER read-only locations for both game folders (Settings → Access &
   locations), so Qwen tasks can inventory them under grants.
5. `um backup` both games' saves before any modded launch, and install loaders into
   game folders only after explicit approval, with a removal list.

No game file, extracted asset or decompiled code goes into this repository.
