# Workspace files and task relationships

## Safe targeted edits and checkpoint recovery

For focused changes use `smelter_propose_coding_edits`, then review and apply
the returned proposal. Its `changes` array contains one to six existing files;
each file has `relative_path`, the current full-file `expected_sha256`, and an
`edits` array of one to sixteen `{old_text,new_text}` pairs. Every old_text must
match exactly once in sequence. A missing/ambiguous context or stale hash rejects
the complete proposal without writing code. The controller retains the rest of
each file, including UTF-8 BOM and CRLF bytes. Use actual text from a fresh read.

`propose_coding_patch.content` remains a COMPLETE file replacement, never a diff
or snippet. Proposal previews now expose before_lines/after_lines and a
large_replacement flag. For existing files of at least 1 KiB and thirty lines,
shrinking below 35% of bytes and 50% of lines rejects by default. Intentional,
reviewed whole-file rewrites can use explicit `allow_large_replacement=true`;
do not use that acknowledgement for focused fixes. This is a truncation clue,
not semantic validation or a guarantee against edits made outside SMELTER.

Before replacing existing code, apply persists a pre-edit checkpoint under the
exact workspace's `.smelter/coding-workspaces/<UUID>/checkpoints/` metadata.
Checkpoints verify full path/workspace/SHA ownership, use short storage keys for
Windows path limits, and share the existing 128 MiB/4,096-file evidence quota.
Identical bytes/path reuse the same checkpoint. No automatic history deletion
or new external dependency is introduced. Ordinary apply rollback remains intact.

Apply receipts and `coding_workspace_context` expose checkpoint relative paths,
full hashes and byte counts. To recover a file that exists only in the coding
copy, call `propose_coding_restore` with `workspace_id`, one path in
`relative_paths` and its `checkpoint_sha256`; review and apply the proposal.
The checkpoint is verified again before apply. Without that optional hash,
restoration still uses the original checkout. An original baseline cannot
restore a file created later in the coding copy. A derived index stores paths
and hashes, not replacement file bytes.

27 October recovery evidence:
`.smelter/progress-reviews/patch-corruption-20261027/`. The operator recovered
exact pre-edit audit bytes rather than inventing new gameplay logic, preserved
the bad fragment, restored the reviewed hash and saved a durable checkpoint.

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

Lua test receipts now expose `source_snapshot` (fresh copy ID, host/container
source manifest hashes and `bytes_match`) and `test_programs` (each test's working
directory, exit code and actual standard Lua file-loader imports with SHA-256).
Missing or inconsistent source/execution proof makes the run ERROR. The immutable
Docker image contains the runtime/toolchain; current project files are copied
per invocation and bind-mounted read-only. Rebuilding an image or preparing a new
workspace does not fix a test's Lua call signature or import prefix. The `mods`
profile runs Python tests; Lua uses `profile=lua` from each `mods/<project>` root.
Returned manifests/import lists are bounded; the full runner evidence is retained
in the run log. Custom loaders and `dofile` are outside the standard-import trace.

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

## Guided recovery after repeated failures

See [RECOVERY_GUARDRAILS.md](RECOVERY_GUARDRAILS.md) for the read-only recovery
context tool, automatic LF/CRLF matching, first-stack-frame diagnostics, bounded
read retries and persistent MCP work-window limits. `coding_recovery_context`
resolves test-relative paths through the recorded failing test working directory
rather than the current Melty folder. Checkpoint restore remains a reviewable
proposal; recovery does not weaken acceptance or replay writes automatically.
