---
name: ecc-cpp-testing
description: Write or repair portable C++ behavior tests and diagnose native build failures through SMELTER's existing fixed compiler and build adapters.
---
# Test native logic

Use the project's existing test framework and fixed runners. SMELTER's `cpp` profile compiles and runs `mods/<mod>/tests/cpp/test_*.cpp` with C++17 and strict warnings. GoogleTest, CTest and sanitizers in the upstream examples are optional candidates, not installed capabilities; do not add them for a test already supported by the current runner.

Exercise the real portable implementation through public interfaces. Use explicit expected values and independent binary fixtures, plus invalid inputs and state boundaries. Keep engine/hook access behind a fake interface. Confirm assertions remain active under the build flags. Run an intended reproducer before the minimal fix when behavior is faulty.

For build errors, read the exact diagnostic, file and compiler settings, make a focused repair and rerun the same target. Avoid broad rewrites or suppressing diagnostics to obtain green. Read [build resolution](references/build-resolver.md) if compilation/linking fails.

Report executed test counts and current-tree receipts. Keep portable test execution, Windows artifact compilation and actual game execution as separate evidence stages.

Adapted from [ECC C++ testing](references/upstream.md).
