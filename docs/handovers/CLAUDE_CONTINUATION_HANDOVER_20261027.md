# SMELTER continuation handover for Claude — 2026-10-28

## Start here

Repository: `https://github.com/Dr-Dark92/SMELTER`

Branch: `feature/agent-stack-game-mods`. The checkpoint is the commit containing
this handover. Continue from this branch and inspect current Git/runtime state
before assuming any PID, hash, proposal or test receipt is still current.

Local checkout: `C:\Users\Dr.Dark92\Documents\ChatGPT\SMELTER`.
Shell: PowerShell. User timezone: Asia/Muscat.

User requested a GitHub checkpoint and this handover before the conversation
limit. They have authorized implementation, fixes and tests without repeated
confirmation. Modding should run through SMELTER/Qwen; the outside agent provides
controller fixes, diagnosis and concrete guidance. Do not restart ended work
just because its previous model summary says more remains.

## User decisions to preserve

- SMELTER is a universal platform, not a GTA/ARK-specific application. Those
  mods are a regression fixture. Put reusable logic in generic contracts/tools;
  game-specific behavior belongs in adapters.
- Target chain: Melty → OpenCode → Ollama → Qwen3.5 35B-A3B, with MCP tools,
  REA/Ghidra, coding/debugging skills and ECC bridge.
- Keep the chosen 131072 context / 8192 output profile. Do not raise the ceiling.
- Tools should be CLI/MCP usable by the AI. Declare every added tool/dependency
  in requirements and update documentation. No new package is needed now.
- Directory access should wait inline for an explicit grant and resume the same
  task, preserving completed work. Never auto-grant access.
- The predator fixture targets human NPCs, police and players, excluding vehicles.
  Eligibility uses normalized kinds and traits, not names or game-specific IDs.
- Preserve meaningful tests and frozen acceptance. A successful compile, model
  summary or editable GREEN alone does not prove acceptance or in-game behavior.
- Do not commit unrelated `dw3_decomp-main/`; it is pre-existing untracked work.

## What is implemented in this checkpoint

### Coding and verification

- Host coding copies are edited through hash-checked proposals/apply/checkpoints.
  Each Docker test receives a fresh read-only source snapshot, not image-cached
  project code. Lua receipts include observed/expected hashes and actual imports.
- `propose_coding_edit` offers five flat strings for one exact replacement:
  `workspace_id`, `relative_path`, `expected_sha256`, `old_text`, `new_text`.
  It uses the same checked engine as the batch tool. Batch edits require unique
  file entries and actual arrays, not JSON-encoded array strings.
- Stdio validates the same published schemas inside ToolSession, before any
  operation. Malformed calls are budgeted, guarded and audited; compact
  `input_contract_error` responses do not echo rejected code. The SDK's old
  pre-handler validation bypassed these controls.
- `coding_recovery_context` supplies canonical paths/hashes, checkpoints and
  actual first-failure evidence. Exact-edit matching handles LF/CRLF safely.
- Protected acceptance lives outside the editable copy. Operator registration
  is not a model tool. Overall GREEN requires editable tests and frozen checks.

### Watchdog

- Separate hidden service, private scoped capture hook and durable SQLite retry
  journal. It preserves the original session, workspace, model/agent/variant and
  request constraints. Retries resume checkpoints rather than replay writes.
- At most three continuations after the original attempt. Restarts, compaction
  and watchdog messages do not reset the count. Stop/new human input override.
- Completion requires explicit `finish_coding_task` plus current matching
  receipts, tree, hashes and frozen acceptance. Ordinary TDD RED is not an end.
- Active work, child work, native provider retries, access/questions, unknown
  side-effect domains and uncertain delivery do not admit another turn.
- Three protocol errors among twelve recent tool calls hold recovery. Three
  comparable frozen RED results without improvement also hold. Holds do not
  spend retries, fabricate GREEN/RED, or add terminal rules.
- The earlier runaway watch was stopped at 3/3 and remains cancelled. Two later
  human-created focused tasks finished explicitly RED with zero retries each.
  Do not replay those ended tasks.

