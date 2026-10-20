# Changelog

This file records verified changes. Older research rounds are preserved in their source scripts and historical diagnostics; their filenames are not treated as release guarantees.

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
