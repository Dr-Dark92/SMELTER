# Resume checkpoint — 28 October 2026

The user resumed work after a PC reboot, requested SMELTER startup and then
authorized coding while AFK without waiting for confirmation. No commit/push
requested. Branch `feature/agent-stack-game-mods`, HEAD `876352f`.
Never stage or change unrelated `dw3_decomp-main/`.

## Preserved state

The earlier pause archive and reviewed main controller/test remain intact; read
[the pause checkpoint](CODEX_PAUSE_CHECKPOINT_20261028.md) for their hashes and
offline evidence. The old adapter/profile/test draft was not promoted.
The existing Codex-side database and seven configured locations were preserved;
no access grant was added. Model remains Qwen3.5 35B-A3B, 131072 context and
8192 maximum output. All evidence remains offline.

## New operator work

- `provider-admission-v1`: 26 frozen checks in
  `tools/dashboard/acceptance/provider_admission_v1.lua`, registered for the
  coding-copy `mods/gta-ark/Mods/GtaArkLink/Scripts/engine_adapter.lua`.
- Pure structural admission, direct read/command results and arguments,
  explicit simulation/provider modes, no implicit runtime or spawn success.
  `init_real_game` is a legacy name for admitting configured functions; it is
  not proof that native game calls work.
- Disposable reference GREEN; eight mutants RED (wrapped position/candidates,
  swallowed refusal, scalar panic, wrong missing-capability reason, implicit
  simulation, unconditional real-provider refusal and fake spawn).
- Focused acceptance/scaffold tests: 20 OK. Requirements catalog: 24 OK.
  Logs: `.smelter/codex-provider-{contract,requirements}-tests-20261028.log`.
  Proof: `diagnostics/PROVIDER_ADMISSION_PROOF_20261028.json`.
  Full dashboard suite: **798 OK (9 skipped)**, log
  `.smelter/codex-provider-dashboard-tests-20261028.log`.
- Both requirement files and frozen-acceptance/adapter docs updated. No package
  installed. Registry now has policy 30, controller 52, provider 26 checks.
- Exact previous draft baseline: provider 5/26; policy 30/30 and controller
  52/52. Tree `b6233f0219d2b100403ebe3c6b5c4909b0bcb4ad6d5a73665e5ed359d3295156`.

## Services and active repair

Dashboard was restarted and gracefully refreshed after tool changes. Current
private URL is in `.smelter/dashboard-knowledge.stdout.log`; never commit it.
Docker 29.8.2 and Ollama were checked. Melty's existing conversation was opened;
a read-only reconnect prompt initialized its ACP backend and was cancelled once
the exact backend was verified, before the bounded repair. The idle instance
was disposed through its documented API to reload MCP; conversations preserved.

ACP PID at dispatch: 9484, port 4096, owned by Melty. Watchdog PID at dispatch:
30588. PIDs are historical: rediscover exact process identity after any restart.
The observer is bound to fresh root native session
`ses_e7de90adaffe1TITQty7BPZXTq`, directory
`C:\Users\Dr.Dark92\Melty\grand-theft-auto-v-enhanced-ark-survival-ascende-2`,
coding UUID `897b9243-fd7e-42f4-a46a-d1b814a33a81`. This is a root session in
Melty's OpenCode backend, not a new Melty UI conversation or delegated agent.
Watch `5fcc934e37664de9b1e891a5810439d4` captured the task with zero retries.

Task permits only eight SMELTER read/list/context/recovery/propose/apply/test/
finish tools; other native tools and restores are disabled for this task.
Qwen must repair only `engine_adapter.lua`, run Lua and mods, and explicitly
finish with actual outcome. The known broken editable adapter test/profile is
intentionally a separate next task, so an overall RED/ERROR is expected until
those are corrected. Provider acceptance counts must be reported separately.
Private dispatch: `.smelter/codex-provider-task-20261028.json`; never commit it.

## Continue in order

