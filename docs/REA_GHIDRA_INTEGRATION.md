# Qwen, REA and Ghidra integration

The intended route is the SMELTER GUI → managed OpenCode → Ollama →
`qwen3.5:35b-a3b` for reasoning. OpenCode's approved `smelter_` MCP calls return
through the host gateway to fixed REA/Ghidra operations. Credentials and native
analysis processes remain host-owned; the OpenCode container has no network.

## Requirements and instructions

`system-requirements.json` declares the `qwen35b_agent` profile, pinned
`rea-agents@6.7.0`, MCP 1.30.0, managed OpenCode 1.19.3, Java and Ghidra setup.
`tools/setup/install_rea_skill.py --enable` installs a compact supported-tool
workflow under `morluto-rea/reverse-engineer-anything`, retaining the exact
matching package's upstream SKILL.md and its SHA-256 as provenance. The compact
workflow is what Qwen receives; the upstream document is retained reference.
This installs no unrestricted MCP server and changes no Codex/native OpenCode
configuration. Restart the dashboard after adding instruction manifests.

After installation and live verification, stop the dashboard and preview
`python tools/setup/configure_agent_stack.py`. Its `--apply` mode selects the
35B reasoning model and a conservative 16K runtime on first selection, preserves
an existing saved Qwen runtime on repeat setup, enables OpenCode/MCP, and
adds execution-only locations for the two installed analysis runtimes. Existing
location rows, including denials, are preserved. It grants no target folder or
per-task tools, and preserves the lightweight-model choice.

The native REA CLI operations `rea_capabilities` and
`rea_inspect_pe_resources` remain distinct from SMELTER's `rea_ghidra_*` adapter.
Installed instructions, executable detection and successful analysis are
different readiness states. The integration's live verification is recorded
below when complete.

## Operations

The fixed Ghidra workflow imports an approved local binary into a new
application-owned project; lists/searches functions and strings; and inspects
cross-references and decompilation at selected addresses. Input hashes and
evidence files identify the analyzed bytes. It does not execute target programs
or run model-supplied Ghidra scripts. Decompiled code and target strings are
untrusted data.

The project directory is application-owned data at
`%LOCALAPPDATA%/SMELTER/GhidraProjects/<checkout-hash>/<analysis-id>`, with ten
projects per checkout and 256 MiB per retained project/evidence pair. Ghidra
rejects dot-prefixed directory components, so projects cannot be under
`.smelter`; input snapshots and JSON evidence stay there. Existing backup and
retention operations do not silently remove or back up these external projects.
Missing projects require reanalysis. Native parsing is a bounded trusted host
process, not a container sandbox.

REA tasks permit 16 tool calls. `rea_ghidra_analyze` has a fixed 180-second
native-process bound (210-second transport allowance); follow-ups have a
60-second native bound. Returned previews are at most 64 KiB while full bounded
JSON evidence is retained with its hash. Ghidra execution requires an explicitly
registered engine location with the `rea` operation, plus read permission for
the selected input folder. Instructions cannot expand these grants.

## Model settings

On the current 16 GB GPU / 64 GB RAM machine, begin with 16K context and one
active request. The 35B Q4 model is approximately 22 GB, so CPU/RAM offload is
expected. Do not automatically apply the 64K hardware-extreme preset. Retain 9B
as a selectable alternative. Installing the weights and selecting a saved model
are separate actions, and quality/performance require actual measurements.

## Melty

Melty is a separate fixed-endpoint host MCP connector. The current bridge exposes
read-only account/game lookup using the existing host sign-in; the model receives
no credential. The verified kit is installed as data. Building, artifact upload,
game launch and publishing remain separate adapters and are not enabled by a
lookup grant. See [Melty connector](MELTY_CONNECTOR.md).

## Verification

The real generated-ELF smoke passed analyze, functions, strings, incoming
references and a decompilation through the built-in MCP transport on Ghidra
12.1.4. It verifies a hand-encoded addition function without executing it.
`tools/analysis/smoke_ghidra.py` writes a fresh isolated checkout/database and
retained evidence. `smoke_qwen_ghidra.py --native-evidence PATH` additionally
requires live model calls and actual controller receipts through managed
OpenCode. No game binary, production mod, upload or public release is used.

Live acceptance on 25 October 2026 passed: Qwen `qwen3.5:35b-a3b`
(`72aac7c28be8`) requested real function search and Ghidra decompilation through
OpenCode/MCP, then produced a completed persisted result with controller
receipts. That two-tool fixture task took 47.1 seconds at 16K context; this is
one acceptance observation, not a general game-analysis benchmark. Ollama
reported 38% CPU / 62% GPU placement for the loaded model on this machine.

OpenCode pool repairs bind model/tool packets to an active task generation,
revoke dispatch before detaching, preserve the active bridge until operations
settle, discard aborted/failed workers, and block replacement after failed
cleanup. These repair review findings R03–R05. Source snapshots now include the
mandatory requirements catalog, and CI includes pushes/PRs on `main`.

This machine now explicitly retains 131,072 context / 8,192 output in both managed and native routes; see [current review fixes](REVIEW_FIXES_20261025.md).
