# Runtime layer review progress — 2026-10-21

Source: GitHub `Dr-Dark92/SMELTER`, branch `SMELTERV1`, head `a609148fab2dec8915da24ca46550f9cd275b694`. All 247 scripts beneath tools/automation verified against Git blob identities before this review. The application graph at `e27036e0` describes the same application code; `a609148` adds graph/documentation only.

**First review pass complete. Seven reproduced defects remain open; zero production fixes applied in this review.**

| Work item | State | Evidence |
| --- | --- | --- |
| Pin GitHub source and verify local scripts | Complete | 247 matched, zero mismatches |
| Trace frontend → API → admission → direct model/tool loop | Complete first pass | Manual source trace, 43-file scope matrix |
| Trace managed OpenCode → relay → Ollama → persistence | Complete first pass | Source and existing relay fixtures |
| Trace MCP grants, child lifetime and restrictions | Complete first pass | Source and real optional SDK tests |
| Reproduce policy, locking, finish, protocol, Linux path and preparation retry issues | Complete | evidence.json; fixture-only reproducer |
| Actual GLB rendering/playback/export and lifecycle edges | Complete | Three GLBs rendered; PNG/playback/labels, one WebM; both R04 races reproduced |
| Suspected ordinary cross-conversation navigation issue | Rejected after source check | History open/delete guards reject interaction while composer disabled; no defect claimed |
| Findings, action plan, progress and handover | Complete | Four Markdown files in this directory |
| Production repairs R01–R07 | Pending | Review is separate from patch implementation |
| Live Qwen/Ollama/OpenCode/Docker or native Windows validation | Not run | User at work; offline scope |

## Defect tracker

| ID | Priority | Confirmed issue | Status | Next gate |
| --- | --- | --- | --- | --- |
| R01 | P1 | Final file policy bypass in report writing and workspace source copy | Open | Direct/MCP per-file denial regressions |
| R02 | P2 | Stop waits behind global POST lock | Open | Concurrent real HTTP cancellation tests |
| R03 | P2 | Length output treated as success or not terminal | Open | Shared engine finish-reason contract |
| R04 | P2 | Released GLB preview/export callbacks leave enabled/stuck controls | Open | Owner/generation and busy/timer lifecycle tests |
| R05 | P2 | Malformed NDJSON bypasses partial transcript finalization | Open | Protocol shape and after-tool persistence tests |
| R06 | P3 | Linux case-distinct locations rejected as duplicates | Open | Platform path identity tests |
| R07 | P2 | Failed preparation leaves new V2-Data that blocks retry | Open | Owned rollback/recovery and pre-existing data protection |

## Validation

- Full dashboard: **347 tests run, OK, two skipped** (opt-in live model and Docker).
- Targeted model/assets/repair/MCP run: **45 tests run, OK, one skipped**.
- JavaScript: **15 passed**; setup: **32 passed**; analysis: **four passed**.
- Runtime finding script rerun with disposable SQLite/files/HTTP fixtures. GLB browser run used Chromium software WebGL and the real pinned viewer bundle. Zero page errors and external HTTP requests recorded.
- These checks contain no live Qwen/Ollama inference, OpenCode agent task, Docker integration, native Windows process or GPU performance test. Passing covered tests does not close the new findings.

The review is bounded to critical paths. Remaining work includes all patch acceptance tests, live rig checks and broader module/branch coverage; this file must not be read as a complete security certification.
