# Raptor run review — 27 October 2026

## Fragment replacement incident: exact recovery and general editing fix

The user reported a stall after repeated focused-proposal attempts. Native
lifecycle metadata shows the response ended with finish=stop, not a tool still
running. Applied proposal `d2e29b77-ae2c-4ef3-a777-8774fb8d2524` supplied only a
small replacement fragment to a whole-file content API, reducing entity_policy.lua
from 4,962 bytes/118 lines to 537 bytes/11 lines. Pre-edit SHA was
`0eeb5bccda445136d25a65ef6b75f941a31c6e49e386eabd8e1df84f1e07feeb`; fragment SHA
`ec4bd17f5fdb2200e52c4de8293ad74f515bf5944c09edb935666531d262c74e`.
There is no original-checkout baseline for this coding-copy-only module, and an
index hash alone cannot reconstruct its content.

Preserved the fragment, found exact pre-edit content in the existing read-tool
audit and verified its full SHA against the proposal and prior reviewed receipt.
Restored through proposal `c21e761c-3f75-47c9-b01a-ee1811187e4d`; the complete
task tree returned exactly to `3b2801df...d8cfd4`. Saved a durable owned checkpoint
with that full pre-edit SHA. Evidence and recovery receipt are under
`.smelter/progress-reviews/patch-corruption-20261027/`. No new gameplay logic was
authored. Fresh receipt `556796d3-aa2c-4021-876c-fc4a8f7fefbe` is GREEN for six
Lua programs with source/import proof; the six frozen acceptance failures below
remain because those semantics were restored unchanged.

Fixed the general controller mechanism: new propose_coding_edits assembles whole
files from unique old_text/new_text pairs; full-content proposals carry line
counts and reject likely accidental truncation unless an intentional complete
rewrite is explicitly acknowledged. Apply writes recoverable pre-edit checkpoints
before source replacements. Restore can use checkpoint_sha256 for workspace-only
files, with ownership/hash revalidation. Schema, direct/native instructions,
dispatch, file cards, requirements and documentation were updated. Checkpoint
storage keys were shortened after tests exposed Windows path-length failures;
complete SHA/path identity remains verified inside each record.

Validation: 712 dashboard tests OK / 9 skipped, 136 setup OK, 50 JavaScript OK,
including eight new focused editing/recovery tests with real MCP. Exact incident
fragment replay is now rejected without modifying the recovered file. Live trace
labels a final assistant message Response ended and shows current/stale test
receipts separately. GUI is PID 50064 on 8769 at this observation. No ACP worker
was available for hot MCP refresh; next Melty OpenCode connection loads updated
tools. The separate HTTP serve process is not evidence of an active ACP client.
No model continuation or prompt was sent. No external package was installed.

## Twenty-six-check GREEN: progress verified, one acceptance assertion changed

Report `bb169603-9e91-4a69-b444-64733f544c3a/Pasted text.txt` was checked against
the owned workspace, receipt and actual source. Receipt
`46d43b67-2cd0-4168-a67e-bbd9d2c76825` is genuinely GREEN for one Lua profile
with six programs, zero failures/errors/skips. The report's “six test profiles”
description is inaccurate. Current independent tree digest matches
`3b2801df5fdf5320b979cb6b4d4d6785725fe08d707c34434e8649a8f0d8cfd4`.
Source snapshot proof and actual imports match.

| File relative to the owned coding root | SHA-256 |
|---|---|
| `mods/gta-ark/Mods/GtaArkLink/Scripts/entity_policy.lua` | `0eeb5bccda445136d25a65ef6b75f941a31c6e49e386eabd8e1df84f1e07feeb` |
| `mods/gta-ark/tests/test_entity_policy.lua` | `97916a81363a178b5e3845e56700118c1047e93a8c54453156cd00204406022e` |
| `mods/gta-ark/tests/test_raptor_behavior.lua` | `408f9c7927e7c0c43ffa30967a705ed5fea46b1b6a77f388ee350407b5f62729` |

Real progress: all seven checks from the prior operator probe pass unchanged.
False required traits no longer impose presence; false any-trait entries cannot
satisfy enabled alternatives; a queried nonboolean entity trait is rejected;
nonboolean required-policy entries reject. Original flag/block/malformed-field
fixes remain intact. Test-local normalizers now translate two distinct raw
representations and call the real shared evaluator. They demonstrate one allowed
human-police case, not live Unity or RAGE API integration. Both controllers and
six original regression fixtures remain unchanged.

