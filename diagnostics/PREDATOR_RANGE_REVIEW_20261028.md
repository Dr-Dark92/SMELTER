# Predator range regression review — 28 October 2026

Scope: operator-owned acceptance and review. Gameplay changes remain authored
by Qwen through the existing Melty/OpenCode/SMELTER workspace. All evidence in
this review is offline.

Later on 28 October, a separate RPH author-documented 1158.16 route and
compile-only read probe were prepared. See
[the native probe checkpoint](NATIVE_READ_PROBE_20261028.json) and
[probe guide](../docs/GTA_NATIVE_READ_PROBE.md). Runtime observations below
describe the earlier SHV inventory; they are not a claim that every alternate
loader route is unavailable. No live native result has been added.

## Baseline verified before changes

- Branch `feature/agent-stack-game-mods`, HEAD `876352f`; no commit or push
  requested. The unrelated untracked `dw3_decomp-main/` is excluded.
- Docker engine 29.8.2 responded. The dashboard on port 8769 uses the existing
  Codex-side SQLite database and seven access grants. No grants were changed.
- Saved tree `d04cc87228f7b4a2b12b63e43b12f48843b0196fcee92f292871f79c0f4f5b50`
  matched the current workspace. Receipt verification checked file/log hashes,
  runner revision, frozen acceptance revision and the current tree.
- Lua receipt `d970f26f-b137-4779-93ff-a4ed69491909` and mods receipt
  `950a93e8-1976-4b93-92f8-5bdc421fa529` were GREEN. Watch
  `93ad3ee2675a41fd99a289bc1b0da73b` ended explicitly GREEN with one retry.

## Reproduced defect and frozen tightening

The promoted controller discards the validated distance returned by acquisition
and retention. It then describes the target again. If that call throws or
returns nil, `type(s_dist) == "number" and s_dist > attack_radius` is false,
which incorrectly reaches the attack branch.

Two scenarios were added at both existing adapter scales (1 and 100): acquisition
with unavailable `describe`, and retention with a successful first lookup but
failed second lookup. Both use an eligible target outside attack range. They
assert movement, no extra movement command on retention, and zero attacks.

The disposable reference passes **52/52**. A deliberately redundant-lookup
mutant passes all older 48 and fails exactly the four new checks. Missing
constructors still produce counted RED (52 failures), not a count ERROR.
`test_acceptance_contracts` passes 11 tests, including these proofs.

The operator migrated `predator-controller-v1` in workspace
`897b9243-fd7e-42f4-a46a-d1b814a33a81` from verifier
`c5478a76886d9c46a74fb9cb0fdfff7c2874e44635c83db4aa3b8667d22bbc0e` to
`3a3b3b8d4069b3ce238cd309e7c878bce911e4e497fc7d60118027ab228a3b02`.
The migration reason and both hashes are retained in the private ownership
metadata. Earlier GREEN receipts are historical after migration.

## Service refresh and model task

The dashboard was gracefully reloaded while native work and human waits were
absent. Melty's bound OpenCode instance was disposed through its documented
idle reload endpoint; the conversation was preserved and the MCP child process
was replaced. The watchdog was restarted without deleting its journal. No
model inference was submitted during service refresh.

Qwen was then given one small numbered range-fix task, with fresh reads and a
targeted proposal, Lua tests and an explicit end flag. The prompt requires a
tool call in every reply. The model remains the existing 131072/8192 profile.
Reference proof above does not claim that Qwen's working file is repaired.

### Saved fix and review

Qwen repaired the working controller, SHA
`5e2077c84320490218688cb42f94127cc20d436eb2735622ab137873ff3e95ab`.
It stores the distance validated in each acquisition/retention branch and reuses
it for the movement/attack decision. A failed retained lookup exits before the
attack branch. Code review confirmed this data flow as well as the frozen result.
The cache comment's "next pass" wording is imprecise: each live-target update
refreshes the distance before use. A local variable would be simpler, but the
reviewed branches do not use the preceding tick's distance to attack.

