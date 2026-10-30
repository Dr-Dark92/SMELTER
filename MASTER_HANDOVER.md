# SMELTER — Master handover

> **Current state lives in [docs/CURRENT_HANDOVER.md](docs/CURRENT_HANDOVER.md)** (desktop, Qwen 3.5 35B-A3B).
> The section below is the 24 October laptop baseline, kept for history.

## State (2026-10-24)
`main` installs and runs end to end on a Windows 11 laptop (GTX 1050 Ti, 4 GB):
direct chat and managed OpenCode work with `qwen3.5:4b`. Every tool and setup
step is declared in `system-requirements.json` and installed by
`tools/setup/install_missing.ps1`. Dashboard configuration is still manual.

Current documents:
- [Laptop deployment review](docs/reviews/2026-10-24/REVIEW.md): problems found, fixed and open.
- [Handover](docs/reviews/2026-10-24/HANDOVER.md): machine and configuration state, how to start, known traps.
- [Next plan](docs/reviews/2026-10-24/NEXT_PLAN.md): phased work with acceptance criteria.

## Planned integrations
OpenCode/Ollama; REA/Ghidra; Blender/Python and Unreal tooling; web Studio; GitHub sync.

## Next
1. Phase 0 quick fixes: direct chat as default engine, separate OpenCode timeout, profile diff, token estimate.
2. Phase 1: configuration seeded by deployment from hardware and installed tools.
3. Phase 2: readiness and actionable errors inside the dashboard.
4. Phase 3–4: OpenCode workflow and UI/UX overhaul.
5. Desktop live acceptance with `qwen3.5:9b`.
6. Initialize projects only upon explicit request.
