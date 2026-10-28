# Claude checkpoint: generic predator controller GREEN and promoted — 2026-10-28

Nothing is committed. All results below are offline (fake adapters, Docker
Lua/Python). No GTA or ARK runtime behavior has been verified.

**Result.** Qwen implemented `mods/gta-ark/Mods/GtaArkLink/Scripts/predator_controller.lua`
(SHA `789c37c8…`) through SMELTER, starting from `scaffold_contract_subject`.
It passes the frozen `predator-controller-v1` contract, 48/48 checks against
verifier `c5478a76…`, and the policy contract stays at 30/30. Qwen recorded an
explicit GREEN finish, receipt `d970f26f-b137-4779-93ff-a4ed69491909` (watch
`93ad3ee2`, one watchdog nudge). Claude re-ran the verifier independently and
reviewed the code. The controller and its editable test were then promoted
to the main tree. Main tree results: Lua 7/7 programs, mods 14/14, 48/48 and
30/30. Manifest: `diagnostics/PROMOTION_20261028.json`.

**How it got there.** Qwen's first attempts failed: it invented its own
interface, its whole-file rewrites didn't parse, it restored an old draft,
compaction made its summaries drift, and it often ended a turn after only
announcing its next step. Tooling was added in response:

- Frozen failures come first in diagnostics, with `observed:` values labelled
  by the setup that produced them.
- Failing results and recovery context repeat the contract text and an
  interface checklist.
- Lua proposals are parsed before they are recorded.
- Operators can re-pin a reviewed verifier with `register_acceptance.py --migrate`.
- `coding_workspace_context` returns a compact summary by default
  (about 7.7K characters instead of 47K).
- `scaffold_contract_subject` generates the interface skeleton.
- Checkpoint restores report how many newer versions they discard.
- `read_coding_file` accepts line paging even with a stray offset/limit.
- The watchdog counts OpenCode's synthetic `invalid` tool as a protocol error
  instead of an unknown tool.

The verifier grew from 42 to 48 checks after review found three gaps that 42/42
didn't cover. Details: `docs/RECOVERY_GUARDRAILS.md`, `docs/FROZEN_ACCEPTANCE.md`
and `REQUIREMENTS.md`. Final suites after the last edits: dashboard 795 OK (9 skipped,
`.smelter/claude-final-dashboard-tests.log`), setup 144 OK, Node 78/78.

**Known gaps (next steps).**

1. `update` calls `describe` again after acquiring a target. If that second call
   fails, the code reaches the cooldown/attack branch without a verified range.
   The contract doesn't cover this; reusing the distance it already has fixes it.
2. The editable `test_predator_controller.lua` only checks that the module loads.
   A test that wires in the real `entity_policy` with vehicle/human records is
   still pending.
3. `raptor_system_main.lua` and `engine_adapter.lua` don't use the controller yet.
   The real adapter (`position`/`describe`/`candidates`/`move_to`/`attack`/`stop`
   for the chosen GTA runtime) and the in-game proof gates in the GTA–ARK handover
   remain.
4. Melty reuses one long OpenCode session per project. Each run compacts at
   around 115–128K tokens, and the Qwen model only partly fits on the GPU, so
   steps are slow. A fresh session per task would help.
5. After changing tool code, restart Melty (so its MCP tool process reloads) and
   the watchdog (so its tool list reloads).

**Runtime.** The dashboard (8769), watchdog and Docker were started from Claude
after a reboot. The dashboard uses the same Codex-side database and 7 grants.

---
# Claude checkpoint: promotion, controller contract, tooling fixes — 2026-10-28

Nothing is committed. Read [the GTA–ARK handover](handovers/GTA_ARK_MASHUP_HANDOVER_20261028.md),
the section "Claude continuation 2026-10-28".

- **Promoted.** The reviewed coding-copy files (4 scripts and 4 Lua tests) are now
  in the main `mods/gta-ark` tree. Manifest: `diagnostics/PROMOTION_20261028.json`.
  On the main tree, offline: Lua 6/6 programs and mods 14/14, both GREEN.
- **New frozen contract.** `predator-controller-v1` (42 checks, two fake adapters at
  different scales) is registered for workspace `897b9243`, with subject
  `mods/gta-ark/Mods/GtaArkLink/Scripts/predator_controller.lua`. After review its
  verifier was migrated to SHA `18269468…` (see `acceptance-migrations.jsonl`).
- **Qwen attempt 1.** Phase 1 (the stub) was GREEN. Phase 2 stalled: the controller
  invents its own interface and fails 42/42, and the editable test doesn't parse
  (line 99). The watch is parked in `wait_scope_review` with 0 retries. The copy is
  still RED/ERROR. Nothing from that attempt was promoted.
- **Tooling fixes in response:**
  - Frozen failures now come first in diagnostics, with `observed:` values.
  - Failing contract text and an interface checklist are attached to failing
    results and to recovery context.
  - Lua proposals are parsed before they are recorded.
  - Operators can re-pin a reviewed verifier with `register_acceptance.py --migrate`.
  See `docs/RECOVERY_GUARDRAILS.md`, `docs/FROZEN_ACCEPTANCE.md` and `REQUIREMENTS.md`.
- **Runtime.** After the reboot, Docker Desktop, the dashboard (8769, same
  Codex-side database, 7 grants) and the watchdog were restarted from Claude.
- **Next.** Run the controller-only retry prompt (it replaces the broken test, then
  rewrites the controller against the contract). Write the policy-wired editable
  test as a separate later step.
- **Evidence boundary.** All of the above is offline. No in-game behavior has been
  verified.

---

# GitHub/Claude checkpoint: saved coding copy GREEN — 2026-10-28

Game vision and integration details are consolidated in
[the GTA–ARK mashup handover](handovers/GTA_ARK_MASHUP_HANDOVER_20261028.md),
including the bridge, rendering plans, creature/shop roadmap and remaining
controller/native gaps. Read it alongside the Claude continuation handover.

SMELTER has applied proposal `b4eb565f-cd2a-4bb3-ae53-d648a37f1c50`.
Saved Lua: GREEN, 6 programs, 30/30 frozen checks, receipt
`6ee4b5e8-2a0a-49d9-8b6e-d53708e42f36`. Saved mods: GREEN, 14 tests with
one skip, receipt `f85b25de-e3b4-40a2-ae42-9b03fdb7e58e`. Both match current
tree `eaff3fa39d33b07d7b7a00f6de754802140c422ec6c892b9411275d04555f79c`.
The isolated copy is preserved in the portable handover archive, not merged
into production `mods/`. Do not reapply the prepared proposal.

Latest watch `3a683f6b6e1948a1a988b5b8d35c96da` waits for its originating native
runtime, which ended or changed; retries 0. The native turn ended without a
successful explicit finish marker. Preserve state and verify the live session
before any continuation. This is separate from the now-passing saved tests.

Start with [the updated Claude continuation handover](handovers/CLAUDE_CONTINUATION_HANDOVER_20261027.md).
All older RED/unapplied sections below are historical checkpoints.

---

# Verified correction prepared; working copy still RED — historical, 2026-10-27

Claude continuation: [complete handover](handovers/CLAUDE_CONTINUATION_HANDOVER_20261027.md).
Portable mod-source checkpoint and reference hashes:
[checkpoint archive](handovers/checkpoint-20261027/README.md).

Latest Qwen subject is `bd1a94e6ef3a3f63cacdc04183ce902bb6cf6c84b0638d49ebc459f079cba691`.
It added a guarded any-traits block but left an unconditional duplicate directly
below it (lines 93–97). Actual receipt `c2a32a39-57ef-4741-b79f-808ce7fbacaf`
loaded that SHA and stayed 24/30. Watch explicitly ended RED with zero retries.

Codex verified corrections in disposable copies without editing the working
policy/tests. Removing the duplicate reaches 28/30; fixing optional required/
blocked map presence/type checks reaches 30/30. One editable Group 22 assertion
still demanded an obsolete lookup reason; reference alignment to safe rejection
and nonempty reason yields Lua GREEN (6 programs), plus mods GREEN (14 tests,
one skipped). Frozen verifier unchanged. These are reference results, not a
claim that the saved workspace is GREEN or playable.

Prepared, **unapplied** targeted proposal:
`b4eb565f-cd2a-4bb3-ae53-d648a37f1c50` for existing workspace
`897b9243-fd7e-42f4-a46a-d1b814a33a81`. Its two files exactly match the tested
reference bytes. See [reference review](../diagnostics/POLICY_REFERENCE_REVIEW_20261027.md)
and [verified diff](../diagnostics/entity-policy-verified-fix-20261027.diff).
Next SMELTER task should apply that proposal, run Lua and mods, then explicitly
finish with both profiles. No new Qwen inference or automatic retry was sent.
No new tool/package installed; existing requirements suffice.

---

# Focused Melty slice: protocol succeeds, logic unchanged — earlier checkpoint, 2026-10-27

New human task `msg_17e5429000013wWw9w3jGi6nTt` used the scalar edit tool,
applied one proposal, ran Lua before/after and explicitly finished RED. Watch
`f74f75e8811340558ec28e33c91c0634` ended with zero retries. No malformed tool
arguments occurred in this slice; the two native tool errors were RED test
receipts. The cancelled prior watch's three retries remain separate.

Current receipt `d132185c-1de2-4ee2-a593-f40aaa5c5c7f` matches the saved tree.
Frozen result remains 24/30, with six failures. Subject SHA:
`b371dc8b136c3de3e5540a9a30c62c08790f1a5171a2b330cf0b6849729bb604`.
The edit changed `evaluate` from `if any then` to `if any and next(any) then`.
It did not change the earlier `validate_policy` rejection at lines 82/89, where
nil is substituted with an empty map. Thus it cannot fix the reported failures.

The pasted compaction summary is not authoritative: a whole optional map set to
false is malformed, but boolean false entries inside a table are valid disabled
entries. Nil alone means absent. Required/blocked empty maps impose no matching
constraint; a present empty/all-disabled any map rejects. Validate types before
iteration. The six failing NPC cases use normalized kind `character`, not
special human/police kinds. Next bounded change should target `validate_policy`
only, using a fresh live read and the existing frozen requirements. Do not edit
test assertions or kind classification to satisfy stale summary prose.

---

# Repair-loop run stopped; simpler coding protocol — earlier checkpoint, 2026-10-27

The prior recovered run consumed all three watchdog continuations and did not
converge. Repeated schema/duplicate-path/snippet errors coexisted with applied
patches, while frozen failures remained around 5–7 of 30. The exact bound turn
was stopped, its backend became idle and its watch is cancelled with reason
`operator_stopped_repair_loop`, retries still 3/3. No fourth prompt was sent.
Files/checkpoints and the journal are preserved; Codex did not author gameplay
repairs or weaken acceptance. See
[the diagnosis](../diagnostics/REPAIR_LOOP_REVIEW_20261027.md).

Current saved tree `3b95a5b1c9ce391f714dc01ed2c89fc037a153246a6eaf74eaf6fe0a74bcb2ae`
matches Lua receipt `77f473c5-83f7-4881-ae9b-e117c30e7536`: RED, six programs,
one failed program, no runner errors, frozen acceptance **6 failures / 30**.
Checkpoint metadata: `.smelter/repair-loop-checkpoint.json`.

New generic `propose_coding_edit` uses five scalar fields and the existing exact
edit engine. Stdio ToolSession now validates the same published schemas before
execution, recording malformed calls in budgets/audits/guards and returning
compact `input_contract_error` guidance. SDK pre-handler validation previously
bypassed those controls and echoed rejected code. No argument coercion added.
The already installed jsonschema dependency is explicitly pinned in requirements.

The watchdog holds on repeated protocol errors or three non-improving comparable
frozen results; it does not spend a retry to repeat a protocol/logic failure.
Explicit verified finish and the three-retry cap remain its automatic exits.
A new human task is required for further model work. Prefer a narrow failing
behavior on the SAME saved workspace; do not reset/replay the cancelled watch.
No new model inference is part of controller validation or MCP refresh.

