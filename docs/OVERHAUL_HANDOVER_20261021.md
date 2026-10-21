# SMELTER UI/UX overhaul handover — 2026-10-21

Application revision: **43ff086bac02a42c6257c91db983a307ff345f15**. Branch: SMELTERV1. CI: **[run 39561889060](https://github.com/Dr-Dark92/SMELTER/actions/runs/39561889060)**. Read [implementation and rollout](UI_UX_OVERHAUL.md), [design system](../design-system/smelter/MASTER.md) and [repair progress](reviews/2026-10-21/PROGRESS.md).

The seven reproduced review defects are repaired with focused regressions. The frontend is a redesigned vanilla web workbench rather than a framework migration. Existing API fields and approved execution boundaries remain in use.

## Source ownership and verification

Edits were prepared through the GitHub connector because the local execution environment was unavailable. GitHub Actions supplied real Linux/Windows contract tests and Chromium UI/GLB checks with synthetic inference. UI screenshots were inspected and used to reduce mobile composer/status overhead. The pinned UI UX Pro Max generator ran on a disposable runner; unsuitable landing-page recommendations were rejected.

No production database, user's local checkout, game directory, existing V2, model weights or hardware configuration was changed by this work. No live Qwen/Ollama prompt or OpenCode/Docker task was used for validation. A generated animated GLB provided deterministic browser fixtures; previous user-asset rendering evidence remains in the historical review.

## Continue from here

1. Pull SMELTERV1 with --ff-only, preserving local/untracked state. Restart the old server and use the newly printed authenticated URL.
2. Inspect Settings search, location Add/Browse/Apply/Revert, skill collection controls, chat roles/composer and resource disclosure.
3. Attach a representative animated GLB on the rig. Verify labels, PNG/WebM, release while exporting and reload. Labels belong to SMELTER metadata; original GLB names/bytes remain unchanged.
4. When live inference is allowed, run the small model-contract fixtures with the admitted model/context/output/timeout recorded. Do not infer model quality from synthetic responses.
5. Verify actual Docker/OpenCode images, confinement, relay and cleanup before enabling a live read-only agent task. Keep arbitrary external MCP blocked.
6. Treat broad complexity refactors, a safe V2 refresh/rebase workflow and a separately approved coding mode as future work. Do not turn the read-only agent into an unrestricted writer to work around its documented limits.

The application source graph is pinned to the tested application commit. Subsequent documentation commits do not imply additional runtime changes. Full browser evidence and generated design output are retained in the linked CI run; no auth token is included in the committed evidence summary.

## Focused regression command

```fish
python -m unittest discover -s tools/dashboard -p 'test_overhaul_repairs.py'
```

Use these regressions on the repaired branch. The historical `review_runtime_layers.py` reproducer targets the original pinned review source and intentionally assumes the old failures; it is not the current acceptance runner.