Commands: `python tools/setup/manage_task_watchdog.py status` / `start` /
`disable`. `install` enables/registers the capture hook; `activate` refreshes
only an idle exact native instance without a new model turn. Operator `resume`
is solely for the legacy receipt-as-end RED bug, not explicit finish or Stop.

### Trace/workbench (Claude's contribution included)

- Authenticated read-only WebSocket task trace and full-screen relationship
  graph, inspector, waits/timeline/files/outcome tabs and exports.
- Persisted task charts and hash/access-checked image/GLB artifacts through
  opaque IDs. Existing model/animation viewer is reused.
- Evidence classes distinguish observed activity, configuration and inference.
  Response ending is separate from task success; observer/socket/native clocks
  are separate. A quiet model is not proof of deadlock.
- Graphify was evaluated but is not installed. It is an optional offline
  enrichment direction, not a replacement for live lifecycle telemetry.
- Melty's exposed MCP interface did not provide a verified coding-task ID.
  Show actual native IDs; never invent Melty correlation or hidden reasoning.

See `docs/TRACE_WORKBENCH.md`, `docs/WATCHDOG.md`,
`docs/RECOVERY_GUARDRAILS.md`, `docs/FROZEN_ACCEPTANCE.md` and
`docs/handovers/CLAUDE_TRACE_WORKBENCH_REPORT_20261027.md`.

## Current saved result: verified correction applied through SMELTER

Workspace: `897b9243-fd7e-42f4-a46a-d1b814a33a81`.
Physical copy:
`C:\Users\Dr.Dark92\Documents\ChatGPT\SMELTERV2\coding\897b9243-fd7e-42f4-a46a-d1b814a33a81`.

Melty applied proposal `b4eb565f-cd2a-4bb3-ae53-d648a37f1c50` while this
GitHub checkpoint was being prepared. **It is already applied. Do not apply or
recreate it again.** The main production `mods/` directory has not been merged
from that coding copy; this commit preserves the copy in a handover archive.

Current exact coding-copy tree:
`eaff3fa39d33b07d7b7a00f6de754802140c422ec6c892b9411275d04555f79c`.

| Saved check | Receipt | Result |
| --- | --- | --- |
| Lua | `6ee4b5e8-2a0a-49d9-8b6e-d53708e42f36` | GREEN, 6 programs, 0 failures/errors |
| Frozen acceptance, within Lua | same receipt | GREEN, 30/30, verifier unchanged |
| Python mods | `f85b25de-e3b4-40a2-ae42-9b03fdb7e58e` | GREEN, 14 tests, 0 failures/errors, 1 skipped |

Both receipts were checked against this same current saved tree. The Python
skip requires the optional C++ writer build. These results are offline; they
are not proof of host-game loader compatibility or playable behavior.

Current subject `mods/gta-ark/Mods/GtaArkLink/Scripts/entity_policy.lua` SHA:
`2a0f65002b562b409abce2ac698563fab6f1bbc9fd81a087bd2696be417ad1c7`.
Current editable `mods/gta-ark/tests/test_entity_policy.lua` SHA:
`9ab4733cdf8b2f0603b1e474209efecccc7b05be39c4696f19c6258e4b885115`.
Frozen verifier SHA, unchanged:
`b303d3d738ee98a847174e706d15264c091731c23459d2c2ba9a4c59854680ea`.

The correction removed a leftover unconditional all-disabled rejection below a
new guarded block, then enforced presence/type checks for required/blocked maps.
One editable Group 22 assertion demanded `missing_required_trait` after lookup,
although strict validation rejects malformed entity traits earlier. Its input
is unchanged; it now asserts no exception, false rejection and a nonempty
reason. Frozen tests were not edited and independently validate queried and
unused malformed trait values.

Contract to preserve: only nil means absent; a present whole map must be a
table. String keys and boolean values are required; false entries are valid
but disabled. Empty required/blocked maps impose no matching constraint;
present empty/all-disabled any-trait maps reject. Validate before iteration and
matching. NPC cases use normalized kind `character`, not game-specific names.

