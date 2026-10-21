# Agent bridge progress — 2026-10-21

Milestone 1 is implemented and smoke-tested. Application source:
`6217ea7a39fd73aeaf460997286066d116c60dcc`. Verified
[CI run 39575344467](https://github.com/Dr-Dark92/SMELTER/actions/runs/39575344467).
See [plan](AGENT_BRIDGE_PLAN.md), [handover](AGENT_BRIDGE_HANDOVER_20261021.md)
and [machine-readable evidence](agent-bridge-evidence.json).

| Work | State | Evidence |
| --- | --- | --- |
| Shared selected/automatic skill resolution | Complete | Actual instruction text and hashes; explicit selection, CRLF and changed-manifest regressions |
| OpenCode built-in MCP bridge | Complete | Real OpenCode 1.19.3 discovers/calls the stdio proxy; host Python MCP executes the action |
| GUI forwarding | Complete | Chromium captures selected skill, write grant and one-session approval; approvals reset |
| Scoped controller dispatch | Complete | Existing ToolSession/registry reused; unknown tools, traversal and exclusions denied |
| Saved results and file activity | Complete | Controller receipts, saved-byte/hash check and existing CSS file tracker retained |
| Cancellation/follow-up failure | Complete | New calls denied; active bounded operations settle before receipt finalization; completed writes survive follow-up failure |
| Linux/Windows contracts | Passed | 371 dashboard tests each; 2 Linux/3 Windows opt-in/platform skips; 32 setup, 4 analysis, 15 JavaScript each |
| Managed Docker smoke | Passed | Real no-network OpenCode/MCP, 68-byte report, exact SHA-256, SQLite/audits, denied write and confirmed cleanup |
| Live Qwen inference | Pending on rig | Explicit --live command supplied; no real model was used here |
| Generic multi-file coding | Planned | Existing frontend grant remains CSS-only |
| Arbitrary external MCP | Planned | Remains blocked pending a confined server adapter |
| Safe existing V2 refresh | Planned | No silent reset/rebase/delete added |

The real smoke initially exposed a 7 MB provider catalogue exceeding the old
4 MiB adapter cap. Only GET /provider now receives an 8 MiB cap; ordinary message
responses remain capped at 4 MiB. Native Windows CI also caught an LF/CRLF test
fixture assumption; fixtures now specify bytes and a separate regression checks
the exact loaded CRLF instruction hash.

The generated function explorer is still explicitly pinned to the earlier
overhaul source. The manually maintained system diagram includes this bridge.
Subsequent documentation/whitespace commits do not imply additional behavior.

A pinned OpenCode source review confirmed that the configured MCP timeout also
applies to tool calls. The bridge now gives the existing 120-second host MCP
operation a 150-second RPC envelope. The final real Docker smoke delays the
action by 12 seconds and checks that OpenCode acknowledges the successful result,
as well as checking disk bytes, audits and cleanup.

## Home acceptance and ECC follow-up

The operator runner, known inventory/two-animation GLB inputs, new isolated GUI demo, retained audit/chat evidence, and pinned ECC instruction preview/import are implemented. See [home smoke](HOME_SMOKE_TEST.md) and [ECC scope](ECC_COMPATIBILITY.md). The large-catalogue discovery defect is fixed; metadata discovery is bounded separately from the 40-manifest reviewed import limit and uses immutable commit URLs. The GUI no longer claims that skills/MCP are not forwarded.

Local contracts passed with 372 dashboard tests, 32 setup tests, 13 analysis tests and 15 JavaScript tests. Real OpenCode with the pinned ECC verification-loop instruction and actual Python MCP passed the explicit process fixture; this is not Docker or live Qwen evidence. Native Windows/Linux, Chromium and the updated production Docker smoke all passed in [CI run 39594834409](https://github.com/Dr-Dark92/SMELTER/actions/runs/39594834409), application source `baff8c4ebdfe1108521445fc4583435e2fccbff4`. The browser additionally verified the large-catalogue filter, empty initial selection and 40-item review guard. The Docker smoke selected ECC verification-loop, preserved its audits/chat/report evidence, acknowledged a 12-second tool delay and confirmed cleanup. Live Qwen and manual GUI acceptance remain pending on the home rig.

Machine-readable follow-up evidence: [home-smoke-evidence.json](home-smoke-evidence.json). The new graph was generated as a CI artifact for the tested source; the committed explorer still identifies its earlier pinned snapshot.

## ECC coding workflow — verified milestone

Application source `bab265817bd3e63fb82669327ac36d461b9372c3` passed [CI run 39620302505](https://github.com/Dr-Dark92/SMELTER/actions/runs/39620302505). The universal registry now exposes seven coding tools behind a separate one-message flag. The agent can create a new registered V2/coding/UUID copy, inspect exact text/hashes, record and apply 1–6-file proposals, run fixed Python/Node tests in confined snapshots, and review evidence against the current tree. Original source and existing V2 are preserved; native shell/edits stay denied. The coding pack adds the pinned ECC TDD instruction.

Native Linux/Windows: 390 dashboard tests each (2 Linux / 3 Windows skips), 32 setup, 17 analysis, and 15 JavaScript tests each. Actual Chromium verified coding-grant forwarding/reset, selected instructions and existing GLB behavior with zero page errors/external HTTP. Real OpenCode/MCP/Python containers completed nine coding calls and ten synthetic model exchanges: a saved failing assertion (RED), minimal implementation fix, passing test (GREEN), two confirmed file cards and a current-tree review. MCP audits, saved bytes, original-source preservation and owned cleanup were checked. The existing 12-second delayed report smoke also passed.

The coding smoke exercises the Python container profile. The Node profile is implemented and contract-tested; this milestone does not claim a separate Node coding container smoke. Coverage, Git checkpoints, executable ECC plugin hooks/custom tools, delegation and memory remain unconnected. Live Qwen quality and performance remain pending on the home rig. See [coding guide](ECC_CODING_WORKSPACE.md) and [machine-readable evidence](ecc-coding-evidence.json).

Follow-up order: complete live rig acceptance; extend fixed test profiles/coverage; audit an isolated ECC executable-plugin profile; add scoped memory and any explicitly allowed delegation; then design confined external MCP adapters. Skill text alone does not implement these layers.
