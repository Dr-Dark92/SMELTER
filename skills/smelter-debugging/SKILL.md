---
name: smelter-debugging
description: Repair syntax, module loading or repeated coding failures in SMELTER's Windows-hosted isolated workspaces using exact paths, saved hashes and current runner receipts.
---
# Debug the actual failing copy

Retain the existing coding workspace ID. Obtain the exact failing relative path from a fresh runner receipt, then read it using `read_coding_file`. Record its full-file SHA-256 and the failing line. Prefer propose/apply with that hash to shell string replacements. Host PowerShell, JSON transport and Linux containers have different path/quoting rules.

For Lua, the current test runner uses Lua 5.4 and executes each test from `mods/<mod>`. A source under `ark/Mods/...` is relative to that mod root; repeating `mods/<mod>` in its test path is wrong. Windows absolute paths are unavailable inside the Linux test container. Lua 5.4 has no `continue` statement. Use structured guards, or a valid scoped goto when appropriate.

Repair one causal defect at a time and verify the saved file by reading it again. Rerun the same profile; compare the new tree, exact failing paths and diagnostics. A cache explanation requires evidence: if the file on disk contains the reported defect, fix that file. Avoid replacing complete modules with stubs or deleting the failing tests.

If the same path/error recurs after two attempted repairs, stop repeating edits. Read exact bytes/hashes, trace duplicate copies/import paths, and report a changed diagnosis or precise blocker. Preserve useful changes and hand off a small failure record rather than restarting the entire feature.

Syntax success is followed by module execution, behavior assertions and relevant regressions. `loadfile` alone does not execute a module. Treat syntax/import failures as ERROR, and preserve the intended game host while repairing offline code.