Acceptance is still incomplete:

1. Test group 25 retains the heading “Present any_traits with no enabled
   alternatives rejects” but line 299 now asserts `allowed == true`. This changes
   an explicitly supplied requirement to match implementation behavior. Policy
   lines 98–112 impose no restriction when no true entry exists, so both a present
   empty map and an all-disabled map are admitted. Restore the specified reject
   behavior; absent any_traits alone disables that rule.
2. `validate_entity` only checks traits is a table. Values/keys that are not
   referenced by a policy are never validated. An entity with
   `{human=true,extra="yes"}` or `{[1]=true}` can be admitted. The contract says
   all entity trait keys must be strings and all values booleans, independently
   of which traits a policy uses. Treating a queried string as missing is not
   whole-map validation.
3. `validate_policy` checks trait-map keys but not values. The later any-trait
   scan validates values only until its first enabled entry, then breaks. A
   malformed entry after that first entry can be ignored and the entity allowed.
   The proof selects the actual first/second iteration keys and modifies the
   second value in place, avoiding dependence on randomized Lua table order.
   Validate every map entry before eligibility short-circuits. Optional maps
   supplied as false must also reject; only nil means absent.
4. Group 20's fixture already has human=true, so it would not detect a regression
   that incorrectly requires the disabled human trait. Use a fixture missing it.
   Group 18 still expects both policies to allow the same entity, leaving the
   required opposite-outcome policy-switch assertion absent. The adapters need
   negative cases (vehicles/invalid/dead) and genuinely contradictory IDs/names.

An unchanged-copy diagnostic reuses the previous seven regression assertions
verbatim and adds six already specified contract cases. The seven pass; the six
fail: empty any-map, all-disabled any-map, unreferenced malformed entity trait,
nonstring entity-trait key, a later malformed any-entry and a false optional map.
One Lua program exits 1 (RED) with matching source/import proof. Evidence and
exact diagnostic test source:
`.smelter/progress-reviews/f86231eb88614804a6de9750745c98ab/`
(`policy-acceptance.json`, `policy-acceptance.log`, `test_policy_acceptance.lua`).
Temporary diagnostic source was removed; the active tree was not edited.

The next run should pin those acceptance expectations rather than adapt them to
the current implementation. Keep the working harness, flags, block priority and
native adapters; make a focused full-map validation/any-rule correction and add
missing conformance assertions. No full controller rewrite, Docker rebuild,
workspace reset or in-game acceptance claim is warranted. Applied-edit metadata
still ends at the old harness proposal; native edits are not a proposal receipt.
No package installation, model prompt or active gameplay edit by the operator.

## Nineteen-check GREEN verified: partial acceptance, trait semantics incomplete

Reviewed report `0e848155-b42d-4fd1-863b-a47d2ca03554/Pasted text.txt` against
current files and saved receipts in the original owned UUID. Receipt
`2c922abd-cbd9-4af0-a3ac-bcffe41d5db5` is GREEN: six Lua test programs, zero
failures/errors/skips, with nineteen checks in the policy program. Independent
rehash matches tree
`7c95849a44f541f4fde25ca30a10dd39e24d83b5b9699d0a97552211fed9f90c`.
Source snapshot proof matches and the real module import resolves correctly.

| File relative to the owned coding root | SHA-256 |
|---|---|
| `mods/gta-ark/Mods/GtaArkLink/Scripts/entity_policy.lua` | `428b29e0eca3080f52886a33fd77b1d7b99488bdb3ddd27e4f6fe70b8c973cdd` |
| `mods/gta-ark/tests/test_entity_policy.lua` | `1b006966dea9d3d119268e10e5cb4d32e28ca16a7b939dc4ea76ad4248bda4a5` |
| `mods/gta-ark/tests/test_raptor_behavior.lua` | `408f9c7927e7c0c43ffa30967a705ed5fea46b1b6a77f388ee350407b5f62729` |

