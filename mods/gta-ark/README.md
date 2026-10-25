# GTA V Enhanced × ARK: Survival Ascended

A Melty-style live mashup: GTA V Enhanced (host, Story Mode) and ARK: Survival
Ascended (companion, single player) run side by side and share state. Milestone M1
links GTA's camera to ARK's view, with no rendering yet. Design:
[GTA_ARK_M1_DESIGN.md](../../docs/discovery/GTA_ARK_M1_DESIGN.md). Record format:
[link-format.md](link-format.md). Journal: [MODLOG.md](MODLOG.md).

**Status:** offline parts only. Nothing here has been installed into or run with
either game. Script Hook V does not yet support the installed Enhanced build
(1.0.1158.16; latest Script Hook V supports 1.0.1158.13), so the ASI builds as a
skeleton with no native access. **Do not install the skeleton build.**

| Path | What it is |
| --- | --- |
| `gta/src/link_record.h` | GAL1 seqlock writer (Win32), layout checked by `static_assert` |
| `gta/src/camera_source.h` | Camera source interface: native route kept swappable |
| `gta/src/shv_source.cpp`, `natives.h` | Script Hook V source (with `GAL_WITH_SHV` + `SHV_SDK`); native hashes to verify before first run |
| `gta/src/GtaArkLink.cpp` | ASI: writes the record each frame, F7 toggle, notifications |
| `gta/build.bat` | MSVC x64 build: C++ record test, Script Hook V route compile check, ASI |
| `gta/tests/` | C++ record test; `shv_stub/` declarations for the compile-only check |
| `ark/Mods/GtaArkLink/` | UE4SS Lua mod: `gal_link.lua` (reader, transforms) and `main.lua` (game glue, unverified) |
| `tools/gal_link.py` | Python reference implementation |
| `tools/fake_gta_writer.py`, `tools/read_link.py` | Stand-ins for each game, for offline tests |
| `tests/test_link.py`, `tests/vectors.json` | Python tests and shared transform vectors |
| `tests/test_gal_link.lua` | Lua 5.4 tests (confined `lua` profile; shared 64-byte fixture) |

```bat
gta\build.bat
python -m unittest tests.test_link
```

No game files, extracted assets or decompiled code belong in this folder.

The model-facing native builder now uses confined MinGW-w64, and the `lua` profile executes the repaired GAL1 reader. Both are offline checks; engine glue remains unverified. See [game-mod tools](../../docs/GAME_MOD_TOOLS.md).
