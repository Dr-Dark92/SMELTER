# SMELTER Vanilla V1.3.1 dashboard

Launch on Windows from the repository root:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\dashboard\start_dashboard.ps1
```

The dashboard listens only on `127.0.0.1:8768` by default. API calls require the browser session token. Extension activation is persisted to `.smelter/extensions.json` and does not install packages, launch Blender/FFmpeg/7-Zip, or grant process execution permissions.

Extension health values:

- `ready`: enabled and its executable was verified by the requirements scanner
- `available_disabled`: verified executable, extension not enabled
- `dependency_unavailable`: missing or unverified executable, including an enabled extension whose dependency disappeared

All permissions shown are declarations, **not grants**. Workflow execution and explicit permission approvals are future work.

Run tests:

```powershell
py -3 -m unittest discover -s tools\dashboard -p "test_*.py" -v
```

No AI, bundled optional tools, or network downloads are required for the unit tests.

## Python tools in local Qwen chat

Open **Python tools for the next message** below the chat. Both permissions are
off by default and reset after Send (including a failed Send):

- Enter an absolute folder and check **Allow read-only inventory** to expose
  `inventory_directory`. It lists metadata only, not file contents. It never
  launches the game, extracts archives, or identifies a mesh from file bytes.
- Check **Allow new Markdown reports in diagnostics/** to expose
  `write_diagnostic_markdown`. It creates UTF-8 LF files of at most 32 KiB in
  this checkout's `diagnostics/`. Existing names receive numeric suffixes.

The native Ollama `/api/chat` tool-calling loop has four calls and a 180-second
turn budget. Inventory is limited to depth 8, 3,000 observed entries, 150 listed
entries, and a five-second traversal budget between filesystem operations.
`scan_complete` and `scan_stop_reasons` describe traversal. `returned_entries`,
`entries_truncated`, and `listing_limit_reasons` describe the returned path
sample separately. A completed traversal may return a short path sample while
the aggregate file/extension counts cover every observed entry. The legacy
`truncated` flag is true for either type of limit; never use it alone to infer
incomplete traversal. Inventory is not an atomic filesystem snapshot.
OS filesystem calls may themselves block;
this is a local application permission boundary, not an OS sandbox against a
hostile local process changing paths concurrently. Links/junctions/reparse points
and inventory roots including `projects/` are rejected. No arbitrary Python,
shell, file-content reader, MCP, REA executable, or Blender execution is added.

Structured calls/results are recorded in `.smelter/tool-runs/*.jsonl`. Chat
history includes controller-generated receipts with the actual saved report
path, byte count and SHA-256, or errors. A failed model follow-up after a tool
action keeps its receipts. Repeated identical requests within a turn reuse the
first successful result instead of writing another file.
These receipts verify execution and saved file bytes, not the factual accuracy
of model-generated prose (`content_verified: false`). Prompts require raw byte
sizes, unknown asset semantics, and separate observations/hypotheses.

Enabled skills still need selection in **Skills Manager** (or supported auto
routing) to enter the prompt. Approving REA automatically selects its enabled
skill for that message. The skill reference budget is 48,000 characters,
at most three skills, and tool/skill chats request a 32,768-token Ollama context.
This can use more model memory than plain chat. Large history is bounded to the
most recent whole messages within 12,000 characters.

First Windows smoke test (not exercised by the offline unit tests):

1. Restart the dashboard and create a new conversation.
2. Approve diagnostic writing for the next message.
3. Send: `Use write_diagnostic_markdown to create python-tool-smoke.md with
   content "# Python tool smoke test". Report the actual saved path and hash.`
4. Confirm a controller receipt and the file in `diagnostics/`.
5. For the game test, approve inventory of `D:\Epic\Darksiders` and diagnostic
   writing. Ask Qwen to inventory the approved folder, write a handover using
   the actual metadata returned, mark partial coverage, and make no extraction
   or game-engine/War mesh identification claims without evidence.

### REA connection through Python

The REA checkbox grants two fixed CLI operations for one message:
`rea_capabilities` and `rea_inspect_pe_resources`. Both require the installed,
enabled `morluto-rea/reverse-engineer-anything` skill. PE inspection additionally
requires the analysis folder entered above the checkbox. Inventory permission
is separate. Checkboxes reset after sending.

Install the isolated upstream package from PowerShell in `C:\SMELTER`:

```powershell
node --version
if ($LASTEXITCODE -ne 0) { throw "Install supported Node.js first" }
npm view rea-agents@6.7.0 version
if ($LASTEXITCODE -ne 0) { throw "Pinned REA release unavailable; stop" }
npm install --prefix .smelter\tooling\rea --save-exact --omit=optional rea-agents@6.7.0
if ($LASTEXITCODE -ne 0) { throw "REA installation failed" }
python tools\dashboard\rea_connection.py
```

The adapter checks the package name/version, installed `scripts/rea.mjs`
launcher, and Node engine requirement: 22.19+, 24.11+, or 26+; odd majors 23/25
are unsupported. It invokes the real Node executable without a shell, npx,
model-supplied commands, or automatic dependency installation. The passive
**Check REA connection** button checks installed files; runtime verification
occurs on an approved invocation. npm release availability and Windows runtime
behavior require the local installation/live test; offline tests mock Node.

First live test: create a new chat, approve REA, and ask:
`Call rea_capabilities. Report its actual supported operations and limitations.`
No analysis folder is needed for this command. Then approve REA with a selected
folder and request `rea_inspect_pe_resources` for a relative `.exe` or `.dll`
path using forward slashes. The adapter validates scope, rejects links and
traversal, requires an MZ signature, and limits the input to 64 MiB. REA parses
the file as data; it does not launch the target.

Full JSON results are retained under `.smelter/rea-evidence/` with SHA-256
receipts and tool-run audit entries carrying the REA skill ID. Results over
10,000 characters produce an explicitly partial preview for Qwen. REA calls
have a 35-second timeout and a 2 MiB accepted JSON output limit. Node version
checks have a separate five-second timeout. The output limit is checked after
capture, rather than serving as a process memory limit. REA may create its own
local runtime/cache files. No providers are installed or configured by chat.

This adapter does not expose native decompilers, arbitrary REA commands,
`.oppc` extraction, or Blender. Those need separately verified adapters and
dependencies. Installed skill instructions alone do not supply these tools.


### Chat layout and live footer

New conversations require a nonblank title of at most 120 characters, enforced
in the UI and create API. Existing conversations remain available. User and
assistant messages have distinct alignment, backgrounds, speaker labels and
stored timestamps; content is inserted as text rather than HTML. The message
list scrolls independently inside the workspace.

The footer polls every five seconds while the page is visible, without
overlapping requests. CPU percentage is sampled from host counter differences;
the first sample says sampling. RAM displays total minus available and shows
available bytes, rather than treating cache as permanently occupied. Linux
uses /proc; Windows uses native system APIs. Other unsupported hosts display
unavailable. Disk free space refers to the checkout filesystem.

GPU means model allocation reported by local Ollama /api/ps, not GPU activity
or all applications' graphics memory. Integrated GPU allocation shares RAM.
An absent Ollama service displays unavailable; an empty model list means no
model loaded. Status polling never loads a model or starts a process. These
figures describe the host and Ollama, not per-process SMELTER resource usage.


### Composer, request jobs and Stop

The multiline composer sends on Enter, inserts a newline on Shift+Enter, and
respects input-method composition. Submitted user text appears immediately.
The controller reports waiting, thinking, generating, or running a tool, with
elapsed time. These are backend states; model prose cannot set them. Replies
are still displayed after completion, rather than token-by-token in the chat.

The web interface submits a background chat job and polls its status once per
second. One job runs at a time. Normal resource/status requests no longer wait
for the chat's shared configuration lock. Duplicate sends and conversation
switch/delete actions are disabled in the sending tab while it is running.
The current job ID is retained in sessionStorage so a reload can reconnect.
Job metadata is bounded to 50 records and is not persisted across server
restarts. A network status failure offers Stop/reload guidance rather than
claiming that the inference stopped.

Stop closes that request's local Ollama TCP connection and checks cancellation
before each later inference/tool action. It does not unload the model or stop
other Ollama clients. A tool operation already underway is allowed to finish;
its actual audit/receipt is preserved, and subsequent tools are skipped.
Cancelled turns retain the prompt and a stopped message with any tool receipts.
This mechanism was tested against a local streaming HTTP fixture, not live
Qwen. Windows and actual Ollama cancellation still need workstation validation.

For a smaller office context, launch from Fish with:

```fish
env SMELTER_CONTEXT_LENGTH=16384 python tools/dashboard/dashboard.py
```

The setting applies to skill/tool chats, defaults to 32768, and accepts values
from 2048 through 131072. It is local to the launched process and does not
change the home workstation's configuration. Existing synchronous ask clients
remain compatible; the web interface uses the new start/status/stop API.


### Controller execution cards

AI prose and backend tool results now render in separate regions. Tool cards
show recorded status, errors, file/evidence paths, byte counts, SHA-256, and
audit location where present. Full event JSON is expandable and rendered as
plain text. Success colors establish neither model narrative accuracy nor
asset semantics; they represent the operation's recorded result.

Execution records are saved atomically with each assistant message in an
additive message_execution table. Existing databases acquire that table on
the next successful/cancelled chat persistence; reading old chats does not
change their schema. Old messages remain unchanged and show that structured
execution metadata is unavailable. The system does not infer execution from
receipt-shaped historical prose. Deleting a conversation also deletes its
execution rows, while actual diagnostic files/audits remain on disk.

The legacy reply/content strings still include controller receipts for API
compatibility. The current GUI displays the separately retained model text
and renders the actual controller events as cards. Model text cannot create
these cards by imitating a receipt header or path.


### Skills & Tools view and manifest discovery

Open Tools & Integrations → Skills & Tools for a full workspace view. Search
by name, ID or purpose, filter activation status, review manifests and
fingerprints, and enable/disable through the existing approved settings API.
The tool overview lists actual implemented connections; an installed skill
does not imply a tool is connected or that an executable has been verified.

The dashboard snapshots skill instructions at process startup. Every 15
seconds while the page is visible it checks supported skill folders beneath
skills/ and .smelter/managed-skills/ (including collections/group/skill/).
Changes to SKILL.md or optional smelter.json produce a dismissible notification
and restart-required indicator. The rescan button checks immediately. The
existing catalog bounds and supported folder layout apply; this is not an
unbounded recursive filesystem watcher. Supporting scripts are not monitored
or executed in this version. The browser must be open to receive notifications.

New or modified manifests cannot enter chat context until the server restarts;
automatic routing also excludes them. Restart by stopping with Ctrl+C and
relaunching the dashboard. There is no automatic restart or dependency install.
Reviewing a manifest does not activate it. Enable/disable settings take effect
immediately for unchanged startup snapshots; new/changed instructions also
require restart. Deleted skills are no longer eligible. At restart the normal
existing skill enabled-state rules apply; review/disable any unwanted changes
before restarting. This is not a cryptographic approval or quarantine system.

Optional dependency declaration placed beside SKILL.md:

```json
{"schema_version": 1, "requires": ["node", "blender"]}
```

Only these keys are accepted. Up to 20 simple executable names are checked
with PATH lookup; paths, command arguments and executable code are rejected.
Missing declarations display unknown, rather than guessing dependencies from
prose. A found executable is not runtime verification. Declarations neither
register tools nor grant execution permissions. The displayed fingerprint
combines SKILL.md and smelter.json bytes; it is not the SKILL.md-only hash.

A universal execution registry, automated adapter development, dependency
installation, and supporting-script execution remain future work. This change
provides discovery visibility and activation gating, not those capabilities.


### Chat runtime settings in the GUI

AI & Models → Chat runtime settings provides context length, maximum response
tokens, total model-turn timeout, and a plain-text thinking toggle. Office
and Home presets populate the form; Save applies it. Saving never loads a
model or starts a request. Profiles are starting points, not hardware capacity
checks or performance guarantees.

Office: 16384 context, 1024 output, 900 seconds, thinking off. Home: 32768
context, 2048 output, 180 seconds, thinking on. Tool/image requests continue
to request direct responses. Supported context range is 2048–131072, output
128–8192, and timeout 30–1800 seconds; output must be smaller than context.

Settings persist in the selected local database's runtime_settings.json
configuration row. Saved context takes precedence over SMELTER_CONTEXT_LENGTH;
that environment variable remains a fallback until context has been saved.
The GUI displays each setting's source. A turn snapshots settings once, so
changes during generation apply only to later requests. Context and output
limits now apply explicitly to plain chat as well as skill/tool chat.

These settings do not alter OpenCode or Ollama's service defaults, and saving
them does not require restarting the dashboard. The timeout covers model
requests within the turn; an already-running tool retains its own execution
bounds and cannot be undone by a timeout or Stop.


### Conversation navigation

History filters conversation titles as you type and highlights the selected
conversation. It searches the latest 200 conversations returned by the
existing API, not message bodies or an unbounded archive.

New and Rename use an in-page modal dialog with required titles, a 120-character
limit, Enter to submit, Escape/Cancel to dismiss, inline server errors and
duplicate-submit protection. Active requests block conversation mutations
in the sending tab. The delete confirmation names the conversation and
explains that diagnostic files and audit logs remain on disk.

Message and history timestamps are displayed in the browser's local timezone.
SQLite timestamps remain unchanged. Dialog focus is initially placed in the
title field; the browser provides modal keyboard focus containment.


### Technical response formatting

Assistant responses support a deliberately small Markdown subset: fenced code
blocks (backticks or tildes), headings, flat ordered/unordered lists, quotes,
bold text and inline code. Code blocks retain indentation and scroll
horizontally. Each block has Copy code; the response header has Copy response,
which copies the model text rather than controller cards. Clipboard permission
failures show manual-copy guidance.

The renderer creates only fixed DOM elements and text nodes. Raw HTML and
Markdown links remain literal text, with no images, external requests, link
activation, syntax highlighter or HTML interpretation. It is not a complete
Markdown implementation; tables and nested formatting are currently literal.
The browser loads the fixed local /assets/chat-renderer.js script.

Renderer tests require no npm dependencies:

```fish
node --test tools/dashboard/test_chat_renderer.js
```

These tests cover code preservation and inert HTML/link content using an
inert DOM fixture; they do not verify native browser clipboard behavior or
visual layout.


### GLB attachments, interactive preview and PNG capture

Install the pinned local browser viewer once, from the checkout (Fish or
PowerShell):

```text
npm install --prefix .smelter/tooling/model-viewer --save-exact --ignore-scripts @google/model-viewer@4.1.0
```

Create/select a chat, click Attach GLB, choose a file, then click Load 3D
preview on its attachment card. Drag to orbit, scroll to zoom, use Auto-rotate
to spin/pause, and Save PNG to download the current view. The PNG may have a
transparent background. Release preview removes the active viewer. One
preview is retained at a time; switching conversations releases it. Loading
a preview requires browser WebGL support. Animated turntable export/GIF is
not implemented; auto-rotation is interactive playback.

GLB upload and rendering do not call Qwen, Blender or OpenCode. Only the
filename marker enters subsequent AI history; the model does not receive GLB
bytes or the rendered PNG automatically. The viewer bundle is served locally
from its isolated installation, with no runtime CDN. CSP permits embedded
images/blob resources and WebAssembly needed by the bundled viewer, while
external model resource URIs and compressed-decoder extensions are rejected.

Uploads are limited to 25 MiB, glTF 2.0 containers, bounded JSON metadata and
embedded buffer/image resources. These are container/resource-policy checks,
not a full geometry validator. Invalid renderable content may still fail in
the browser; a failed load displays an error. Uploaded models are user data
parsed by the browser, never executed as programs.

Files are retained under .smelter/model-assets/<UUID>.glb; filename, hashes and
metadata are stored against their chat message in an additive database table.
Reloading/reopening the conversation restores the attachment card. Deleting
the conversation removes its attachment records/access but preserves the
original uploaded files on disk; no automatic cleanup is performed. Asset
bytes require the dashboard authentication token. No uploaded sample model
is bundled in the repository.

The Tabern.glb user sample was exercised through the actual local web API and
a headless browser: titled chat creation, upload, embedded texture rendering,
PNG download, reload/reopen, auto-rotation/pause and viewer release. The test
used software rendering in the development environment, not the user's UHD
770. The application reported no page errors after fixes.
