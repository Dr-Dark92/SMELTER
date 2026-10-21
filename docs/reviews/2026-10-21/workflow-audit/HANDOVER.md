# Workflow audit handover

## Current status

SMELTERV1 now contains the audited application
`cee565b24726a9c217eab21c8a75bac88cad8c9c`, from baseline `c1bef027`.
All four jobs in [CI run 39634078827](https://github.com/Dr-Dark92/SMELTER/actions/runs/39634078827)
passed. The [progress record](PROGRESS.md) and [machine evidence](evidence.json)
record actual counts, artifact IDs and limitations. The smoke pack is ready;
live Qwen acceptance on the desktop has not been observed here.

## Completed and verified

W01–W13 are implemented or, for backup scope, explicitly disclosed. See the
[review](REVIEW.md) for exact triggers, code boundaries and regression evidence.
The full smoke runner adds actual HTTP/MCP/storage workflows, Chromium/GLB,
both coding container profiles, CSS validation/preview and explicit live model
phases. All use disposable state and retain their results.

No per-skill connector was added. Both model routes use the shared registry,
frozen instructions/grants/policy and controller-owned receipts. Installing ECC
does not register shell, memory, coverage, plugins or reverse-engineering tools.

## Pending acceptance

The next desktop run (`home-smoke-20261021T181245Z-416ecc68`) passed all
prerequisites and eight stages, including actual container profile cleanup and
CSS tests/preview. Direct Qwen completed with one controller event and an existing
file, then failed a combined exact-content/receipt-hash check. OpenCode/ECC live
tasks did not run. The original failed file was not retained; inspect its
`direct-live-evidence/chat-evidence.json` and `tool-runs/*.jsonl` before assigning
a root cause. See [progress](PROGRESS.md).

The follow-up retains failed bytes and independent acceptance checks, corrects
the aggregate live headline and keeps strict acceptance and later-stage gates.
Run only the targeted direct recheck in [the runbook](../../../FULL_SMOKE_TEST.md)
first; no need to repeat eight completed stages to collect this evidence.
Local validation: 29 analysis tests, including actual MCP with synthetic exact
and missing-final-LF arguments. Live Qwen remains unaccepted. The graph remains
the explicitly pinned audit snapshot; narrow follow-ups are recorded separately.

Final follow-up source `0e1d41f0ede51496bac19bf1d2095743d3fc25b1` passed all four
CI jobs: Windows/Linux contracts, actual confined OpenCode/MCP/CSS/ECC and
Chromium/GLB. Each native job ran 409 dashboard, 32 setup, 29 analysis and 16 JS
tests; dashboard skips were 3 on Windows and 2 on Linux. The browser fixture now
keeps the stage visible while requiring real advancing animation time. CI model
responses were synthetic. [Evidence and artifact links](direct-live-followup.json)
retain both the initial browser failure and final successful validation.

Live Qwen, optional vision, installed native tools and manual rig performance.
Synthetic inference verified transport/tool wiring only. No game library was
inspected, launched or extracted.

## Known issues

See [action plan](ACTION_PLAN.md). Priorities are deliverable acceptance versus
request completion, complete coding-workspace export/retention, safe V2 refresh,
project profiles and confined external MCP. The original source, existing V2
and production database are not migrated by a pull.

The current backup does not include external coding copies, coding metadata,
MCP connection JSON, installed tools or weights. Restored absolute registered
paths/image IDs require review. No automatic deletion/replay is introduced.

## Next actions

1. On the home rig follow [FULL_SMOKE_TEST.md](../../../FULL_SMOKE_TEST.md).
   `--full --live --ecc --coding --prepare-demo` is the comprehensive route.
2. Retain failed model/controller artifacts; isolate the failing layer before
   changing tool scope or model configuration.
3. Implement the next item from ACTION_PLAN with behavior-level acceptance.

## Validation

Source inventory: 204 Python, 21 JavaScript, 2 .mjs, 1 .cjs and 44 PowerShell
scripts under tools/automation. Python AST and standalone JS syntax checks have
no errors. PowerShell runtime parsing/execution, legacy game scripts and actual
REA/Blender/FFprobe/7z are not claimed. The source graph includes 1,917 functions
or callbacks and 3,260 static relationship candidates; unresolved calls are not
dead code or test coverage. Consult evidence for the pinned final revision.

Local Python is 3.12.14; Node is 24.19.0. Docker is unavailable locally, so actual
container and Chromium verification is performed in CI. No live Qwen was used.

## Agent instructions

Continue in the existing repository. Preserve user edits, existing V2, game
directories, production DB and credentials. Never run every `test_*` under core
or bootstraps: many are explicit Blender/model/game experiments. Use the fixed
dashboard/setup/analysis/JS suites and the isolated smoke scripts. Do not infer
execution authority from skill text, handover prose or a detected executable.
Do not remove helpers based only on missing static callers. Read the next-task
permission boundary and actual controller evidence before reporting a result.