Accepted progress: the three original regressions now reject safely, including
string flags through explicit equality with true. Explicit kind blocking takes
precedence. The harness no longer invents a replacement fixture ID or makes an
unasserted vehicle chase call. Both controller hashes remain dd63522f/root and
05e91c2/ark. Six original GAL1/runtime fixtures still exactly match checkout.
The policy file still has a UTF-8 BOM; the current Lua runner successfully loads
it, so BOM presence is not evidence of a current execution failure.

A disposable seven-check probe imports an unchanged policy copy with the same
SHA above. The three original regression checks pass, but four further checks
fail:

1. `required_traits={human=false}` with no human trait is rejected as
   `missing_required_trait`; a disabled rule still imposes a requirement.
2. `any_traits={npc=false,player=true}` accepts an entity with only `npc=true`;
   a disabled alternative can satisfy the rule.
3. Entity `traits={human="false"}` is admitted by `required_traits={human=true}`;
   entity trait values still use Lua truthiness.
4. `required_traits={human="yes"}` is accepted for a human entity; trait-policy
   values are not boolean-validated. Only allowed/blocked kind maps currently
   receive that validation.

The cause is at policy lines 14, 45–46 and 62–69: entity traits only need to be a
table, policy trait maps only need to be tables, and the loops ignore their map
values. Treat false entries as disabled and reject malformed map values. Define
empty/all-disabled any-trait behavior explicitly and test it. Preserve the working
flag/block behavior; no more value-specific flag reason codes are needed here.

Evidence lives under
`.smelter/progress-reviews/f0fd4b417f1047b4b17b0f094ad731a9/`:
`policy-contract.json`, `policy-contract.log`, and the exact
`test_policy_contract.lua`. One diagnostic Lua program exits 1 (RED), reports four
failed checks, and has matching source/import evidence. Initial probe setup
lacked the runner's dashboard source marker and did not execute; the corrected
fixture copied the unchanged checkout dashboard source to satisfy that existing
runner precondition. Neither attempt changed active gameplay files. Temporary
diagnostic source was removed; proof/log/test source were retained.

Missing conformance evidence remains material: there are no fake-adapter
translation functions in the nineteen-check test, despite its comment and
adapter-portability output. Group 18 evaluates the same human NPC under two
policies but expects true for both; it does not prove a policy switch changes the
result. Group 17 still names a vehicle with a Vehicle prefix; add genuinely
contradictory IDs/names in both classification directions. Use two distinct raw
representations feeding the exact real evaluator, not duplicated policy logic.

The report describes repeated destructive native rewrites while chasing a
mixed-flag reason-code mismatch. Current saved bytes and GREEN receipt are real,
but workspace applied-edit history still ends with proposal `5e75056e...` for
the older harness. Proposed IDs are not evidence of applied changes. Future
focused edits must use current hashes with propose/apply/readback, preserving
all regression fixtures. No new operator gameplay edits, model prompt or package
installation occurred in this review. Refresh the file index/relations and
project memory with this partial acceptance before the next user-submitted task.

## Live progress check: stalled child recovered, new changes unverified

Final observation: parent and child subsequently became idle with
`MessageAbortedError`, completed at approximately 07:58:53 UTC. The second native
read reports `Tool execution aborted`. The actor/cause of cancellation is not
established by lifecycle metadata. No new test receipt was produced. Do not
describe the task as still running or automatically resume a cancelled turn.

At approximately 11:54 Muscat the root session was busy with a `task` call since
06:46:33 UTC. Its child `ses_e83e3ab6cffep45ufziYUadIAG` had three exhausted-budget
SMELTER errors, followed by a native `read` waiting since 06:47:14 UTC. A pending
`external_directory` request targeted only the existing workspace's
`mods/gta-ark/tests/*` scope. No model was loaded in Ollama. This was blocked
execution, not evidence of a long computation or a Docker test running.

The original owned task tree had changed to
`4cef4fd171305ba6a51939cd0a9edac17014c8c9c6b7a75bc9967de4b00c7750`:

| File | SHA-256 |
|---|---|
| `entity_policy.lua` | `a9ac06ee46a21a7a483cb70224768c6bc3a7d1ffb3cd59eeb85943db640d5281` |
| `test_entity_policy.lua` | `1b006966dea9d3d119268e10e5cb4d32e28ca16a7b939dc4ea76ad4248bda4a5` |
| `test_raptor_behavior.lua` | `408f9c7927e7c0c43ffa30967a705ed5fea46b1b6a77f388ee350407b5f62729` |

