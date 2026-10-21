# Changelog

This file records verified changes. Older research rounds are preserved in their source scripts and historical diagnostics; their filenames are not treated as release guarantees.

## Runtime layer review — 2026-10-21

Reviewed GitHub head `a609148fab2dec8915da24ca46550f9cd275b694`; all 247 scripts matched Git blobs. Added [findings](docs/reviews/2026-10-21/REVIEW.md), action plan, progress, handover and fixture evidence. Seven new defects reproduced; no production code repaired. Actual GLB preview/playback/PNG and one WebM export checked alongside lifecycle races. No live Qwen/Ollama/OpenCode/Docker tests.

## Registered locations GUI — 2026-10-21

Application commit: `e27036e0da3a3052273bca938faa4cb185f4aaba`. Refreshed graph pins this revision (242 scripts).

- Replaced location cards with a searchable permission table and Add / Remove / Enable / Disable / Apply / Revert toolbar.
- Added an authenticated directory browser for operator selection, with no model-tool grant or process launch. Add starts read-only; roots, links and traversal remain restricted.
- Keep edits in a draft, preserve it across settings navigation, and atomically reject stale Apply revisions. Applied task choices and admitted active tasks retain their respective policies.
- Modernized table, editor and folder-picker controls with responsive layouts and explicit status. See [registered locations](docs/REGISTERED_LOCATIONS.md).
- Validation: 347 dashboard tests OK (two opt-in skips), 15 JavaScript tests, 32 setup tests, four analysis tests; desktop/mobile location and existing GUI browser flows. No live Qwen/Docker tests.

## Settings and skills GUI revision — 2026-10-21

Application commit: `92e14fe0bb098b4a02712b1cc88f196324b4b9db`. Source graph/function inventory regenerated against that commit.

- Replaced stacked settings with grouped navigation/content panes and a mobile section picker; refreshed the shared dark theme and controls.
- Replaced visible type-specific attachment controls with one accessible + menu for supported images and GLBs; added removable image filename chip.
- Replaced skill cards with a searchable table, clear runtime/enabled indicators, expandable collections, parent/child checkboxes and top bulk toolbar. Task-context selection stays explicit and separate.
- Skip duplicate IDs/content during reviewed imports, append unique children without overwrite, preserve existing enable states and report skipped identities. Protect bundled skills; allow imported child removal. Roll back failed new imports.
- Extended the offline GUI fixture with collection/status/import samples. Validation: 338 dashboard tests OK (two opt-in skips), 15 JavaScript, 32 setup, four analysis; desktop/mobile actual fixture flows passed without live Qwen.

## Office/offline follow-up — 2026-10-21

Application commit: `4bd636dbcc04de5d2cb016489c923e3146a611db`. Refreshed graph: 235 scripts, 1,454 declarations/callbacks, 2,241 static relationships and 50 reviewed runtime links.

- Fixed same-basename skill entries being hidden across namespaced sources; genuine identity collisions are disabled and explained. Hardened linked state/collection paths.
- Commit admitted job outcome with transcript/execution atomically. Retry failed terminal metadata saves without replaying actions or relabelling committed outcomes. Record worker-start failures.
- Preserve unknown active tasks across status failures; add explicit Reconnect task and retain Stop until terminal state is observed.
- Keep consumed/expired/failed retention plans disabled; invalidate plans on age edits and require fresh review after ambiguous deletion failures.
- Added a temporary offline GUI harness with synthetic replies and isolated disposable state; no live model/container services required.
- Validation: 329 dashboard tests OK (two opt-in skips), 15 JavaScript tests, 32 setup tests, four analysis tests, desktop/mobile retention/reconnect/Stop fixtures. Live Qwen and Docker tests disabled.

## V1.7 operational repair — 2026-10-21

Application commit: `a3e3f854934ed90f36d49478eb336b86dd93948b`. Graph follow-up pins that source and records 233 scripts, 1,400 declarations/callbacks, 2,169 static edges and 49 reviewed runtime links.

