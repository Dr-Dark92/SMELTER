---
name: ecc-tdd-workflow
description: Implement or fix source behavior with an executed reproducing test, a minimal repair and fresh RED/GREEN evidence through SMELTER's fixed test runners.
---
# Test-driven changes

Identify the intended behavior, actual module path, language version and existing runner. Write a test importing and executing that implementation. For a bug fix, reproduce the intended failure before changing behavior. An unrelated syntax/import/dependency error is ERROR, not the behavioral RED gate; repair test setup first and describe that distinction.

Use the current task's coding workspace ID. Read exact bytes/hashes, propose a small patch, apply it, then run the relevant `run_coding_tests` profile. A proposal is unsaved until apply succeeds. Implement the smallest behavior change that fixes the reproducer; rerun that test and relevant regressions. Preserve failure cases and assertions. Refactor only after behavior passes.

For Lua, tests execute from `mods/<mod>`; use a module path relative to that directory. `loadfile` compiles and returns a function: call it to obtain exports. Mock/fake the engine boundary while executing the real controller. A print containing PASS or a returned false without an assertion cannot establish a test pass.

Report changed paths, RED/GREEN receipt IDs, exact tested tree, skipped checks and remaining runtime limits. Existing runners do not measure coverage: report it as unmeasured. Do not promise ECC's 80% coverage or Git checkpoint features without an actual adapter/result. Run no upstream installer or generic npm command merely because it appears in an example.

Adapted from [ECC TDD](references/upstream.md); consult its detailed examples only when applicable. Upstream agent/model choices are not activated by this skill.