No new test receipt accompanied these changes at the check. The earlier GREEN
result does not validate this tree. Gameplay implementation review is pending.

Recovery used the actual ACP API (PID 28516, port 51748 at this observation),
validated both session directories, and confirmed zero in-flight SMELTER tool
calls in the bound directory. While the conversation remained busy waiting on
native access, its SMELTER connection was quiescent. Re-added only the existing
SMELTER registration using its exact configuration, confirmed connected, and
granted the specific pending read once under standing user authorization. The
native API schema was inspected locally before mutations. No other permission
was changed, no model prompt was submitted, and neither conversation was restarted.

A subsequent native read paused on an additional permission for the owned
task's `mods/gta-ark/Mods/GtaArkLink/Scripts/*` scope. Verified the pending call
was a read inside that exact folder and replied `always` for that folder only,
using the same standing authorization. The original tests-folder approval was
once only. Neither operation granted general filesystem access.

The read completed at 07:56:51 UTC. At 07:57:30 UTC Ollama reported
`qwen3.5:35b-a3b-128k`, context length 131072. Remaining validation is a fresh
task-owned Lua receipt and review of actual saved fixes. Follow-up infrastructure
issues: parent-only busy status hides child permission waits; a persistent MCP
connection's exhausted call budget can block later task turns. Surface these
conditions without silently granting broad access or removing execution limits.

## Eligibility helper reviewed: basic GREEN, three reproduced defects

Attachment `e879d687-3ecf-4e08-9a7b-e4e4d54afe3b/Pasted text.txt` reports the
first pure policy evaluator in the original owned workspace. Its implementation
is independent of native APIs and interprets configured kind/trait keys. This is
useful progress toward the universal boundary; controller integration is still
absent, as the report acknowledges.

Verified file identities:

| File relative to the owned coding root | SHA-256 |
|---|---|
| `mods/gta-ark/Mods/GtaArkLink/Scripts/entity_policy.lua` | `ee4e5fedc4dc5b79fc2ec20d0086a9744cb7350d66fb7413e1d5154b43537e66` |
| `mods/gta-ark/tests/test_entity_policy.lua` | `e9764d3cbd4cf57d110cba3b21cb8281223ef1dc36a515f331ada4a66cc4d78e` |

Receipt `7ee2d221-1065-4ac3-b1d3-4502fd6ad94e` is GREEN, six Lua programs,
zero failures/errors/skips. The policy program has eleven passing checks and
imports the actual module above. Host/container bytes match; independent rehash
matches its tree `9cced0c411e561d580cff110987ccdf378c5e2da9b87b3e3baab8830fac1fe64`.
The earlier unknown-kind fixture correction supplies `alive=true` to isolate
kind rejection; that correction does not establish broader validation coverage.

An operator-authored disposable negative-case test imports an unchanged copy of
the policy module, with the exact same SHA-256. Source evidence matches. Its
single program exits 1 (RED) and reports three failed assertions:

1. `required_traits="human"` reaches `pairs()` at module line 70 and throws,
   rather than returning false and a reason. The other optional policy maps also
   lack type validation. Malformed ordinary configuration must reject safely.
2. `allowed_kinds={character=true}` combined with
   `blocked_kinds={character=true}` admits a character. Lines 59–65 only consult
   the blocklist when the allowlist rejects; explicit blocking must take priority.
3. An otherwise valid character with `valid="false", alive="false"` is allowed.
   Lua treats nonempty strings as true. Normalized flags and map values need
   defined boolean validation instead of truthiness.

Probe receipt/log:
`.smelter/progress-reviews/1c19ea5bdd754a6fb59fb8a9b07575cf/policy-safety.json`
and `policy-safety.log`. Source snapshot ID:
`6cd65134-6a87-4216-b90a-82c71908d039`. These are diagnostic fixtures, not a
modified task tree or an additional product coding workspace. No active gameplay
module/test was edited and no model turn was submitted by the operator.

The test comment and final output claim fake-adapter/portability evidence, but
the file contains only directly constructed normalized tables. It does not
translate two different raw adapter representations, test names that contradict
classification, or explicitly evaluate the same entity under both policies.
Add those assertions against the real evaluator. Treat false-valued map entries
as disabled (or document another consistent contract); validate nonboolean values
and do not accidentally require/count disabled traits.