Saved Lua receipt `f4ef0e36-6b69-4c4a-b357-3a4e7d23ea36` is GREEN: seven editable
programs, 52/52 controller and 30/30 policy checks. The task ended explicitly
GREEN under watch `2cafb13aa28142d286804ea4bc1844a3` after one bounded watchdog
nudge for the missing finish call. The source was hash-checked and promoted to
the main tree; see `PROMOTION_20261028.json`. No tests were changed for this fix.

Infrastructure suites after the operator changes: 796 dashboard tests (nine
skipped), 144 setup tests and 78 Node tests pass. Logs are private under
`.smelter/codex-*-20261028.log`.

## Editable integration test review

The first Qwen test attempt was rejected in review. Its fake adapter returned
`true, value` for reads, although the real adapter must return the table directly.
It also used `kind="human"` against a `character` policy, an invalid
`detect_radius=10, lose_radius=8` profile, dot syntax for the colon-method update,
and weak alternative-action assertions. One attempt filtered the vehicle before
the evaluator, masking the very policy integration being tested.

Qwen restored the load-only test and produced GREEN receipts. Those receipts
describe the restored tree; they do not satisfy the requested new coverage.
No defective test was promoted. The next watchdog continuation repeated the
interface mistakes, so an explicit operator review correction was submitted
into the same session, keeping the workspace and earlier watch history. Its
existing `smelter-thinking` variant was selected; model/context/output limits
were unchanged. This is revised guidance after review, not a reset of a stored
watchdog retry counter. Acceptance still requires code review and deliberate
regression checks on the resulting editable test.

The long session continued inventing signatures after that correction. The
operator stopped this failed offline attempt through the documented abort API;
the journal records cancellation and no defective test was promoted. The old
session/history/checkpoints remain. A fresh root OpenCode session in the same
Melty-owned backend and project directory was created:
`ses_e7e475992ffecLCoawxqFI9uax`. The dashboard observer was stopped and rebound
through its revision-checked API, preserving the former binding archive. It
uses the same owned coding workspace, model ceiling and access grants. This
fresh session is not a newly created Melty UI conversation; its native ID is
the progress authority and no Melty task ID is claimed.

The passing Qwen-authored dictionary fixture was eventually recovered from its
exact checkpoint (`18b8b86d…`) through proposal
`57b01361-55cb-4610-83ca-9190196b1bdd`, applied by Qwen with edits/restores excluded
from that bounded recovery task. Saved Lua/mods receipts are
`08a6f1b3-a405-44fa-a59d-cae855a05b7e` and
`ff186455-2417-4342-a88b-45810bf2d5fe`; explicit GREEN, zero nudges.
The independently executed baseline passes and two deliberate mutants exit 1:
`PREDATOR_POLICY_TEST_PROOF_20261028.json`. The test was promoted. Role labels
currently repeat one normalized human fixture; native role classification and
explicit command-target spies remain unverified.

The following adapter draft was rejected in review and remains unpromoted.
Work is now paused by the user; the proposed provider-admission frozen checks
have not been written or registered. The complete source/status/resume map is
`docs/handovers/CODEX_PAUSE_CHECKPOINT_20261028.md`.

## Fresh runtime inventory

The existing read-only inspector was run against both installed game folders:

| File | Version resource | SHA-256 |
| --- | --- | --- |
| GTA5_Enhanced.exe | 1.0.1158.16 | `b48e80f5fc899eb89e5dcc9f3b68e9551cc8dcfac78b2a940b207e569e9987ea` |
| ArkAscended.exe | 5.5.4.0 | `fa416320b3be8830d6d0fee1a5e9f8ec5331dff98bc833a7ea38360e34b928ad` |

The ARK executable version resource is not proof of an Unreal engine minor
version or a working runtime API. None of the inspector's Script Hook V/ASI
loader/UE4SS/bridge paths were present. No `.asi`, Hook-named, Lua-named or log
files were found by the separate GTA-root checks. Other possible routes have
not been exhaustively inspected.

The [Script Hook V author page](https://www.dev-c.com/gtav/scripthookv/), checked
28 October, still lists Enhanced 1.0.1158.13 support. That does not establish
compatibility with installed 1.0.1158.16. No loader was installed, version check
patched, game file changed or game launched. The complete local inspector
receipt is ignored at `.smelter/runtime-inspect-20261028.json`.

No new tool or package was installed. The existing acceptance dependency/count
declarations were updated in both requirement files.
