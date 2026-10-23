# SMELTER V1 — System Requirements

This is the requirements baseline for the `SMELTERV1` branch. Requirements are divided into **vanilla**, **developer**, and **optional extension** categories. Do not install every optional tool by default.

## Vanilla source installation

| Requirement | Baseline | Policy |
| --- | --- | --- |
| Operating system | Windows 10/11 x64, or a supported Linux/macOS installation | Target platforms; compatibility must be validated |
| Python | 3.12 or newer, with `venv` and `pip` | Required to run the current source-based Python backend; Python 3.14 compatibility needs testing |
| Browser | Current Chromium-, Firefox-, or WebKit-based browser | Required for the local web console |
| Network | Loopback (`127.0.0.1`) | No internet required for vanilla operation |
| RAM / disk | To be measured during V1 validation | No unsupported minimum claimed yet |

The vanilla runtime must start without an AI model, external skill package, Node.js, Java, Docker, Blender, or Ghidra. The current Python package requirements are in [`requirements.txt`](requirements.txt), intentionally without third-party dependencies.

## Requirements file

[`system-requirements.json`](system-requirements.json) is the machine-readable source for:

- **tools**: executables, their version checks, winget IDs or pinned npm packages;
- **setup**: project steps that run after the tools are installed (below);
- **profiles**: which tools and setup steps each kind of use needs.

The requirements scanner, the setup wizard's profile preview, the approved winget queue and `install_missing.ps1` all read it. To add or change anything, edit that file; the tables below describe it.

| Setup step | What it does | Needed for |
| --- | --- | --- |
| `mcp_sdk` | `pip install -r tools/dashboard/requirements-mcp.txt` (`mcp==1.30.0`) | Built-in MCP tools, OpenCode |
| `ollama_model` | `ollama pull qwen3.5:9b` (an installed `qwen3.5:4b` also counts) | Chat, OpenCode; the full smoke test expects `9b` |
| `image_python` | `docker pull python:3.12-alpine` | Confined Python tests |
| `image_node` | `docker pull node:22-alpine` | Confined Node tests, CSS preview, OpenCode image base |
| `image_opencode` | `docker build -f tools/dashboard/Dockerfile.opencode -t smelter-opencode:1.19.3 .` | Managed OpenCode; select its `sha256` ID in Settings |
| `glb_viewer` | `npm install --prefix .smelter/tooling/model-viewer @google/model-viewer@4.1.0` | GLB preview and PNG capture |
| `rea` | `npm install --prefix .smelter/tooling/rea rea-agents@6.7.0` | REA analysis |
| `playwright`, `chromium` | Playwright 1.56.1 in `.smelter/tooling/browser` plus its Chromium | Full smoke test only |

Profiles: `local_ai`, `opencode_agent`, `media`, `reverse_engineering`, `smoke_test`, `developer`, `game_modding`.