The state-creation harness remains SHA `46e1f095...ed9d`, including the `_new`
fallback and unasserted vehicle call. The two controllers remain unchanged.
Metadata has no new applied proposals for the helper/test: their native file
creation bypassed the requested proposal/readback evidence chain. Future edits
should use existing SMELTER propose/apply tools and include proposal IDs.

Next action is policy hardening plus two-adapter tests in the same UUID, not
controller movement, attack, spawning, Docker rebuilds or another workspace.
Retain the six original regression fixtures. No dependencies were installed;
requirements need no additions for this review. Refreshed workspace file index
and relations source retain the current paths/hashes and receipt currency.

## Aligned harness verified: ready for the eligibility slice

Proposal `5e75056e-a257-4ca7-9f3a-c67934b2cb83` is applied and changes only
`mods/gta-ark/tests/test_raptor_behavior.lua`, now SHA-256
`46e1f095f32122c7a353f5f954fd8c22e0f2e552cb3e95576724b2c37a91ed9d`.
Receipt `58e11405-b6b4-4089-bccc-81a5b311e2ef` is GREEN: five Lua programs,
zero failures/errors/skips. Four counted state checks pass, with additional
module/table/function validation guards. Independently rehashed current tree:
`c3f870a1a3d18bb097576da19db072f4d1d4385b45dedae934b0d16e62ec44fd`.

Behavior and export tests now both import root `Mods/GtaArkLink/Scripts/raptor_aggro.lua`
with controller SHA `dd63522f...9750c`. Host/container manifests match. The harness
validates real exports before setup, does not replace the state table, and no
longer counts vehicle handling as a pass. The three principal prior review issues
are corrected. This evidence covers offline state creation only.

Two small test cleanups remain to fold into the next slice: unexpected preexisting
fixture state should fail instead of silently choosing a `_new` ID, and the
unasserted vehicle chase call should be removed/replaced by a real policy test.
Vehicle rejection is correctly labelled UNIMPLEMENTED/untested in the present
harness. Do not treat that label or the program's GREEN exit as eligibility proof.

Next meaningful slice: engine-neutral classification/eligibility using normalized
adapter descriptors and configured policy. Prove human NPC/cop/player acceptance
and vehicle/invalid/dead target rejection through two fake adapters before adding
chase movement, attack, spawning or asset work. Preserve this aligned harness and
baseline fixtures. No new operator gameplay edits or extra model/test run were
performed in this review. The Python/mods receipt is still stale.

## Subsequent harness attempt: call fixed, sign-off still incomplete

Attachment `e946261f-46f6-457c-b3aa-d53b9a12c36b/Pasted text.txt` ends with a
real dot-call correction. Applied proposals `77fdeb24-b560-469d-bb84-9848ce04a139`,
`08f4817e-be09-4a49-a71d-a4f59bfdcd94` and
`9e75d989-1807-4103-abe5-a0a630256af0` affect only the behavior harness.
Both reviewed controller hashes remain unchanged.

Latest harness SHA-256: `86edcf72ffd86e845df077be3d4961795939258b310549b882625005aaf2c3af`.
Lua receipt `9251a9d5-bdd0-4056-9eec-18b175d4e831` is GREEN: five Lua programs,
zero failures/errors/skips. Source manifests match. Its tree
`55a46cf2c5a15664a3242c1dc6518b0dbb34176c1aac61dfa7c452399b4f34c0`
was independently rehashed and is current. All six original regression fixtures
still match the original checkout. The old Python/mods receipt remains stale.

The original argument-shift bug is fixed, but the harness is not ready for
acceptance:

1. Its package.path was redirected to `ark/Mods/GtaArkLink/Scripts/?.lua`, so the
   behavior program now loads controller `05e91c2...`. The module/export test
   still loads the root `Mods/...` controller `dd63522f...`. These are distinct
   implementations. Choose one authoritative module by tracing intended runtime
   callers, then align behavior and interface evidence to that same path/hash.
2. The vehicle branch calls start_chase and increments `tests_passed` without
   asserting its return value, rejection or absence of state. This is a disguised
   unconditional pass, not vehicle-policy evidence. Report classification as
   unimplemented/untested rather than counting that case as passed.
