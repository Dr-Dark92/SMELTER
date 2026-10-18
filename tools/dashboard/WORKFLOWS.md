# SMELTER V1.4 — workflow planning (phase 1)

The dashboard now offers **Asset preflight** (7-Zip → Blender → FFmpeg) and **Media preflight** (FFmpeg). These are dependency-validation plans, not real asset processing workflows.

The browser calls `GET /api/workflows` for definitions and `POST /api/workflows/plan` with `{"workflow_id":"asset_preflight"}` for a dry-run report. The API requires the existing session token and enforces the same Origin policy as the extension manager.

Reports contain an ordered list of steps, readiness/blocking reasons, timestamp, run identifier, and explicit `executed: false` and `permissions_granted: false` flags. No external process is launched; no project data is read or written. The report is not persisted.

Future phases: explicit permission approvals, sandboxed tool execution, input/output validation, durable reports and cancellation.

To test on Windows:

```powershell
cd C:\SMELTER
git pull origin SMELTERV1
py -3 -m unittest discover -s tools\dashboard -p "test_*.py" -v
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\dashboard\start_dashboard.ps1
```

## V1.4.1 — input validation and report history

The planner accepts an optional `inputs` array of up to 16 **absolute** file or directory paths. Input validation checks metadata only; it does not open, hash, or process file contents. Missing paths block the dry-run report. Empty inputs remain valid for capability-only preflight.

Each preview is saved as a unique UUID-named JSON file under `.smelter/reports/`. Existing report files are not overwritten. `GET /api/workflows/reports` returns the 20 most recent valid reports (bounded at 128 KiB per report). Reports contain the paths the user supplied, so avoid including sensitive locations in screenshots or shared logs.

The output validation status is `not_applicable` until actual execution is introduced. No files under `projects/` are modified. No tools are executed.

The dashboard's previous instance must be stopped before launching the new version on port 8768.

## V1.4.2 — approved archive inspection

The dashboard includes a separate archive inspection form. It requires a path to an existing regular archive file and an approval checkbox for each request. The server also requires the literal approval value `LIST ARCHIVE`, an enabled 7-Zip extension, and a verified 7-Zip executable.

Only `7z l -slt -bd -- <absolute-path>` is allowed, invoked without a shell and with a 20-second timeout. It captures at most 12,000 characters from each output stream and saves a report with `mode: approved_read_only`. No extraction, modifications, or external downloads are requested.

The initial version does not provide process isolation or a sandbox. Inspect only archives you trust; even listing a malicious archive exposes the installed 7-Zip parser to untrusted data. Restart the dashboard after pulling changes.

## V1.4.3 — FFprobe metadata inspection

The dashboard has an additional read-only media inspection form. It requires a regular file, enabled and verified FFmpeg extension, and explicit `PROBE MEDIA` approval per request. The implementation resolves `ffprobe.exe` adjacent to the detected `ffmpeg.exe` and invokes it directly with `-v error -show_format -show_streams -of json -i <path>`, without a shell. Timeout: 20 seconds. Captured JSON is bounded at 32,000 characters; invalid/oversized metadata results are failures. Reports use `mode: approved_read_only` and are saved in `.smelter/reports`.

FFprobe parses media, so test only trusted files; this is not a sandbox and does not yet isolate processes. No transcoding or generated media outputs are requested.

## V1.4.4 — Blender version capability check

The dashboard now supports an explicitly approved `CHECK BLENDER` action. It requires an enabled Blender extension, a verified scanner status and a discovered `.exe`. It runs exactly `blender.exe --version` without shell, file inputs, Python expressions or project loading. Timeout is 20 seconds; output is bounded and saved to the existing report history.

This verifies executable launch and version output only. It does **not** yet validate Blender's embedded Python environment, import/export add-ons, headless rendering, asset parsing or scene operations. Those require separate narrowly scoped probes with their own permissions and tests.

## V1.5.0 — optional Ollama / Qwen discovery

Enable the Ollama extension in the dashboard, then select **Discover local models**. The API reads `GET http://127.0.0.1:11434/api/tags` using Python's standard library with a 3-second timeout and a 256-KiB response cap. The dashboard only displays installed model names and sizes. Qwen models are displayed when present; nothing is downloaded automatically. Ollama must already be running to respond.

This phase does not send prompts, invoke models, launch an agent, start Ollama, or access project files. Model selection, OpenCode integration, and execution approvals are future phases. The endpoint is available only through the dashboard's existing session-token protection.
