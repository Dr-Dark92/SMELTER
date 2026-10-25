> Latest status: read [current handover](../../CURRENT_HANDOVER.md) and [engine archive integration](../../ENGINE_ARCHIVE_CLI.md) first. This ledger is historical. The current native builder is confined MinGW-w64; engine CLIs and Universal Modder are installed, and Qwen remains at 128K.

# Progress ledger — 25 October 2026 (updated 14:23 Asia/Muscat)

Base `3f72721`; HEAD `982950b` on `fix/r07-r08-setup-lifecycle` (R07+R08 only).
Everything else is uncommitted. "Status" means the stated acceptance was observed
on this machine, not a claim about every game or machine.

| ID | Work | Status | Evidence / acceptance |
| --- | --- | --- | --- |
| S01 | Pull repository | Complete | Local checkout at base |
| S02 | Local AI/OpenCode prerequisites | Complete | Python/MCP, Docker, Ollama, pinned OpenCode image |
| S03 | Remove repeated OpenCode startup approval | Complete | Saved engine starts with the GUI; R06 keeps it working through Stop/Start |
| S04 | Qwen 35B | Complete | `72aac7c28be8`; SMELTER context 131,072 and output 8,192 since 25 Oct; 9B lightweight kept |
| S05 | REA package and instructions | Complete | Pinned 6.7.0; supported skill enabled |
| S06 | Fixed Ghidra tools | Complete for stated scope | Generated ELF, five operations, no target execution |
| S07 | Live Qwen/OpenCode/Ghidra loop | Complete for fixture | 47.1 s (earlier profile) |
| S08 | Melty kit | Complete | Pinned archive and per-file hashes |
| S09 | Melty host authentication | Complete | Existing sign-in referenced; nothing copied |
| S10 | Melty read-only lookup | Complete | On by default and remembered; GUI auto-check; live OpenCode task matched the raw result |
| S11 | Frontend workflow repair | Complete | Real container tests and preview pass |
| S12 | Requirements/docs | Complete for current changes | Catalog (`msvc`, `winget_override`, `native_game_mods`, `image_cpp`), REQUIREMENTS.md, GAME_MOD_TOOLS.md, MELTY_CONNECTOR.md, discovery docs, this pack |
| S13 | GTA × ARK mashup | **In progress (offline)** | Target: GTA V Enhanced host × ARK companion. Discovery and M1 design done; `mods/gta-ark/` offline parts built (C++ writer and skeleton ASI, Python 7/7, round trip). Blocked in-game: Script Hook V doesn't support 1.0.1158.16; UE4SS build and ARK BattlEye-off method undecided; loader installs need approval |
| S14 | Melty upload/test/publish | Open | No write tools |
| S15 | Visual/performance acceptance | Partial | Context sizes measured (16K–256K); R06 GUI checked; 375 px layout and real-game benchmarks not done |
| S16 | Durable handoff | Complete locally | This pack plus a regenerated checkpoint/manifest (base `982950b`); no remote backup |
| S17 | Melty desktop app → host OpenCode → local Qwen + SMELTER MCP | Complete for connection | `opencode.json` (backed up): `ollama` (`qwen3.5:35b-a3b-128k`) and `smelter` MCP (Melty lookup only). CLI runs used the SMELTER tool; operator saw the model in Melty's dropdown. No Melty builder task run yet. Unconfined route |
| S18 | SMELTER game-mod tools | Complete for first runs | `inspect_game_files`; `mods/` in the coding copy; `mods` and `cpp` confined profiles; `build_native_mod`; policy rows via `configure_native_build.py`. Qwen tests: (1) discovery correct; (2) GREEN plus a build, but a C++ bug compiled undetected; (3) portable C++ `cpp` GREEN plus a build in 114.7 s |
| S19 | MSVC Build Tools | Complete | VS 2022 Build Tools 17.14.42 with the C++ workload; a test program compiled and ran; `build_native_mod` real-compile tests pass |

## Review finding disposition (`diagnostics/REVIEW_20261024.md`)

| Finding | Status |
| --- | --- |
| R01 workspace catalog omission | Fixed, live verified |
| R02 main-branch CI filters | Fixed in local YAML; no remote run (not pushed) |
| R03 idle/stale OpenCode inference | Fixed |
| R04 premature bridge detach | Fixed |
| R05 replacement after failed cleanup | Fixed |
| R06 component/pool lifecycle | Fixed and live verified: default load → ready; Stop removes the container; Start re-warms it. Busy-task refusal and failed cleanup are unit-tested only |
| R07 installer exit status | Fixed, committed `982950b`: 0 complete or dry run, 1 failed, 2 incomplete; real dry run exit 0. A blocked real run wasn't forced |
| R08 web-setup children | Fixed, committed `982950b`: owned job or process group, deadlines, output caps, cancel, shutdown reaping; real stalled and pipe-holding children tested. No real winget installs |

## Validation record (latest first)

- **14:00–14:23 (cpp profile):** dashboard 539 OK, 9 skips (real MSVC compiles and
  Docker g++ runs); setup 99 OK; JS 24 passed. Real confined runs: correct program
  passes; the FOV bug fails; compile errors and warnings are errors; no DNS inside.
- **Game-mod tools:** dashboard 532 OK; real `mods/gta-ark` build of 3 targets through
  `build_native_mod`; `inspect_game_files` on the real GTA folder (179 RPF7 NG, 0.5 s)
  and ARK folder (pak v12 / IoStore v8, unencrypted, 0.4 s).
- **SMELTER runs (Qwen 35B, 128K):** test 1 discovery correct; test 2 completed in
  259 s at output 8,192 (it stopped at 2,048); test 3 completed in 114.7 s.
- **Melty default:** dashboard 513 OK; live OpenCode `melty_search_games` task 57.1 s,
  answer matched the raw result.
- **128K:** GUI OpenCode task 36.7 s with the model loaded at 131,072.
- **R06–R08:** dashboard 512 OK after R06 (was 505); setup 77 → 86 → 94; live R06
  with real Docker.
- **Earlier (morning):** frontend Docker smoke, native Ghidra + MCP, Qwen + Ghidra,
  Melty discovery all PASS; analysis 30 OK (not rerun since).

Nothing was installed into or launched from a game folder. No target execution,
model fine-tuning, upload, publication or push was performed. Built mod binaries
were never run; only portable C++ tests ran, inside the confined container.
Dependencies, evidence and build outputs are machine-local ignored data.