1. Wait for the bounded adapter task; inspect actual code and current test
   receipts. Preserve the verified controller and real-policy test.
2. Fix the editable adapter tests and canonical profile import/location through
   Qwen. Require exact capability reasons and real refusal/argument assertions.
3. Wire a passive generic entry module with explicit injected dependencies,
   registered string actor IDs and honest stop/error handling. Test before
   promotion. Prepared brief: `.smelter/codex-entry-task-prompt-20261028.txt`.
4. Promote only reviewed bytes with fresh exact-tree Lua/mods evidence.
5. Update this checkpoint and top of CURRENT_HANDOVER. Runtime gates remain
   blocked until verified; no in-game claim, game writes or version-check patch.

## Adapter repair review checkpoint

Qwen corrected the adapter through proposals. All 26 provider checks now pass;
controller 52 and policy 30 remain GREEN. Coding tree at that point:
`da652e002c88c63516cc5d4c97b12e3ca52e9a223d6b6a5d91238b923cb82f93`.
The editable Lua adapter test still has a runtime ERROR; mods passes 14 with
one optional C++ writer skip. Qwen attempted a GREEN finish despite that ERROR;
the finish tool correctly rejected it. The operator stopped the adapter-only
session at the review boundary instead of accepting false GREEN or permitting
repeated finish calls. No adapter task end flag is claimed. Fresh session
`ses_e7de2a260ffe3quq2Am3cyZkcQ` is now working on adapter tests and the canonical
profile path, with the same coding UUID, permissions and model limits.
No main-tree promotion yet. Initial observer rebind returned HTTP 400 during
shutdown; a fresh-state retry after confirming stopped succeeded. No history
was deleted or reset.

## Test fixture correction boundary

The first editable-test task created the canonical profile with unchanged SHA
`ac49c9fdbda545271eb05547704f3002593c6eebe7028f70a33c1f52075fe1f0`.
Its long test rewrite was rejected in review: wrong return-value assumptions,
uncalled spies, invented Adapter.require and permissive assertions. A syntax
proposal was rejected before application; later a proposal used string changes
instead of an array and was rejected without writes. The production adapter
remained unchanged and all 108 frozen checks stayed GREEN. The operator stopped
that bounded attempt after the failed repairs; no GREEN finish or promotion.
A fresh compact test-only task is being dispatched using smelter-tools (same
Qwen model and 131072/8192 limits), with a one-line read of the old test only for
its hash to avoid feeding the broken fixture back as an example. The original
misplaced profile remains until reviewed canonical copy and idle cleanup.

## Latest backend continuation (after interruption)

The user assigned Claude to improve the workbench interface, and explicitly
asked Codex to use the backend while they use the PC. Do not control desktop UI
or overwrite Claude's interface changes. No Codex thread/message was created or
sent to Claude. Continue backend/gameplay tooling only.

The repeated editable test rewrites were stopped: malformed Lua, invented APIs
and schema-invalid calls were rejected. New operator-only
`tools/setup/scaffold_acceptance_test.py` with
`tools/dashboard/contract_test_scaffold.py` generates a normal reviewable proposal
from a registered pinned contract. No automatic apply/registration/access grant.
Its four tests include exact scoping/hashes and a real reference/mutant run.
The generated editable test is contract-derived, NOT independent integration or
native evidence. Requirements and documentation declare the tool; no package
was installed.

Qwen applied adapter-test proposal `2e0ffa51-91aa-4730-9f68-8ab47495eff9`;
Lua/mods GREEN on tree
`34c7ed163d7ce8af3b320265598ac29e11dd01cb5ad72b8e1f634177b355cb12`.
Explicit GREEN watch `fac32ea61e554d749b019036fc4b886a`, zero retries, flag receipt
`9bd4dea0-a280-4ee2-ae89-dbaf44450461`. Provider SHA
`829b87ebc7d6e2d8af1eb67ae60679b01f1dde22ff345a13a11ea02d883bb756`.
Canonical profile SHA remains `ac49c9fd…`. The unused misplaced copy was
checkpointed and archived in `.smelter/checkpoints/profile-relocation-20261028/`,
then removed from the coding copy only after identical bytes were verified.