3. The test assigns `raptor_aggro.raptor_states = {}` before validating the export.
   This can mask a missing state table. Assert the actual module's exported table
   before any fixture reset; missing exports must fail.

Next SMELTER step is still harness quality and consistent module identity, not
another controller rewrite or a claim of generic behavior completion. Shared
classification/adapters follow once this slice has honest evidence. The operator
performed read-only review and updated this record; no gameplay file was edited
and no extra model/test run was submitted for this review.

## Conclusion

The supplied report repeatedly misdiagnosed Lua call and import defects as Docker
image caching. Edits occurred, but the requested generic boundary and meaningful
vehicle rejection test remain unimplemented. Do not rebuild images, reset the
original workspace or copy files between more guessed roots.

Original task workspace: `897b9243-fd7e-42f4-a46a-d1b814a33a81`.
Its controller `mods/gta-ark/Mods/GtaArkLink/Scripts/raptor_aggro.lua` is
`dd63522fd0479a55440646045e136e753d32a4a3d9b2962fc6ed7f85ffe9750c`.
Its behavior test is `3d96b91fc559a2bd49ef12ec0b7fd7a810a93229cf420e339825e2274e32cb2c`.
The test still uses `raptor_aggro:start_chase(...)`; the function is declared as
`M.start_chase(raptor_id, target_pawn, initial_location)` and rejects a non-string
first argument. Colon supplies the module table in that slot. `pcall` returns
true because this rejection returns false without an exception. The test mistakes
that for success, then finds no state. This is not stale source.

The new copies `3c1b21d9-2c59-46a1-b7b3-f0aa4586eeb0` and
`d5277878-a372-43d6-b594-63aedd84fad4` retain the colon call and use a module path
starting `mods/gta-ark/Mods/...` while tests already run from `mods/gta-ark`.
The resulting repeated directory prefix explains their import failure. Their
Python `mods` GREEN receipts do not execute Lua and cannot verify this repair.
The vehicle branch contains `check(true, ...)`, which cannot prove rejection.
All copies and their evidence are preserved; none was reset or deleted here.

## Fresh evidence

The runner now reports per-invocation source identity and standard Lua imports.
A fresh original-workspace Lua run returned RED with host/container bytes matching.
It loaded the controller at the exact path/hash above. Receipt:
`.smelter/coding-workspaces/897b9243-fd7e-42f4-a46a-d1b814a33a81/test-runs/4e6049ea-9abb-4ec3-95bb-72c1b0ae9191.json`.

A disposable forensic fixture ran the identical controller alongside the original
harness and an argument-contract probe. The original harness failed; the probe
passed, demonstrating colon → false/no state and dot → true/state created with
the same module/runtime. This is narrow evidence for argument semantics, not
Raptor completeness or correct target filtering. Active gameplay files were not
changed. Full diagnostic receipts/log:
`.smelter/progress-reviews/24f0f091b50049e985cfb7372e9a3188/`.

## Universal infrastructure corrections

- Lua receipts include host/container source manifests, actual test directories,
  standard-loader import paths/hashes and program exit codes. Inconsistent
  source/execution receipts cannot be GREEN. The Docker image is explicitly
  labelled runtime/toolchain-only; every test has a new source copy.
- Python and Lua profiles now describe their different discovery scopes.
- Native progress coverage now includes read-only shared lifecycle metadata.
  Melty's ACP process and the separate HTTP server have different event buses;
  the old HTTP-only card missed this real run. Session identity was correct.
- The current native connection exhausted its fixed 32-call budget during the
  loop. Reloading the actual idle ACP process's SMELTER MCP registration loads
  the updated instructions without restarting the AI conversation. Refreshing
  only the separate HTTP process would not refresh that ACP connection.

No new third-party package or image is installed. Shared gameplay architecture
remains the user's direction: controller/contract logic is portable, with native
calls and policy in explicit adapters/profiles.

## Next SMELTER slice

Use only the original task workspace. Correct the harness call signature and
assert the returned result, state and explicit vehicle rejection. Preserve the
original GAL1/runtime fixtures. Use `source_snapshot.bytes_match`, `test_programs`
and the exact current hashes as evidence before suggesting an environment fault.
Only then implement and test the normalized generic adapter boundary. Stop on
repeated identical failure with a changed diagnosis; do not create more copies.
