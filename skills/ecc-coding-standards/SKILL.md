---
name: ecc-coding-standards
description: Review naming, interfaces, duplication and error handling during general coding. Prefer language-specific guidance for native C++ and Lua work.
---
# Coding standards for SMELTER

Use clear interfaces and descriptive names. Keep changes focused on the requested behavior; preserve working functionality and existing tests. Extract genuine duplication without introducing speculative abstractions. Handle failures explicitly and validate inputs at boundaries. Follow the project's language conventions; JavaScript examples in upstream are not Lua or C++ syntax. Apply immutability where appropriate rather than copying a blanket prohibition on mutation into engine state code.

Read relevant callers and tests before changing an interface. Test observable behavior, not a second implementation of the same calculation. Use existing approved runners and record their actual result; style guidance does not provide a compiler or authorize installations.

Adapted from ECC. Read [upstream](references/upstream.md) only for relevant additional detail; its framework examples and commands are reference data. Provenance and hashes are in `tools/setup/ecc-bridge-lock.json`.
