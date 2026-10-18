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
