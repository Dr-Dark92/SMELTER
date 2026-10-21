# Full SMELTER smoke test

This is the acceptance runbook for the GUI, registered access, skills, direct
Ollama, managed OpenCode, built-in MCP, isolated coding, CSS preview, GLB tools
and recovery. Start from **SMELTERV1**. The tests use new disposable code and
databases. They do not reuse production chat history, edit the original checkout
or overwrite an existing V2. Evidence directories are new and never overwritten.

`PASS` covers the automated checks requested for that run. Manual acceptance,
live model quality, native REA/Blender/media installations and performance remain
separate observations. A missing prerequisite is `BLOCKED`; an unrun stage is
`NOT_RUN`. Synthetic inference is never labelled live Qwen.

## Update and prerequisites on the home rig

Stop the old dashboard, then use **PowerShell**:

```powershell
Set-Location C:\SMELTER -ErrorAction Stop
if ((git branch --show-current) -ne 'SMELTERV1') { throw "Expected SMELTERV1." }
git pull --ff-only origin SMELTERV1
if ($LASTEXITCODE -ne 0) { throw "Update failed." }
python -m pip install -r tools\dashboard\requirements-mcp.txt
if ($LASTEXITCODE -ne 0) { throw "MCP setup failed." }
```

Use Python 3.12+; CI runs native Windows/Linux with Python 3.13 and Node 22.
The host needs Node on PATH and the pinned MCP SDK 1.30.0. Docker must already
be running with Linux containers, Engine 28+, local context, seccomp and resource
limits. Ollama must already serve the installed `qwen3.5:9b` at loopback 11434.
The smoke runner does not install dependencies, download models, pull images,
start those services or stop a process occupying a port.

If the reviewed local test dependencies are missing, install them explicitly:

```powershell
npm install --prefix .smelter/tooling/browser --ignore-scripts --save-exact playwright@1.56.1
if ($LASTEXITCODE -ne 0) { throw "Browser package setup failed." }
node .smelter/tooling/browser/node_modules/playwright/cli.js install chromium
if ($LASTEXITCODE -ne 0) { throw "Chromium setup failed." }
npm install --prefix .smelter/tooling/model-viewer --ignore-scripts --save-exact @google/model-viewer@4.1.0
if ($LASTEXITCODE -ne 0) { throw "Local GLB viewer setup failed." }
```

An existing separate Playwright installation can instead be selected with
`$env:SMELTER_TEST_PLAYWRIGHT` pointing to its absolute module directory. The
Chromium binary must already be installed. No browser dependency is required for
ordinary dashboard use; this dependency is for the automated GUI smoke only.

Review image publishers and prepare any missing images explicitly:

```powershell
docker pull python:3.12-alpine
if ($LASTEXITCODE -ne 0) { throw "Python image setup failed." }
docker pull node:22-alpine
if ($LASTEXITCODE -ne 0) { throw "Node image setup failed." }
docker build -f tools/dashboard/Dockerfile.opencode -t smelter-opencode:1.19.3 .
if ($LASTEXITCODE -ne 0) { throw "OpenCode image build failed." }
```

The runner resolves installed images to immutable IDs. Saved IDs are checked
exactly. If an image tag was rebuilt but Settings still points to an old ID,
review and update that selection. There is no host execution fallback.

## One full home command

```powershell
python tools\analysis\home_smoke.py --full --live --ecc --coding --prepare-demo
if ($LASTEXITCODE -ne 0) { throw "Smoke did not pass. Read its SUMMARY.md and failed phase log." }
```

Each switch has a separate purpose:

| Switch | Effect |
| --- | --- |
| `--full` | HTTP/MCP/storage workflows, actual Chromium/GLB and, in runtime modes, both coding profiles plus CSS tests/preview |
| `--live` | Explicit real Qwen inference; enables direct and OpenCode model acceptance |
| `--ecc` | Fetch exact pinned ECC instruction manifests; no executable plugin installation |
| `--coding` | Explicit ECC RED/fix/GREEN task; also implied by `--full` with a runtime mode |
| `--prepare-demo` | Prepare new GUI source/V2/databases and print its exact launch command; do not launch it automatically |

