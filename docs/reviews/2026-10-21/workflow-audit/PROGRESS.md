# Workflow audit progress — 2026-10-21

Baseline: `c1bef027c0722dea73124c07f748915437c5aeac`.
Verified application: `cee565b24726a9c217eab21c8a75bac88cad8c9c`, published to
**SMELTERV1**. Documentation and graph pin that exact application source.

| Work | State | Evidence |
| --- | --- | --- |
| All-layer source/call inventory | Complete | 272 scripts; Python AST/JS syntax checks; pinned function graph. PowerShell declarations only |
| Workflow/authority trace | Complete for active paths | REVIEW layer matrix and W01–W13 register; legacy/game execution explicitly excluded |
| Source/runtime boundary, frozen direct skills, shared result semantics | Implemented and verified | Native regressions, actual HTTP/MCP fixtures and managed containers |
| Node RED/GREEN/ERROR distinction | Verified | Real host reporter fixtures and actual Python/Node container profiles |
| Frontend deadlines and stale launch denial | Verified | Fixed envelopes, native regression and actual CSS/tests/preview smoke |
| Catalogue, URI, parser and discovery defects | Verified | Targeted regressions; actual hash-path backup/restore |
| Full operator smoke pack | Ready | FULL_SMOKE_TEST.md; --full runner; retained phase evidence; no automatic dependency/service installation |
| Windows and Linux native contracts | Passed | Per OS: 405 dashboard (3 Windows/2 Linux skips), 32 setup, 18 analysis, 16 JS |
| Actual HTTP/MCP/storage smoke | Passed on both OS | 15 checks, six synthetic model replies, saved bytes/hashes, recovery/retention/restore and cleanup |
| Actual Chromium GUI/GLB | Passed | No page errors/external HTTP; Stop/reload, result states, permissions, settings/skills/locations, PNG/WebM and responsive checks |
| Actual Python/Node containers | Passed | RED both, GREEN both, mixed assertion/import ERROR both, current review, stale rejection and cleanup |
| Actual CSS tests/preview | Passed | Saved CSS in authenticated response; later edit rejects stale preview launch |
| Real OpenCode/MCP and ECC TDD | Passed with synthetic inference | Delayed write acknowledged; saved report/test/fix hashes, denied write, RED/fix/GREEN and cleanup |
| Cross-platform CI | All four jobs passed | [Run 39634078827](https://github.com/Dr-Dark92/SMELTER/actions/runs/39634078827), exact head cee565b |
| Live Qwen, vision/native tools, rig performance | Pending | Explicit home command/manual matrix; no claim from synthetic replies |

Initial [run 39633329869](https://github.com/Dr-Dark92/SMELTER/actions/runs/39633329869)
passed Linux, browser and managed container smokes, but Windows caught the new
Node reporter's absolute-path loading error. The corrected file-URL candidate
reran all jobs and passed. The initial run is not labelled fully green.

CI artifacts expire on **2026-11-04**. Their exact job/artifact IDs, counts and
limits are retained in [evidence.json](evidence.json). Current open work and
acceptance criteria are in [ACTION_PLAN.md](ACTION_PLAN.md). A ready smoke pack
is not a claim that the live desktop run already passed.

## Home preflight follow-up

The first operator report was BLOCKED before any test phase or inference. Python,
MCP, Node, Ollama/model metadata and browser/viewer dependencies passed; Docker
info returned exit 1, and the report omitted its stderr. Subsequent operator
output showed a reachable Linux Docker engine with seccomp. That later success
does not establish the original probe's cause or a completed smoke run.

The follow-up runner uses the backend's standard JSON info probe, retains bounded
redacted native errors, and requires both test images in full preflight-only
mode. All 23 analysis tests passed locally. The comprehensive application CI
above remains evidence for its exact audited source; new local test counts are
not substituted into that historical run. The next operator action is
`python tools/analysis/home_smoke.py --full --preflight-only`, then the live run
only after prerequisite PASS. Manual and live acceptance remain pending.
