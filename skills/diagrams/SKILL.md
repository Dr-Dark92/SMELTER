# Diagrams Skill

## Purpose
Generate maintainable architecture diagrams from verified project evidence.

## Formats
- Prefer Mermaid source embedded in Markdown or stored as `.mmd` for portable, editable diagrams.
- Diagram types: component, data-flow, sequence, deployment, state machine, and entity relationship.
- Optional local rendering is a separate, permission-controlled step; no cloud renderer is required.

## Procedure
1. Inspect actual services, modules, API routes, and data structures.
2. Identify which relationships are verified and which are inferred.
3. Create the smallest diagram that communicates the relevant architecture.
4. Keep labels consistent with source code and documentation.
5. Validate syntax with available local tools when installed; otherwise mark validation pending.
6. Save diagram source under `docs/diagrams/` only after approval.
7. Update `docs/ARCHITECTURE.md` with references to diagrams.

## Rules
- Never invent endpoints, services, trust boundaries, or data flows.
- Treat unverified edges as proposed, not implemented.
- Keep editable source, not only screenshots or exported PNGs.