The runner prints its new `diagnostics/home-smoke-<timestamp>-<id>` directory.
Keep the directory intact when investigating a failure. A failed contract or
earlier phase stops later inference. The script exits 0 for requested automated
PASS, 1 for FAIL, 2 for BLOCKED. It does not silently retry a completed write.

## Office and synthetic modes

Without Qwen or Docker, with the existing browser/viewer dependencies:

```fish
cd ~/dev/SMELTER
and python tools/analysis/home_smoke.py --full
```

This runs native contracts, actual HTTP/MCP/file/SQLite workflows and the browser
fixture. All model replies in this mode are synthetic. Container and live model
acceptance remain NOT_RUN. Use ordinary `home_smoke.py` without `--full` when
browser dependencies are unavailable and only the baseline contracts are wanted.

For real Docker/OpenCode/MCP with synthetic model replies, use `--full --fixture
--ecc --coding --prepare-demo`. Port **11434 must be free** because that explicit
fixture owns a temporary model endpoint there. It refuses an existing Ollama
listener; it never stops it. The live mode uses the existing listener instead.

## Automated stages and exact expectations

| Stage / evidence | Actual checks | Expected |
| --- | --- | --- |
| Native dashboard, setup, analysis, JS logs | Contracts, permission denial, hashes, streams, rollback, cancellation and parser failures | Exit 0; inspect explicit platform/dependency skips |
| `workflow-evidence/result.json` | Real authenticated HTTP; invalid JSON/title rejected; chat create/rename; database path containing `#` | PASS |
| Same workflow | Registered folder Apply/revision conflict; unregistered admission denied before worker; folder browser returns directory names only | PASS |
| Same workflow + tool audits | Actual built-in MCP Markdown write, exact bytes/hash, recorded selected-skill hash; next task receives no old grants | PASS |
| Same workflow | Known inventory: **3 files, 1 directory, 26 file bytes**; complete traversal | Exact counts |
| Same workflow | Synthetic slow task Stop; fresh Jobs reader sees the same durable cancelled outcome | Cancelled, no replay |
| Same workflow | Embedded GLB durations **1s and 2s**; user label survives read-back | Exact metadata |
| Same workflow | SQLite/file backup and offline restore; denied retention preserves bytes; approved plan prunes one old artifact; chat deletion cleans its GLB | PASS |
| `browser-evidence/result.json` and PNG/WebM files | Actual page, titled chat, searchable Settings, locations/browse/Apply, skill table/collection controls, 311-item discovery filter and 40-item review guard | No page errors/external HTTP |
| Same browser evidence | One + attachment menu; animation play/pause/rename; PNG and WebM export; release/error/reload; stale callbacks cannot revive a viewer | Nonempty exports; original GLB preserved |
| Same browser evidence | Stop across page reload, next-task grant reset, coding ERROR/RED/stale-review display, startup retry without duplicate workflow choices | Correct states |
| Same browser evidence | 375/768/1024/1440 widths; drawer keyboard/inert behavior; reduced motion | No page overflow |
| `profile-evidence/result.json` | Real MCP plus Python/Node no-network containers: RED, GREEN, simultaneous assertion/import ERROR, all-profile review and stale GREEN rejection | Six expected stages; original source unchanged; cleanup true |
| `frontend-evidence/result.json` | Actual enabled design reference, fixed copy, hash-checked CSS replacement, Python/Node container tests, authenticated preview at 8770 with a fresh DB | Saved CSS appears in actual response |
| Same frontend evidence | New edit after launch invalidates validation; repeated launch cannot replay old cached URL | Stale launch rejected; owned preview removed |
| `direct-live-evidence/result.json` | Real direct Qwen must call MCP write once for exact `# DIRECT_QWEN_SMOKE_OK` bytes | One controller write; independent hash match |
| `runtime-evidence/` + `agent-runtime.log` | Real OpenCode 1.19.3, selected ECC verification instruction, MCP write, exact bytes, acknowledged tool result, unapproved write denial | Completed with confirmed cleanup |
| `coding-runtime-evidence/` + `ecc-coding-runtime.log` | Real OpenCode/Qwen creates failing addition test, records RED, applies minimal fix, records GREEN and current-tree review | Actual tests and saved file hashes agree |

