# MODLOG: GTA V Enhanced × ARK: Survival Ascended

Journal for this mod (Melty kit convention). Facts observed, not plans. Design:
`docs/discovery/GTA_ARK_M1_DESIGN.md`.

## 2026-10-25

- Host GTA V Enhanced, executable version 1.0.1158.16; companion ARK: Survival Ascended
  (UE5; DevKit 5.5.4). Both installs clean (no loaders or mods), per read-only discovery.
- Script Hook V page (checked 25 Oct): latest v3889.0 / 1158.13, released 15 Jul 2026,
  supporting Legacy 1.0.3889.0 and Enhanced **1.0.1158.13**. The installed Enhanced
  build is **1.0.1158.16**, so Script Hook V does not support it yet. The ASI keeps
  native access behind a camera-source interface; the Script Hook V source compiles
  only with `GAL_WITH_SHV` and the SDK, neither present.
- MSVC 14.44.35207 (VS 2022 Build Tools 17.14.42) installed and verified.
- Built the offline parts of M1. Nothing installed into either game.
  - `gta/build.bat` (MSVC 19.44, `/W4 /WX`): `gal_record_test.exe` OK. The Script Hook V
    route compiles against stub SDK declarations (not linked). Skeleton
    `GtaArkLink.asi` (102,912 bytes) built.
  - Python `tests/test_link.py`: 7/7 OK, including a torn-read stress test and reading
    the C++ writer's sample.
  - End to end offline: `fake_gta_writer.py` (about 60 Hz) and `read_link.py` (30 Hz)
    together. Walking north 1.4 m/s gave Unreal +X growing 140 cm/s; a GTA left sweep
    gave a negative (left) Unreal yaw; "stale" about 1 s after the writer stopped.
  - The Lua mod (`gal_link.lua`, `main.lua`) has not run: no Lua 5.4 interpreter is
    installed, and the UE4SS calls in `main.lua` are unverified in ARK.
  - `natives.h` hashes are written from alloc8or's native DB naming; verify them
    before the first in-game run.
- First SMELTER (Qwen 35B) coding run on this mod, in an isolated coding copy
  (`SMELTERV2/coding/a8aea689…`, not merged here): added `horizontal_fov` + tests
  (GREEN in the confined `mods` profile) and a C++ `HorizontalFov` that compiled with
  `build_native_mod` but is wrong (degrees given to `std::tan`, radians returned).
  Not adopted. Lesson: C++ logic needs tests that run, not only a compile.
- SMELTER added a confined `cpp` test profile (g++ in Docker, no network). Second Qwen
  run, coding copy only (not merged): portable `gta/src/link_math.h` with a correct
  `HorizontalFov` plus `tests/cpp/test_link_math.cpp`. cpp profile GREEN (1/1) and
  native build OK in 114.7 s. Worth adopting: keep testable math in portable headers.

### Review-fix verification (same day)

- Repaired Lua GAL1 layout (11 floats / 64 bytes); shared Python/Lua fixture and
  actual Lua 5.4 confined tests pass. ARK engine calls remain unverified.
- ASI, Script Hook V stub-route objects and Windows record-test EXE cross-compile
  in the confined MinGW-w64 CLI image. Produced Windows code was not executed.
  `std::ifstream` now uses `std::filesystem::path` for portable wide paths.
- Earlier statements that no Lua interpreter/profile exists are historical; the
  current toolchain provides the fixed `lua` profile. No game files were installed.
