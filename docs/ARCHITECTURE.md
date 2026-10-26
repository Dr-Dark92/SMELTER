# SMELTER architecture

The active application is `tools/dashboard/dashboard.py`, with a Python job controller, direct local Ollama execution, registered tools and optional built-in MCP transport. OpenCode is a separate read-only bridge to an independently running server. Legacy core/CLI registries and Studio scaffolding are not automatically connected to it.

- [Detailed system documentation](SYSTEM_DOCUMENTATION.md)
- [Layer, call and storage relationships](SYSTEM_RELATIONSHIPS.md)
- [Offline source graph](graph/system-graph.html)
- [Complete static function index](FUNCTION_INDEX.md)
- [Workspace index and relation charts](WORKSPACE_TRACKING.md), [editable architecture diagram](diagrams/workspace-tracking.mmd)
- [Native progress and generated-media bridge plan](NATIVE_PROGRESS_AND_MEDIA_ROADMAP.md)
- [Read-only native progress monitor](NATIVE_PROGRESS.md)
- [Remaining defects and complexity review](DEEP_CODE_REVIEW.md)

Registered location flags, per-message grants and fixed adapters intersect to limit application operations. They are not an OS sandbox. Broad external MCP/general command execution remains blocked pending confinement. See the linked documents for the pinned source revision, evidence and operational boundaries.
