# GTA–ARK runtime preparation

26 October 2026. The prototype now has a reproducible CLI readiness report,
source-only staging manifest and tested ARK engine-adapter logic. It remains
**offline only**. No loader was installed, game launched or game file changed.

## What the current checks show

The installed GTA Enhanced executable reports **1.0.1158.16**. The author's
[Script Hook V page](https://www.dev-c.com/gtav/scripthookv/) currently lists
`v3889.0 / 1158.13`, released 15 July 2026, supporting Enhanced **1.0.1158.13**.
That is an exact-version mismatch. The preflight does not infer that a nearby
patch is compatible or install the skeleton ASI.

Neither ScriptHookV.dll in GTA nor UE4SS.dll in the checked ARK loader locations
was found. ARK's executable had no readable Windows file-version resource, so its
engine minor version is not guessed. Its SHA-256 is retained for future probes.
The reviewed upstream UE4SS stable release is v3.0.1; a development API page is
not evidence that this release supports the timer API or this ARK client.

Reviewed upstream source commit:
`cdbc0b66cb2bb5b4a3d2f69b6e61a8460961e54c` in
[UE4SS](https://github.com/UE4SS-RE/RE-UE4SS). The required
[game-thread timer API](https://docs.ue4ss.com/dev/lua-api/global-functions/delayedactions.html)
is documented in the development branch. The mod checks for its presence and
reports a clear blocked state rather than silently losing its update loop.

The dated source/version snapshot is
`mods/gta-ark/runtime_requirements.json`, referenced by `prototype_workflows` in
`system-requirements.json`. Updating the requirements snapshot requires another
upstream review. The CLI does not pretend a dated snapshot is a live release check.

## CLI workflow

Read installed executable versions/hashes and exact loader file locations:

```powershell
python mods/gta-ark/tools/runtime_workflow.py inspect `
  --gta 'D:/SteamLibrary/steamapps/common/Grand Theft Auto V Enhanced' `
  --ark 'D:/SteamLibrary/steamapps/common/ARK Survival Ascended'
```

The JSON includes observed time, exact executable hashes, version-resource
results, loader-file observations, requirements hash and named blockers. File
presence does not establish that a loader successfully ran. `inspect` performs
no downloads, target execution or writes; save its output to a private report if
needed. A successful CLI exit means the inspection completed, not runtime readiness.

Print the proposed source package; default mode writes nothing:

```powershell
python mods/gta-ark/tools/runtime_workflow.py package
```

Create a new source-only package under `.smelter/mod-packages/gta-ark-<UUID>`:

```powershell
python mods/gta-ark/tools/runtime_workflow.py package --stage
```

It contains the ARK `main.lua`, `gal_link.lua` and `enabled.txt`, with byte counts
and SHA-256 in `manifest.json`. It contains no loader DLL, GTA ASI, game executable
or extracted asset. It is explicitly `installable:false` and is not an
installation receipt. Existing packages are preserved; a 32-directory limit
requires reviewing old packages before creating more. Linked/reparse paths,
oversized source files and changed source hashes are rejected. Partial staging
keeps a `staging` manifest so it cannot masquerade as a complete package.

These operator CLIs are not registered as additional managed MCP operations.
Qwen can still edit/test the prototype through its existing isolated coding,
`mods`/`lua` profiles and fixed native build tools. Installing loaders and launching
games are separate future runtime operations, not capabilities implied by staging.

## Prototype fixes

- Select an explicitly local player controller and confirm a standalone world
  using the reflected `UKismetSystemLibrary.IsStandalone` function. Missing or
  failed checks stop that tick. Its standalone meaning is documented by
  [Epic for UE 5.5](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/Kismet/UKismetSystemLibrary?application_version=5.5).
- Require both GAL1 Story Mode and enabled flags, and valid pawn/camera objects.
- Anchor displacement at the pawn location. The old code moved the pawn to the
  camera's offset location, adding eye height/camera-boom displacement again.
- Recapture the origin when the controller/pawn changes, rather than snapping a
  respawned pawn to the previous pawn's coordinate frame.
- Do not announce following when pawn movement fails. Catch tick errors, clear
  stale origins, keep the repeating callback alive and suppress duplicate errors.
- Reject NaN/infinite floats and FOV outside `(0, 180)` in both Python and Lua
  readers before the values can reach engine consumers.

These bindings pass synthetic-engine tests. That proves their control logic,
not reflection names, loader ABI, actual camera behaviour or game compatibility.
The existing physical-pawn camera method and ignored FOV still need in-game
calibration; the prototype has no rendering/compositing or automatic view restore.
Staleness stops further mutations and recaptures the origin on resume.

## Verification

```powershell
python -m unittest discover -s mods/gta-ark/tests -p 'test_*.py' -v
python tools/analysis/smoke_gta_ark_runtime.py
```

The smoke freezes the prototype sources, selects the existing immutable
`smelter-cpp:2` image ID and runs Python plus both Lua suites as UID 65534, read-only,
without network, with CPU/memory/PID limits and bounded scratch. It never pulls
an image, executes game binaries or changes the source. Each generated container
is removed by exact generated name. Source/log hashes and exit codes are retained.

Latest passing confined evidence:
`.smelter/mod-runtime-runs/039e5a3c-143a-482a-b85f-3d08f5af4018/report.json`.
Python: **14 tests, OK (one skipped)**. The skip is the optional Windows C++ sample,
which is deliberately absent from the frozen source. Both Lua suites pass;
the engine-binding suite performs **16 checks**. The directory-link rejection
test ran inside Linux. No new dependency was installed; this reuses the existing
Python/Lua toolchain.

Current game observations:
`.smelter/gta-ark-runtime-preflight.json`. Staged package receipt:
`.smelter/gta-ark-package.json`. The source package is
`.smelter/mod-packages/gta-ark-e00a1c2c-3951-429c-804c-2409864d992c`.

The next runtime gate is a supported GTA native route and an ARK loader probe
that demonstrates the required timer/reflection APIs on this exact client.
After those pass, validate the camera link and removal/restore behaviour in the
two games. No success in the current report substitutes for that observation.
