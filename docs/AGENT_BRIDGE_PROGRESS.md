# Agent bridge progress — 2026-10-21

Current audited application: `cee565b24726a9c217eab21c8a75bac88cad8c9c`, published
to **SMELTERV1**. All four jobs in [CI run 39634078827](https://github.com/Dr-Dark92/SMELTER/actions/runs/39634078827)
passed. Read the [workflow audit](reviews/2026-10-21/workflow-audit/REVIEW.md),
[progress](reviews/2026-10-21/workflow-audit/PROGRESS.md),
[evidence](reviews/2026-10-21/workflow-audit/evidence.json) and
[handover](reviews/2026-10-21/workflow-audit/HANDOVER.md) for the current record.

| Work | State | Evidence / boundary |
| --- | --- | --- |
| Shared selected instructions | Complete | Both engines freeze actual text/hashes at admission; changed manifests need restart |
| Universal agent/tool bridge | Complete | Real OpenCode 1.19.3 and built-in Python MCP; existing shared registry and policy, no connector per skill |
| Current source reference | Corrected | Readiness and every managed task use the same original checkout snapshot; live destinations are read through tools |
| GUI forwarding/status | Verified | Chromium checks skill/grant forwarding, next-task reset, Stop/reload and ERROR/RED/stale review |
| Scoped multi-file coding | Implemented | Separate UUID copies, hash-checked proposal/apply, fixed tests and current-tree review; no shell/deletion/merge/Git |
| Python and Node runners | Verified in real containers | Both RED, GREEN and simultaneous assertion/import ERROR; stale GREEN rejected |
| CSS validation/preview | Verified in real containers | Current CSS in authenticated preview; later edit prevents stale launch replay |
| Operation lifetime | Corrected | 120s/135s normal host/proxy; 420s/435s frontend validation; 450s RPC envelope; active-call cleanup follows deadline |
| Native contracts | Passed | Per OS: 405 dashboard (2 Linux/3 Windows skips), 32 setup, 18 analysis, 16 JS |
| HTTP/MCP/storage smoke | Passed on both OS | 15 real workflow checks, six synthetic model replies, owned cleanup |
| Managed report and ECC TDD | Passed with synthetic model | Actual OpenCode/MCP, exact saved hashes, delayed receipt acknowledgement, denied write, RED/fix/GREEN and cleanup |
| Live Qwen / vision / rig performance | Pending on rig | [Full acceptance command](FULL_SMOKE_TEST.md); synthetic replies prove wiring only |
| External MCP / full ECC plugin | Not connected | Needs separate confinement, hooks/tools, coverage, memory and any permitted delegation |
| V2 refresh and coding export/retention | Open | Existing V2 remains preserved; backup excludes coding copies/metadata |

## Operator acceptance

```powershell
Set-Location C:\SMELTER -ErrorAction Stop
git pull --ff-only origin SMELTERV1
if ($LASTEXITCODE -ne 0) { throw "Update failed." }
python tools\analysis\home_smoke.py --full --live --ecc --coding --prepare-demo
if ($LASTEXITCODE -ne 0) { throw "Smoke failed or is blocked; inspect the printed evidence directory." }
```

Use [FULL_SMOKE_TEST.md](FULL_SMOKE_TEST.md) for explicit prerequisite installation,
expected results, manual GUI scenarios, native-tool limits and failure triage.
No services, model downloads, images or browser dependencies are installed by
the runner. It creates new evidence and disposable state, never overwrites an
existing V2 and prints rather than automatically starts the GUI demo.

## Earlier milestones

Historical evidence remains available: [initial bridge](agent-bridge-evidence.json),
[home/ECC instruction smoke](home-smoke-evidence.json),
[initial coding smoke](ecc-coding-evidence.json) and
[bridge handover](AGENT_BRIDGE_HANDOVER_20261021.md). Their versions, counts and
older timeout observations do not describe the current release. The refreshed
function graph pins the current audited source and includes analysis scripts
and the MCP .mjs proxy. Static reachability is not execution coverage.
