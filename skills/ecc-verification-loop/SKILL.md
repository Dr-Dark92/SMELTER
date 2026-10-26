---
name: ecc-verification-loop
description: Verify changed source using current syntax, behavioral tests, native build receipts and diff review; separate offline correctness from live game compatibility.
---
# Verify the actual change

Establish what changed and which validation profiles cover it. Use actual tool results for the current coding tree: `python`/`node` for dashboard code, `mods` for mod Python tests, `lua` for Lua syntax and tests, `cpp` for compiled/executed portable C++ tests. Use `build_native_mod` separately for supported Windows cross-build artifacts.

Check source-syntax results, exit status, discovered/executed counts, failures, errors and skips. ERROR is an unsuccessful setup/import/syntax/run, not an assertion RED. GREEN covers only the executed tests on the returned tree. Read new tests to ensure they execute production functions and assert relevant outcomes. Deleted failing tests, stubs replacing behavior and old receipts do not establish completion.

Use `review_coding_workspace` to compare changed files and current evidence. Any later source edit makes old evidence stale. Report unmet checks rather than inventing lint, coverage or security results. The Lua source preflight does not itself execute controller behavior. Native cross-compilation does not execute its output or establish loader compatibility.

Conclude with applied changes, test/build receipt IDs, exact tree or artifact hashes and remaining unverified behavior. Keep game/version facts distinct from hypotheses and prior memory.

Adapted from [ECC verification](references/upstream.md). Its shell examples, security greps, coverage target and hooks require separate actual support; this bridge uses SMELTER's existing operations.
