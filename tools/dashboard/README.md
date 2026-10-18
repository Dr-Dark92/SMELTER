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

No AI, bundled optional tools, or network downloads are required.
