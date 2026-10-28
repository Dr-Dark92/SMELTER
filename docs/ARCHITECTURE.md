# SMELTER architecture

The [live WebSocket task trace](NATIVE_PROGRESS.md#live-websocket-task-trace)
observes the exact native root/turn and its current child sessions through
allowlisted SQLite metadata and GET-only ACP inspection. A same-origin socket
pushes component/file/skill activity and distinguishes access waits, quiet tasks
and delayed telemetry. Supplied Melty task IDs remain distinct from native turn
IDs. See [the trace graph](diagrams/live-task-trace.mmd). The [trace workbench](TRACE_WORKBENCH.md) renders it as an
interactive evidence graph with saved final charts and explicit task artifacts.

The active application is `tools/dashboard/dashboard.py`, with a Python job controller, direct local Ollama execution, registered tools and optional built-in MCP transport. OpenCode is a separate read-only bridge to an independently running server. Legacy core/CLI registries and Studio scaffolding are not automatically connected to it.

- [Detailed system documentation](SYSTEM_DOCUMENTATION.md)
- [Layer, call and storage relationships](SYSTEM_RELATIONSHIPS.md)
- [Offline source graph](graph/system-graph.html)
- [Complete static function index](FUNCTION_INDEX.md)
- [Workspace index and relation charts](WORKSPACE_TRACKING.md), [editable architecture diagram](diagrams/workspace-tracking.mmd)
- [Native progress and generated-media bridge plan](NATIVE_PROGRESS_AND_MEDIA_ROADMAP.md)
- [Read-only native progress monitor](NATIVE_PROGRESS.md)
- [Test source provenance chart](diagrams/test-provenance.mmd)
- [Universal gameplay/adapter specification](UNIVERSAL_GAMEPLAY_CONTRACT.md), [proposed boundary chart](diagrams/universal-gameplay.mmd)
- [Remaining defects and complexity review](DEEP_CODE_REVIEW.md)

Registered location flags, per-message grants and fixed adapters intersect to limit application operations. They are not an OS sandbox. Broad external MCP/general command execution remains blocked pending confinement. See the linked documents for the pinned source revision, evidence and operational boundaries.

## Controller-owned acceptance contracts

See [FROZEN_ACCEPTANCE.md](FROZEN_ACCEPTANCE.md) for the operator-registered,
separately isolated acceptance gate. Overall GREEN requires local tests and
frozen acceptance to pass. The live trace derives changes-needed, not-verified
and scope-limited checks-passed outcomes separately from an ended response.
