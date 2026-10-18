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

## Developer conveniences

| Tool | Purpose | Policy |
| --- | --- | --- |
| Git | Version control and branch management | Recommended for source development |
| GitHub CLI (`gh`) | Authenticated GitHub workflows | Optional |
| PowerShell 7 | Windows automation | Optional; Windows PowerShell may suffice for basic commands |
| Node.js LTS + npm | JavaScript/TypeScript builds and tooling | Optional until a selected frontend/tool requires it |
| C/C++ compiler and build tools | Native extension compilation | Optional, extension-dependent |
| Docker Desktop / Docker Engine | Containers and isolated services | Optional |

## Extension-dependent runtimes and applications

| Tool | Enabled for | Policy |
| --- | --- | --- |
| Java JDK | Ghidra and Java-based extensions | Optional; match JDK version to the chosen application release |
| Blender | 3D asset conversion, scene and animation automation | Optional |
| Unreal Engine / Unity | Engine-specific workflows | Optional; license and version dependent |
| Ghidra | Reverse engineering | Optional |
| FFmpeg | Audio/video processing | Optional |
| 7-Zip | Archive workflows | Optional |
| Ollama / other local AI runtime | User-selected AI core | Optional |
| GPU drivers and acceleration libraries | GPU-enabled local inference or graphics | Optional, hardware/model dependent |
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

## Planned environment validation (not implemented yet)

1. Detect OS, architecture, Python version, and available tools without changing the system.
2. Evaluate only the dependencies required by the user's selected extensions.
3. Present exact installation actions and sources for approval.
4. Verify installed executable versions and health checks.
5. Save an environment report, without credentials or private system information.

**Security:** No automatic downloads or execution of third-party installers without user approval. Do not add dependencies solely because a skill mentions them. Pin versions and verify provenance when a dependency is introduced.
