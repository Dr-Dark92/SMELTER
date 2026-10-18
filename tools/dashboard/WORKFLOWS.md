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