To install everything that is missing, run from an **administrator** PowerShell in the checkout:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\setup\install_missing.ps1 -DryRun   # show the plan only
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\setup\install_missing.ps1           # run after typing yes
```

`-Profile opencode_agent` limits the run to one profile; `-Only docker,image_opencode` to named tools or steps. The script prints exact commands, marks steps **blocked** when a prerequisite is not ready (for example Docker Desktop not started), asks before changing anything, does not auto-accept agreements, and summarizes each result. Docker steps need Docker Desktop running. After installing WSL or Docker, restart Windows, start Docker Desktop once, open a new PowerShell and run the script again to finish the setup steps.

## What each dashboard feature needs

| Feature | Needs |
| --- | --- |
| Dashboard | Python 3.12+ and a browser |
| Direct chat | Ollama running at `127.0.0.1:11434` with a model installed (default `qwen3.5:9b`; `qwen3.5:4b` for GPUs with 4 GB or less) |
| Skills | Nothing extra. A skill provides instructions only; it does not install software or require WSL |
| Built-in MCP tools | Pinned MCP SDK: `python -m pip install -r tools/dashboard/requirements-mcp.txt` |
| Managed OpenCode agent | Ollama + model, MCP SDK, **Docker Desktop** (which needs **WSL 2** on Windows) and the pinned OpenCode 1.19.3 container image built per [OPENCODE_RUNTIME.md](tools/dashboard/OPENCODE_RUNTIME.md). The native `opencode` CLI is not used |
| Frontend tests/preview and coding workspace tests | **Docker Desktop** (WSL 2 on Windows). There is no host fallback |
| GPU inference | A current NVIDIA driver. Old drivers can make Ollama fall back to an unstable backend or to the CPU |

## Developer conveniences

| Tool | Purpose | Policy |
| --- | --- | --- |
| Git | Version control and branch management | Recommended for source development |
| GitHub CLI (`gh`) | Authenticated GitHub workflows | Optional |
| PowerShell 7 | Windows automation | Optional; Windows PowerShell may suffice for basic commands |
| Node.js LTS + npm | JavaScript/TypeScript builds and tooling | Optional until a selected frontend/tool requires it |
| C/C++ compiler and build tools | Native extension compilation | Optional, extension-dependent |
| WSL 2 | Linux backend for Docker Desktop on Windows | Required for Docker features on Windows; `wsl --install` as administrator, then restart |
| Docker Desktop / Docker Engine | No-network containers for managed OpenCode, frontend tests/preview and coding workspace tests | Required for those features; not needed for the dashboard or direct chat |

## Extension-dependent runtimes and applications

| Tool | Enabled for | Policy |
| --- | --- | --- |
| Java JDK | Ghidra and Java-based extensions | Optional; match JDK version to the chosen application release |
| Blender | 3D asset conversion, scene and animation automation | Optional |
| Unreal Engine / Unity | Engine-specific workflows | Optional; license and version dependent |
| Ghidra | Reverse engineering | Optional |
| FFmpeg | Audio/video processing | Optional |
| 7-Zip | Archive workflows | Optional |
| Ollama / other local AI runtime | User-selected AI core | Required for chat and OpenCode |
| OpenCode 1.19.3 container image | Managed OpenCode agent route | Required for that route; operator-built, never pulled or built by SMELTER during a task |
| GPU drivers and acceleration libraries | GPU-enabled local inference or graphics | Optional, hardware/model dependent; keep NVIDIA drivers current |
| Playwright and browser binaries | Browser automation/testing | Optional; install only when selected |
| SearXNG / internet search provider | Internet research | Optional; network required |
| MCP adapters or gateway | External tool/agent compatibility | Optional |

## Setup — current source checkout

```powershell
cd C:\SMELTER
git fetch origin
git switch SMELTERV1
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe tools\web\smelter_console.py
```

If the branch is not yet tracked locally, use `git switch --track origin/SMELTERV1` instead of `git switch SMELTERV1`. The commands assume the Python launcher (`py`) is available on Windows. The console is a legacy development entrypoint, not yet the V1 first-run wizard.

## Controlled optional installation queue (V1.2)

The web wizard can now prepare and run a separate, explicitly approved Windows `winget` queue for allowlisted optional tools. This is **opt-in**: selecting a profile does not install anything. The queue displays exact package IDs and commands before approval; execution is sequential and stops on first failure. Each successful command is followed by a requirements rescan to verify the tool is detected.

Supported allowlist (every tool with a `winget` ID in `system-requirements.json`): Git (`Git.Git`), Node LTS (`OpenJS.NodeJS.LTS`), GitHub CLI (`GitHub.cli`), WSL (`Microsoft.WSL`), Docker Desktop (`Docker.DockerDesktop`), Ollama (`Ollama.Ollama`), Blender (`BlenderFoundation.Blender`), FFmpeg (`Gyan.FFmpeg`), 7-Zip (`7zip.7zip`). WSL and Docker Desktop usually need elevation and a restart, so expect to finish them in an administrator terminal. This feature requires Windows and `winget`. It deliberately does **not** use silent mode, automatically accept agreements, elevate privileges, or install dependencies merely because a profile was selected. Some packages may require an interactive prompt or elevation that this browser-driven background process cannot satisfy; those installs may fail and must be completed manually in a terminal. Installation rollback and cancellation are not implemented. Restarting the shell may be needed for PATH updates before verification.

Run all tests with `py -3 -m unittest discover -s tools\setup -p "test_*.py" -v`. Windows integration and actual `winget` installs have not yet been verified.

## Optional profile preview (V1.1)

The local setup wizard now exposes **Developer**, **Local AI**, **OpenCode Agent** (Ollama, WSL, Docker), and **Game Modding** profiles in addition to Vanilla. Profile selection produces a read-only dependency preview using the requirements scanner. Missing or unverified dependencies are marked for manual review. **No optional tool installation commands are generated or executed.** The approved Vanilla setup flow remains independent of preview selections.

Profiles are declared in `system-requirements.json` and resolved by `tools/setup/profiles.py`; their unit tests are in `tools/setup/test_profiles.py`. Re-run all setup tests with:

```powershell
py -3 -m unittest discover -s tools\setup -p 'test_*.py' -v
```

## CLI-launched web setup wizard (V1 preview)

On Windows, from the SMELTER checkout:

```powershell
cd C:\SMELTER
git pull origin SMELTERV1
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\setup\start_setup.ps1
```

The CLI starts a loopback-only web app at `http://127.0.0.1:8767/` and opens a browser with a per-session authorization token. Leave the PowerShell window open while using the wizard. Review the plan and explicitly approve it before the backend runs a fixed sequence: create a local `.venv` if missing, run the requirements scanner, and run setup unit tests. Logs stream into the browser; no second terminal window is required.

This is an initial functional wizard, **not** a package-manager installer: it does not download dependencies or install Node.js, Java, Blender, FFmpeg, 7-Zip, or other optional tools. Do not expose the loopback service through a proxy or port-forward. The wizard and its browser integration require local Windows testing.

## Read-only requirements scanner (implemented; Windows verification pending)

Run the scanner before installing optional tools:

```powershell
.\.venv\Scripts\python.exe tools\setup\check_requirements.py --output diagnostics\requirements-local.json
.\.venv\Scripts\python.exe -m unittest discover -s tools\setup -p test_check_requirements.py -v
```

The scanner uses Python's standard library, checks executable presence and version commands, and writes an explicit JSON report. It performs no installation, network access, or system modifications. The report omits executable paths. Some Windows command shims are marked `detected_unverified` rather than executed. The report should be reviewed before sharing; version output may still include local metadata.

## Planned environment validation (remaining work)

1. Detect OS, architecture, Python version, and available tools without changing the system.
2. Evaluate only the dependencies required by the user's selected extensions.
3. Present exact installation actions and sources for approval.
4. Verify installed executable versions and health checks.
5. Save an environment report, without credentials or private system information.

**Security:** No automatic downloads or execution of third-party installers without user approval. Do not add dependencies solely because a skill mentions them. Pin versions and verify provenance when a dependency is introduced.
