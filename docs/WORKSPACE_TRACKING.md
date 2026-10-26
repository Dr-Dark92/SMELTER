# Workspace files and task relationships

SMELTER keeps a derived file ledger for each owned coding workspace. This fixes
the missing context behind repeated searches in the Melty staging folder: a
coding copy lives on the host, and Docker tests use a read-only snapshot of it.
The ledger does not move source files or resolve duplicate roots by guessing.

## Use from Melty / native OpenCode

1. Call `smelter_coding_workspace_context` with no arguments to recover the owned
   workspace IDs and canonical host roots. Reuse the ID belonging to this task;
   do not choose the newest workspace automatically.
2. Pass that exact `workspace_id` and a filename/path substring `query`. Results
   include relative paths, full host paths, current and baseline SHA-256, file
   status, recent observations, tree revision and a bounded relation graph.
3. Read the indexed path with `smelter_read_coding_file`. Use `start_line` and
   `line_count` for line pagination. The older `offset` / `limit` pair counts
   characters; mixing both modes is rejected.
4. Use current destination hashes for ordinary proposals, or the checked
   `smelter_propose_coding_restore` operation for original baseline files.
5. Refresh the workspace context after changes/tests and before the handoff.
   Load the bundled `diagrams` skill when explaining relationships.

The active GTA × ARK workspace is `897b9243-fd7e-42f4-a46a-d1b814a33a81`, at
`C:\Users\Dr.Dark92\Documents\ChatGPT\SMELTERV2\coding\897b9243-fd7e-42f4-a46a-d1b814a33a81`.
The Melty staging folder and `SMELTER` original checkout are separate locations.
This is a known task mapping, not a default for every future task.

## Dashboard

Open **Settings → Debugging → Workspace files & relations**. Select the task
workspace, search its file table, and use **Refresh index** to observe external
changes. Full SHA-256 values and physical paths stay visible. The panel polls
the cached view every two seconds while open; it does not hash the whole tree
on every poll. SMELTER preparation, list/context reads, applied patches, tests
and reviews update the ledger. Arbitrary external writes are observed at the
next refresh or SMELTER scan; there is no filesystem watcher yet.

The SVG chart and editable Mermaid source show observed file membership,
literal static imports, inferred import candidates and test-snapshot receipts.
Receipts are marked stale when their tree differs; Lua runner changes also
invalidate the Lua receipt. Import relationships do not prove behavior coverage.
The SVG currently uses labelled nodes and hover descriptions for relation edges.
SVG output is covered by local JavaScript tests. Mermaid source is preserved,
but compilation with a Mermaid renderer has not been checked on this machine.
Managed/direct dashboard coding tasks save the latest indexed graph alongside
their final transcript. The [native progress monitor](NATIVE_PROGRESS.md) also
captures a final chart after observed native activity ends, displayed separately
from the dashboard transcript. Native file/test operations update the workspace
panel, while arbitrary external writes still need a scan.

## Storage, limits and API

Derived records are stored under
`.smelter/coding-workspaces/<workspace_id>/file-index.json` and `relations.mmd`.
The index is separate from immutable baseline hashes and proposal admission.
Filesystem bytes remain authoritative for writes. A failed tracking update
cannot turn a successful patch into a reported apply failure.

The existing managed-copy limits apply: approved paths under `tools/`, `skills/`
and `mods/`, selected top-level documents, 20,000 current files / 128 MiB, excluded
credentials, build products and linked paths. This is not a whole-disk index.
Graphs start with at most 60 changed files (or 60 files when unchanged), add
bounded resolved references, retain 120 recent observations and return bounded
pages. Renames appear as missing and created paths. Lua, Python and JavaScript
literal imports are analysed statically; dynamic loading remains unverified.
Assets already present in permitted copies can be named/hashed, without granting
binary editing, conversion or preview access.

Authenticated, same-origin dashboard endpoints:

- `GET /api/workspace-tracking`: list owned workspace roots.
- `GET /api/workspace-tracking?workspace_id=…&query=…&offset=0&limit=50`:
  cached page and graph, with current access-policy filtering.
- `POST /api/workspace-tracking` with
  `{"action":"refresh","workspace_id":"…"}`: scan the approved host copy.

Both the native bridge and dashboard use existing runtimes. Enable/bridge with
`python tools/setup/install_workspace_tracking.py`; `--preview` verifies without
writing. It copies the bundled `diagrams` skill and compact continuity instructions,
backs up changed native configuration, preserves model/permission/MCP settings,
and refuses conflicting native instructions. Setup/profile `workspace_tracking`
is declared in `system-requirements.json`. No extra package is installed.

## Next integrations

See [native progress and media plan](NATIVE_PROGRESS_AND_MEDIA_ROADMAP.md) and
the [tracking architecture source](diagrams/workspace-tracking.mmd).
