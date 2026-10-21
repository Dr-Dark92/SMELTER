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

## Desktop container cleanup follow-up

The next uploaded run passed every prerequisite and six phases: 405 dashboard
tests (8 skipped on that desktop), 32 setup, 23 analysis, 16 JS, all 15 actual
HTTP/MCP/storage checks and the real Chromium/GLB flow. Browser page errors and
external HTTP requests were empty. These results establish wiring and fixture
behavior; live Qwen, CSS validation/preview and managed model tasks had not run.

The first Python container outcome was hidden by a false cleanup error. The
operator's exact-name listing was empty and Docker returned lowercase
`error: no such object`. The previous helper required uppercase `No such`.
The old function reproduced false cleanup against that captured stderr. The
repair requires a successful empty exact-name container listing, keeps label
checks before deletion, and handles auto-removal between inspect and remove.
Unavailable Docker, a nonempty listing or a mismatched label cannot confirm
cleanup or authorize another container's removal.

Repair source: `095add422d399a481ee9898d7f14905a0f62bb36`.
Verification: [run 39644336135](https://github.com/Dr-Dark92/SMELTER/actions/runs/39644336135).
All four CI jobs passed: Windows/Linux contracts, actual Chromium and real
container profiles, CSS preview, OpenCode/MCP report and ECC TDD. Inference was
synthetic. Native counts per OS are 409 dashboard (2 Linux/3 Windows skips), 32
setup, 23 analysis and 16 JS; every actual container cleanup check passed.
Local 409 dashboard tests (2 skips) and 23 analysis tests passed. Exact final CI
results are retained in [cleanup follow-up evidence](cleanup-followup.json).
Repeat the isolated profiles before the full live run; original desktop results
remain evidence for their completed stages, not a full smoke PASS.

## Desktop direct-model acceptance follow-up

The run beginning 2026-10-21 18:12:45 UTC passed all prerequisites, 409 dashboard
tests (8 desktop skips), 32 setup, 23 analysis, 16 JS, actual HTTP/MCP/storage,
Chromium/GLB, all six Python/Node fixture outcomes and current CSS validation/preview.
Cleanup was confirmed. Direct Qwen then ran for 13.72s and failed the combined
saved-content/receipt-hash check. That source branch requires completed model
outcome, one controller event and an existing expected file before that check.
The raw mismatched bytes and requested arguments were not in the uploaded logs.
Their cause remains unresolved pending the retained transcript/tool audits.

The direct harness now retains failed saved bytes and independent acceptance
checks; the full report marks direct live FAIL and managed/ECC NOT_RUN correctly.
All 29 local analysis tests passed, including real MCP with synthetic responses
for exact content and deliberately wrong final-newline content. Strict byte
acceptance and stop-before-later-live-phases remain enforced. No local model
quality, GPU performance or full desktop acceptance is claimed by those fixtures.

The first follow-up CI run passed Windows/Linux contracts and actual confined
OpenCode/MCP/CSS/ECC checks, but timed out waiting for advancing GLB animation.
Its screenshot showed the animation controls in view and the stage above the
chat viewport. Pinned model-viewer 4.1.0 intentionally suspends offscreen animation
(`packages/model-viewer/src/features/animation.ts`, `$tick`). The browser fixture
now scrolls the stage into view before the unchanged advancing-time assertion;
no product render policy, timeout or retry was changed.

Final source `0e1d41f0ede51496bac19bf1d2095743d3fc25b1` passed all four jobs in
[CI 39654266647](https://github.com/Dr-Dark92/SMELTER/actions/runs/39654266647).
Windows/Linux each passed 409 dashboard, 32 setup, 29 analysis and 16 JS tests
(3/2 dashboard skips respectively), plus actual HTTP/MCP contracts. Chromium
passed playback/labels, PNG/WebM, release/error lifecycle, forwarding and layout
checks with no page errors or external requests. Actual container profiles,
OpenCode/MCP saved bytes, CSS preview and ECC RED/GREEN passed with cleanup.
Model responses in CI were synthetic. See [retained evidence](direct-live-followup.json)
for job/artifact IDs and the unresolved desktop direct-model acceptance.

## Later direct live recheck: PASS

The operator supplied the updated harness console result on 2026-10-21: live
`qwen3.5:9b`, completed outcome, one executed MCP write and all six acceptance
checks true. Expected, observed and receipt byte counts are 23; the SHA-256 is
`dd016db1f3dff0293ca5ca98a590a8ad1c2c629643b611b37f4e44bb83f16e8d`.
The saved content is exactly `# DIRECT_QWEN_SMOKE_OK` plus LF. This is evidence
from the operator's pasted output; no receipt file was independently opened here.

Direct live acceptance is now PASS for this recheck. Managed OpenCode/ECC live
acceptance remains NOT_RUN. The earlier complete smoke remains a historical FAIL;
a successful separate recheck does not explain its original byte/hash mismatch
or create a single full acceptance pack. Continue with the targeted managed and
ECC steps in [the runbook](../../../FULL_SMOKE_TEST.md), then record manual GUI
acceptance. Preserve both results rather than relabelling the earlier failure.
