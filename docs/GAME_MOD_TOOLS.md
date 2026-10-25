# Game mod tools (SMELTER)

Current implementation after the 25 October review fixes. Historical Qwen runs
below used the earlier MSVC path; they are not evidence for the replacement.
CLI choices across engines: [MODDING_CLI_TOOLKIT.md](MODDING_CLI_TOOLKIT.md).

## Inspection and coding

`inspect_game_files` reads approved RPF7/PAK/UTOC headers and bounded PE section
samples. It checks the entry/time budget inside directory enumeration and header
sampling, labels malformed inputs, and reports incomplete scans. High entropy is
consistent with several causes and does not prove encryption or a protector.

Coding workspaces include `mods/<mod>/` source. Build scripts are readable but not
model-editable; binaries and build outputs are not copied. The original checkout
is preserved. `modding_tool_catalog` reads the 31-entry CLI inventory from the
requirements file; candidate metadata is not an installed tool or execution grant.

## Confined test profiles

- `mods`: each mod's Python tests run in a fresh interpreter, isolating helper
  module names as well as test module names.
- `cpp`: portable `mods/<mod>/tests/cpp/test_*.cpp` compiled with g++ C++17,
  `-Wall -Wextra -Werror`, then run inside the container. More than 64 programs is
  an ERROR; tests are never silently sliced away. The total runner limit is 160 s.
- `lua`: `mods/<mod>/tests/test_*.lua` executed with Lua 5.4, from each mod's root,
  in the same confined toolchain image. Limit 64 programs and 70 s overall.

The image receives a read-only source snapshot, no network or credentials, a
non-root user and fixed CPU/memory/process/output limits. Only C++ test binaries
run in executable scratch. Lua/portable unit tests do not prove engine runtime
or another Lua ABI is compatible. The GAL1 fixture is shared between Python and
Lua; the reader now asserts its 64-byte layout before decoding.

## `build_native_mod`

Requires both native-build and coding-workspace grants. Cross-compiles
`mods/<mod>` to Windows x64 with MinGW-w64 **inside the no-network container**.
The model path never invokes host MSVC or executes produced artifacts. Source
text filters are only defense in depth; the container supplies the actual file
and network boundary, including for macro-based includes.

`native.json` schema 1 declares 1–6 targets: name, kind (`asi`, `exe`, `obj`),
1–16 C/C++ sources, optional include_dirs (max 16), defines (max 8 NAME or
NAME=number), and allowlisted system libs (kernel32/user32/shell32/ole32/advapi32/gdi32).
An exe may set `entry` to `main` or `wmain`. Flags are fixed C++17 warnings-as-errors;
linked outputs use static GCC/C++ runtimes and omit PE timestamps and symbols.
MSVC-only SDKs/import libraries may require a separate operator build.

Sources are frozen under `.smelter/native-builds/<run>/src` (200 C/C++ files,
128 KiB/file, 1 MiB total, bounded inventory). The compiler has a 180 s total
worker budget; transport allowance is 240 s. No per-target accumulation beyond
that total is allowed. Individual artifacts are capped at 2 MiB, 4 MiB in total.
Only validated names and bounded bytes are saved from the container. New output
folders preserve previous runs; the existing last-20 retention policy remains.
Receipts include image/compiler identity, source/manifest hashes and artifact
hashes. Cleanup failures remain visible through Confined execution reconciliation;
reconciliation does not delete retained native-build artifacts.

`native_build_failed` is an MCP error and affects the final task outcome.
Compilation is distinct from a unit-test pass and from an in-game test.

## Setup

`system-requirements.json` declares every installed direct package and the pinned
base digest through `image_cpp` / `Dockerfile.cpp`: g++ 15.2.0-r5, Lua 5.4.8-r0,
mingw-w64-gcc 15.2.0-r0. Resolved transitive packages are recorded inside the image
at `/opt/smelter-toolchain-packages.txt`; the runtime uses an immutable image ID.

```powershell
docker build -f tools/dashboard/Dockerfile.cpp -t smelter-cpp:2 .
docker image inspect --format '{{.Id}}' smelter-cpp:2
python tools/setup/configure_native_build.py --image-id sha256:<ID>
python tools/setup/configure_native_build.py --image-id sha256:<ID> --apply
```

Alternatively select the image ID in Settings -> Confined execution. Existing
v1 images remain installed but lack Lua/cross-compilation. The configuration
helper can also add explicit `--read-folder` game locations. It preserves existing
policy rows/denials and adds no host execution grant. MSVC remains optional for
operator-run `gta/build.bat`; it is no longer a model build dependency.

Reproducible transport smoke (no inference/game execution):
`python tools/analysis/smoke_modding_cli.py`. Add `--activate-toolchain` only when
selecting the already-built image for this checkout is intended.

## First SMELTER runs (25 October 2026, Qwen3.5 35B-A3B, 128K context)

1. **Discovery:** `inspect_game_files` on the GTA V Enhanced folder. Qwen reported 179
   RPF7 archives (NG), the three largest executables, and `GTA5_Enhanced.exe` as packed
   (`.text` 7.99–8.0). This matched the manual discovery. Its first call used an
   absolute path, which was rejected; the retry succeeded, so the task shows
   "partially completed".
2. **Mod coding:** add a vertical → horizontal FOV conversion to the Python reference,
   its tests and a C++ helper; run `mods` tests; build natively.
   - At the saved 2,048 output tokens the whole-file patch (about 15 KB) didn't fit:
     "Model output limit reached". Output was raised to 8,192.
   - The rerun completed in 259 s: workspace, 3 reads, patch, apply, `mods` tests RED
     (the expected value in the operator's prompt was wrong), test fix, GREEN (9 run,
     1 expected skip), native build of all 3 targets, review. The report matched the
     tool results.
   - **The C++ helper had a logic bug** (degrees passed to `std::tan`, result left in
     radians). It compiled cleanly, so `build_native_mod` correctly reported success,
     but no running C++ test exists to catch it. Compile success is not correctness.

3. **Portable C++ with the `cpp` profile:** move the FOV helper into a portable
   `gta/src/link_math.h` and add `tests/cpp/test_link_math.cpp` (50° at 16:9 within
   0.01 of 79.317; 60° at aspect 1 unchanged). It completed in 114.7 s: workspace,
   patch, apply, `cpp` GREEN on the first run (1 program, 0 failures), native build of
   all 3 targets. This time the implementation was correct (degrees → radians → degrees),
   so there was no live bug to catch; the real confined runner test reproduces the
   earlier bug and reports it as a failure.

Gaps these runs exposed: whole-file patches cost a lot of output (an exact-text edit
tool would help); C++ logic needs tests that run (addressed by the `cpp` profile
above, for portable code); and there is no reviewed merge from a coding copy back into
`mods/`.

## Not provided

Installing into game folders, launching games, running built Windows code,
Unreal/RAGE asset readers, and Melty upload or publishing.
