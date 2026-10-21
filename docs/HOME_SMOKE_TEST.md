# Home smoke test and demo — SMELTERV1

This tests **GUI → SMELTER → managed OpenCode → Ollama/Qwen**, with selected
instructions and approved built-in tools carried through MCP. It separates
transport correctness from model quality. A model's success claim is never a pass.

The default runner uses no live model. `--live` is the explicit inference opt-in.
The runner creates new diagnostics, known input files and, with `--prepare-demo`,
a separate application/database pair. It does not overwrite `C:\SMELTERV2`, use
game files, change the production database, start services or open terminals.

## 1. Update at home

Stop the old dashboard with Ctrl+C in its own terminal. In PowerShell:

```powershell
Set-Location C:\SMELTER
if ((git branch --show-current) -ne 'SMELTERV1') { throw 'Select SMELTERV1 before updating.' }
git pull --ff-only origin SMELTERV1
if ($LASTEXITCODE -ne 0) { throw 'Update failed; stop here.' }
python -m pip install -r tools\dashboard\requirements-mcp.txt
if ($LASTEXITCODE -ne 0) { throw 'MCP dependency installation failed.' }
python tools\analysis\home_smoke.py --preflight-only
```

Expected: Python 3.11+, host Node 20+, MCP SDK **1.30.0**, a local Docker Engine
**28+** using Linux containers with resource limits/seccomp, and an installed
`qwen3.5:9b` reachable through Ollama on `127.0.0.1:11434`.
An empty `ollama ps` is valid before inference. No separate host OpenCode server
on port 4096 is required; the managed image contains OpenCode **1.19.3**.

Exit **2 / BLOCKED** means a prerequisite is missing. Inspect the printed
`SUMMARY.md` and `summary.json`; the runner does not silently fall back to a host
agent or download anything.

If Docker Desktop is installed but stopped, start it manually and select Linux
containers. Build the reviewed OpenCode image once if it is missing:

```powershell
Set-Location C:\SMELTER
docker build -f tools\dashboard\Dockerfile.opencode -t smelter-opencode:1.19.3 .
if ($LASTEXITCODE -ne 0) { throw 'OpenCode image build failed.' }
```

Optional CSS validation needs the separate fixed-test images:

```powershell
docker pull python:3.12-alpine
if ($LASTEXITCODE -ne 0) { throw 'Python image preparation failed.' }
docker pull node:22-alpine
if ($LASTEXITCODE -ne 0) { throw 'Node image preparation failed.' }
```

These are explicit operator setup commands. The smoke runner only inspects local
images, resolves their immutable IDs and uses `--pull never` through the existing
managed runtime. Existing saved image IDs take priority; use `--opencode-image
sha256:...` for an explicit existing replacement. No production image setting is
changed by the runner.

## 2. Run the automated smoke and prepare the demo

```powershell
Set-Location C:\SMELTER
python tools\analysis\home_smoke.py --live --ecc --prepare-demo
if ($LASTEXITCODE -ne 0) { throw 'Smoke did not pass. Read its summary before continuing.' }
```

`--ecc` retrieves three hash-checked manifests from ECC commit
`90606c8315ee09cafc303515c5f33024db6b9882`. It does not run ECC's installer or
load its plugin. The live task selects `verification-loop` and asks for one
approved diagnostic write. The three manifests are imported **disabled** in the
isolated GUI demo, ready for review and enablement.

The runner prints the evidence directory and the exact PowerShell command to
launch the isolated dashboard on **8780**. Run that printed command in a second
terminal. It does not launch automatically. Open the authenticated URL printed
by that dashboard; retain its `#token=` locally and do not share it in logs.

| Automated stage | Expected evidence |
|---|---|
| Prerequisites | Exact versions and local immutable image IDs; no inference |
| Dashboard / setup / analysis / JavaScript contracts | Four PASS entries and separate logs; live-test environment flags forced off |
| Managed agent smoke | Real OpenCode container, actual MCP call, selected ECC instruction hash |
| Saved bytes | `agent-bridge-smoke.md`, exactly **68 bytes**, independently compared with the requested bytes |
| Report digest | `dfe22aa9e274e9f3b4487c10cc6c3456df909d30d3f8544abb9e8588951054d1` |
| Receipts | Controller receipt, Python MCP audit, persisted chat execution and OpenCode's completed-tool acknowledgement |
| Guardrail | An unapproved second write is denied; `denied.md` does not exist |
| Cleanup | Managed-container cleanup is confirmed; disposable runtime state removed; evidence retained |

The live test profile is **16,384 context / 512 output tokens / 120 seconds /
thinking off**. This is a fixed diagnostic profile, independent of production
GUI settings. The demo GUI uses 16,384 / 1,024 / 180 / thinking off. These are
bounded smoke tasks, not a benchmark or a promise that every larger task fits.

Contract checks may take a minute or more on Windows; the runner prints each
phase as it starts and finishes. A live-model timeout is recorded as a failure,
with evidence retained. Do not repeatedly resend while a task is active.

