# Laptop deployment review — 2026-10-24

First full install of `main` (`72f0758`) on a fresh Windows 11 Home laptop, from
clean checkout to a working direct-chat and managed OpenCode task. This review
records every problem met on the way, what was fixed, and what is still wrong.
The [handover](HANDOVER.md) has the resulting machine state and the
[next plan](NEXT_PLAN.md) the ordered work.

## Rig

| Item | Value |
| --- | --- |
| OS | Windows 11 Home 26300 (no Hyper-V; WSL 2 backend only) |
| CPU / RAM | Intel i7-8750H / 32 GB |
| GPU | GTX 1050 Ti Max-Q, 4 GB, compute capability 6.1, driver 582.78 (CUDA 13.0) |
| Python / Node | 3.13.15 (not on PATH) / 24.22.1 |
| Ollama / model | 0.40.10 / `qwen3.5:4b` (3.4 GB, about 50 % GPU / 50 % CPU) |
| Docker / WSL | Engine 29.9.2 / WSL 3.0.3 |

## Outcome

| Area | Result |
| --- | --- |
| Dashboard tests | 424 + 4 JS files pass on Windows; one Windows-only flaky test fixed |
| Direct chat | Works: about 14 s for a one-line reply. No project context, so answers about SMELTER are invented |
| Managed OpenCode | Works end to end after one rule fix: container start, four real reads of `skills/`, cleanup confirmed. Task then hit the 180 s timeout because of runtime settings, not code |
| Setup | Every tool and setup step now comes from `system-requirements.json` and installs with `tools/setup/install_missing.ps1` |

## Problems found and their disposition

Severity: **P0** blocks first use, **P1** breaks a workflow, **P2** friction or risk.

### Fixed this session

| # | Sev | Problem | Fix (commit) |
| --- | --- | --- | --- |
| L01 | P1 | `test_jobs_reject_overlap_and_stop_cooperatively` always failed on Windows: the job thread still held SQLite when the temp folder was deleted (`WinError 32`) | Test waits for persistence under `Jobs.lock` (`1fbf140`) |
| L02 | P0 | `REQUIREMENTS.md` called Docker "optional" and never named WSL or OpenCode; no list of what each feature needs | Feature → requirement table; machine-readable `system-requirements.json` read by scanner, profiles and winget queue (`ddb5ed5`) |
| L03 | P0 | Requirements listed executables but not the project setup after them: MCP SDK, model, three Docker images, GLB viewer, REA, Playwright/Chromium | `setup` section with typed steps and profiles; installer checks done/todo/blocked (`c069224`, `96918be`) |
| L04 | P1 | Ghidra not in requirements; seven bootstrap scripts only found Temurin JDK while the catalog installs Microsoft OpenJDK | Ghidra setup step; bootstraps accept both JDKs; test guards Temurin-only scripts (`0552c21`) |
| L05 | P0 | Docker engine never started: winget `Microsoft.WSL` does not enable Virtual Machine Platform, and enabling it needs a restart | `wsl_platform` step checks feature, pending restart and firmware (`4905eb6`) |
| L06 | P1 | That check then reported "virtualization off": Windows reports `VirtualizationFirmwareEnabled = False` while its hypervisor runs | Trust `HypervisorPresent` (`54ab348`) |
| L07 | P0 | Every OpenCode native read was denied. OpenCode checks `path.relative(worktree, file)`; the non-Git `/workspace` snapshot has worktree `/`, so reads arrive as `workspace/skills/...`, which no allow rule matched | Root-worktree patterns for allows **and** exclusion denies; tests use OpenCode's own matcher and fail on the old rules (`d8c4676`) |
| L08 | P2 | Task access cleared every grant and the OpenCode approval after each Send | Opt-in, unticked-by-default "Keep these permissions for following sends" (`72f0758`) |
| L09 | P2 | Installer under Windows PowerShell 5.1: native stderr aborted the script; `docker image inspect` hung on a half-started engine; `npm.ps1` blocked by execution policy | Continue-on-stderr with exit codes, 20 s probe timeout, prefer `npm.cmd` (`96918be`) |

### Open — first start-up and configuration

Nothing below is configured by deployment; each was found by hitting an error.