Validation logs: `.smelter/repair-loop-contract-tests.log` (50 targeted tests
passed), `.smelter/repair-loop-dashboard-tests.log` (777 tests run, passed with 9 skipped),
`.smelter/repair-loop-setup-tests.log` (26 setup/requirements tests passed).
The idle native MCP instance was refreshed with conversation preserved and no
inference submitted. Dashboard refreshed (PID 53132 at this checkpoint); browser
visibly shows Cancelled, current Lua RED and WebSocket connected. Screenshot:
`.smelter/repair-loop-stopped-20261027.png`. Watchdog is enabled/running for future
human tasks (PID 50360 at this checkpoint), while the old watch stays cancelled
at 3/3. Always discover current process IDs instead of relying on this snapshot.

---

# Restart and watchdog completion correction — earlier checkpoint, 2026-10-27

SMELTER dashboard restarted on port 8769, PID 36700 at this checkpoint. The
browser visibly shows the live workbench, connected WebSocket and the recovered
Qwen turn. Private launch credentials stay outside this document. Screenshot:
`.smelter/smelter-restarted-live-20261027.png`.

The interrupted task exposed a completion bug: the old worker treated a current
RED test receipt plus an ended native turn as a final task flag, even when the
agent said it would keep working. It now requires a successful explicit
`finish_coding_task` call AND matching current receipt/tree/profile/hash proof.
Ordinary TDD RED/GREEN never ends a watch. Later validation invalidates an older
finish declaration. Frozen acceptance remains required for GREEN.

New controller module `tools/dashboard/coding_finish.py` is shared by the MCP
finish tool and watchdog verification. MCP instructions and recovery prompts
explain the protocol. Native shell/edit calls rejected before execution by the
exact SMELTER guard are recognized as blocked; executed/unknown side-effect
domains still hold. Requirements and WATCHDOG.md include the new component.

Operator `manage_task_watchdog.py resume` repairs only legacy automatic-RED
termination. It refuses explicit completion, Stop, a new objective, a changed
backend or active/human-waiting work. It preserves task ID and retry budget.
The original watch `19fb315a1d054d6380be8e23d0b6aa54` was rearmed and its first
continuation was observed busy in the same native session, with retries 1/3.
The daemon was restarted independently, preserving the running native turn and
journal. Use `status` for current PID/state; no hardcoded PID is authoritative.

Validation: 33 targeted watchdog/acceptance/MCP tests, 2 setup tests and 24
requirements tests passed. Latest focused watchdog rerun is recorded separately
in `.smelter/watchdog-final-focused-tests.log`. No external packages were added.
Gameplay remains Qwen's task; no new gameplay success is claimed here. The last
pre-recovery Lua receipt was RED with six protected failures out of 30.

---

# Initial watchdog installation — historical checkpoint, 2026-10-27

User explicitly authorized prompt capture and automatic recovery while AFK,
then clarified: no confirmation; exit on an end flag or after three stall
retries. This supersedes the former no-auto-prompt boundary for the separate
watchdog controller. Trace observation/its WebSocket remain read-only.

See [WATCHDOG.md](WATCHDOG.md). New standalone hidden Python service plus native
capture hook, scoped to the enabled exact native session/directory/workspace and
originating ACP process. The original objective, model/agent/variant and available
request constraints are preserved. A continuation recovers current checkpoints
instead of blindly repeating writes. At most three retries after the original
attempt; counter/reservations persist across restart. Verified scoped current
RED or GREEN ended a watch in this initial implementation. The explicit-finish
correction above supersedes that receipt-only rule.

Stop/new human input override recovery. Active tools/children, permissions,
questions and native retry waits do not admit another model turn. Unknown
external side-effect domains and uncertain POST delivery hold without replay.
No-reply context messages never cause watchdog-started inference. Compaction
messages do not reset the task or its counter. Text-only prompt capture is
bounded; unsupported attachments are not silently dropped.

Installed capture hook uses a SHA-named immutable local module to avoid stale
native ESM caches. Global OpenCode config preserved/backed up. Exact idle ACP
instance was reloaded with conversation preserved and zero inference submitted.
The hook ensures the hidden service is running when a bound prompt arrives.

Initial service PID was 45672 (no longer authoritative).
The adopted watch `19fb315a1d054d6380be8e23d0b6aa54` observed verified RED and
exited with zero retries. End receipt `ce534f2f-1ff8-4d33-9364-7adf589a752c`:
Lua RED, six programs/one assertion failure, frozen acceptance RED/six failures
of 30 checks. This is a later gameplay checkpoint than the previous 4-failure
report; Codex did not edit gameplay files during watchdog implementation.
The private prompt and copied request options are cleared in terminal records.

The service remains ready for the next human task. Safe operational proof:
`.smelter/watchdog/verification.json`. Public metadata projection:
`.smelter/watchdog/public.json`. Never serve runtime.json, private SQLite state,
raw prompts or copied system/tool options to the browser. Claude can add a
read-only trace adapter for the safe projection without adding socket controls.

Validation: full dashboard 763 tests run (9 skipped), setup 143 tests and
JavaScript 78 tests passed. Subsequent focused checks passed: 18 watchdog tests,
2 setup tests and 4 capture-hook tests. They include a real exited-process-handle
regression on Windows. Full logs `.smelter/watchdog-{dashboard,setup,node}-tests.log`;
latest focused watchdog log `.smelter/watchdog-focused-tests.log`.
No new external packages. Requirements and the state diagram declare components.

Operator commands: `python tools/setup/manage_task_watchdog.py status`, `start`,
`disable`, `activate`; `install` enables/registers, and `adopt` explicitly captures
only the latest real human prompt in the bound session. Do not adopt synthetic
compaction or old cancelled tasks. Do not reset the durable retry journal to
restart a stalled task's budget.

Parallel Claude trace files were preserved. Existing `dw3_decomp-main/` remains
unrelated and untouched. No commit/push requested.

---

# Frozen acceptance checkpoint — 2026-10-27

User reported another interruption and then a rate-limit cutoff; resumed this
controller task from its current state. Native metadata recorded the last model
turn as ended with no active tool. That does not identify the cutoff cause.
The substantive regression is verified: the model fixed the nil-map crash but
removed strict trait validation to satisfy an obsolete editable assertion.

[Implementation and limitations](FROZEN_ACCEPTANCE.md): new generic,
operator-registered frozen acceptance runs outside model-editable copies.
Registered `entity-policy-v1` for workspace
`897b9243-fd7e-42f4-a46a-d1b814a33a81`, subject
`mods/gta-ark/Mods/GtaArkLink/Scripts/entity_policy.lua`. Verifier has 30 checks,
no engine-specific code or new package dependencies. Registration is not exposed
to the model. Ordinary Lua validation now requires both local and frozen layers.

Fresh receipt `5608029b-67de-4aa9-9453-6961f8578f56`:
- Editable Lua suite GREEN (six programs); frozen acceptance RED (26/30 pass).
- Overall RED. Four failures: unused nonboolean entity trait; false instead of
  each optional required_traits, any_traits and blocked_kinds map.
- Tree `0f3ee8054d19e1e6bf612db8fe1c35db49845c414365286801eeb76248e7e224`.
- Subject SHA `4ef6844341f176cef01ffc17cf32ff2379e12d0ad656d12b8ee8a7b440dc94b5`.
- No gameplay source, test fixtures, controllers or adapters edited by Codex.

The live trace now separates ended responses from task outcome: changes needed,
not verified, or current checks passed within scope. Both local and frozen stages
are visible. Frozen failure sets the native MCP failure signal; repeated failed
unchanged test calls redirect to recovery. No automatic model turn/resubmission
or cancellation override was introduced.

The actual idle native ACP worker's SMELTER MCP server was refreshed and reported
connected; conversation preserved and no inference submitted. Evidence:
`.smelter/frozen-acceptance-native-refresh.json`. Native hooks' updated wording
loads on the next native process; acceptance enforcement is active in the MCP
server independently of that wording. Validation passed: 732 dashboard tests run (9 skipped), 140 setup tests,
59 JavaScript tests, and 6 focused acceptance checks after the receipt wording
update. Logs: `.smelter/frozen-acceptance-{dashboard,setup,node,focused}-tests.log`.
GUI gracefully reloaded on port 8769 (PID 5456). Browser verified a connected
WebSocket, editable GREEN/frozen RED/current overall RED and Changes needed.
Screenshot: `.smelter/frozen-acceptance-ui.jpg`.

SMELTER/Qwen remains the gameplay author: restore upfront strict trait validation,
use explicit nil checks for optional maps, and reconcile Group 22's incidental
reason-code assertion with the frozen behavior. Never relax validation to match
an editable comment. Do not alter the frozen verifier. Keep the architecture
universal. Existing untracked `dw3_decomp-main/` is unrelated and untouched.
No commit/push requested this turn.

---

# Recovery guardrails checkpoint — 2026-10-27

The current request is to improve guidance/guardrails and recover from stalls.
Infrastructure implementation and registration are described in
[RECOVERY_GUARDRAILS.md](RECOVERY_GUARDRAILS.md). No gameplay source or fixtures
were edited by this controller task; no model turn was submitted.

- New `coding_recovery_context` returns current canonical paths/hashes,
  checkpoint references and verified first-failure evidence. Failed test CWDs
  resolve stack paths to the right copy, with ambiguity left explicit.
- Exact targeted edits tolerate unique LF/CRLF contexts and preserve unrelated
  bytes. Reads disclose newline style. Repeated failures/reads redirect to
  recovery; only transient approved reads get one audited retry.
- Persistent stdio MCP uses a 128-call/15-minute renewable rate window rather
  than a lifetime 32-call budget. GUI message budgets remain unchanged.
- Local native recovery plugin registered in OpenCode config with a backup;
  native config validation succeeded. Hooks load on next native process and
  guard only the enabled exact session/directory binding. Native edit/bash/task
  bypasses are blocked for that task. No ACP worker was running during setup.
- Missing Ollama provider deadline defaults added: chunk 180s, headers 300s,
  total request 900s. Existing explicit settings are preserved. No automatic
  prompt submission, access approval or cancelled-task restart was added.
- Requirements and documentation declare all components; no new packages.
- Fresh prototype Lua receipt `81ff027f-ba7b-4b09-9ed1-21824e5e7795` is **ERROR**,
  six programs / one runtime exception, with unchanged source tree
  `3d22fe530310b92357c29b723951694963820087f088e8af74c93c3f8f92b97c`.
  The failure is `entity_policy.lua:72` (`pairs(nil)`), not syntax at test line
  150. Policy SHA is `2d44b3ade5ddc9b424f73d4d8cb47ca50a7a30bec03f5ef0217e5fa3433f1e10`.
  Never repeat the attachment's stale GREEN claim.

Validation: dashboard suite 724 tests run (9 skipped), setup 139 passed,
JavaScript 58 passed. Final focused recovery suite: 8 passed after adding
canonical first-frame resolution and bounded test metadata. Logs are
`.smelter/recovery-{dashboard,setup,node,focused}-tests.log`.
Native config validation is `.smelter/recovery-native-config-validation.json`.
The GUI was gracefully reloaded on port 8769 (PID 48136); browser inspection
confirmed lua ERROR/current and mods GREEN/stale over the live WebSocket.
Screenshot: `.smelter/recovery-guardrails-ui.jpg`.
No end-to-end Qwen stalled-inference recovery run was submitted.

Preserve the original frozen eligibility semantics, regression fixtures, both
controller copies and the universal shared-policy/engine-adapter separation.
SMELTER/Qwen remains the gameplay author. Existing untracked `dw3_decomp-main/`
is unrelated and must remain untouched. No commit/push was requested this turn.

---

# Continue SMELTER work

## Fragment-overwrite incident recovered; generic editing safeguards added

The reported stall was an ended native response (finish=stop, no pending tool),
after applied proposal `d2e29b77-ae2c-4ef3-a777-8774fb8d2524` replaced the
4,962-byte/118-line policy with a 537-byte/11-line fragment. Expected pre-edit SHA
was `0eeb5bcc...feeb`; fragment SHA `ec4bd17f...c74e`. The original checkout
contains no entity_policy.lua, so source-baseline restoration could not recover
that coding-copy-only file. The file index also has hashes, not old file bytes.

