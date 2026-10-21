# Runtime review repair progress — 2026-10-21

Original review source: `a609148fab2dec8915da24ca46550f9cd275b694`. Repair application source: **43ff086bac02a42c6257c91db983a307ff345f15**. See [overhaul implementation and rollout](../../UI_UX_OVERHAUL.md).

The original review is retained as historical evidence. R01–R07 are now implemented and verified by the targeted regressions, full Linux/Windows suites and actual browser checks. The application source graph is refreshed against the tested revision.

| ID | Repair state | Evidence |
| --- | --- | --- |
| R01 | Verified | Denied report filenames/suffixes blocked in direct/MCP; denied top-level reads rejected |
| R02 | Verified | Real HTTP Stop bypasses long probe and configuration lock |
| R03 | Verified | Output-limit results are partial; OpenCode ends polling immediately |
| R04 | Verified | Actual browser GLB load/export/release, stale event and error/reload checks |
| R05 | Verified | Protocol shape failures preserve completed-action receipts and partial text |
| R06 | Verified | Host-appropriate Path identity; Linux distinct-case regression |
| R07 | Verified | Owned preparation rollback and retry; pre-existing data retained |

UI changes include the workbench shell/composer, grouped searchable settings, readable tables and permission context, mobile drawer, adaptive resources and explicit OpenCode/MCP capability labels. [Design system](../../../design-system/smelter/MASTER.md) was derived from the requested pinned skill with its actual recommendation recorded in CI.

Final results: **359 dashboard tests per OS**, **32 setup**, **four analysis** and **15 JavaScript**. Linux: two opt-in skips; Windows: three, including the Linux-specific case fixture. Actual browser/GLB and final keyboard checks passed: **[run 39561889060](https://github.com/Dr-Dark92/SMELTER/actions/runs/39561889060)**.

No live Qwen/Ollama inference, live OpenCode task or Docker integration runs were performed. Hosted Linux/Windows contract checks are separate from user-rig verification. Broad maintainability refactors and a future confined coding mode remain planned rather than implicitly enabled.