Fourth registered contract `predator-system-v1`: 20 lifecycle checks. Reference
passes; false removal, stale cooldown, policy bypass and hidden fallback mutants
fail. Logs `.smelter/codex-predator-system-contract-tests-20261028.log`.
Generated editable system-test proposal `9396996d-9d7b-4b12-a9af-c7065bf194a0`
is prepared (not assumed applied). All four contracts total 128 checks.

Final infrastructure suite after these tool changes: **804 OK, 9 skipped**,
`.smelter/codex-final-infrastructure-tests-20261028.log`. Requirements catalog:
24 OK, `.smelter/codex-final-requirements-tests-20261028.log`.

Services were off after the interruption and were restarted without desktop UI
control. Current dashboard PID at restart 42340/8769, watchdog 32248. Installed
OpenCode 1.19.3 runs headless ACP PID 45972/4096 with the same configuration,
directory and persistent session database. It is now operator-owned headless
ACP, not Melty's child process. The private host helper holds its stdin open;
`.smelter/codex-headless-acp.json` records the owner PIDs. Rediscover identities
before stopping anything. Dashboard URL rotates; read the private launch log.

Current entry task session `ses_e7d50e307ffeL2CPee09LkaRtg`, watch
`3d76d06f3dde4772bdbe8c563d7a01ba`. Same coding UUID and directory as before,
8 scoped tools, Qwen thinking variant, 131072/8192 limits. It must apply the
prepared system test and write ONLY passive raptor_system_main.lua, then run
Lua/mods and finish with actual proof. Dispatch is in private
`.smelter/codex-entry-module-task-20261028.json`. Do not claim success or promote
until those receipts and a source review pass. Main remains unchanged by this
adapter/entry continuation. No commit/push requested.

## Structured lifecycle scaffold and small edits

The first full entry rewrite was rejected: out-of-scope factory, module-global
actor state, incorrect controller self/stop calls. It was not promoted. The
existing generic subject scaffold now supports operator-declared imports and a
bounded constructor setup. It provides the actual Adapter/Predator/Policy
factory and per-instance state, leaving three colon methods TODO. Scaffold
9/20; completing only those methods in a disposable reference passes 20/20.
Four regression mutants still reject. Focused scaffold/contract tests: 14 OK.
Requirement files/docs declare this extension; no package installed.

The operator applied subject scaffold proposal
`083fb345-d980-4041-830e-b89cc691c1c1`, preserving the rejected draft through
normal workspace checkpoints. Qwen implemented add_actor using the existing
five-string propose_coding_edit tool. This avoided the wrong-array/whole-file
rewrite errors. Reviewed method validates IDs/duplicates and creates a fresh
real controller per registration. Bounded add_actor slice explicitly ended
RED (other two methods intentionally TODO), watch
`7e141e73b39445b494a5cf3ba3b33ed3`, receipt
`dcb9507e-36b1-4500-a879-3a88228f5c75`, zero retries. Lifecycle 10/20, other 108
checks GREEN, mods 14 GREEN, tree
`e4d3ff7600b428e6b789d6a39a3659a7ec8470527fb0a9b4475d046b0f8cbb0f`.
This partial RED is not whole-task completion.

Current continuation is ONLY remove_actor and tick with separate scalar edits
and fresh hashes. Session `ses_e7d430cdaffeCgIDw5rKTWmCLx`; dispatch record
`.smelter/codex-lifecycle-complete-task-20261028.json`. It was created while the
observer was still stopping; no prompt was sent on that timeout. The same exact
pending session was reconciled/bound, then submitted once. No duplicate session
or prompt. Helper shutdown wait increased to 25 seconds. No trace archives were
deleted. The user-facing dashboard was gracefully refreshed after tool changes;
its previous URL expired. Current private URL is only in the launch log.
Dashboard PID 56536, watchdog 23096, headless ACP 45972 (rediscover before use).
Full infrastructure rerun is in `.smelter/codex-lifecycle-final-dashboard-tests-20261028.log`;
do not claim its result before completion. No main promotion yet.

