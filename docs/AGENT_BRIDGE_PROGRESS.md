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
