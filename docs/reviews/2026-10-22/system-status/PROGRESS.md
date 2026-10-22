# System status progress — 2026-10-22

Implemented installation/runtime/version rows, five fixed lifecycle action types,
capability explanations, cached status checks and persistent OpenCode/MCP gates.
Ollama ownership, model residency, active task/admission, stale model identity and
HTTP operator boundaries have regression coverage. Frontend resource updates
preserve the table. Operator actions retain bounded local events.

Final source `33f4fd323095d60187f456edc6e63021b479c3e8` passed [all four CI jobs](https://github.com/Dr-Dark92/SMELTER/actions/runs/39707087492).
Each native platform passed 422 dashboard, 32 setup, 30 analysis and 16 JS tests
(2 Linux / 3 Windows dashboard skips). Actual browser checks passed desktop and
375px table rendering, Status, Stop, disabled controls and telemetry preservation.
Actual confined Python/Node profiles, OpenCode/MCP saved bytes, CSS validation/
preview and ECC RED/GREEN passed with cleanup. CI model responses were synthetic.

The first container run caught a fixture assuming the optional SDK was present.
That controlled provider-start test now supplies its SDK observation explicitly;
13 focused tests also passed with the SDK reported absent. Production checks
still require the pinned SDK. An additional local real stdio MCP Stop/Start
completed discovery, closed the process and retained two operator audit events.
No live Qwen inference or actual desktop Ollama lifecycle was run here.

Use [System status](../../../SYSTEM_STATUS.md) for semantics and manual acceptance.
[Evidence](EVIDENCE.json) records source, CI jobs, artifacts and remaining limits.

## Confirmed cleanup ownership follow-up

A failed Ollama Stop now retains its owned process handle until exit is observed,
so a cleanup timeout remains a structured error with a retryable owned handle.
The added regression passes alongside the other 13 focused tests. Final source
`0bef3a9f77c63c907fea1fc7fbcf95db856ddbee` passed [all four CI jobs](https://github.com/Dr-Dark92/SMELTER/actions/runs/39708077907).
Windows/Linux each passed 423 dashboard, 32 setup, 30 analysis and 16 JS tests
(3/2 dashboard skips). Browser and actual container workflows passed. CI model
responses were synthetic; desktop Ollama/model lifecycle acceptance remains.
