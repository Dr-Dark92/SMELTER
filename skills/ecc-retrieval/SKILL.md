---
name: ecc-retrieval
description: Find authoritative code and missing context with bounded searches before a coding repair, especially when duplicate paths or an incomplete Melty directory cause confusion.
---
# Retrieve authoritative context

Retain the task's existing workspace ID. The native Melty working directory may be incomplete; list/read the coding copy through SMELTER before declaring repository files absent. Keep repository-relative source paths separate from host paths and container working directories.

Start with a focused filename/symbol search. Read directly relevant implementations, callers and tests. Refine missing terminology or paths for at most three discovery passes, then proceed with sufficient evidence or identify the precise missing artifact. Avoid repeatedly reading unrelated documentation or entire catalogs.

When duplicate files exist, inventory their exact paths/hashes and trace imports to determine which is authoritative. Do not invent a corrected-looking path or overwrite both blindly. A model's relevance score is a selection aid, not correctness evidence.

Adapted from [ECC iterative retrieval](references/upstream.md) to a single Qwen session. Its subagent examples do not create or authorize delegation.