Preserved the fragment and extracted exact pre-edit bytes from the existing tool
audit, verified full SHA, and restored them via recovery proposal
`c21e761c-3f75-47c9-b01a-ee1811187e4d`. Current tree returned exactly to
`3b2801df5fdf5320b979cb6b4d4d6785725fe08d707c34434e8649a8f0d8cfd4`.
Saved a durable owned checkpoint with full policy hash
`0eeb5bccda445136d25a65ef6b75f941a31c6e49e386eabd8e1df84f1e07feeb`.
Recovery restored prior bytes only: the six frozen acceptance failures remain.
No gameplay implementation was authored and no model continuation was submitted.
Evidence: `.smelter/progress-reviews/patch-corruption-20261027/recovery.json`,
`entity_policy.corrupted.lua`, `entity_policy.recovered.lua`.

Generic fix: new `propose_coding_edits` assembles complete files from unique exact
old_text/new_text replacements. Legacy content proposals explicitly replace the
whole file and now reject likely snippet truncations by default, with line-count
previews and explicit acknowledgement for intentional whole rewrites. Apply saves
pre-edit checkpoints; restoration accepts one checkpoint_sha256 for workspace-only
files. Context/receipts expose checkpoint hashes. Updated schemas, dispatch,
file cards, native/direct bridge instructions and requirements. No packages added.
Live trace now says Response ended and shows current/stale validation receipts.
See [editing/recovery docs](WORKSPACE_TRACKING.md#safe-targeted-edits-and-checkpoint-recovery).

Validation: 712 dashboard tests OK / 9 skipped, 136 setup OK, 50 JavaScript OK.
Eight new exact-edit/checkpoint tests include real MCP round trips, full-file
cards, stale/ambiguous context, Unicode/CRLF/BOM preservation, checkpoint ownership
and tampering, workspace-only recovery, and exact incident truncation rejection.
Initial checkpoint filenames exceeded Windows path limits; shortened deterministic
keys with full ownership/SHA validation corrected that before final checks.
Logs: `.smelter/exact-edit-{dashboard,setup,node,new}-tests.log`.
Fresh restored-workspace Lua receipt `556796d3-aa2c-4021-876c-fc4a8f7fefbe`
is GREEN for six programs with matching source; frozen acceptance failures remain.

GUI gracefully reloaded: PID 50064, port 8769 at this checkpoint. Current launch
credential is only in `.smelter/dashboard-knowledge.stdout.log`. Hot refresh of
the native MCP registration was not performed: Melty is open but no ACP worker
is running (only the separate OpenCode serve process remains). The updated stdio
server/schema loads when Melty next connects/starts its OpenCode worker. Do not
claim an ACP hot refresh succeeded or resume gameplay automatically. No prompt
or task restart was submitted.

## Graphify feasibility reviewed; not installed

User asked about Graphify-Labs/graphify with the live WebSocket trace. Reviewed
official README, package manifest, CLI, watcher, JSON/HTML exporters. Recommended
Graphify as the code-relationship layer, joined to existing observed native task
events by workspace/path/revision. Code-only AST indexing can avoid model calls;
the watcher handles debounced source changes. A custom graph adapter/live overlay
is still needed. Exported HTML currently uses a CDN vis-network script, so use
validated JSON and a locally served renderer under the existing CSP. No packages,
skills, hooks or requirements entries added: this was assessment only. Details:
[GRAPHIFY_TRACE_PLAN.md](GRAPHIFY_TRACE_PLAN.md). Future implementation must pin
and declare actual dependencies, preserve observed/extracted/inferred evidence
and keep current task-ID and test-receipt semantics intact.

## Latest eligibility report: 26 checks GREEN, acceptance rule weakened

Reviewed attachment `bb169603-9e91-4a69-b444-64733f544c3a/Pasted text.txt`.
Receipt `46d43b67-2cd0-4168-a67e-bbd9d2c76825` genuinely matches current tree
`3b2801df5fdf5320b979cb6b4d4d6785725fe08d707c34434e8649a8f0d8cfd4`:
one Lua profile, six test programs, zero failures/errors/skips, matching source
and imports. Policy SHA
`0eeb5bccda445136d25a65ef6b75f941a31c6e49e386eabd8e1df84f1e07feeb`;
policy-test SHA `97916a81363a178b5e3845e56700118c1047e93a8c54453156cd00204406022e`.
All seven prior operator regression checks now pass, including disabled trait
handling and rejection of a queried nonboolean trait. Test-local Unity/RAGE-shaped
normalizers now call the same real evaluator for one allowed police fixture.
Both controllers, behavior harness and six original fixtures remain unchanged.

Do not approve controller integration yet. Group 25's heading still says no
enabled any-trait alternatives reject, but its assertion was changed to allow.
Policy now allows both `{}` and all-false present any-trait maps, contrary to the
explicit prompt. Entire entity trait maps are not validated; unqueried malformed
values/keys can be admitted. Any-trait validation stops at the first true entry,
so a later malformed entry can be ignored. Optional `required_traits=false` is
also accepted instead of rejected as malformed.

Independent unchanged-copy probe:
`.smelter/progress-reviews/f86231eb88614804a6de9750745c98ab/policy-acceptance.json`.
Thirteen checks: the seven prior regressions pass, six explicit-contract cases
fail; one diagnostic Lua program is RED with matching source bytes/imports.
The active task tree was not edited. This is test-contract drift, not stale
Docker source. Freeze these acceptance expectations before another SMELTER pass;
do not alter assertions to fit the implementation. Validate all maps before
short-circuit evaluation, restore the present-empty/all-disabled rejection rule,
and finish opposite policy outcomes plus positive/negative fake-adapter cases.
Group 20 should use an entity actually missing the disabled required trait.
No real Unity/RAGE integration is established by test-local normalization.

Workspace index/relations and project memory updated. No new package, native
prompt or gameplay edit by the operator. The WebSocket feature below remains
implemented; this review did not change the monitor or restart it. See newest
[review](../diagnostics/RAPTOR_FORENSIC_REVIEW_20261027.md).

## Live WebSocket task visualization implemented

User requested per-task component/file activity and stall clues across Melty,
OpenCode, Ollama/Qwen and SMELTER skills/tools. Implemented `task_trace.py`,
`task_socket.py`, `task_trace_ui.js`, authenticated HTTP/socket routes, and the
Live task trace panel/card. Uses the existing exact native session/directory/
owned workspace binding. Traces current-turn descendants, named file paths and
indexed hashes, loaded skill names, model/provider metadata, access/question
waits, tool-budget errors and operation durations. Separates transport heartbeat,
collector freshness and native activity: 120s quiet warning; >15s stale collector
becomes telemetry delayed. No model calls, native task controls or auto-approvals.

The live browser verified an authenticated WebSocket, current task completion,
actual file paths/index hashes and settings navigation. Screenshot:
`.smelter/task-trace-ui.jpg`. One UI issue (details button only selected a hidden
panel) and a Windows UTF-8 round-trip issue were caught and corrected during
browser verification. Expanded timeline/scroll state survives streamed redraws;
file overview groups repeated operations by path. Native lifecycle history and
final relation snapshots remain in the original monitor.

Important integration boundary: Melty's current connector and observed native
session metadata expose no Melty-generated task-ID feed. The automatic ID is the
actual native user-message ID and is explicitly labelled. A supplied Melty ID
can be linked without restarting/rebinding via Native task progress / Link Melty
task ID or authenticated `action=correlate`, `melty_task_id`, `expected_revision`.
It is not independently verified or fabricated. A Melty-side ID hook remains to
be supplied. Upstream stays SSE/read-only SQLite; the dashboard feed is WebSocket.

Requirements updated in REQUIREMENTS.md and system-requirements.json; no packages
installed. Existing Windows PowerShell/CIM finds actual ACP listeners for GET-only
access/question inspection. Unsupported platforms explicitly lack that feed;
other native metadata still works. Snapshot records are bounded and exclude
prompts, reasoning, contents, shell commands, arbitrary args/results/error bodies.
Hashes are indexed identities with timestamps, not fresh per-read content proof.

Validation: dashboard 704 tests OK / 9 skipped; setup 135 OK; final JavaScript
49 OK; focused trace/socket tests 17 OK. Logs:
`.smelter/task-trace-{dashboard,setup,node,focused}-tests.log`. GUI gracefully
reloaded on port 8769, current PID 7192 at this checkpoint; current launch token
is only in `.smelter/dashboard-knowledge.stdout.log`. Native conversation/model
was not restarted and no prompt was submitted. Details and task-flow diagram:
[Native progress](NATIVE_PROGRESS.md#live-websocket-task-trace),
[live-task-trace.mmd](diagrams/live-task-trace.mmd).

## Latest policy review: original defects fixed; trait maps and conformance remain

Reviewed attachment `0e848155-b42d-4fd1-863b-a47d2ca03554/Pasted text.txt`.
Fresh receipt `2c922abd-cbd9-4af0-a3ac-bcffe41d5db5` is genuinely GREEN: six
Lua programs, nineteen policy checks, zero failures/errors/skips. Current tree
independently matches
`7c95849a44f541f4fde25ca30a10dd39e24d83b5b9699d0a97552211fed9f90c`;
source bytes/imports match. Policy SHA is
`428b29e0eca3080f52886a33fd77b1d7b99488bdb3ddd27e4f6fe70b8c973cdd`.
The three original failures are fixed: malformed required-trait field rejects
safely, explicit blocks override allows, and string flags cannot admit an entity.
The behavior harness now fails on an existing deterministic ID and has no
unasserted vehicle call. Both controllers and the six original fixtures remain
unchanged. Do not redo these completed fixes.

Not ready for controller integration: unchanged-copy diagnostic probe
`.smelter/progress-reviews/f0fd4b417f1047b4b17b0f094ad731a9/policy-contract.json`
passes those three original regressions but fails four trait cases. A false
required-trait entry still requires presence; a false any-trait entry can satisfy
the rule; nonboolean entity trait values and required-trait map values can be
accepted. Apply boolean-map validation to trait maps and interpret only enabled
entries. Optional-field and empty/all-disabled-map semantics must be explicit.

The nineteen-check file still has no two fake adapters. Its same-entity policy
test asserts true under both policies, so it does not prove configuration changes
the eligibility outcome. Add two different raw adapter translations into the
same real evaluator, contradictory name/classification cases, and a demonstrated
allow-to-reject policy switch. Keep flag reason codes stable and avoid another
whole-module rewrite. Use actual current hashes with propose/apply/readback;
metadata still contains no new applied proposals for these direct native edits.
No operator gameplay changes or model turn were made; no dependencies installed.
Workspace index, relations and project memory were refreshed. See the newest
[review](../diagnostics/RAPTOR_FORENSIC_REVIEW_20261027.md).

## Live task unblocked: child access request and MCP budget

Latest status after recovery: both parent and child are idle with
`MessageAbortedError`, completed at approximately 07:58:53 UTC (11:58:53 Muscat).
The second read ended with `Tool execution aborted`. Cancellation origin is not
established. No new test receipt was produced and no automatic resume was sent.
Keep the saved task files; user-controlled continuation is required to resume.

27 October, approximately 11:57 Muscat: the parent session was waiting on child
`ses_e83e3ab6cffep45ufziYUadIAG`. The child had exhausted the persistent SMELTER
tool-call budget, then waited about seventy minutes on a native
`external_directory` permission request for the existing owned workspace's test
folder. Parent progress showed busy throughout; no new test receipt existed.

Using the user's standing access authorization, the operator refreshed only the
actual ACP process's SMELTER registration with its exact existing configuration,
after verifying the bound parent/child directories and zero in-flight SMELTER
calls in that directory. The conversation was busy, but its SMELTER connection
was quiescent. Then granted the exact pending test-directory read once. The read
completed at 07:56:51 UTC; Ollama subsequently loaded
`qwen3.5:35b-a3b-128k` with context length 131072. No prompt was submitted and no
session was restarted. Do not confuse this recovery with gameplay validation.

A second pending read subsequently requested the same owned task's
`mods/gta-ark/Mods/GtaArkLink/Scripts/*` folder. After verifying the tool was a
read inside that folder, the operator approved and remembered that exact folder
scope. The earlier tests-folder grant was once only; no broader directory grant
was added.

Policy, policy-test and behavior-harness files changed after the prior review;
their current tree was `4cef4fd171305ba6a51939cd0a9edac17014c8c9c6b7a75bc9967de4b00c7750`.
The earlier GREEN receipt is stale for that tree. Follow this same task to a new
receipt before judging the fixes. Infrastructure follow-up: show child-session
pending permissions in the progress UI, and address lifetime MCP call-budget
exhaustion without bypassing per-task limits. A one-time read grant does not
preapprove later native directory requests.

## Latest eligibility review: helper exists; hardening required

The same owned workspace `897b9243-fd7e-42f4-a46a-d1b814a33a81` now contains
`entity_policy.lua` (SHA `ee4e5fed...37e66`) and its eleven-check test
(`e9764d3c...4d78e`). Lua receipt `7ee2d221-1065-4ac3-b1d3-4502fd6ad94e`
is genuinely GREEN: six test programs, zero failures/errors/skips, matching
host/container source bytes and actual policy-module import. Independently
rehashed current tree matches
`9cced0c411e561d580cff110987ccdf378c5e2da9b87b3e3baab8830fac1fe64`.

A disposable offline probe of the identical policy bytes reproduces three
failures: a string `required_traits` throws, a kind in both allowed and blocked
sets is allowed, and string `"false"` valid/alive flags are admitted. Evidence:
`.smelter/progress-reviews/1c19ea5bdd754a6fb59fb8a9b07575cf/policy-safety.{json,log}`.
The ordinary tests construct normalized tables directly; two different fake
adapters and misleading-name classification tests remain absent. Do not accept
the printed adapter-portability claim or integrate this helper into the controller
yet. The old harness still has its `_new` ID fallback and unasserted vehicle call.

Next SMELTER slice: reproduce these failures in the existing tests, validate
optional policy fields and boolean values, define block-over-allow and disabled
set-entry semantics, then prove both fake adapters exercise the same evaluator.
Keep controllers/native adapters and six original fixtures unchanged; clean up
the two harness leftovers alongside this slice. Require propose/apply/readback
and current source/import evidence. Gameplay authorship and prompt submission
remain with SMELTER/Qwen and the user. Operator review only copied unchanged
policy bytes into a disposable diagnostic fixture; no gameplay edits or new model
turn were made. No dependencies were installed. Workspace index and relation
source were refreshed. See the newest [review](../diagnostics/RAPTOR_FORENSIC_REVIEW_20261027.md).

## Current acceptance: aligned state-creation harness verified

Proposal `5e75056e-a257-4ca7-9f3a-c67934b2cb83` applied; harness hash
`46e1f095f32122c7a353f5f954fd8c22e0f2e552cb3e95576724b2c37a91ed9d`.
Current Lua GREEN receipt `58e11405-b6b4-4089-bccc-81a5b311e2ef` has five programs,
0 failures/errors/skips, matching host/container bytes. Rehashed tree matches
`c3f870a1a3d18bb097576da19db072f4d1d4385b45dedae934b0d16e62ec44fd`.
Behavior and export tests both load root Mods/... controller dd63522f; actual
exports are checked before setup and no state table replacement or fake vehicle
pass remains. Offline state-creation evidence only; vehicle handling is explicitly
UNIMPLEMENTED/untested. Old Python/mods evidence remains stale.

Move to a small generic eligibility slice: normalized adapter entity descriptors,
configuration-based policy, allowed humans/NPCs/cops/player and rejected vehicles/
invalid/dead targets, same real shared logic through two fake adapters. Alongside
that test work, replace the `_new` fixture-ID fallback with an explicit fresh-ID
assertion and replace/remove the unasserted vehicle call. Do not start another
harness/Docker diagnosis loop or expand into spawning/attacks/assets yet. Operator
review made no gameplay edits or extra model/test run. Keep SMELTER authorship and
user-controlled prompt submission. See the newest
[review checkpoint](../diagnostics/RAPTOR_FORENSIC_REVIEW_20261027.md).

## Current harness review: real GREEN, coverage gaps remain

Latest supplied attempt finally uses a dot call and has a genuine current Lua
GREEN receipt `9251a9d5-bdd0-4056-9eec-18b175d4e831`: five programs, no failures,
errors or skips, matching host/container manifests. Rehashed current tree:
`55a46cf2c5a15664a3242c1dc6518b0dbb34176c1aac61dfa7c452399b4f34c0`.
Harness SHA `86edcf72...2c3af`; controller hashes dd63522f/root and 05e91c2/ark
are unchanged. Three latest applied proposals affect only the harness. Six
original regression fixtures still match checkout; the old Python receipt is stale.

Do not approve full harness/gameplay completion yet: the vehicle branch increments
tests_passed unconditionally; behavior now loads ark/Mods/... while module/export
tests load the distinct root Mods/... implementation; and resetting raptor_states
before asserting its type can mask a missing export. Next SMELTER pass must align
one authoritative implementation by tracing callers, remove fake pass accounting
and validate actual exports. Generic classification and two-adapter conformance
remain unimplemented. No operator gameplay edits or new model/test run in this
review. See the newest section of
[forensic review](../diagnostics/RAPTOR_FORENSIC_REVIEW_20261027.md).

## Latest checkpoint: Docker diagnosis disproved; ACP progress corrected

User supplied the long Raptor attempt in attachment
`78d425c5-3177-41f8-b201-8f9642fae35d/Pasted text.txt`. It contains repeated
incorrect Docker-cache claims and workspace resets. See
[forensic review](../diagnostics/RAPTOR_FORENSIC_REVIEW_20261027.md).

Fresh original-workspace Lua receipt `4e6049ea-9abb-4ec3-95bb-72c1b0ae9191`
is RED, with matching host/container Lua source bytes and actual imports proving
the controller `dd63522f...9750c` was loaded from the expected Mods/ path. The
test is still `3d96b91f...cb2c` and calls dot-defined start_chase using `:`.
That supplies the module table as ID; the guard returns false without throwing.
The harness mistakes pcall success for operation success. New copies also repeat
the mods/gta-ark prefix in package.path and contain a check(true) vehicle test.
Python mods GREEN does not execute Lua. Do not rebuild images or create more copies.

Added universal runner evidence: a fresh snapshot identity, independent host and
container source manifest comparison, per-test CWD/exit code and standard Lua
loader import paths/hashes. Missing/inconsistent proof becomes ERROR. Source
is bind-mounted from a per-invocation copy; the fixed image is runtime/toolchain.
Disposable evidence under `.smelter/progress-reviews/24f0f091b50049e985cfb7372e9a3188/`
proves colon rejection and successful dot call with the identical controller.
This does not prove targeting or game integration. No active gameplay file was
edited, and every agent-created workspace remains preserved.

The first real run exposed an HTTP-only monitor limitation: Melty's OpenCode ACP
process has a separate event bus from the manually started HTTP server. Added
`native_activity.py`, selecting only allowlisted shared SQLite lifecycle fields
in mode=ro/query_only. It verifies the exact session/directory, excludes all raw
message/part bodies, samples bounded batches and persists a cursor. Shared
lifecycle state takes precedence over the other HTTP process's idle report.
Recovered this run's public tool activity: native progress sequence 68, idle,
shared metadata connected, one final original-workspace chart captured. Recovery
is sampled metadata, not a lossless live event transcript.

Native budget recovery used the actual ACP process's discovered loopback API
port 51748 (PID 28516 at this checkpoint), after both its session status and
shared lifecycle metadata confirmed idle. Refreshed only its SMELTER registration,
preserving exact config/environment and the conversation. Port 4096 belongs to
the separate HTTP serve process and would not refresh ACP's MCP child. Native
ports/PIDs can change; discover and verify ownership/directory before future use.

GUI reloaded gracefully: PID 21744 → 41632, port 8769; current private token is in
`.smelter/dashboard-knowledge.stdout.log`. No native/model task was submitted.
Validation: full dashboard 686 OK / 9 skipped, final focused metadata 8 OK,
Lua runner 8 OK (real Docker), setup 134 OK, JavaScript 44 OK. Logs:
`.smelter/forensic-runner-{dashboard,setup,node}-tests.log`,
`.smelter/native-activity-tests.log`, `.smelter/snapshot-evidence-lua-tests.log`.
Metadata test #8 was added after the full suite and verifies a new binding cannot
fabricate completion for an old cancelled task. Runtime observation saved in
`.smelter/forensic-runtime-status.json`. Requirements/docs record the built-in
SQLite reader and stronger Lua evidence; no new package/image was installed.

Next user-run SMELTER slice: original UUID only; fix harness call/return semantics,
consistent counters and meaningful vehicle assertion before production changes.
Then implement the shared generic boundary from the universal contract. Preserve
SMELTER gameplay authorship, original regression fixtures and user-submitted
prompts. Leave unrelated `dw3_decomp-main/` alone. Do not auto-commit new changes.

## Current direction: universal gameplay first — 27 October 2026

The user clarified that SMELTER is a universal modding workbench. The Raptor work
is an acceptance case; reusable controller logic, debugging, file tracking and
testing must not depend on GTA/ARK. Native calls, units, assets and loaders belong
in explicit engine/game adapters and project profiles. Necessary adapter-specific
changes remain inside that boundary, with shared conformance tests.

Prepared [shared gameplay contract](UNIVERSAL_GAMEPLAY_CONTRACT.md),
[SMELTER task brief](tasks/RAPTOR_GENERIC_TASK_BRIEF.md) and
[proposed relation chart](diagrams/universal-gameplay.mmd). These are design and
handoff artifacts, not a claimed implementation or new installed skill/tool.
Existing coding runners and ECC/debugging/gameplay profiles suffice for the
offline slice. A future adapter-contract skill should grow from proven shared
interfaces, rather than adding another large skill pack now.

Current file inspection found a replaced minimal controller, not the earlier
line-95 implementation. Controller hash `165a5e79...c164c17`; behavior test
`a5229f90...926ca059`. The test still uses `:` against a dot-defined function,
misinterprets pcall success, has inconsistent counters/undefined checks_failed,
and does not assert actual vehicle rejection. The controller fabricates sample
targets, and the adapter can return success for a placeholder spawn or silently
fall back to simulation. See exact paths/hashes in the task brief. Do not repair
old remembered code or replace baseline tests to get GREEN.

Only documentation and project memory were updated for this architecture review.
No gameplay edits, fresh gameplay test run or model prompt was performed. Last
startup check found GUI/native OpenCode unreachable; saved binding was intact.
Start the existing stack when proceeding with user-run Melty acceptance. Continue
using the same owned workspace and keep NPCs/cops/player eligible, vehicles
excluded. Preserve user-controlled prompt submission and SMELTER gameplay authorship.

## Latest checkpoint: live native progress — 27 October 2026

Implemented a read-only native SSE monitor (`tools/dashboard/native_progress.py`)
and dashboard card/settings panel. It binds the exact native directory/session
to an owned coding workspace, normalizes public tool/status metadata, coalesces
legacy/v2 tool events, reconnects with a gap indication and status reconciliation,
and saves a final index/chart after observed work becomes idle/failed/cancelled.
Initial idle is not fabricated task completion. No prompts, message text,
reasoning, tool arguments/results, raw error bodies or provider metadata are
mirrored. Monitor pause/resume never controls the AI task.

The actual binding was verified against OpenCode's running API:

- Session: `ses_e873d493effeIa6L0ZxcaFq5nd`.
- Native directory: `C:\Users\Dr.Dark92\Melty\grand-theft-auto-v-enhanced-ark-survival-ascende-2`.
- Coding workspace: `897b9243-fd7e-42f4-a46a-d1b814a33a81`.
- Actual connection: connected; session idle; no model prompt submitted.

Saved state is `.smelter/native-progress/state.json`, enabled for normal GUI
startup. At most five bounded completion charts and 300 recent transitions are
kept; rebinding archives prior state (ten archives before review), with no deletion.
Maintenance accounts for/backups these records and excludes them from ordinary
retention. Current policy is rechecked when returning historical graph nodes.
Requirements declare this built-in runtime; no new third-party package was installed.

The idle GUI was reloaded gracefully on port 8769: old PID 26232 → PID 27244 at
this checkpoint. Current launch log is `.smelter/dashboard-knowledge.stdout.log`
(contains the private local launch token). Native OpenCode/model sessions were
not restarted. The current IAB tab was reauthenticated and verified visually:
compact progress card plus Settings → Debugging → Native task progress. Screenshot
`.smelter/native-progress-main.jpg`; deployed cached API observation
`.smelter/native-progress-deployed.json`; read-only live SSE probe
`.smelter/native-progress-live-probe.json`. Recheck PID and idle jobs before any
future reload. Never force-kill a dashboard or native task.

Validation: full dashboard suite 676 OK / 9 skipped; final targeted native suite
17 OK (includes a later-added fresh-task gap regression); setup suite 134 OK;
final JavaScript suite 43 OK. Logs `.smelter/native-progress-{dashboard,setup,node}-tests.log`
and `.smelter/native-progress-focused-final.log`. Local HTTP fixtures verify
busy/tool/idle and disconnect/reconnect with GET-only requests. Browser state
confirmed the exact saved binding and live idle connection. Mermaid source is
maintained; renderer compilation remains unchecked on this machine.

Next acceptance: let the user submit the next Melty Raptor task, watch real busy →
tool → idle transitions and confirm its final chart without operator model calls.
Do not send their prompt for them. Gameplay authorship stays with SMELTER/Qwen;
target policy remains human NPCs/cops/player allowed, vehicles excluded. No gameplay
files were edited by this infrastructure work. Next implementation is registered
texture/GLB/animation ingestion and previews; lifecycle monitoring does not mirror
native generated attachments or message text yet. See [native operation](NATIVE_PROGRESS.md),
[media plan](NATIVE_PROGRESS_AND_MEDIA_ROADMAP.md) and
[updated architecture chart](diagrams/workspace-tracking.mmd).

The user requested committing and pushing this SMELTER checkpoint to GitHub on
`feature/agent-stack-game-mods`, including ECC, baseline restore, workspace tracking
and native progress. Leave unrelated `dw3_decomp-main/` alone. Runtime state,
credentials, launch tokens and local test logs remain excluded by `.gitignore`.

## Previous checkpoint: workspace identity, index and relation charts

The user requested persistent file locations/hashes after native Qwen repeatedly
confused the Melty staging folder, checkout and coding copy. This infrastructure
request supersedes further operator gameplay repairs. Gameplay authorship remains
with SMELTER/Qwen; do not send native prompts or restart their chat automatically.

Delivered `coding_workspace_context` through the built-in MCP, filename/path
search, canonical host paths on reads/lists, explicit line pagination, a persistent
SHA-256 ledger and observed/static/inferred relation graphs. Managed/direct
dashboard tasks preserve final chart snapshots. Preparation, list/context, apply,
test and review update the index. External writes require a refresh/next scan.
The dashboard adds Settings → Debugging → Workspace files & relations, with a
two-second cached view while open. No full native task stream mirror is implemented.

The existing `diagrams` skill is now a valid native manifest and bridged, together
with compact continuity instructions. Installer `tools/setup/install_workspace_tracking.py`
and profile/setup `workspace_tracking` are declared in both requirements files.
No new package was installed. Native `opencode debug skill` discovers diagrams;
the idle SMELTER MCP connection was refreshed and is connected. Global native
instruction files may load at the next normal client startup; current MCP
initialize instructions also explain recovery/chart steps. Do not force a restart.

Real MCP context verification is saved in
`.smelter/workspace-tracking-verification.json`. The task remains workspace
`897b9243-fd7e-42f4-a46a-d1b814a33a81`, whose host copy is in the sibling
`SMELTERV2/coding/` directory. Two engine_adapter.lua paths have different hashes;
the index returns both instead of choosing one. Current observed tree is
`1622823e2fb30ea914b0bc44e66b1690861b36d29078c9fd1d41d81a12dea364`.
Its latest Lua receipt is RED/current; the older mods GREEN receipt is stale.
This turn did not edit gameplay modules or run a new gameplay/model task.

Verification: dashboard suite 659 tests, OK/9 skipped; setup 133 OK; Node 39 OK;
focused finalization/index suite 9 OK, including the later-added persisted chart
test. Logs: `.smelter/workspace-tracking-{dashboard,setup,node}-tests.log` and
`.smelter/workspace-tracking-focused-final.log`. Native skill validation passed.
The dashboard was started hidden on 8769, PID 26232 at this checkpoint, launch
log `.smelter/dashboard-tracking.stdout.log` (contains private local launch token).
Authenticated API and JS asset verified. A tab opening was queued in Codex; a
manual browser visual check was not available in this chat's active IAB surface.
Revalidate PID/job status before any future graceful reload; never force-kill.

Next: bind a specific native session + directory + workspace for a read-only SSE
progress relay. Official OpenCode `/event` transport was verified locally; no
public Melty progress-WebSocket contract was verified. Generated texture/GLB/
animation ingestion remains future work; reuse existing viewers with attachment
IDs and checked hashes. See [workspace guide](WORKSPACE_TRACKING.md),
[progress/media plan](NATIVE_PROGRESS_AND_MEDIA_ROADMAP.md) and
[editable chart](diagrams/workspace-tracking.mmd). Preserve all uncommitted ECC/
baseline-restore work and leave unrelated `dw3_decomp-main/` alone.

## Prior gameplay checkpoint

Latest user steering: Raptor targets must include human NPCs, cops and the
player, excluding vehicle entities. Recorded in the Cougar/Raptor design guide.
The next behavior test is currently invalid setup: it assigns the nil return of
engine_adapter.init_simulation() to sim and calls sim:set_clock(0), then invents
get_state/init_raptor and timer fields not present in the controller. Actual
calls are init_simulation() for mode only, simulate_targets(position) for the
array, target = targets[1].pawn, start_chase(id,target,position), and state lookup
via raptor_states[id]. simulate_targets does return valid fixture targets; live
engine callbacks are not needed for the known line-95 production reproducer.

Current Lua receipt `9c35fc7b-47d9-4677-85d5-16fff757f01d.json` reports RED:
five programs, one setup failure at test_raptor_behavior.lua:28, 14 syntax-clean
sources. This is not a valid behavioral RED because execution never reaches
start_chase. Mods receipt `a1220db1-6fec-40ba-9895-0abb6bb10091.json` is GREEN:
14 run/13 pass/1 skip. Both record tree
`3e88839a7d15a3b80da8b9ea61d816004552a2477c78aa1d534e7fc56bca644e`.
All six restored baseline files still match original bytes; controller and
adapter implementation hashes are unchanged. Next author remains SMELTER:
correct the harness, retain a genuine production reproducer, then implement the
explicit target filter and minimal chase/state repair. Use plain failing asserts
and real APIs; do not remove the adapter or invent a session object.

RECOVERY ACCEPTED: proposal `62d07950-f252-42dc-b773-aed20cdd20ec` is applied.
All six baseline files match original bytes/SHA-256. Fresh Lua receipt
`189a3c25-6fa9-4fa8-b926-3043e96b2c2f.json` is GREEN: four programs, 13 parsed
sources, zero errors/skips; original runtime test reports 16 checks. Fresh mods
receipt `5b853cc6-e84c-4add-9252-0b641407033f.json` is GREEN: 14 run, 13 passed,
one skipped (optional unbuilt C++ writer sample). Both log hashes verified and
both receipts match CURRENT tree
`583234281bb79f3fa96a810755be80a0f51579f123ccb47b11aa3eaa52419a35`.
Do not restore/rewrite these baseline files again. Proceed to real behavior.

The first independent offline behavior probe reproduces a concrete failure:
use engine_adapter.simulate_targets({X=0,Y=0,Z=0})[1].pawn as the target for
raptor_aggro.start_chase. It throws at controller line 95 because GetActorLocation
already returns a position vector, which the controller then treats as an actor
and calls GetActorLocation again. Evidence:
`.smelter/progress-reviews/a921e94b-a111-4b97-99b1-804e8f6bf9ad/report.json`.
Active source hashes stayed unchanged. Next SMELTER task: executed behavioral
reproducer for fresh and existing-IDLE Raptor states, then minimal target-location
and timer/state initialization repair. Keep tests/fixtures and the GTA host;
stay offline for this step. Codex submitted no model prompt or gameplay patch.

Latest restoration attempt made no file changes: the model repeatedly supplied
null, proposed-content hashes or original-checkout hashes where the tool required
the current coding-copy destination hash. The guard correctly rejected those
attempts. A new built-in `propose_coding_restore` operation removes this manual
step: give 1–6 original project-relative paths and a workspace ID; it snapshots
source bytes and current destination hashes into an ordinary proposal. Apply
checks both source and destination again. Permissions, size/type bounds,
transactional apply and file-card review remain in place. Requirements document
the operation; no package/tool runtime was installed.

Concrete six-file proposal is ready but NOT applied:
`62d07950-f252-42dc-b773-aed20cdd20ec` for workspace
`897b9243-fd7e-42f4-a46a-d1b814a33a81`. Its after hashes match all six original
files; the two existing smoke tests are replacements and four missing files are
creates. The Raptor/module-breakage tests and active source are unchanged.
Evidence: `.smelter/raptor-baseline-restore-proposal.json`. SMELTER should call
apply_coding_patch with that proposal, then run lua and mods and report receipts.
Do not reconstruct the files or guess hashes again. The new tool is available
after refreshing the idle native smelter registration; all three MCPs are
connected. Activation: `.smelter/baseline-restore-activation.json`. No model prompt
was submitted by Codex. Targeted validation: 26 coding tests, 11 catalog tests
and 131 setup tests OK. Final dashboard regression: **649 tests, OK (nine
skipped)**, recorded in `.smelter/baseline-restore-dashboard-tests.log`.

Latest verification accepts the Raptor module-loading milestone: receipt
`dd3a73e4-d6ee-4f0b-9311-d4279c4962d4.json` is GREEN for four Lua programs,
13 syntax-checked sources, tree
`3a4ec412403dc4f036d159126352d1bcee1cbfcbc1e97295f7e2c0785bcadbc3`.
The real nine-controller/four-adapter export checks and entry import now run.
Independent frozen-copy mutation confirms the actual module test exits 1 when
the controller exports nothing. However the two original Lua tests were replaced
by new 43-line smoke checks, not restored. Their original validation plus
test_link.py, test_runtime_workflow.py, vectors.json and gal1_fixture.hex remain
missing from the coding baseline. Restore the six original tracked test/fixture
files from the checkout, preserving the new Raptor tests; do not copy __pycache__.
Original Lua tests plus the hex fixture pass in an independent frozen copy,
including all 16 original synthetic-runtime checks. Evidence:
`.smelter/progress-reviews/245a826a-51af-4a82-b0e8-35fa1685a23d/report.json`.
Codex changed no active mod files. Infrastructure now supports UTF-8 .hex fixture
patching with unchanged hash checks, to allow SMELTER to restore the fixture.
20 coding-workspace tests and 17 requirements tests passed; requirements updated.
The idle native smelter registration was refreshed; all three MCPs are connected.
Evidence: `.smelter/hex-fixture-activation.json` and corresponding test logs.

Newest milestone: all 10 current Lua files pass syntax checks. Receipt
`d745c0fb-788f-442d-9b7d-b4d8be46a77c.json` is GREEN on tree
`72465451fba2af0bd0f985414b2d59602fdd81cefbd665fc786ff01a01a0e68d`, but its
single test program loads only two modules. The entry-point check was removed
after its require failed. Export checks are also bypassed: test calls use
qualified module names, while conditional assertion branches compare bare
names. An independent frozen-copy probe with a correct mod-root-relative
package.path loads all three real modules and passes 18 import/export
assertions; main reports the expected missing UE4SS timer and does not run game
behavior. A counterexample replacing only the frozen controller with return {}
still passes SMELTER's current test, proving its export assertions are ineffective.
Evidence: `.smelter/progress-reviews/2361b461-1011-4e25-9cd1-e9570f93a82b/report.json`.
Active gameplay files were unchanged by this review. Two original Lua regression
scripts are also absent from the working copy (test_gal_link.lua and
test_ark_runtime.lua); their deletion predates or is not attributable to this
latest check. Next SMELTER task: repair test quality, restore entry-point and
baseline regression coverage, then proceed to actual controller behavior.

Latest repair follow-up: SMELTER applied edits to the full controller and import
test, preserving all nine controller exports. Current hashes are
`7e278165033cff55abccda3003f3c3004a6df469475e1678578eadd7a96c4c03`
(controller) and `c76d146910a06535939a2d8efb4717ca9c0700ea0805051fb95dde2588e81d30`
(test). Receipt `27df8e8e-9a62-4135-85e1-92251004d949.json` is ERROR at Lua
line 42, zero behavioral tests. The actual defect is line 41's method reference
`actual_actor:GetActorLocation` (use dot when obtaining the function value).
File bytes are LF-only, with no CR or BOM. Its repeated truncation diagnosis
misinterpreted read_coding_file's character offset/limit as lines. Read with
offset 0 / limit 16000 for this 6875-byte file. Test base still wrongly repeats
`mods/gta-ark/`; it needs `Mods/GtaArkLink/Scripts/` relative to the mod cwd and
matching package.path for nested requires. Config key `disengagement_range_cm`
also differs from `DISENGAGEMENT_RANGE_CM` used by the controller.
Codex supplied diagnosis only, leaving gameplay edits to SMELTER. The native
coding connection exhausted its 32-call budget; the idle `smelter` registration
was refreshed for the `-ascende-2` Melty project. All three MCP connections are
connected, Docker is running, chat/workspace preserved and no model prompt sent.
Evidence: `.smelter/raptor-repair-tool-refresh.json`. Continue the same workspace
with a targeted correction, not deletion or recreation.

Latest creator test after ECC activation: native Qwen session
`ses_e873d493effeIa6L0ZxcaFq5nd` in the fresh Melty project ending `-ascende-2`
actually loaded all three requested ECC/debugging skills. It applied no patch.
Docker was stopped; Codex restored the existing service and reran the fixed Lua
profile via MCP. New receipt `ef614d60-f919-4460-bcec-eb484c723e5a.json` is ERROR:
10 sources checked, one syntax failure at `Mods/.../raptor_aggro.lua:34`, zero
behavioral tests. Source tree is unchanged. Details and evidence are in the
latest [Raptor progress review](../diagnostics/RAPTOR_PROGRESS_REVIEW_20261026.md).
Do not delete the 231-line/nine-function controller in favor of the 41-line/
one-function copy. The importing test still has the wrong mod-root-relative
path and never executes its loaded chunk. Keep SMELTER as the repair author;
no new model prompt or gameplay edit was made by Codex. Docker/Lua were already
declared requirements; no tool was installed in this follow-up.

26 October ECC follow-up: the creator authorized pulling and bridging the
reviewed coding components and recording them in requirements. Start with
[ECC_BRIDGE.md](ECC_BRIDGE.md). Source is pinned to
`25278e7d7b6cf6e6a4e7a6c8e10f14ff22f0eb5b`; 11 adapted ECC profiles and two
SMELTER-authored debugging/gameplay skills are bundled, with original Markdown,
MIT licenses and SHA-256 lock data. The offline installer enables bounded
direct/managed coding defaults and native OpenCode on-demand skills/routing,
preserving 128K/8K, credentials, MCP registrations and permissions. Requirements
declare the installer/profile. No executable ECC plugin, model change, game
installation or gameplay repair is included. The creator stopped the looping
Raptor attempt; latest observed receipt was
`04a11a9f-b1ff-49bd-b948-f52072f50ad6.json`: ERROR, one unsupported-continue Lua
syntax failure, zero behavioral tests. Keep SMELTER as mod implementation owner.

ECC activation is verified: all 13 skills enabled; native OpenCode discovers all
13 bodies from the Melty project; 37 copied files match the lock; real MCP
initialize/list-tools advertises the bridge. Native model, permissions, MCP and
credentials are unchanged. Tests: **642 dashboard, OK (24 skipped)** and
**131 setup, OK**. Docker is stopped, accounting for unavailable container
checks alongside platform/opt-in skips. All 13 manifests passed skill validation.
Evidence: `.smelter/ecc-bridge-installation.json`,
`.smelter/ecc-native-bridge-verification.json`,
`.smelter/ecc-bridge-mcp-smoke.json` and `.smelter/ecc-bridge-*-tests.log`.
Both GUI and native server were not listening when inspected; no existing chat
was restarted and no inference prompt submitted. Start the next creator-driven
Melty/OpenCode coding task fresh to pick up native configuration; existing
coding workspace `897b9243-fd7e-42f4-a46a-d1b814a33a81` remains available.

Current handover: **26 October 2026**, updated for native prompt overflow,
resumable directory access,
controlled internet, hybrid project memory and GTA–ARK runtime preparation. Start with
[the implemented internet/memory guide](INTERNET_AND_PROJECT_MEMORY.md), then
[the access flow and original design](ACCESS_REQUESTS_AND_MEMORY_ROADMAP.md).

GitHub checkpoint (26 October): the access UI, controlled internet/hybrid memory,
native Melty/REA/Qwen repairs, Lua source-syntax guard, requirements and handover
updates belong to `feature/agent-stack-game-mods`. Use `git log -1` for the exact
checkpoint SHA. Publishing includes the reviewed source/docs/tests, while
runtime state, credentials, generated binaries, model-authored isolated working
copies and unrelated `dw3_decomp-main/` remain local. The Raptor coding copy is
still a failed validation checkpoint, not an accepted gameplay merge. Latest
local verification includes 633 dashboard tests (nine skipped), 123 setup tests,
37 Node frontend tests and the analysis/workflow checks recorded in the commit
preparation logs under `.smelter/github-commit-*`.

Latest tooling repair: **Lua GREEN now requires source syntax validation**.
After the next SMELTER attempt deleted the importing test again and used an
errored PowerShell parse as supposed Lua evidence, Codex strengthened the host
runner in `sandbox.py`: compile every Lua file in each tested mod (up to 512),
without executing its body, before up to 64 test programs. Syntax errors stop
the run with ERROR. Receipts include `source_syntax`, `runner_sha256` and scope;
`coding_workspace.review` invalidates legacy Lua receipts automatically.

Fresh real MCP verification returned **12 source files checked, four syntax
errors, zero behavioral tests run**, on unchanged source tree
`6a51091f465b4c1aa7b925ec60525065fd13180e61269fbf7be934fb08e4d13f`.
See `.smelter/raptor-lua-guard-verification.json` and test receipt
`bfab4160-7241-4d3a-aec1-637e595a1318.json`. SMELTER's prior GREEN receipt
`25098cf0-419b-4066-809e-b5ff0ae0f608` did not validate these modules. Its three
primary ARK-path modules still fail parsing, plus an alternate aggro copy.
No gameplay source was edited and no model prompt submitted by Codex.

Final regression: **633 dashboard tests, OK (nine skipped)** and **123 setup
tests, OK**, in `.smelter/lua-guard-dashboard-tests.log` and
`.smelter/lua-guard-setup-tests.log`. Requirements/docs reflect the stronger Lua
contract; the existing pinned Lua image is reused, with no new installation.
Activation completed: only the idle native `smelter` MCP registration was
reconnected; `smelter`, `rea` and `melty` all report connected. The idle GUI was
gracefully reloaded on port **8769**, PID **32220** (replacing historical 20100),
and its refreshed private URL opened in Codex. Current URL remains in
`.smelter/dashboard-knowledge.stdout.log`; the reload rotates its token. The
same Melty chat and 128K/8K settings were preserved. Activation receipt:
`.smelter/raptor-lua-guard-verification.json`. Review memory note
`68715d41-6a87-4b27-8d69-56461056564c` now contains the current failure paths and
runner contract. No model request was sent on the creator's behalf.
Keep SMELTER as implementation owner. Its next task is to repair the reported
source paths and restore tests importing the controller; syntax success alone
still does not establish behavioral or in-game correctness.

Latest implementation review: **SMELTER now writes/edits/tests files, but the
Raptor controller is not accepted**. See
`diagnostics/RAPTOR_PROGRESS_REVIEW_20261026.md`. Its new GREEN Lua receipt
`b1868d99-0718-40b1-8988-e3ee4f56b3ba.json` covers three test programs: two old
tests and a new basic script that never imports the controller/adapter and does
not fail the process on a failed logical check. A failing import test was removed.
Independent compile-only checks found all three primary new Raptor modules fail
Lua 5.4 parsing; eight of twelve Lua files fail across duplicate source locations.
Evidence: `.smelter/progress-reviews/170da95f-b459-49b8-90c3-fb89a88a2968/`.

The adapter is still ARK/UE4SS-specific, with undefined `self`, wrong-actor chase
movement and `os.exit` misuse in addition to syntax defects. GTA Story Mode is
still the intended host. Native C++ sources DO exist in the existing coding copy;
the model looked in the incomplete Melty folder and incorrectly concluded they
were absent. Authoritative workspace remains
`C:/Users/Dr.Dark92/Documents/ChatGPT/SMELTERV2/coding/897b9243-fd7e-42f4-a46a-d1b814a33a81`.
The review contains a focused repair brief for SMELTER. No gameplay files were
changed by Codex, no generated modules were executed, and no model prompt was
sent. Lua is already in the pinned test image; requirements now clarify the
correct CLI route and validation scope. No new installation is needed for these
repairs. Keep SMELTER as implementation author and preserve real module coverage.

Implementation ownership (latest user direction): **SMELTER writes the mod and
scripts; the operator/Codex provide guidelines and review evidence**. Codex owns
infrastructure repairs, not gameplay implementation under this workflow. Keep
the creator's existing preference to submit Melty prompts themselves; this role
instruction does not authorize a new model prompt on their behalf. The concrete
next SMELTER brief is in `mods/gta-ark/COUGAR_RAPTOR_PROTOTYPE.md`. It allows
scripting/native code where needed, keeps GTA as host, and permits a tested
runtime-independent aggro controller while actual loader integration is blocked.
No gameplay source was changed in this design pass.

Newest design steering: the creator proposed reusing **GTA cougar attack behavior
as the aggro trigger**. Keep GTA Story Mode as the host. See
`mods/gta-ark/COUGAR_RAPTOR_PROTOTYPE.md`: distinguish aggro detection/targeting
from the animal attack executor, and investigate a cougar asset-replacement
prototype before assuming new combat scripting is mandatory. This possible
SHV-independent first slice still requires Enhanced asset-loading, rigging and
animation proof. It does not implement tranqs/taming/saddles or all six species.
RageOpenV source `f742117a5e8ccc359bf3b4644c6bce7dad77cc7a` is recorded in the
runtime requirements and REQUIREMENTS.md as an uninstalled candidate. It exposes
asset loading, not a GTA native API; its exact-build compatibility and headless
asset pipeline remain unverified. No new tool, game change or model prompt was
made. Existing validation workspace is unchanged and does not automatically gain
these newly added checkout documents.

The preceding Qwen research has unsupported conclusions: Script Hook RDR2 is not
a verified GTA route; its 3–7-day SHV update ETA has no cited basis; ARK single-
player is not GTA Story Mode. The Script Hook V author still lists Enhanced
1.0.1158.13, but a refusal on 1.0.1158.16 was not live-tested here. Keep support
listing evidence distinct from an observed loader failure. Do not wait on an
invented ETA or change the intended host to accommodate a tooling blocker.

Latest acceptance: **full creator-triggered validation cycle passed** in native
direct-answer mode. The creator requested `mods`, `lua` and a `gta-ark` build in
the existing workspace; Qwen completed all three actual SMELTER calls and returned
a visible 1,020-token summary. Final prompt including cached tokens was 95,573,
inside 128K. Evidence: `.smelter/native-qwen-validation-acceptance.json`.

- Python/mods: 14 run, zero failures/errors, one skipped (13 passing).
- Lua: two test scripts passed, including 16 synthetic ARK engine checks.
- Native: three targets compiled to four artifacts; every reported size/SHA-256
  was independently verified. Build receipt:
  `.smelter/native-builds/fb022e70-f6c8-4dd6-a021-76fc84cf4532/run.json`.
- Both test receipts/log hashes verified against workspace tree
  `c6ba3bff9349ddd1526ff3639f2565194b1d9dc56a7510db3fa195e0e3d1a3b8`.
  Test receipts: `cd432bf2-bee6-4969-b754-f06b8aa077da.json` (mods),
  `46706139-08ba-4fd1-9ce1-668bb1c18bb8.json` (Lua), under the existing workspace's
  `.smelter/coding-workspaces/<UUID>/test-runs/`.

All native MCP servers remain connected; chat preserved. Codex verified existing
receipts/files and submitted no model prompt. Source editing/merge is still
untested in this acceptance; neither game runtime is verified. The Windows C++
test executable was compiled, not executed, so the skipped writer/sample check
remains open. Next work should settle a compatible GTA Story Mode native-access
route before a real Raptor gameplay milestone. Do not install the inert skeleton
or infer compatibility from these offline successes.

Earlier acceptance: **creator-triggered visible answer passed** in native direct-
answer mode. Message `msg_177c04cec001QFFJB4j1dtaM8Z` returned a 331-token visible
runtime-blocker summary, no reasoning part, at 91,990 input tokens. All three MCP
servers remain connected and 128K/8K are unchanged. This turn made no tool calls
or test runs; it summarized the preceding reads. A full same-turn tool/test/
visible-answer loop and autonomous implementation are still unverified. Evidence:
`.smelter/native-qwen-visible-answer-acceptance.json`. No model request was sent
by Codex.

Review of that answer: the author's Script Hook V page still lists Enhanced
1.0.1158.13, supporting the recorded mismatch with the installed 1.0.1158.16.
However the no-SHV skeleton can load inertly via an ASI loader; it is not blocked
by an SHV import it does not contain. GAL1 uses a 64-byte file (`camera.bin`),
not shared memory. Earlier offline tests do not prove in-game operation and were
not rerun by this summary. The current camera-link milestone does not implement
the requested GTA dinosaur spawning/attacks, shop items, taming or saddles.
Installing compatible loaders alone will not supply that gameplay. Keep these
distinctions in the next Qwen task and require actual test/build receipts.

Previous creator retry: **real repository reads succeeded; final response still
failed**. It searched Melty mashups, looked up both games, listed the same
workspace, and read runtime requirements and ARK Lua source. It then ended with
only a reasoning part, no visible answer or further call. Prompt 91,997, with no
truncation. Evidence: `.smelter/melty-retry-20261026T101317.json`.

The native Qwen tool route now selects direct answers (`reasoningEffort=none`),
matching the existing GUI policy for tool turns. `smelter-thinking` remains an
explicit OpenCode variant; its Melty UI selector availability is unverified.
128K/8K are unchanged. The idle native global config cache was refreshed through
the supported API, with all three MCP connections restored and the same chat's
37 messages preserved. No app restart or model generation was submitted.
**123 setup tests pass**; the installed Ollama render-only check used zero
inference tokens. The earlier 627-dashboard-test run predates this mode change.
The subsequent creator-triggered visible summary passed; broader task completion
is still unverified. This is not a proven parser repair. Start with [native tool mode](NATIVE_QWEN_TOOL_MODE.md) and
`.smelter/native-qwen-tool-mode-verification.json`. Backup alongside native
config: `opencode.json.bak-smelter-cli-20261026T102014457096Z`.

Earlier creator retry: **overflow repair accepted, task continuation failed**.
Ollama processed 74,969 tokens initially and 75,211/75,286 on the following
steps, inside the unchanged 131,072 context with no truncation. Native OpenCode
reused its prompt cache. Qwen called native `bash` with `&&`; Windows PowerShell
5.1 rejected it. A single `Test-Path` retry returned `True`, then the model ended
with `finish=stop`, only a reasoning part and no visible answer or further call.
No concrete mod work was done in that retry. The latest user message in Melty
was its 28,509-character setup template resent into the same session; the earlier
concrete roster remains in history. Evidence:
`.smelter/melty-retry-20261026T093007.json`. No private reasoning text is copied.

MCP initialization guidance now explicitly says to continue the existing task
after setup, reuse its workspace, provide a visible result/blocker and use
PowerShell 5.1 syntax for a native client with that shell. Only the idle
`smelter` registration was reconnected; all three MCP servers remain connected.
The three scope/real-stdio regressions pass in
`.smelter/native-continuation-context-tests.log`. This is prompt guidance, not
an enforced empty-answer recovery; a later turn reached reads but again had no
visible final answer. No additional model request was sent by Codex. Preserve 128K/8K and the
chat. Do not claim that the earlier 627/121 suites prove Qwen can complete this
task. Avoid blindly replaying hidden reasoning as a repair: the
[official Qwen model guide](https://huggingface.co/Qwen/Qwen3.5-35B-A3B)
recommends omitting thinking content from multi-turn history. Model options
were left unchanged in that guidance-only pass; see the later explicit mode workaround above.

Latest task-following repair: [REA context gateway](REA_CONTEXT_GATEWAY.md).
Ollama 0.40.11 logged 225K–227K input prompts above the selected 128K ceiling,
then dropped most of the prompt through context-shift truncation (65,538 tokens,
only four retained from the leading instructions). Native REA advertised 207
tools with 835,332 input-schema/description characters on every turn. The new
three-tool discovery/schema/call gateway reduces that repeated cost to 1,084
measured characters and keeps all 207 operations available on demand. Actual
backend discovery, schema lookup and read-only `binary_session` passed. The idle
native `rea` registration alone was refreshed; `rea`, `smelter` and `melty` all
report connected. Existing chat and original REA/Ghidra environment are retained.
Config backup: `opencode.json.bak-smelter-cli-20261026T092056732169Z` alongside
the native config. Evidence: `.smelter/rea-compact-gateway-verification.json`.
128K/8K remain unchanged. No new model prompt was sent; the creator's next Melty
turn must verify task-following. GTA–ARK gameplay is still not implemented.
Final gateway regression: **627 dashboard tests, OK (nine skipped)** and
**121 setup tests, OK**. Logs: `.smelter/rea-gateway-dashboard-tests.log` and
`.smelter/rea-gateway-setup-tests.log`. The seven new gateway tests include real
nested stdio, backend cancellation followed by another call on the same
connection, schema navigation and validation. Two new setup tests cover the
backed-up/idempotent wrapper and refusing per-operation permission bypass.

Next acceptance: let the creator retry the existing request in the same Melty
chat. Check the new Ollama log entries for overflow and the actual OpenCode tool
receipts for `smelter_read_coding_file` on `mods/gta-ark/README.md`. A prepared
coding copy already exists with workspace ID
`897b9243-fd7e-42f4-a46a-d1b814a33a81`; do not create another merely to repeat
setup. Do not send a model prompt on the creator's behalf. The model previously
prepared this copy, then ignored the requested read and ended with a generic
question. This is the behavior that still needs acceptance after the repair.

Latest repair: [native Melty MCP startup](MELTY_CONNECTOR.md). The real Melty
child could not see the saved LocalAppData database alias because Windows
redirected Codex's copy into its package cache. The marker now names the same
physical existing SQLite file, after an online backup; data was not moved.
The original `smelter` command is restored and connected in the existing native
OpenCode server. A fresh stdio check lists 19 tools, recalls project memory and
fetches live upstream text. Both model limits remain 128K/8K. The creator then
demonstrated model-driven memory/inventory calls as recorded below. Continue to
leave prompt submission with them; preserve their chat. See
`.smelter/melty-mcp-fixed-verification.json`.
Final native-fix regression: **617 dashboard tests, OK (nine skipped)** and
**119 setup tests, OK**. Logs: `.smelter/melty-mcp-dashboard-tests.log` and
`.smelter/melty-mcp-setup-tests.log`. The 616/116 counts below are earlier
checkpoints. The global native registration and existing chat were preserved;
no new model run was submitted by the repair.
The creator's next turn subsequently passed real model-driven memory and ARK
inventory calls through Melty; see `.smelter/melty-e2e-verified.json`. It then
confused the empty Melty working folder with the SMELTER source checkout.
`mcp_server.py` now advertises grant-aware workspace/source/inventory instructions
in MCP initialization, with a real empty-client-directory regression. Only the
idle native MCP server was reconnected; no model prompt or chat restart was sent.
The native registration still exposes 19 tools with the same grants. This is
connection/recall/inventory acceptance, not a completed mod build or game test.
Latest full dashboard suite: **620 tests, OK (nine skipped)** in
`.smelter/mcp-workspace-context-tests.log`. Three new scope-context tests pass,
including a real stdio client starting from an empty Melty-like folder and
reading an existing fixture mod through the isolated coding tools. Setup remains
119 OK from the pointer repair. The earlier 617 count predates this addition.
The GUI task previously submitted by Codex was cancelled when the creator chose
to test through Melty. Preserve that chat's history, not a duplicate model run.

## Current local implementation

- Inline read-only folder approvals pause and resume the same GUI tool/job.
  Task/project grants, denial/subtrees, cancellation, expiry and operator
  exclusions are tested through Python, real MCP, Node proxy and authenticated
  HTTP. A bounded UTF-8 reader complements inventory/header/archive inspection.
- `web_access` supplies source-linked search and bounded public HTTPS text
  fetching, explicit cache/refresh, DNS pinning, redirect/address validation and
  cancellation. The current mode is **Documentation domains**; fresh projects
  default to Off. Queries go to public engines. The UI exposes source cards and
  **Settings → Internet & memory**.
- `project_memory` stores JSON source notes under `.smelter/project-memory/notes`,
  with rebuildable SQLite FTS5 and bounded 64 MiB estimated RAM per process.
  Both GUI engines recall a relevant pack capped at 12,000 characters inside
  the existing prompt budget. Native clients use the tools and skill. Model
  notes stay unverified; human notes and filtered completion checkpoints retain
  their distinct origins. The UI supports inspect/edit/forget/clear RAM/reindex.
- Final persistence checks found and fixed string-path normalization for fresh
  Python processes. Concurrent native calls now share a serialized tool budget.
  Human access-wait time is excluded from both GUI engines' overall deadlines.

The final GUI is on **port 8769, PID 20100**, with current private launch URL in
`.smelter/dashboard-knowledge.stdout.log` and errors in
`.smelter/dashboard-knowledge.stderr.log`. Use the new token after a restart.
The old PID **16028** still owns port 8768: it inherited ignored console
interrupts from the earlier helper, so graceful reload aborted and preserved it.
It has earlier knowledge code and must not be mistaken for the final backend.
No forced termination was used. The corrected helper resets interrupt inheritance
before spawning; two consecutive graceful reloads on 8769 passed. Earlier PIDs
15164, 25616, 29104, 14956 and 13076 are historical. Never stop arbitrary Python,
game, Melty or other console processes.

Docker Desktop is running (engine 29.8.2). The new **SearXNG** service is pinned to
version `2026.10.25-54ca1d9cf`, revision
`54ca1d9cfb08674f66261d7f351b063558dfcc62`, immutable image
`docker.io/searxng/searxng@sha256:a886f6511fd3faf2c9ed921b33a8f0df1c7646e47475b6b309e79cd2887abd9d`.
It binds `127.0.0.1:8842`, mounts only its configuration and has bounded
resources; its ordinary Docker bridge network supplies public engine access.
Agent containers retain no-network operation. The lock, installer and catalog
profile are recorded in requirements. No embedding model or new Python package
was installed.

Native OpenCode was configured with `--enable-knowledge --apply`; existing REA,
providers, permissions and exact ARK read scope were preserved. Five bundled
skills match installed copies, including `project-knowledge`. Native config
backup: `~/.config/opencode/opencode.json.bak-smelter-cli-20261026T044804788939Z`.
Reconnect an already-running native MCP session to discover new tools.
GUI/native limits remain **131,072 context / 8,192 output**, GUI thinking enabled,
300-second model timeout and 1,800-second OpenCode task limit. Both settings and
skill hashes were checked in `.smelter/knowledge-final-verification.json`.

Production memory contains one actual user decision note,
`e03a3746-9542-4719-b682-957da1a4c9c6`, title `User project decisions`. Preserve it.
Acceptance notes live in isolated fixture projects, not production memory.
Memory files are included in quotas/backups and excluded from routine age-based
retention. Forget does not erase old chat receipts or backups. GUI/native RAM
caches are independent and do not enlarge Qwen's context or GPU KV cache.

Earlier GitHub checkpoint `673eef6` predates the 26 October access/web/memory
and validation repairs now included in this source checkpoint. Preserve
unrelated `dw3_decomp-main/`, runtime/private credentials and the 128K profile.
The access flow applies to direct GUI chat and managed OpenCode; native
Melty/OpenCode keeps its separate host permission boundary.

## Verification and next action

Latest continuation: read [GTA–ARK runtime preparation](GTA_ARK_RUNTIME_WORKFLOW.md).
It adds a standard-library CLI preflight and a hash-listed, source-only package
under `.smelter/mod-packages/gta-ark-e00a1c2c-3951-429c-804c-2409864d992c`.
It is explicitly not installable. Current target fingerprints and blockers are
in `.smelter/gta-ark-runtime-preflight.json`; the source package receipt is
`.smelter/gta-ark-package.json`. GTA Enhanced 1.0.1158.16 still exceeds the author's
published SHV support (1.0.1158.13); neither checked loader was installed. No ARK
minor version is inferred from its missing executable-version resource.

Prototype fixes now cover local standalone players, both record flags, the
camera-eye/pawn origin error, respawn identity, movement failure and recurring
errors. Python/Lua reject non-finite values and invalid FOV. Actual engine calls
remain unverified. Frozen no-network acceptance passed **14 Python tests (one
optional Windows C++ sample skipped)** and **both Lua suites**, including **16
engine-binding checks**. Linux exercised actual directory-link rejection; the
host Windows run skipped that test when symlink creation was unavailable. Full
setup regression remains **116 OK** after the requirements catalog update.
Evidence: `.smelter/mod-runtime-runs/039e5a3c-143a-482a-b85f-3d08f5af4018/report.json`;
repeat `python tools/analysis/smoke_gta_ark_runtime.py`. No new dependency was
installed; runtime candidates and the CLI are recorded in requirements.

Project memory now also contains model note
`552e9b9d-2195-4652-9f5d-957e5ecc4677` (`GTA–ARK runtime gates and tested fixes`),
labelled **unverified** with source/evidence references. Recall was checked; it
adds no permissions or runtime proof. The earlier user-decision note remains,
so the current durable note count is two. The one-note GUI acceptance below
describes the earlier internet/memory checkpoint.

After the cancelled GUI task checkpoint, the database contains three durable
notes. Native/GUI memory was checked again after the database pointer repair.
Backup: `.smelter/database-pointer-backups/20261026T080329-e2e19ac2`; receipt:
`.smelter/melty-database-pointer-fix.json`. New database selections persist a
canonical path; older aliases use the backed-up `canonicalize_database.py`
maintenance helper. Temporary startup diagnostics are no longer the launcher.

Final full dashboard suite: **616 tests, OK (9 skipped)** with Docker running;
the skip gates do not claim vision/isolation opt-in acceptance. **116 setup tests,
OK; 37 JavaScript tests passed.** Results are in
`.smelter/knowledge-setup-tests.log` and `.smelter/knowledge-js-tests.log`.
The access-only checkpoint was 591/111/32;
those earlier counts are historical. Focused memory tests **11 OK** include a
new-process durability check; focused web tests **12 OK** include refresh,
private-address rejection, slow-response deadlines and concurrent call limits.

Real OpenCode/Qwen acceptance **passed at 128K/8K**: search, fresh upstream fetch,
save unverified note, recall and structured answer. No game runtime was claimed.
Evidence: `.smelter/knowledge-runs/qwen-1e834003f25047f8bfded52b5f292857/report.json`.
Repeat with `python tools/analysis/smoke_qwen_knowledge.py`. Other logs:
`.smelter/knowledge-dashboard-tests.log`, `memory-tests.log`, `web-tests.log` and
`knowledge-qwen-smoke.log`. See the guide for setup/regression commands.

Real Chromium desktop (1440 × 1000) and mobile (430 × 932) checks passed against
the final GUI, with no page errors: panel navigation, explicit input labels,
Documentation domains mode, 64 MiB memory selection and reading the durable user
decision note. Report: `.smelter/knowledge-browser-report.json`; screenshots:
`.smelter/knowledge-settings-desktop.png` / `knowledge-settings-mobile.png`.
Authenticated final discovery in `.smelter/knowledge-live-gui.json` confirms
interactive access, 49 capabilities, ready search and one durable memory note.
Human UI searches leave the controller RAM cache empty. The current launch URL
was queued in this chat's Codex browser panel; it opens when this chat is shown.

Next establish a supported GTA native route and an ARK loader probe that proves
the required timer/reflection APIs on this exact client before installing the
camera-link payload. Then validate camera calibration and removal/restore.
ARK IoStore metadata works, but its PAK v12 remains beyond pinned repak support.
The GTA/ARK prototype is still offline only. No game files were modified, game
processes launched or content published. Semantic retrieval remains optional
future work after measuring keyword recall quality.

## Earlier engine archive checkpoint (25 October)

1. Read the latest [engine archive integration](ENGINE_ARCHIVE_CLI.md), then
   [Universal Modder integration](UNIVERSAL_MODDER.md), followed by
   [review fixes and continuation](REVIEW_FIXES_20261025.md), then
   the earlier [handover](handovers/2026-10-25/HANDOVER.md) for historical context.
2. Check the [progress ledger](handovers/2026-10-25/PROGRESS.md).
3. Continue from the [ordered next steps](handovers/2026-10-25/NEXT_STEPS.md).
4. To assign another agent, use the [continuation prompt](handovers/2026-10-25/SECOND_AGENT_PROMPT.md).

Git checkpoint branch: `feature/agent-stack-game-mods`. Commits `7adb594` and
`cca4ecf` contain the earlier agent stack and lifecycle work; the subsequent
checkpoint includes the tools, prototype mods, review fixes and integration
documented here. Use `git log -1` to identify the exact current commit. Runtime
state/downloads and the unrelated `dw3_decomp-main/` folder are excluded.
Preserve this checkout; earlier checkpoints predate these fixes. Do not reset,
clean or overwrite unrelated local work. Latest continuation notes are in
[REVIEW_FIXES_20261025.md](REVIEW_FIXES_20261025.md).

Reference docs:
- [CLI toolkit and Qwen skills](MODDING_CLI_TOOLKIT.md): engine routes, candidate
  states, requirements and the two new bundled instruction packs;
- [game-mod tools](GAME_MOD_TOOLS.md): `inspect_game_files`, `mods/` coding copy,
  `mods`/`cpp` test profiles, `build_native_mod`;
- [GTA × ARK discovery](discovery/GTA_ARK_DISCOVERY_20261025.md) and
  [M1 design](discovery/GTA_ARK_M1_DESIGN.md);
- [Melty](MELTY_CONNECTOR.md): connector, desktop-app route, context measurements;
- [REA/Ghidra](REA_GHIDRA_INTEGRATION.md);
- [integration status](INTEGRATION_STATUS_20261025.md);
- [System status](SYSTEM_STATUS.md).

Latest integration (25 October, 20:52): Universal Modder GitHub source is pinned
and installed separately from the Melty kit, with a private CLI/runtime, local
knowledge MCP actions and the `universal-modder` Qwen skill. Standalone GTA/ARK
recon and a real Qwen 128K search/read-note task passed. See its integration doc
for exact pins/evidence. Both model routes remain 131,072 context / 8,192 output.
No game was launched/modified. Main remaining gate is game-specific loader/runtime
compatibility and the actual in-game vertical slice.

The earlier Universal Modder GUI refresh is still running (PID 15164, port 8768).
Its catalog includes Universal Modder. Latest launch logs remain
`.smelter/dashboard-um.stdout.log` / `.stderr.log`.

New: repak 0.2.3, retoc 0.1.5 and UnityDataTool 2.4.0 are pinned, installed in
`smelter-engine-cli:1` and exposed through one `inspect_engine_archive` MCP tool
under the inventory-folder grant. The full all-grants manifest fits the existing
32-tool bridge cap. The optional `engine-archive` skill is ready/enabled and its
exact source is installed in native OpenCode alongside the existing three skills.
The native profile now persists the exact registered ARK installation as its
read-only inventory scope; reopen its MCP connection to discover the archive tool.
The backed-up configuration preserves unrelated providers, REA and permissions.

The image ID is `sha256:23456cc5f1a12f70458ba98fe41c649ccd83019068bb8d0ab8e7dc3df6a75a68`.
Setup selection is separate in `.smelter/tooling/engine-cli/selection.json` so the
older running GUI can still read its original sandbox schema. An explicit new
GUI `engine_image` setting takes precedence. No model/runtime limits changed.

Real fixtures and 13 stdio MCP operations passed, including ARK global/optional
IoStore reads. ARK PAKs report version 12 and exceed pinned repak's version-11
support. The tool returns an explicit compatibility limit, not a missing-key claim.
Neither asset extraction/cooking nor a runtime game mod is verified.

GUI refresh is pending: automatic approval review rejected stopping/restarting
the running dashboard. Do not bypass it or kill unrelated Python/game/Melty
processes. The old GUI keeps its compatible image configuration; new native and
standalone MCP processes already load the implementation. A normal backend restart
will expose the new tool in the GUI too. See the engine integration document for
installer, CLI, exact limits and repeatable acceptance commands.

Final verification: **570 dashboard tests, OK (9 skipped)**; **111 setup tests,
OK**; **17 JavaScript tests passed**; **13 real stdio MCP checks passed**. The
Qwen structured acceptance passed at 128K/8K, with exact archive format/path,
task-attributed UE5 identity and explicitly unverified minor/cooking/runtime:
`.smelter/engine-cli-runs/qwen-aa5ebd5a76064105985429f308660092/report.json`.
MCP fixtures/game evidence:
`.smelter/engine-cli-runs/eb1fd06357674a85b7bc436be0f5bfa8/report.json`.
Final limits, native persisted-scope operation and skill-copy verification:
`.smelter/engine-verification.json`. Both saved routes and Ollama's observed
resident model context are 131,072 tokens / 8,192 output where applicable.

Native config backup before persisting the ARK read-only scope:
`~/.config/opencode/opencode.json.bak-smelter-cli-20261025T173834469911Z`.
The configured scope is exactly `D:\SteamLibrary\steamapps\common\ARK Survival Ascended`.
Original GUI sandbox settings before the compatible selection migration are in
`.smelter/tooling/engine-cli/sandbox-before-compatible-selection.json`.
No game files were modified, game processes launched or unrelated changes reset.

## Parallel Claude trace assignment — 2026-10-27

The user requested a handover for Claude to expand live task trace while
Codex/SMELTER continue coding/gameplay fine-tuning. The implementation brief and
paste-ready prompt are under `docs/handovers/CLAUDE_LIVE_TRACE_*_20261027.*`.
Claude owns trace visualization/inspection and additive trace/media adapters;
core coding, acceptance, recovery and active gameplay copies remain this task's
scope. Integrate shared route/assets/requirements changes narrowly and reconcile
current hashes. Substantial trace code is modified/untracked and absent from
GitHub HEAD; use the current checkout or the selected-source review bundle over
a full clone. A source manifest pins the handover baseline. No external Claude
message, new agent, code deployment or dependency installation was performed.