### Native/watchdog status needs attention, not more coding repairs

Latest watch `3a683f6b6e1948a1a988b5b8d35c96da`, original human message
`msg_17e7f620f001IRfR2qiKGnIg8j`, has **zero retries** and `wait_runtime`.
The captured native process ended or changed. Native persisted metadata reports
an ended turn and no active tools, but no successful explicit finish marker.
Its first GREEN finish call preceded fresh mods validation and was rejected;
mods subsequently passed. Do not confuse that earlier rejected marker with
failing source tests or an infinite repair loop.

Do not fabricate an end flag, reset the journal, blindly replay the original
prompt, or force a continuation into another native process. Discover the
current Melty/OpenCode session and source binding when the user resumes. If
asked to conclude that task, recover current receipts and record an explicit
completion through the supported current session. No additional code patch is
needed solely because its native lifecycle record is unfinished.

### Portable checkpoint and reconstruction

`docs/handovers/checkpoint-20261027/` contains the coding copy's full mod source,
the two verified reference files and a SHA-256 manifest. Current policy/test
bytes now equal the verified reference. It is outside production test discovery.
Read its README before restoring. Preserve historical duplicate controller
copies as evidence; do not guess canonical paths or load them automatically.

On this PC use the existing managed copy. On a fresh clone, UUIDs and local
proposal IDs are not portable authority: verify archive hashes, reconstruct a
managed copy through the approved workflow, and review promotion to production
`mods/` against fresh destination hashes. Do not treat the older main-checkout
fixture as the latest isolated copy. The committed verified diff remains a
historical explanation, not a patch to reapply to the corrected copy.

See `diagnostics/POLICY_REFERENCE_REVIEW_20261027.md` and
`diagnostics/entity-policy-verified-fix-20261027.diff` for the original diagnosis
and disposable verification. Their 2026-10-27 unapplied/RED statements are
historical and superseded by this saved-state update.

## Verification and local-state boundaries

- Controller suite: **777 tests run, OK, 9 skipped**;
  `.smelter/repair-loop-dashboard-tests.log`.
- Setup/requirements affected checks: **26 passed**;
  `.smelter/repair-loop-setup-tests.log`.
- Latest JavaScript suite: **78 passed, 0 failed**;
  `.smelter/commit-node-tests-20261027.log`.
- Disposable policy/full-Lua/mods proofs and prepared proposal manifest:
  `.smelter/policy-diagnosis-20261027-4b1517c1/`.

Do not rerun all infrastructure tests merely for an unchanged local proposal.
Validate the actual saved Lua/mods state after applying it. Run additional
checks when changes, failures or unresolved concerns warrant them.

At handover the dashboard listened on localhost port 8769, PID 53132; hidden
watchdog PID 50360 was last observed enabled; its latest watch now waits for
the original runtime with zero retries. Exact bound native session was `ses_e873d493effeIa6L0ZxcaFq5nd`.
Those IDs/PIDs are discovery hints, not fresh authority. Use the status helper
and current binding before any control action.

Private launch URLs/tokens, prompt text, copied options, runtime credentials,
native databases, retry journal and coding-copy metadata are deliberately not
committed. Get the current local launch link from the dashboard startup log;
do not paste its token into documentation or GitHub. Do not reset private state.

## Next development milestones (saved checks are now GREEN)

1. Promote/merge the verified coding-copy changes through the normal reviewed
   source workflow; proposal apply alone does not update the main Git checkout.
2. Integrate the generic policy with the controller/adapter path and exercise
   behavior, not only exports/state creation. Keep vehicle rejection explicit.
3. Recheck runtime/loader evidence before promising a playable test. Offline
   Lua/Python/C++ results are not proof of host-game integration or current
   loader compatibility. Do not repeat older version claims without verification.
4. Continue generic recovery improvements from actual evidence. The watchdog
   bounds retries; it does not repair reasoning by itself. Prefer one measured
   task with current paths/receipts over replaying a broad old prompt.