## FINAL: offline milestone promoted and verified

The remaining two methods were implemented by Qwen with scalar proposals.
All 128 frozen checks passed. The bounded lifecycle task explicitly finished
GREEN, watch `ff95242610374ebd83f91df77ed3deb8`, one watchdog retry, receipt
`016c9a90-7c48-458a-be7e-2a1c3953b76a`. Review then found an uncovered error
edge: a table-valued stop refusal broke concatenation, and thrown stop details
were dropped. An operator-owned disposable probe reproduced this as ERROR,
with clean syntax and exact bytes, in the intended probe program only.

A retained `tests/test_failure_reasons.lua` regression was added through a
normal reviewed proposal. Qwen fixed only the error-reporting expressions via
scalar edits: tostring(why) for refused stops, tostring(value) for thrown stop
and controller errors. Final task `ses_e7d3c24bbffeWnzrXO1kY5SFRg` explicitly
finished GREEN, watch `0bc75ea8f2094427a1fcc640b1bbf118`, **zero retries**, receipt
`4bc813be-893c-4eea-93c2-de81dfc5862d`. Coding tree:
`bdea47102e69d0246c9efde09cbdb39f1df1f2c9871603104cfd7b13daf60619`.
After-probe GREEN. Source hashes and exact tested receipts are in
`diagnostics/PASSIVE_SYSTEM_PROMOTION_20261028.json`.

Six reviewed files were promoted: provider, passive entry, canonical game
profile, generated provider/system conformance tests, and the independent
failure-reason regression. Constructor/test scaffolds are operator-provided;
Qwen authored the provider and lifecycle behavior via SMELTER. Main validation:
**Lua 10/10, mods 14/14 (no skips), frozen 128/128**, all GREEN. Lua snapshot
bytes match. Disposable baseline passes; swallowed-stop and false-removal
mutants make their intended programs exit 1. Their harness stage is ERROR
because the custom-assert probe is classified as runtime error; do not call
those RED receipts or a production failure. Proof:
`diagnostics/PASSIVE_SYSTEM_TEST_PROOF_20261028.json`.

Final infrastructure: **805 OK (9 skipped)**, requirements catalog **24 OK**.
Logs `.smelter/codex-lifecycle-final-dashboard-tests-20261028.log`,
`.smelter/codex-final-requirements-tests-20261028.log`, and
`.smelter/codex-passive-main-{lua,mods,frozen}-20261028.{json,log}`.
No UI validation claim is made for Claude's concurrent interface edits.
No package/game loader was installed. No game launched or game files written.
The runtime provider/Lua host/loader gates remain unverified; this is not a
playable-game claim. Next clear those gates with exact-build/runtime evidence,
then implement a real game-thread provider/bootstrap. Do not invent success.

The native task is idle and watchdog terminal GREEN. No future inference is
scheduled. Backend service owner information remains in the private headless
ACP file; the current private dashboard link is in its launch log. Do not
restart or take focus in the user's desktop apps. If Melty later needs port
4096, first verify the headless ACP is idle and stop only the recorded owned
backend before allowing Melty to start its own ACP; then rediscover/rebind.
There are now ten retained trace binding archives. Before another binding,
preserve/review the older archives as required by native_progress; do not
silently delete history or raise the bound. Current charts remain available.

Claude's changed workbench JS/tests and TRACE_WORKBENCH.md were left untouched.
No staging/commit/push. Never stage/archive `dw3_decomp-main/`. Verified backend
checkpoint pointer: `.smelter/checkpoints/latest-backend-complete.json` (includes
archive SHA and manifest). The archive excludes Claude's interface files,
credentials, captured prompts and unrelated sources. Existing Git history is
still required; do not blindly apply a working-tree patch over concurrent work.
