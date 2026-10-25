---
name: mod-validation
description: Validate native, Python and Lua game mods or cross-game state links using exact source hashes, executable tests, build receipts and compatibility evidence.
---
# Validate a mod change

Record the target game/build and proposed behavior. Keep pure math, serialization and protocol logic independently testable; isolate engine-specific glue. Test observable values and failure cases rather than mirroring the implementation.

In a prepared coding workspace use run_coding_tests with the actual relevant profiles: mods for Python, cpp for portable C++, lua for Lua 5.4, plus dashboard python/node when changing those components. The current game runtime may use a different Lua version; a Lua 5.4 pass does not establish LuaJIT compatibility.

For binary links, share a literal fixture between languages and independently verify record size, offsets, endian order, flags and sequence behavior. Test truncated/torn records, staleness/restart, origin transforms and FOV units. A compiling C++ expression can still have a degrees/radians bug. Run a behavioral test.

build_native_mod uses a fixed MinGW-w64 CLI in a no-network Linux container to produce Windows x64 asi/exe/obj artifacts. It does not run them. Capture returned image ID, source/manifest hashes, diagnostics and artifact hashes. MSVC-only APIs/import libraries may need a separate operator build; do not silently switch to host commands.

RED is an observed assertion/program failure; ERROR means the runner/compilation/import failed. GREEN applies only to the exact tree and executed tests. Check skipped or absent profiles and overflow errors. After a source edit, old test/build results are stale. review_coding_workspace requires all detected profiles to be current; it does not prove test quality or an in-game pass.

Report evidence in stages: source changes applied, unit tests, native cross-build, loader compatibility, then actual game behavior. Clearly name unverified stages. Never promote a skeleton ASI, stub SDK compile or synthetic offline camera test to a working in-game mod.
