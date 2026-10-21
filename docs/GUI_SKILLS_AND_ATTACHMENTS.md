# Settings, skills table and attachment menu

Application commit: [`92e14fe0bb098b4a02712b1cc88f196324b4b9db`](https://github.com/Dr-Dark92/SMELTER/commit/92e14fe0bb098b4a02712b1cc88f196324b4b9db).

This GUI revision replaces the earlier stacked settings layout and skill cards. It preserves existing chat, model, asset, access, MCP and inspection APIs; bulk skill management is an additive operator action.

## Interface

- Settings uses a grouped navigation rail and a separately scrolling content pane. Small screens use a section picker. Inputs, buttons, dialogs, tables and status colors share a neutral dark theme.
- The composer has one **+** attachment entry point. Its menu lists only supported types: PNG/JPEG/WebP images up to 2 MiB and GLB models up to 25 MiB. Native file-input buttons and the separate Attach GLB button are hidden. Images show a removable filename chip; GLBs follow the existing stored-attachment upload flow. Other document/archive formats are not claimed as supported.
- The skills inventory is a table with selection, name/ID, runtime status, enabled state, source and next-task selection. Manifest details open by clicking the skill name. Status uses text plus color; it does not depend on color alone.
- Collections expand into child rows. A collection checkbox selects its matching children, including collapsed children; partial selection is indeterminate. Search filters names, IDs, collections and descriptions. Select-all applies to matching skills.
- **Add, Remove, Enable and Disable** are above the table in a sticky toolbar. Remove protects bundled/legacy/contract entries; imported collection children can be removed independently. Bulk validation happens before mutation. IO failures report changed IDs and individual errors.
- Management selection is separate from model context. **Use in next task** accepts at most three enabled, active manifests. Automatic routing and clearing task skills remain available. Enabling instructions grants no filesystem/process permissions.

## Import and duplication

Add opens a discovery/review dialog. Repository imports offer sub-skill checkboxes and a manifest-review step. Imports remain disabled by default, and new/changed instruction fingerprints require dashboard restart before model use.

The installer checks both canonical IDs and normalized manifest-content SHA-256 across supported skill sources. CRLF/CR/LF differences do not create separate content identities. Content comparison is exact after newline normalization; differently worded descriptions of the same capability are not semantic duplicates.

Duplicates are **skipped**, with their reason and existing identity returned. Existing bytes and enable states are preserved. Unique reviewed skills continue importing. Existing collections can receive new unique children; re-importing the same collection does not overwrite it. Duplicate content inside a batch is also skipped. Invalid or changed nonduplicate manifests still stop the operation before writing; duplication is not a bypass for validation.

Single GitHub imports use the same duplicate checks. If writing their disabled state fails, newly created manifest bytes are rolled back. Appending to an existing collection also rolls back only new children on failure.

## Code ownership

| Module | Responsibility |
| --- | --- |
| settings_ui.js | Settings rail, mobile picker, panel ownership and focus restoration |
| skills_ui.js | Table, collection selection, toolbar, manifest details and reviewed import dialog |
| attachments_ui.js | Single + menu, keyboard/outside-click dismissal and image chip |
| dashboard_shell.js | Composes UI components with existing conversation/grant/asset flows |
| skill_duplicates.py | Read-only canonical identity and normalized content inventory |
| skill_collections.py / github_skill_discovery.py | Reviewed imports, skip receipts and create-only rollback |
| skill_manager.py | Bulk enable/disable and protected imported-skill removal |

POST `/api/skills/manage` additionally accepts `action=bulk`, `operation=enable|disable|remove`, distinct `ids`, and `approval=true`. Existing single-item actions remain supported. Operator actions still require dashboard authentication and serialization; they are not model tools.

## Verification

- Dashboard suite: **338 tests run, OK, two opt-in skips**. Live Qwen and Docker tests disabled.
- JavaScript suites: **15 tests passed**. Setup: **32 passed**. Analysis: **four passed**.
- Desktop/mobile Chromium exercised the actual temporary HTTP/SQLite fixture: collection expansion/parent selection, enable/disable/remove, import-one/skip-two, repeat-import skip-all, mobile section switching, image selection/removal, GLB upload, menu Escape, hidden native file inputs and no page errors.
- Regression cases cover cross-source and within-batch duplicates, newline normalization, preserving enabled existing children, unique append, append rollback, protected bundled bulk removal, sibling preservation and failed single-import rollback.

For office inspection, run `python tools/analysis/offline_gui_fixture.py`. Its synthetic GitHub import demo uses **https://github.com/offline/design**; that URL is handled by the fixture, not fetched from GitHub. It contains one existing-content duplicate, one unique skill and one duplicate of that new skill. No live model is called. Stop the old fixture and start it again after pulling the revision. Production uses normal GitHub discovery and does not contain those stubs.