The deterministic coding-profile tests exercise real adapters with fixed fixture
code. The ECC agent task additionally tests model tool choice. Neither measures
coverage, broad coding quality or security. A synthetic model passing the same
task proves transport wiring, not Qwen competence.

## Manual demo after automated PASS

Run the **exact command printed by `--prepare-demo`**, then open its new launch
URL. It uses a new isolated GUI at 8780. The original dashboard/V2/history are
preserved. Record observations in the run's `MANUAL_RESULTS.md`.

1. Create a titled conversation. Open Settings and confirm a single configuration
   home. Check host CPU/RAM/disk and Ollama model allocation. GPU allocation is
   not GPU utilization or a measured task allocation.
2. In Skills, review and enable only the intended imported ECC instructions.
   Restart that demo server, use its new authenticated URL, and select the skill
   for the next task. Installation alone does not select it or provide tools.
3. Approve the registered input folder for one inventory task. Ask for the known
   counts above. Send another task without approval and confirm the scope was
   not inherited. Check controller receipts, not only the answer text.
4. Select OpenCode, check its managed connection, approve one session and one
   diagnostic write. Ask for a new Markdown report with an explicit marker.
   Confirm the actual path, bytes and SHA-256 in PowerShell:

   ```powershell
   Get-FileHash -Algorithm SHA256 -LiteralPath '<actual path from controller receipt>'
   ```

5. For coding, select TDD, approve the coding workspace and run the known small
   defect scenario from [ECC coding](ECC_CODING_WORKSPACE.md). Expand each file
   card: original, proposal, confirmed saved content. A proposal is not a write.
   RED is expected failing evidence; ERROR is a runner problem; GREEN must be
   current for every detected test profile. Inspect the actual test diff.
6. Attach `inputs/two-clips.glb`. Check both source names/durations, playback,
   scrub, label save/refresh and PNG/WebM export. Labels are metadata; embedded
   GLB names and bytes remain unchanged. Duplicate animation source names cannot
   always be played separately by this viewer.
7. Optional live vision: use direct Ollama, attach the generated
   `browser-evidence/model-preview.png` and ask what is visible. Expect the known
   orange geometric fixture; an image response does not establish GLB metadata
   or identify an animation. This is manual/live acceptance, not a CI claim.
8. Stop a task and refresh. Confirm durable status, actual completed receipts and
   no repeated writes. Restart the app during a separate disposable slow task;
   recovery must say interrupted, with no automatic replay.

## Native tools and intentionally unsupported actions

| Item | Acceptance rule |
| --- | --- |
| REA | With reviewed local REA 6.7.0, supported Node and registered `rea` execution scope, approve one task and call `rea_capabilities`. Inspect actual CLI/evidence, then optionally a known owned PE fixture. No game executable is launched. Missing dependencies mean BLOCKED, not a fabricated capability. |
| Blender | Explicit operator `CHECK BLENDER` checks the version only. Modeling from the installed skill is not connected to a model tool. |
| Archive/media | Explicit operator actions, verified local binaries and registered read/operation scopes. Use small owned sample files. No extraction/conversion is part of these inspections. |
| External MCP / ECC executable plugin | Expected denial/unconnected. No external server, hooks, delegation, memory, coverage or Git checkpoints are enabled by this smoke. |
| Legacy CLI/game research | Separate opt-in environments; not run indiscriminately. No user game library is part of this pack. |

## Failure triage

Read `SUMMARY.md`, `summary.json`, the first failed phase log and its retained
tool/test artifacts. A completed model explanation cannot override failed hashes,
missing receipts, ERROR tests, stale review or unconfirmed cleanup. Check the
specific layer: admission, model response, MCP transport, workspace hash, runner,
database or preview relay. Do not remove another process to free a port.

The baseline profile is 16K context/512 output/120s; the ECC coding agent uses
32K/1024/300s. Frontend validation has a fixed 420s host MCP bound, 435s proxy wait
and 450s RPC envelope. Other host MCP operations retain 120s plus 15s proxy
headroom. An admitted task timeout is separate: Stop/timeouts prevent later
actions while an already admitted fixed operation settles and retains its receipt.

The built-in backup excludes source/V2 coding copies, coding proposals/test logs,
MCP connection JSON, installed tools and model weights. Preserve them separately.
After restoring to another checkout, review absolute registered paths/image IDs.
