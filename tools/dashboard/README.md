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
