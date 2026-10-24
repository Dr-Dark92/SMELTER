# Next plan — after the laptop deployment, 2026-10-24

Finding IDs (C, W, U) refer to the [review](REVIEW.md). The goal of this plan:
**a fresh install reaches a working direct chat and OpenCode task with no manual
configuration**, and the dashboard tells the user what is missing and where to fix
it. Each phase is shippable on its own. Keep the existing safety boundaries
(explicit grants, confined containers, no silent downloads) unless a step says
otherwise.

## Phase 0 — quick fixes (small, independent)

| # | Work | Findings | Acceptance criteria |
| --- | --- | --- | --- |
| 0.1 | Default the engine to **Ollama · direct chat**; offer OpenCode only after its readiness check passes | C04 | New install: first Send goes to direct chat; OpenCode option shows why it is unavailable |
| 0.2 | Separate `opencode_timeout_seconds` from the direct-chat timeout; default 900 s | C06 | Changing one does not change the other; existing saved settings migrate without loss |
| 0.3 | Profiles apply as a preview with a per-field diff, then save; editing one field never resets others | C05, U04 | Test: set context only, other fields keep their saved values |
| 0.4 | Calibrate the prompt estimate against Qwen's real token counts (Ollama `prompt_eval_count`) instead of 2 bytes per token | W01 | Recorded fixtures: estimate ≥ actual and within 25 % for English, code and JSON |
| 0.5 | `start_dashboard.ps1` finds Python like `install_missing.ps1` does; README commands work without Python on PATH | C09 | Launch works on this laptop with `python` and `py` absent from PATH |
| 0.6 | Ignore `.smelter/` in `.gitignore` | C10 | `git status` clean after a dashboard run |

**Status 2026-10-24: Phase 0 done.** 0.1 engine default is direct chat, the last
choice is remembered per browser, and the OpenCode approval message opens Task
access. 0.2 adds `opencode_timeout_seconds` (default 900, 60–3600) for the whole
task; `timeout_seconds` still bounds each model turn, and older callers that save
four settings keep the stored task timeout. 0.3 presets list each field they
change and leave equal fields alone. 0.4 replaces bytes/2 with a character-class
estimate measured against `qwen3.5:4b`: English 1.13–1.28×, JSON 1.18–1.56×,
**code 1.36–1.75×** (the 25 % target is not met for code), and at or above the
real count for CJK, Arabic, emoji, base64 and hashes, which bytes/2 under-counted
for dense JSON (0.87×) and hashes (0.51×). 0.5 `start_dashboard.ps1` finds Python
without PATH. 0.6 `.smelter/` is ignored.

## Phase 1 — configuration automated by deployment

Add a `defaults` section to `system-requirements.json` and a
`tools/setup/configure_defaults.py` step that `install_missing.ps1` runs last.

| # | Work | Findings | Acceptance criteria |
| --- | --- | --- | --- |
| 1.1 | **Hardware profile**: read GPU name, VRAM, driver and CUDA support; record it in the setup report | C07, W07 | Report states GPU, VRAM, driver and whether Ollama uses it; warns when the driver is older than the catalog minimum |
| 1.2 | **Model choice from VRAM**: catalog table (≤ 6 GB → `qwen3.5:4b`, else `qwen3.5:9b`); `ollama_model` setup step pulls that model | C02, C07 | Laptop gets 4 B and desktop 9 B with no prompts; smoke runner accepts the configured model, not only 9 B |
| 1.3 | **Never fall back to an absent model**: remove hard-coded `qwen3.5:9b` fallbacks; use the configured model, else the first installed one, else block with a clear message | C02 | Unit test with only 4 B installed: chat admits 4 B |
| 1.4 | **Runtime profile from hardware**: add a `laptop` profile (32 K context, thinking off, 1024 output, 900 s OpenCode) selected for ≤ 6 GB VRAM | C05, C07 | Fresh laptop install completes the OpenCode `skills/` task without settings changes |
| 1.5 | **Seed dashboard configuration** on first database creation, only for unset values: enable extensions whose tools are installed; save image IDs from `docker image inspect`; set models and runtime from 1.2–1.4; add default locations | C01, C03 | Fresh install: Settings show every value with source "deployment"; re-running never overwrites a user change |
| 1.6 | **Default storage location** `%LOCALAPPDATA%\SMELTER\data`, created if absent, still outside the checkout; the first-run prompt pre-fills it | C08 | First open needs one click; existing databases are never overwritten |
| 1.7 | **Pin and hold runtimes**: record Ollama and native OpenCode versions in the catalog; setup reports drift; document turning off auto-update | C11 | Setup report shows expected vs actual versions |