Without live inference, use:

```powershell
python tools\analysis\home_smoke.py
```

This runs contracts only and explicitly reports Qwen `NOT_RUN` and GUI
`MANUAL_PENDING`. `--fixture` instead tests real Docker/OpenCode/MCP against a
synthetic model with a 12-second delayed tool call. It requires port 11434 to be
free and refuses to stop an existing Ollama service. Do not use it on a busy rig.

## 3. GUI demo, in order

Use the isolated source printed by the runner, named `SMELTER-DEMO`, with sibling
`SMELTER-DEMOV2`. Its database and preview database are also new. The original
checkout, its conversations, registered locations and existing V2 are preserved.

### A. Interface and readiness

1. Open the demo's port **8780** launch URL.
2. Create a conversation titled **Home smoke — bridge**. An empty title must be
   rejected. User and assistant messages must be visually distinct.
3. In Settings, inspect Workspaces & Access. `Smoke inventory (read only)` is
   pre-registered with read enabled and write/execute disabled.
4. Check the resource footer. Missing telemetry should say unavailable, rather
   than inventing utilization. An unloaded model is not an error.
5. In Next-task tool access, run **Check managed OpenCode** and select the verified
   local Qwen model. Expect the managed version/provider check to succeed. This
   check alone does not prove a model response or successful tool call.

### B. Skill instructions and a verifiable MCP write

In Skills, select the bundled `documentation` row, then **Use in next task**.
If testing ECC, review and enable `affaan-m-ecc/verification-loop`, restart the
**demo** dashboard to activate its manifest, reopen its new launch URL and select
that skill instead. Enablement alone does not select a skill for a task.

