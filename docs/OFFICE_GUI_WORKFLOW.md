# Office GUI workflow — no live model required

Use this workflow on the CachyOS office desktop. Qwen, Ollama, OpenCode and Docker are not needed for the synthetic GUI fixture. It is a development harness, separate from the normal dashboard engine.

## Run from fish

```fish
cd ~/dev/SMELTER
git pull --ff-only origin SMELTERV1
```

Stop if the pull fails. Then:

```fish
python tools/analysis/offline_gui_fixture.py
```

Open the authenticated URL printed by the script. The default fixture port is **18771**, separate from the production dashboard on 8768. For another local port:

```fish
python tools/analysis/offline_gui_fixture.py --port 18772
```

The page banner says **OFFLINE FIXTURE · Temporary data · Synthetic responses**. That label distinguishes it from the normal workbench. A temporary checkout/state/database is created outside your project; Ctrl+C removes it. Fixture conversations and reports are disposable. Do not use it for work you want to keep.

## What to inspect

1. Create a conversation; a title is required. Send any short message. The deterministic reply says no model was called.
2. Send a message containing **slow**. The fixture waits so Stop and reconnect behavior can be examined. Stop remains available after a transient status error; Reconnect task reuses the admitted job ID and polls only. It does not resend the prompt.
3. In Settings → Storage, recovery & backup, preview retention. One old synthetic report is seeded for the first plan. Apply only that reviewed plan. It removes the fixture report and leaves Apply disabled. Another preview should show zero candidates.
4. Edit the retention age. That invalidates the previous plan. Expired or failed/ambiguous deletion attempts require a fresh preview; cancelling the confirmation preserves a still-valid plan.
5. Review Skills, task access and the admitted model/settings summary. The displayed fallback model is configuration text; fixture chat never submits it to a real service.
6. Optional: approve a new Markdown diagnostic report for the next task and send text containing **report**. The fixture issues a real registered report tool call into its temporary checkout. The receipt demonstrates backend writing/auditing; the model response remains synthetic.

Resource metrics and service checks are stubbed in this harness. Confined execution and OpenCode checks deliberately report unavailable. Live service performance, model quality, actual 3D rendering dependencies and real container isolation cannot be validated here.

## Offline follow-up changes

| Area | Repair |
| --- | --- |
| Catalog | Same basenames in bundled, legacy and contract sources remain distinct. A genuine bundled/managed identity collision is disabled and lists its conflicting sources. Linked collection ancestors/state paths are rejected. |
| Atomic outcome | Admitted job outcome, execution record and transcript commit in the same SQLite transaction. A crash after that commit cannot leave a completed task marked running. |
| Metadata recovery | If a worker fails before transcript finalization and its journal write fails, status/admission retry metadata only. Actual task outcome and persistence warning remain separate; no action is replayed. Worker-start failure records a terminal error. |
| Reconnect | Status errors retain the task ID, Stop and admission guard. Terminal reconnection clears the stored task and unlocks the composer. |
| Retention | Consumed/failed/expired/changed plans stay disabled. Button cleanup cannot accidentally re-enable a consumed plan. |

## Verification recorded for this follow-up

- Dashboard: **329 tests run, OK, two opt-in skips**. Live vision/Qwen and Docker tests explicitly disabled.
- Browser JavaScript: **15 tests passed**, including five retention state/error/expiry cases.
- Setup: **32 tests passed**. Static-analysis harness: **four tests passed**.
- Chromium desktop/mobile: actual fixture HTTP/UI/SQLite paths, one synthetic report deletion, chat completion, injected HTTP 503, reconnect, Stop and no horizontal overflow/page errors. No live model invocation.
- Fixtures also verify job/transcript rollback together, durable completion before worker return, no replay after failed journal persistence, and committed outcomes surviving a late worker exception.

These checks do not replace the Windows/Docker/OpenCode smoke tests documented in [repair status](REPAIR_STATUS_20261021.md). The source graph is regenerated against the follow-up application commit in a separate documentation commit.
