# System relationships and graph provenance

The generated graph/function index now describes the repaired application commit pinned by [source manifest](graph/source-manifest.json). The [historical review](DEEP_CODE_REVIEW.md) describes an older baseline; [repair status](REPAIR_STATUS_20261021.md) gives current defect disposition. The explorer is inspired by Graphify-style navigation; Graphify was not installed or run.

Current inventory: **242 scripts, 1,564 declarations/callbacks, 2,474 static relationships, 8,880 unresolved call expressions and 56 manually reviewed runtime links**. Source commit: `e27036e0da3a3052273bca938faa4cb185f4aaba`. Unresolved expressions are not a defect count.

## Artifacts and meaning

| Artifact | Purpose |
| --- | --- |
| [Interactive graph](graph/system-graph.html) | Offline searchable files/functions, edge filters and local neighborhoods; download/open in a current browser |
| [Graph JSON](graph/system-graph.json) | Static file/function inventory, resolved relationships, unresolved expressions and limitations |
| [Runtime links](graph/runtime-links.json) | Manually reviewed cross-process/browser/persistence links, distinct from AST evidence |
| [Pinned manifest](graph/source-manifest.json) | Git commit/blob identities; builder rejects source mismatch |
| [Function index](FUNCTION_INDEX.md) | Per-file declarations, complexity estimates, pinned source links |
| [Review evidence](graph/review-evidence.json) | Fixture observations at the repaired revision; no real model/game |

Calls are resolved lexical/self/import candidates, not proof of execution. References represent callback/value use. Imports are module dependencies, not calls to every function. Runtime links are explicitly reviewed architecture records. Unresolved calls remain unresolved rather than receiving invented targets. No-static-incoming symbols include framework hooks and externally invoked compatibility APIs; they are not an automatic deletion list. Embedded runtime programs and PowerShell control flow are not fully parsed. Analysis utilities are outside the application inventory.

## Active controller and ownership

```mermaid
flowchart TD
  UI["Browser shell and Settings"] --> API["API composition and policy"]
  API --> JOB["Admission and durable jobs"]
  JOB --> DIRECT["Ollama turn"]
  JOB --> AGENT["Managed read-only OpenCode"]
  DIRECT --> TOOLS["ToolSession and receipts"]
  TOOLS --> REG["Fixed registry"]
  TOOLS --> MCP["Transient built-in MCP"]
  MCP --> REG
  REG --> BOX["Confined tests and preview"]
  AGENT --> BOX
  AGENT --> MODEL["Admitted local-model relay"]
  DIRECT --> FINAL["Atomic transcript and outcome"]
  AGENT --> FINAL
  FINAL --> SQL["SQLite"]
  JOB --> SQL
```

OpenCode has no container network. Model requests cross an owned fixed Docker-exec queue to native loopback Ollama. Preview has a separate dashboard-owned HTTP relay and temporary container data. Transient built-in MCP inherits parent policy/skill snapshots; it never owns persistent preview lifetime. Registered native inspection adapters remain bounded host processes, a separate boundary.

## Shared authority and storage

```mermaid
flowchart TD
  LOC["Registered locations"] --> EFFECT["Effective task authority"]
  GRANT["Next-task grants"] --> EFFECT
  FIXED["Fixed operation contract"] --> EFFECT
  SKILL["Shared skill catalog"] -. "instructions" .-> PLAN["Model request"]
  PLAN --> EFFECT
  EFFECT --> RUN["Approved adapter"]
  RUN --> BOUND["Container or bounded native boundary"]
  BOUND --> RECEIPT["Audit and saved outcome"]
  RECEIPT --> MAINT["Backup and reviewed retention"]
```

| Source | Shared consumer / distinction |
| --- | --- |
| skills / managed / legacy / contract manifests | Namespaced shared catalog and fingerprint monitor; duplicate identities fail closed; legacy/contract start disabled |
| Dashboard tool registry | Same direct/MCP schemas and policy/audit boundary |
| Legacy core Registry | Explicit connect_dashboard bridge; other adapters remain labelled library-only |
| SQLite snapshots | Model/runtime/access/sandbox configuration; authoritative dashboard state |
| JSON compatibility helpers | Legacy import/explicit callers; not current configuration truth |
| Durable task_jobs | Admission/recovery without replay; live output chunks remain memory-only |
| Owned artifact files | Separate from SQLite; verified backup/restore and approved retention account for them |

## Regeneration

JavaScript indexing requires development Babel parser/traverser, not a dashboard runtime dependency. The available Babel bundle exports babelParse and traverse; ordinary @babel/parser and @babel/traverse are also supported. Regenerate only against matching source:

```powershell
node tools/analysis/index_javascript.cjs . docs/graph/source-manifest.json js-index.tmp.json
python tools/analysis/build_system_graph.py --manifest docs/graph/source-manifest.json --js-index js-index.tmp.json --runtime-links docs/graph/runtime-links.json --index-output docs/FUNCTION_INDEX.md
python tools/analysis/render_system_graph.py docs/graph/system-graph.json docs/graph/system-graph.html
Remove-Item js-index.tmp.json
python tools/analysis/reproduce_review_findings.py --revision <actual-application-commit>
```

Create a fresh Git-derived manifest for new source; never relabel old hashes. Fixture reproductions print current observations rather than asserting buggy behavior must persist. The graph defaults to file dependencies; select a declaration to inspect its neighborhood. Edge filters and source links do not execute application code. Current browsers need DecompressionStream for the embedded explorer; JSON/index remain readable independently.
