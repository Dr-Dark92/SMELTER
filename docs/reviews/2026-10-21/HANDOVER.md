# SMELTER runtime review handover

Date: 2026-10-21, Asia/Muscat. Repository [Dr-Dark92/SMELTER](https://github.com/Dr-Dark92/SMELTER/tree/SMELTERV1), branch **SMELTERV1**. Reviewed source **a609148fab2dec8915da24ca46550f9cd275b694**. This handover accompanies a review-only change, not application repairs.

## Read first

- [REVIEW.md](REVIEW.md): traced architecture, seven reproduced findings, limits and complexity candidates.
- [ACTION_PLAN.md](ACTION_PLAN.md): patch order and concrete acceptance checks.
- [PROGRESS.md](PROGRESS.md): completed versus pending work.
- [evidence.json](evidence.json), [glb-browser-evidence.json](glb-browser-evidence.json), [scope.json](scope.json): recorded observations and source coverage.

## Current status

All seven R01–R07 defects remain open. Start with final-path policy checks (R01), then protocol/finish handling (R05/R03), cancellation/locks (R02), GLB lifecycle (R04), recovery (R07) and Linux path identity (R06). Add regression assertions before modifying the implementations.

Do not treat passing tests as dismissal of recorded defects. Full offline dashboard run on the pinned source: 347 tests, OK, two opt-in skips. Targeted Python run: 45 tests, OK, one opt-in skip. No live Qwen/Ollama, Docker or OpenCode task ran. The 15 JS, 32 setup and four analysis baseline suites passed on the same application source; the analysis suite is rerun for this review deliverable.

The Python reproducer runs against a temporary database/workspace and a synthetic local HTTP stream/probe. It never contacts a model or Docker service:

```fish
cd ~/dev/SMELTER
and python tools/analysis/review_runtime_layers.py
```

It prints observations, not a pass/fail certification. On the reviewed source R01 shows a denied report written and denied README copied; R03 shows a length-limited direct response marked completed; R05 shows protocol AttributeError and an after-tool transcript gap; R02 shows Stop waiting behind another POST; R06/R07 record path/retry failures. Temporary fixtures clean themselves up.

## GLB follow-up

Actual Chromium/model-viewer 4.1.0 rendered Tabern, WarGreymon (23 clips) and MetalGreymon (42 clips). PNGs, clip playback/labels and one 960×600 VP8 WebM export worked. Original asset bytes were not changed. R04 was reproduced with controlled browser snapshot completion and a late load event; fix active-owner guards and busy/timer reset before declaring preview release robust. Screenshot/video outputs and source assets were not committed. `glb-browser-evidence.json` records hashes/results; no GIF export or native GPU benchmark is claimed.

The temporary browser runner used the existing local viewer bundle with the disposable offline GUI fixture. The ordinary fixture does not automatically install that package. To repeat visually, use an explicitly installed local model-viewer bundle, attach an animated GLB, start export, release during export, then reload; check animation controls and stale load/capture events. Recheck PNG and WebM downloads after the fix.

## Boundaries to preserve

- Preserve `.agents`, `.smelter`, diagnostics, untracked files, current V2/V2-Data and databases. Do not use git clean/reset or delete old data to fix retry.
- OpenCode remains a managed **text-only read-only** pilot. Its default production path does not attach to the old host CLI server. Selected SMELTER design skills/write permissions are not forwarded.
- Arbitrary external MCP is blocked. Built-in MCP uses the fixed tool registry and per-message grants.
- Frontend model tools edit CSS only. Reports are create-only. Folder browsing is authenticated operator metadata navigation, not a model tool or grant.
- Native REA/archive/media/Blender inspection bounds are not an OS filesystem sandbox. Container and Windows live verification remain explicit deployment work.
- Do not rerun Qwen tests at the office unless the user changes that instruction. No dependency installation, model pull, service start or game reverse-engineering work is part of this review.

## Source and publication

GitHub tree/script hashes were checked before review. Use a new branch-head lease before publishing subsequent fixes; re-fetch and rebase if someone changed SMELTERV1. The existing graph remains pinned to unchanged application `e27036e0`; review tools under tools/analysis are outside that application inventory. Refresh the graph when application code changes, not to imply that this documentation fixed the application.