Approve **new Markdown reports in diagnostics/** and **one confined OpenCode
session** for the next Send. Use engine OpenCode. Send:

```text
Use the selected skill within the currently approved tools. Call
smelter_write_diagnostic_markdown once with filename gui-bridge-smoke.md and
content exactly "SMELTER_GUI_MCP_SMOKE\n". Do not use shell commands or other
tools. Then report only the actual tool status, saved path, bytes and SHA-256.
```

Expected: one controller `write_diagnostic_markdown [MCP]` receipt with status
`written`, **22 bytes**, a real new file under the **demo** diagnostics directory,
and an execution record containing the selected skill ID/hash. Independently
check in PowerShell using the actual path from the receipt:

```powershell
Get-Item 'PASTE_THE_RECORDED_DEMO_PATH_HERE' | Select-Object FullName,Length
Get-FileHash 'PASTE_THE_RECORDED_DEMO_PATH_HERE' -Algorithm SHA256
```

Do not count a model paragraph claiming success without a receipt/file as a pass.
If the filename already exists, the expected result is a no-overwrite refusal;
use a new filename for a separate new test.

### C. Read-only inventory

Select the exact `inputs\inventory` path from `inputs\manifest.json` in the
next-message folder field, approve read-only inventory, and approve one OpenCode
session again. Send:

```text
Call smelter_inventory_directory for relative_path "." with max_depth 3.
Report files_observed, directories_observed, extensions_observed, scan_complete,
errors, and the file names/sizes returned. Do not read file content or infer
game, engine, character or package identities.
```

Expected: `inventoried`, **3 files**, **1 directory**, `.txt: 2`, `.json: 1`,
`scan_complete: true`, no errors. Entry file sizes sum to **26 bytes**. This
sum comes from the three returned file entries; the inventory API does not
provide a separate total-bytes field. The sibling `outside` directory must not
appear.

### D. Folder scope and one-Send permission reset

With the same read-only inventory grant, ask:

```text
Call smelter_inventory_directory with relative_path "../outside" and max_depth 1.
Report the actual rejection. Do not substitute another path or claim its content.
```

Expected: a controller error/rejected scope and no outside content. If Qwen
refuses without calling a tool, record **MODEL_REFUSAL**: that is safe behavior,
but it does not independently prove backend path enforcement. The automated
contracts test enforcement without relying on model cooperation.

Now send a new report request **without reapproving the write permission**.
OpenCode session approval must also be renewed for a new agent Send. The report
tool must not be exposed/accepted and no file should be created. Native reads of
the permitted source snapshot remain available; permission reset does not mean
that the model has no source access.

### E. Stop, refresh and retained evidence

Start a sufficiently long explanation, press **Stop** while generating, and
refresh the page during or after cancellation. Expect a settled cancelled state,
no second job, and persisted conversation/tool receipts. A fixed tool operation
already in progress may finish before the worker settles. Its write is not
rolled back. The interface must not report future actions as completed.

If the task finishes before Stop, record **NOT_EXERCISED** and retry once with a
longer explanation. The automated socket/process cancellation tests cover the
deterministic backend path. No new PowerShell windows should appear.

### F. GLB viewer and animations — no model needed

Use **+** → GLB and attach `inputs\two-clips.glb` from the evidence directory.
This is a generated orange triangle, not a game character.

Expected: one mesh; two clips **Lift_1s** and **Slide_2s**, with embedded keyframe
durations of **1 second** and **2 seconds**. Load preview, switch and play both
clips. Set a display label, refresh and check that it persists. Export a PNG and
a short WebM, then release/reload the preview. The original GLB's SHA-256 must
stay equal to `inputs\manifest.json`; labels are stored as application metadata.

If the local `@google/model-viewer@4.1.0` bundle is absent, the demo report says
viewer **BLOCKED**. Install it explicitly in the original checkout, then prepare
a new demo:

```powershell
npm install --prefix .smelter/tooling/model-viewer --ignore-scripts --save-exact @google/model-viewer@4.1.0
```

Qwen is not required for browser rendering. Approving GLB metadata inspection
does not establish visual understanding or automatic animation naming.

### G. Optional visible CSS edit, validation and preview

Use a separate titled conversation. Select bundled **taste** and **Use in next
task**. Approve frontend workspace tools and one managed OpenCode session. The
fresh sibling workspace is already prepared; do not recreate it. Send:

```text
Use the selected taste design skill. Call frontend_workspace_info, then read
the current destination tools/dashboard/dashboard.py. Make one small CSS-only
change: give the existing Send button an obvious amber outline and more vertical
padding while retaining its existing contrast and disabled states. Preserve all
HTML, JavaScript, functions and API routes. Use replace_frontend_css with exact
current text and the supplied hash. Validate the workspace, then launch its
preview only if validation passes. Report actual receipts. No shell commands.
```

The OpenCode tool names use the `smelter_` prefix; the agent may add it when
calling these registered tools. Expected: a file card with expandable old bytes,
updated CSS and a changed hash; source unchanged; fixed Python/JS checks pass;
one owned preview on **8770** with a recorded URL/token and bounded lifetime.
Open that URL and verify the amber Send button yourself. The preview can use
synthetic responses; it is not proof of another live Qwen task.

Missing Python/Node images means validation/preview **BLOCKED**. The frontend permission remains CSS-only. For general source replacements use the separate [ECC coding workspace](ECC_CODING_WORKSPACE.md) permission and tools; they create a new copy and do not launch a general code preview.
Do not delete or reset the original `C:\SMELTERV2` to bypass a baseline error.

### H. Optional existing REA connection

On the original app, if REA is installed/enabled, approve only its capability
check and ask for the actual `rea_capabilities` result. Installed/discovered is
not proof of decompilation or extraction. This smoke test does not inspect or
launch `D:\Epic\Darksiders`. Blender's skill remains instruction-only until a
modeling adapter is connected.

## 4. Results and diagnosis

Record manual outcomes in the generated `MANUAL_RESULTS.md`. Check off only
observed results. Keep screenshots free of the launch token.

| Outcome | Meaning / next action |
|---|---|
| PASS | The requested automated checks succeeded; manual GUI items remain separate |
| BLOCKED / exit 2 | Missing prerequisite; use the named prerequisite, no host fallback |
| FAIL / exit 1 | Actual contract/runtime/evidence error; inspect that phase's log |
| Model timeout / no tool call | Model-side task failure or latency; compare request, receipts and limits before blaming MCP |
| Receipt says written, model follow-up fails | The completed write still exists; inspect retained bytes, do not assume rollback or repeat blindly |
| Native activity reported only | OpenCode observation, not an independent SMELTER controller receipt |
| Old frontend baseline rejected | Preserved prior workspace; use the fresh isolated demo rather than destructive cleanup |
| ECC instructions work | The selected instruction bridge works; full ECC plugin parity is not established |

The evidence folder contains phase logs, `summary.json`, `SUMMARY.md`, known
inputs and expected hashes, and `runtime-evidence/` with MCP/controller audits,
chat execution metadata and the actual saved report. Even a failed runtime run
retains the disposable task's available evidence before cleanup. It never copies
the production database or user credentials. Logs redact common token/password
forms; review diagnostic content before sharing it.

See [ECC compatibility](ECC_COMPATIBILITY.md), [agent bridge plan](AGENT_BRIDGE_PLAN.md)
and [runtime operations](../tools/dashboard/OPENCODE_RUNTIME.md).

## Optional ECC coding acceptance

Use `python tools/analysis/home_smoke.py --live --ecc --coding --prepare-demo` to add the pinned ECC TDD instruction and an actual isolated RED/fix/GREEN test. The Python test image is required. This profile uses 32K context / 1,024 output / 300 seconds / thinking off; the earlier report smoke keeps its own smaller profile. Expect nine coding MCP calls for the deterministic synthetic fixture, two saved code files, an assertion failure before the fix, passing tests afterward, a current-tree review and confirmed cleanup. A real model may use a different number of permitted calls. Audits, proposals, original/fixed hashes, RED/GREEN logs and saved code are retained in `coding-runtime-evidence/`. Live model quality remains a local acceptance item.
