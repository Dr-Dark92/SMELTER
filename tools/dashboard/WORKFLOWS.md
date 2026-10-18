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
