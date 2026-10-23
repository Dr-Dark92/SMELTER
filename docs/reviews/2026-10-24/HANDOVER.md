# Handover — laptop deployment, 2026-10-24

Read with the [review](REVIEW.md) and the [next plan](NEXT_PLAN.md).

## Repository

| Item | State |
| --- | --- |
| Branches | `main` and `SMELTERV1` both at `72f0758` on GitHub; earlier `SMELTERV1` work was fast-forwarded into `main`. Work on `main` from now on |
| Commits this session | `1fbf140` Windows test fix · `ddb5ed5` requirements file · `c069224` installer · `96918be` setup steps · `0552c21` Ghidra + JDK · `4905eb6` WSL platform check · `54ab348` hypervisor fix · `d8c4676` OpenCode read rules · `72f0758` keep task access |
| Tests | `tools/dashboard` 424 pass (8 skipped) · 4 JS test files · `tools/setup` all pass · `tools/analysis` 30 pass |
| Untracked | `.smelter/` only (runtime state; see C10) |
| Git identity | Repo-local `Dr-Dark92 <mkss1992@hotmail.com>`; no global identity on this laptop |

## Machine state

Everything in `system-requirements.json` is installed. A dry run reports every setup step `done`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\setup\install_missing.ps1 -DryRun
```

| Item | Location / value |
| --- | --- |
| Python | `C:\Users\Dr.Dark92\AppData\Local\Programs\Python\Python313\python.exe` — **not on PATH**; use the full path |
| JDK 21 | Microsoft OpenJDK, user `JAVA_HOME` set by Ghidra setup |
| Ghidra | `C:\Tools\Ghidra`, user `GHIDRA_INSTALL_DIR`, `REA_ANALYSIS_PROVIDER=ghidra` |
| npm tooling | `.smelter/tooling/{model-viewer,rea,browser}` |
| Docker images | `python:3.12-alpine` `sha256:b658b05c…815d` · `node:22-alpine` `sha256:fe4f6d74…9914` · `smelter-opencode:1.19.3` `sha256:edc523da…cfeb` |
| Database | `C:\SMELTER-DB\smelter.sqlite3` (pointer in `.smelter/database-location.json`) |

### Saved dashboard configuration

| Setting | Value | Note |
| --- | --- | --- |
| Extensions | 7z, blender, ffmpeg, ollama, opencode enabled | REA not enabled yet |
| Models | reasoning and lightweight `qwen3.5:4b` | |
| Runtime | 32768 context, thinking **on**, 2048 output, **180 s** | Set thinking off and 1024 output. After Phase 0 the OpenCode task has its own timeout (default 900 s); the 180 s now bounds each model turn only |
| Confined execution | all three image IDs saved | |
| Locations | Original source `C:\SMELTER` (read), V2 `C:\SMELTERV2` (read/write/execute), diagnostics (read/write), `C:\SMELTER\skills` (read) | |

## Start the dashboard

```powershell
Set-Location C:\SMELTER
& "C:\Users\Dr.Dark92\AppData\Local\Programs\Python\Python313\python.exe" tools/dashboard/dashboard.py
```

Docker Desktop and Ollama must be running first. Open the printed URL; it changes on each restart.

## Verified live this session

| Check | Evidence |
| --- | --- |
| Ollama on GPU | `ollama ps` showed `50%/50% CPU/GPU` for `qwen3.5:4b` after the driver update and an Ollama restart |
| Direct chat | Job `e25786ef…` done in 14.4 s |
| OpenCode container, permissions, cleanup | Audit `47b2a3b2…`: four `read` calls `completed` for `/workspace/skills` and each `SKILL.md`; `cleanup_confirmed: true` |
| OpenCode full answer | **Not yet.** That task ended `partial` at the 180 s timeout |

## Known traps on this laptop

- **GPU:** keep the NVIDIA driver current. Driver 528 crashed Ollama's Vulkan backend. If `ollama ps` shows `100% CPU` after a reboot, quit and restart Ollama.
- **Docker:** if the engine will not start, run the installer dry run; `wsl_platform` reports a pending restart or BIOS issue.
- **Pushing:** this tool session cannot authenticate to GitHub; pushes are run by the operator.
- **Native `opencode`:** typing `opencode` in a terminal starts the cloud-backed CLI, not the dashboard route. Do not run its `/update`.
- **Prompts for OpenCode:** refer to project files as `skills/...` or `/workspace/skills/...`, never `C:\SMELTER\...`.

## Remaining from earlier plans

The 2026-10-21 [workflow-audit action plan](../2026-10-21/workflow-audit/ACTION_PLAN.md)
items 1–14 are still open; item 1 (home live acceptance) needs the desktop rig
with `qwen3.5:9b`. Its full smoke runner hard-requires `qwen3.5:9b` and will
report BLOCKED on this laptop.
