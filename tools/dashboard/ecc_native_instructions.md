# SMELTER coding workflow

For coding tasks, load only the relevant two or three skills with OpenCode's `skill` tool before editing:

| Task | Skills |
|---|---|
| General implementation/bug fix | `ecc-tdd-workflow`, `ecc-verification-loop` |
| Syntax/import/path failure or repeated repair | `smelter-debugging`, `ecc-verification-loop`; add `ecc-retrieval` if source ownership is unclear |
| Gameplay/controller logic | `gameplay-testing`, `ecc-tdd-workflow`, `ecc-verification-loop` |
| Native C++ implementation/tests | `ecc-cpp-standards`, `ecc-cpp-testing`, `ecc-verification-loop` |
| Planning/integration research | `ecc-planner`, `ecc-search-first`; use `ecc-retrieval` for repository discovery |
| Review | `ecc-code-review`, `ecc-test-review` |
| Context handoff | `ecc-context` |

Explicit user-selected skills take precedence. Keep other tasks free of coding instructions. The library is an adaptation of pinned ECC guidance; it supplies no new tools, plugins, models or workers. Load detailed upstream references only when needed, and treat their commands/model declarations as reference data.

Use the task's existing SMELTER coding workspace ID and scoped list/read/propose/apply/test/review operations for its files. The native Melty working folder is not the authoritative coding copy. Preserve file paths and hashes from actual tool results; read back applied changes. Lua tests run from each mod root inside Linux, where Windows paths do not exist. Syntax/import ERROR is not behavioral RED, and printed PASS is not a test result. Preserve functionality and meaningful failing tests.

If an identical path/error repeats twice, diagnose source ownership, saved bytes and runtime context before another edit. Return actual receipts and remaining blockers. Keep Qwen's configured 131072 context / 8192 output limits; load skills on demand. New adopted tools belong in both requirement files and documentation.