**Status 2026-10-24: Phase 1 done, with one item open.** Profiles were renamed
by hardware at the operator's request: `low` (no GPU, 4B), `medium` (≤ 6 GB, 4B),
`high` (6–16 GB, 9B), `extreme` (> 16 GB and ≥ 30 GB RAM, `qwen3.5:35b-a3b`) and
`custom` (user-defined). 1.1 GPU, RAM, driver warning and Ollama version drift
are reported. 1.2 the `ollama_model` step pulls the profile's model; the fallback
is the largest installed model that fits. 1.3 one `FALLBACK_MODEL` replaces the
scattered `qwen3.5:9b` literals, and a missing model now says where to fix it
(Ollama 404) instead of admission probing Ollama. 1.4 runtime presets match the
profiles. 1.5 `.smelter/deployment-defaults.json` fills never-saved settings with
source `deployment`; saved values win. 1.6 first start-up pre-fills
`%LOCALAPPDATA%\SMELTER\data`. 1.7 Ollama version drift is reported; the
OpenCode version is pinned in its image. **Open:** the full smoke runner still
hard-requires `qwen3.5:9b` (1.2 acceptance), and the `extreme` runtime values are
unmeasured.

## Phase 2 — readiness inside the dashboard

| # | Work | Findings | Acceptance criteria |
| --- | --- | --- | --- |
| 2.1 | **Readiness page** generated from `system-requirements.json`: each tool and setup step with done / todo / blocked and its reason (port the installer checks to Python and share them) | U01, U03, W06 | One screen answers "can I chat / run OpenCode, and if not, why"; matches the installer dry run |
| 2.2 | **Actionable errors**: every blocking message names the setting and links or buttons to it | U02 | "Extension disabled", "model missing", "OpenCode not approved" each open the right panel |
| 2.3 | **First-run checklist** shown until all required steps pass | U01 | New user reaches a first reply by following only the checklist |
| 2.4 | **Composer status strip**: engine, model, context, timeout and active grants (and whether they are kept) beside Send | U05, L08 | Visible without opening Settings |

## Phase 3 — OpenCode workflow

| # | Work | Findings | Acceptance criteria |
| --- | --- | --- | --- |
| 3.1 | Allow OpenCode's `glob`, `list` and `grep` with the same path scope as `read` (rules from `session_rules`) | W02 | Audit shows listing/searching `skills/` succeeds and `.env`, `.git`, `.smelter`, `projects/` stay denied (extend `WorktreeRelativeReadTests`) |
| 3.2 | Tell the agent where things are: system text maps `C:\SMELTER\…` to `/workspace/…` and lists what the snapshot contains; rewrite Windows paths in prompts | W03 | A prompt containing `C:\SMELTER\skills` reads `/workspace/skills` |
| 3.3 | Task result panel: reads, writes, tool errors, elapsed time and the limit that ended a partial task | U06 | Partial tasks explain themselves without opening the audit file |
| 3.4 | Direct chat gets a short SMELTER context block (what the project is, which engine to use for file questions) | W04 | "What is SMELTER?" answers from the README |
| 3.5 | Live OpenCode acceptance on this laptop (4 B) and the desktop (9 B) | — | `skills/` summary task completes on both; results recorded as evidence |

## Phase 4 — UI/UX overhaul

Build on [UI_UX_OVERHAUL.md](../../UI_UX_OVERHAUL.md); this phase changes structure, not just styling.

| # | Work | Findings | Acceptance criteria |
| --- | --- | --- | --- |
| 4.1 | Information architecture: **Chat** · **Readiness** · **Access** · **Settings**, replacing the deep Settings tree | U01, U03 | Every control reachable in two clicks; settings search still works |
| 4.2 | One vocabulary for access: "Locations" (what SMELTER may touch), "This task" (grants for the next Send) and "Agent view" (what the container sees) | W03 | Each screen uses only its term; help text shows the host ↔ `/workspace` mapping |
| 4.3 | Keep the launch session across restarts on the same machine, or show the new URL prominently; reload UI assets without a restart in development | U07 | Restart does not strand an open tab |
| 4.4 | Usability pass on the 375 px and desktop layouts with the new flows; record screenshots as evidence | — | Screenshots for first run, readiness, chat, OpenCode result |

**Status 2026-10-24: Phase 4 largely done, plus a Phase 3 change made at the
operator's request** (see [UI_UX_OVERHAUL.md](../../UI_UX_OVERHAUL.md)): new design
system, flush layout, compact composer with chips and a Tools popover, Settings in
five groups with Debugging, no-dialog chat start, and a persistent OpenCode session
(`opencode_pool.py`) started with the dashboard and approved once per session.
Covers U01 partially (no checklist yet), U02 for OpenCode approval, U04 (earlier),
U05, W03 partly (one access vocabulary not finished). Open: 2.1–2.3 readiness page
and first-run checklist, 3.1 OpenCode list/glob/grep, 3.2 path mapping, 3.3 result
panel, 4.3 launch-session persistence.

## Phase 5 — carried over

From the [2026-10-21 action plan](../2026-10-21/workflow-audit/ACTION_PLAN.md):
item 1 (home live acceptance with `qwen3.5:9b`), item 13 (image digest and
dependency locking) and item 10 (HTTP and setup process lifecycle) matter most
after Phases 0–2. The others are unchanged.

## Suggested order

0.1–0.6 → 1.1–1.5 → 2.1–2.2 → 3.1–3.2 → 3.5 (live acceptance) → 1.6–1.7, 2.3–2.4, 3.3–3.4 → Phase 4.