- Addressed review findings F01–F11; see [repair handover](docs/REPAIR_STATUS_20261021.md) for evidence and deployment conditions. Corrected the earlier F06 top-level-object assertion.
- Added fail-closed owned Docker execution for tests, temporary preview and read-only OpenCode, with local immutable images and a narrow approved-model relay. No host fallback or arbitrary external MCP execution.
- Added bounded process IO/tree cleanup, shared atomic engine outcomes, admitted model/runtime snapshots, attachment cleanup, durable interrupted-task records, artifact quotas, reviewed retention and verified backup/offline restore.
- Unified skill identities/capability descriptors and added an explicit scoped legacy Registry bridge plus operator project-contract checks.
- Separated readiness/integrity checks, cached dependency probes, clarified discovery/lightweight/host-resource status, consolidated Settings/skills ownership and extracted HTTP/browser/inference modules.
- Validation: 321 dashboard tests OK (two opt-in skips), 32 setup tests, 10 JavaScript tests, four analysis tests; desktop/mobile fixture flows passed. Real Docker/OpenCode-image and native Windows process paths require rig smoke tests; no live model/game tested here.
- Existing user state and V2 are preserved. Containers use temporary state; backup scope and rollout are explicit. Refreshed source graph/function index pins the repaired app commit in a following documentation commit.

## Documentation and source review — 2026-10-20

Reviewed application revision: `c9e541e9e0d53fcaba109170f8e5a201b500340d` on `SMELTERV1`.

- Replaced the root scaffold-only README with current installation, capability and limitation guidance.
- Added system documentation, API/storage maps, relationship diagrams, a searchable offline graph, a complete static function index, and a remaining-defect/complexity review.
- Added reproducible static analysis utilities and fixture-only reproductions of remaining lifecycle, cancellation and runtime-setting defects.
- Indexed 216 application scripts, 1,229 function/callback declarations and 1,978 static relationship records. These are source-analysis results, not execution coverage. Analysis utilities introduced by this documentation are outside that pinned application inventory.
- Kept review findings separate from fixes. This documentation revision does not remove legacy functions, change application permissions, or refactor runtime behavior.

## Scoped dashboard repair — 2026-10-20

Commit: [c9e541e](https://github.com/Dr-Dark92/SMELTER/commit/c9e541e9e0d53fcaba109170f8e5a201b500340d). Parent: `e99e0c1d74809c5cae1941eace6fa97db0343a1b`.

### Added

- Central registered-location read/write/operation policy, frozen per admitted task.
- Consolidated Settings and engine-aware next-task access controls.
- Context-budget estimates and explicit oversized-task rejection.
- Cross-layer regression tests and revision notes.

### Fixed

- Dashboard configuration reads now use the same SQLite source as writes.
- Direct inference honors the saved reasoning model.
- Model follow-up/tool failures retain receipts and return partial outcomes.
- Latest chat history and older-page navigation replace oldest-only history.
- Legacy ask and start requests share job admission and cancellation.
- MCP child processes inherit parent skill fingerprints and access policies.
- Blanket tool-result caching was replaced by an explicit deduplication set.
- OpenCode receives bounded prior conversation text in fresh read-only sessions.
- Navigation active state, composer width, selected-engine controls and disconnected-client response handling.
- Failed initial database creation can be retried; POSIX native inspection binaries are accepted; Windows simulation tests avoid constructing WindowsPath on Linux.

### Restricted / unchanged

- GUI execution/discovery of arbitrary external MCP servers is blocked pending a confined runner.
- OpenCode remains a read-only adapter; frontend replacement remains CSS-only.
- Guardrails remain application checks, not an OS sandbox. Tests/previews run application code as the OS user.
- Jobs remain memory-resident. Legacy core registries and CLI experiments remain separate from dashboard tools.
- Existing managed V2 copies and user-local untracked state are preserved.

### Validation recorded for that commit

- Dashboard: 294 tests run, one skipped, with the optional MCP SDK installed.
- Setup: 32 tests passed. JavaScript: 10 tests passed.
- Desktop/mobile Chromium flows passed against a local OpenCode HTTP fixture. This did not invoke Qwen or verify the user's installed Windows server/model.
