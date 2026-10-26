---
name: diagrams
description: Build and update evidence-based Mermaid relationship charts for SMELTER coding tasks, files, imports and test snapshots. Use when starting or completing code work, recovering file locations, or documenting architecture and assets.
---

# Diagrams Skill

## Purpose
Generate maintainable architecture diagrams from verified project evidence.

## Formats
- Prefer Mermaid source embedded in Markdown or stored as `.mmd` for portable, editable diagrams.
- Diagram types: component, data-flow, sequence, deployment, state machine, and entity relationship.
- Optional local rendering is a separate, permission-controlled step; no cloud renderer is required.

## Procedure
1. Recover the task's existing workspace with `smelter_coding_workspace_context` (no arguments lists owned IDs and canonical host roots). Select by task identity, never recency. With the exact ID, refresh/query the index before inventing another path. The coding copy is a host directory; Docker tests use read-only snapshots. The Melty working directory and original checkout are separate locations.
2. Inspect actual services, modules, API routes, and data structures. Use indexed relative paths and current destination SHA-256 for writes; use explicit `start_line`/`line_count` for line reads. An offset is a character offset, not a line number.
2. Identify which relationships are verified and which are inferred.
3. Create the smallest diagram that communicates the relevant architecture.
4. Keep labels consistent with source code and documentation.
5. Validate syntax with available local tools when installed; otherwise mark validation pending.
6. The user has requested ongoing coding-task relation charts. Refresh the exact workspace context after applies/tests and at task completion. Its index and `relations.mmd` persist under `.smelter/coding-workspaces/<id>/`; include the graph scope and tree revision in the final handoff. For architecture documentation, save editable source under `docs/diagrams/` when included in the requested work.
7. Update `docs/ARCHITECTURE.md` with references to diagrams.

## Rules
- Never invent endpoints, services, trust boundaries, or data flows.
- Treat unverified edges as proposed, not implemented.
- Keep editable source, not only screenshots or exported PNGs.
- Mark static imports and inferred candidate links separately from observed files and receipts. A green test receipt applies only to its recorded tree; it does not establish in-game compatibility or behavior coverage.
- Never create duplicate files in a guessed root, weaken tests, clear an existing workspace, or report a nonexistent preview to make the chart look complete.
