# Action plan after the workflow audit

The W01–W13 repair register and code evidence are in [REVIEW.md](REVIEW.md).
This plan separates completed fixes from product work that tests cannot invent.

| Order | Priority | Work | Acceptance criteria |
| --- | --- | --- | --- |
| 1 | P1 | Home live acceptance with the full smoke pack | Direct Qwen, managed OpenCode/MCP and ECC RED/fix/GREEN pass against saved bytes/tests; original/V2 preserved; manual GUI checklist recorded |
| 2 | P1 | Explicit deliverable acceptance for coding tasks | Distinguish model request completion from accepted code; declared task requires applied files and all required current test profiles. Missing/no-call/RED-only/stale cases cannot display an accepted deliverable |
| 3 | P1 | Coding workspace export, backup and reviewed retention | Preserve source/baseline/proposals/audits/test logs together; exact hashes; no overwrite; restore to a new owner/path; expired/changed/live work cannot be pruned; quota recovery after ten copies is documented and tested |
| 4 | P2 | Safe existing frontend V2 refresh | Explicit diff/backup/refresh plan, conflict handling, no silent overwrite of current CSS or database. Old prepared copies remain usable or fail with actionable stale-baseline guidance |
| 5 | P2 | Typed task and effective settings presentation | One admission record includes engine/model/policy/skill hashes/call budget/deadlines/test profiles. GUI shows active snapshot separately from next-task draft without duplicated controls |
| 6 | P2 | Reduce orchestrator/GUI coupling | Extract meaningful session/poll/finalize and renderer interfaces under current regressions. Preserve route names/IDs and structured receipts; expand compressed handlers rather than hiding validation |
| 7 | P2 | Broader project profiles | Explicit registered project root and read/write/execute subset; reviewed fixed build/test profiles, dependencies and output budgets. Do not replace them with arbitrary shell access |
| 8 | P2 | Confined external MCP adapter | Immutable reviewed server image, no ambient host paths/credentials/network, explicit grants/protocol/timeouts/audits/cleanup; unapproved and changed descriptors denied before action |
| 9 | P2 | ECC executable layers | Map requested hooks/custom tools/delegation/memory to actual reviewed adapters; each layer independently demonstrates confinement, evidence and revocation. Keep instruction import distinct |
| 10 | P2 | HTTP and setup process lifecycle | Bounded concurrent requests, body-read deadlines and graceful shutdown; setup installer timeout/cancel/owned children. Windows fixture proves no orphan shells or installers; no broad process killing |
| 11 | P2 | Catalog/metadata scaling | Pagination or larger proven limits with portable snapshot transport; no silent skill omission, identity collision or partial batch. Cache dependency observations without hiding current execution checks |
| 12 | P2 | GLB rendering budgets and additional formats | Explicit aggregate accessor/mesh complexity limits, decoder packaging and independent validation fixtures before accepting compressed assets. Preserve resource/lifecycle/cancellation checks |
| 13 | P2 | Reproducible dependency/image locking | Review and pin image digests and executable package integrity, record build provenance, test deliberate upgrades on Windows/Linux; never silently upgrade/pull at runtime |
| 14 | P3 | Deprecate older configuration/launcher paths | Inventory external consumers, label supported entry points, migrate or archive intentionally. No deletion based only on an absent static incoming call |

First run the actual home smoke before changing models or widening tools. A
failed model task should retain its evidence so transport failure, missing adapter
and model decision quality can be diagnosed separately. Coverage and correctness
require meaningful tests; test counts and the “best skill” description are not
quality measurements.