| # | Sev | Problem | Evidence |
| --- | --- | --- | --- |
| C01 | P0 | All extensions start disabled. Chat shows "Ollama extension disabled" until each tool is enabled in Settings → Installed tools | `config_store.py` default `{"enabled": []}` |
| C02 | P0 | Reasoning model falls back to `qwen3.5:9b` when unset, even if only another model is installed. The model screen has "reasoning" and "lightweight" rows; picking the wrong one leaves chat on a missing model | `task_contract.py:10`, `component_controls.py:116`, `chat_inference.py:11` |
| C03 | P0 | The three Docker image IDs must be copied by hand from `docker image inspect` into Settings → Confined execution | `sandbox.py` default all `None` |
| C04 | P0 | The engine dropdown lists OpenCode first, so a new install defaults to OpenCode and the first Send fails with "Check managed OpenCode and approve this session in Task access" | `dashboard_shell.js:48` |
| C05 | P1 | Runtime defaults are the desktop "home" profile (32 K context, thinking on, 180 s). Choosing a profile replaces every value, so changing context silently reset timeout and thinking — the cause of today's OpenCode timeout | `runtime_settings.py` `save_runtime` requires all keys; audit `47b2a3b2…` |
| C06 | P1 | One `timeout_seconds` governs both direct chat and OpenCode. OpenCode on a 4 GB GPU needs several minutes; direct chat does not | `opencode_runtime.py:357` |
| C07 | P1 | No hardware awareness: nothing picks model size, context or offload from VRAM. The existing `Configure-Smelter-GpuProfile.ps1` is not wired into setup | — |
| C08 | P1 | Storage location must be chosen by hand on first open; there is no default | `database.py` `select_database` |
| C09 | P2 | `start_dashboard.ps1` needs `py` or `python` on PATH; the installer finds Python by path, the launcher does not | `start_dashboard.ps1` |
| C10 | P2 | `.smelter/` (runtime state, audits, tooling) is not git-ignored and shows as untracked | `.gitignore` |
| C11 | P2 | Ollama and native OpenCode update themselves (0.40.9 → 0.40.10, 1.19.3 → 1.19.4) while the container stays pinned at 1.19.3 | observed |

### Open — workflow

| # | Sev | Problem | Evidence |
| --- | --- | --- | --- |
| W01 | P1 | The prompt budget counts 2 bytes per token, about double the real size for English and code. OpenCode's own instructions plus one folder listing exceeded 14.8 K at 16 K context | `context_budget.py:13`; audit `6c5c152d…` |
| W02 | P1 | OpenCode gets only the `read` tool. A 4 B model repeatedly calls `glob`/`list`, which fail as "unavailable tool 'invalid'" | audits `52306a70…`, `6c5c152d…` |
| W03 | P1 | Three different "access" ideas confuse users and the model: registered locations (Workspaces & Access), per-Send grants (Review task access), and the container's `/workspace` snapshot. The model was given `C:\SMELTER\skills` and could not map it | message 10 |
| W04 | P2 | Direct chat has no project context, so "what is SMELTER?" produced an invented answer | message 2 |
| W05 | P2 | Native `opencode` in a terminal uses OpenCode's cloud model by default and is unrelated to the dashboard route | operator confusion |
| W06 | P2 | The setup wizard (port 8767) and the dashboard (8768) are separate; the dashboard cannot show or run missing setup steps | — |
| W07 | P2 | GPU problems are silent: an old NVIDIA driver crashed Ollama's Vulkan backend, and after reboot Ollama started CPU-only until restarted | Ollama `server.log` |

### Open — UI/UX

| # | Sev | Problem |
| --- | --- | --- |
| U01 | P0 | No first-run checklist. A new user must discover Settings → Installed tools, Ollama models, Runtime, Confined execution and Task access in the right order |
| U02 | P1 | Error messages state the rule but not where to fix it ("Ollama extension disabled", "approve this session in Task access") and have no link or button to the setting |
| U03 | P1 | Readiness is scattered: Ollama, Docker, images, OpenCode check and model live on five screens; there is no single "ready / what's missing" view |
| U04 | P1 | Profile buttons overwrite without showing what changes |
| U05 | P2 | Per-Send approval controls sit in a dialog away from the composer; the active engine, model and permissions are not visible next to Send |
| U06 | P2 | A failed or partial OpenCode task shows one line; the reads it did, the time spent and the limit hit are only in the audit file |
| U07 | P2 | The launch URL and token change on every restart, and HTML changes need a restart to appear |

## Method

Evidence comes from this session's commands: test runs, `install_missing.ps1`
dry runs, Docker/WSL/Ollama logs, read-only SQLite queries of
`C:\SMELTER-DB\smelter.sqlite3`, audit files in `.smelter/tool-runs/`, and
OpenCode 1.19.4's bundled source for the read-permission and matcher logic.
Model replies were live Qwen 4 B on this laptop; no synthetic fixtures.
