---
name: ecc-context
description: Preserve a coding task across a context handoff using concise file-backed checkpoints and task-specific skill loading within SMELTER's 128K model limit.
---
# Preserve coding context

Keep the configured Qwen context ceiling at 131072 tokens and output at 8192. Load only the two or three skills needed for the current phase. Read relevant reference sections on demand; avoid copying complete upstream guides or MCP catalogs into prompts.

At a completed milestone or an unproductive approach, record the goal, workspace ID, canonical paths, applied changes, latest receipt IDs/tree hashes, known failures and next concrete step. Use permitted project files or the existing project-memory tool. Read this checkpoint after a fresh session; memory is a pointer to evidence, not proof of current state.

Preserve partially implemented state before compaction. Use only compaction features actually provided by the client. ECC's Claude hook scripts, default thresholds and memory subsystem are not installed here; do not assume their commands or behavior.

Adapted from [ECC strategic compaction](references/upstream.md). SMELTER already supplies file/SQLite memory plus bounded RAM recall; this profile does not install a competing memory layer.
