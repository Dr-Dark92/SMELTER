# Frozen acceptance and task outcomes

## Why this exists

The reported interrupted run fixed an optional-map nil exception, then removed
strict entity-trait validation to satisfy an editable test's reason-code
expectation. Its six Lua test programs passed, while an unused malformed trait
was accepted. OpenCode recorded the turn as ended, with no pending tool; that
lifecycle record does not establish why the reported interruption occurred or
whether the user task was complete.

Guidance and repeated-call guards did not prevent this semantic regression.
The controller now runs separately registered acceptance checks and displays
task outcome independently of response lifecycle.

## Controller-owned contract registration

An operator registers an existing subject module and a reviewed verifier:

```powershell
python tools/setup/register_acceptance.py --workspace-id <UUID> --contract entity-policy-v1 --subject <project-relative-module.lua>
```

The registry is saved in the owning workspace's controller metadata,
`.smelter/coding-workspaces/<UUID>/acceptance.json`, outside its editable source
copy. Registration is deliberately absent from the model's tool registry.
The initial `entity-policy-v1` verifier checks a pure Lua module exposing
`evaluate(entity, policy)`. Its 30 cases use normalized actors, traits and policy
maps; no game or engine names, loaders or native adapters are embedded in it.
Other interfaces require reviewed verifiers and explicit registration; the
framework does not infer acceptance requirements for every project.

The model can inspect the contract summaries through
`coding_workspace_context` and `coding_recovery_context`. Test comments,
compaction notes and incidental reason-code assertions cannot override the
operator's frozen behavior. Correcting a contradictory editable assertion must
preserve the frozen allow/reject expectations and remain a reviewable patch.

### `predator-system-v1` (added 2026-10-28)

Twenty checks cover the passive entry/lifecycle boundary: explicit dependencies,
safe validation, actual policy/controller wiring, per-actor results and command
identity, failed removal retaining registration, successful removal preventing
ticks and removal/re-add starting fresh state. This catches a subtle lifecycle
bug: dropping an ID from an active set while reusing its old controller state
can retain a target/cooldown when the ID is added again. One fresh controller
per registration satisfies the contract without changing the shared controller.

The pure loader permits only the subject's sibling `engine_adapter`,
`predator_controller` and `entity_policy`. Native scheduling/spawn globals are
sentinels that must never be called. Keep their three independently registered
contracts alongside this one; the four contracts total 128 checks. No native
game integration is supplied or proven. The operator fixture proves a reference
and rejects false removal, stale cooldown, policy bypass and hidden fallback.

### `provider-admission-v1` (added 2026-10-28)

When a model repeatedly invents interfaces while writing editable tests, the
operator can run `tools/setup/scaffold_acceptance_test.py --workspace-id <UUID>
--contract <registered-id> --destination <project>/tests/test_<name>.lua`.
`contract_test_scaffold.py` validates the registry/verifier and same-project
destination, then creates a normal proposal with current file hashes and Lua
syntax validation. It never applies automatically. The generated test is an
editable conformance copy of the pinned verifier; changing it cannot change the
independently executed frozen gate. It does not provide separate integration,
profile or native evidence. Add those targeted tests separately.

The existing `scaffold_contract_subject` also supports `predator-system-v1`.
Its operator-reviewed structured imports/setup supply constructor admission and
the real policy/controller factory inside the per-instance scope. Three colon
methods remain TODOs. The pure controller scaffold remains import-free. Imports
are limited to six validated module/alias pairs and setup to forty short lines;
neither can be supplied in a model tool call. The lifecycle skeleton passes 9/20
checks; a disposable completion of only the three methods passes all 20.

Verifier: `tools/dashboard/acceptance/provider_admission_v1.lua`, 26 checks.
The subject exposes `new(provider)`, `get_adapter_type()`,
`init_simulation(provider)`, `init_real_game(provider)` and `spawn_raptor(...)`.
The six required provider functions are `position`, `describe`, `candidates`,
`move_to`, `attack` and `stop`. A missing/non-table provider returns
`nil,"unsupported_runtime"`; each missing function returns
`nil,"unsupported_capability:<name>"`. Construction must not call the provider
or change legacy mode. Read values/reasons, arrays and command arguments/results
pass through unchanged. A successful `pcall` must never mask a refused command.
Exceptions may propagate to the controller's existing containment boundary or
return a refusal with a nonempty reason.

Loading starts in `uninitialized` mode. Simulation requires an explicit complete
provider; configured-provider initialization uses mode `provider`. Failed
initialization clears the previous mode. `spawn_raptor` explicitly rejects with
`unsupported_capability:spawn`. Structural admission proves neither a native
runtime nor game compatibility; no game API, implicit fallback or scheduler is
introduced. The disposable reference and eight regression mutants live only in
the operator test fixture, never the mod. Registration remains operator-owned.

### `predator-controller-v1` (added 2026-10-28)

Verifier: `tools/dashboard/acceptance/predator_controller_v1.lua`, 52 checks (earlier revisions had 42 and 48).
The subject is a pure Lua module exposing `new(deps)`. Everything game-specific
is injected: `adapter` (`position`, `describe`, `candidates`, `move_to`,
`attack`, `stop`), `evaluate(entity, policy)` (for example the registered
entity policy), `policy`, `clock` and a `profile` holding `detect_radius`,
`attack_radius`, `lose_radius` and `attack_cooldown`. `controller:update(actor_id)`
returns `{action, target_id, reason}`. The contract text in
`acceptance_contracts.DEFINITIONS` is the authoritative summary.

The verifier runs 4 construction checks, then the same 24 scenarios against
two fake adapters at different unit scales (×1 and ×100). They cover evaluator
integration, a nearer vehicle being rejected, the actor never targeting itself,
ignoring adapter-returned candidates beyond range, a single move request per
target, attack in range by the actor at the target, cooldown driven only by
the injected clock, disengaging (with `stop`) on death, disappearance or the
lose radius, refused/throwing adapter calls reported as errors without
starting cooldown, and independent state per actor.

Before registration it was checked against a disposable reference (42/42)
and six single-line mutants (self-targeting, move re-issued every update,
no cooldown, evaluator ignored, no stop on loss, cooldown never recorded).
Each mutant failed 2–8 checks. The promoted `raptor_aggro.lua` fails all
42 checks because it has no `new(deps)`. The verifier then reports a counted RED,
not a count ERROR. Fake-adapter success is offline evidence only: it does not
show that any game exposes these capabilities, or that an actor moves or attacks.

Failing checks print `| observed: …` with the last few subject results, adapter
commands or the raised error. A subject that fails to load reports its load error.
The acceptance item keeps `failed_checks` (up to 8) and `failed_total`.
Definitions may carry an `interface` checklist, which context, recovery and
failing results repeat verbatim.

### Tightening after review (42 → 48)

Qwen's first GREEN controller passed all 42 checks. Code review still found
three contract violations the checks did not exercise:

- `candidates` and `describe` were called without `pcall`, so a throwing
  adapter crashed `update`.
- Losing a target set the attack time, so cooldown started on loss.
- A refused `stop` on disengage was ignored.

Three scenarios were added at both adapter scales (+6 checks): a throwing
`candidates`/`describe` is contained, losing a target does not start the
cooldown, and a refused `stop` is reported as `error`. The disposable
reference passes 48/48, and every earlier mutant still fails. That controller
fails exactly the 6 new checks. The scaffold step comments were corrected at the
same time; their earlier wording led to returning `idle` when `candidates` threw.
A GREEN contract run is evidence for the scenarios it contains, not a code review.

### Range reuse tightening (48 → 52, 2026-10-28)

Review found that a redundant target description could fail after selection,
leaving no distance and falling through to attack. Two scenarios at both adapter
scales now require movement to an eligible, out-of-range target when a redundant
acquisition lookup throws or a second retention lookup returns nil. The distance
already validated for that update must be reused. No native APIs are involved.

The disposable reference passes all 52 checks. A regression mutant that adds
this lookup and treats missing distance as in range fails exactly the four new
checks while passing the older 48. The saved Qwen subject is checked separately;
reference success is never reported as a fix to the working copy. Re-pin only
after verifying this proof, while native work is idle. Earlier receipts remain
historical after the verifier/controller revision changes.

### Contract scaffolds

A definition may include a structured `scaffold` spec: dependencies with
types, required adapter functions, numeric profile fields with ordering
rules, plumbing helpers with bodies, behaviour helpers as TODO stubs, and
methods with step comments. The model tool `scaffold_contract_subject` renders
it as a whole-file proposal for the registered subject. That proposal goes
through the Lua syntax gate and is never applied automatically.

For `predator-controller-v1`, the scaffold alone passes 8/52 checks: the four
constructor checks and four error paths. Filling its TODOs with the reference
behaviour in a scratch copy reached 52/52, so the scaffold shape is completable.
Only generic plumbing is pre-written (a pcall wrapper and 3D distance).
Selection, loss, movement, attack and cooldown are left to the implementer.

### Operator migration

A changed verifier fails closed (`Frozen verifier changed`). After review:

```powershell
python tools/setup/register_acceptance.py --workspace-id <UUID> --contract <id> --migrate "<review reason>"
```

The subject path is kept and the new verifier SHA is pinned. The old and new
SHAs and the reason are appended to `acceptance-migrations.jsonl` in the
workspace's controller metadata. Earlier receipts become stale. The model has no
migration tool.

Adding a definition changes `acceptance_contracts.py` and therefore its
execution hash. Earlier Lua receipts in registered workspaces become stale
until they are rerun, and a running dashboard needs a reload before it can load a
workspace registered with the new contract.

## Execution and evidence

`run_coding_tests(profile=lua)` runs the editable test suite, then each registered
Lua acceptance verifier in a separate fresh read-only snapshot. The existing
pinned Lua/Python Docker image is reused; there are no downloads, new packages,
host Lua commands or arbitrary model-supplied executables.

The verifier is copied from controller source and separately mounted read-only.
Editing a same-named file in the coding copy cannot replace it. The pure subject
loads in a restricted Lua environment without `os`, `io`, `debug`, `require` or
`print`, so it cannot rewrite the verifier's counters or output. Each subject
process has a 12-second limit; the fixed aggregate runner has a 60-second limit.
Existing no-network, non-root, read-only and resource limits remain in force.

The receipt binds the workspace, registered subject path, exact tested subject
SHA-256, pinned verifier SHA-256 and executing controller revision. Currentness
requires the source tree, normal runner and acceptance revision to match.
Missing subjects, missing/inconsistent evidence and changed verifier identities
fail closed. A verifier update requires explicit operator review/migration.

The combined stage is GREEN only when both layers pass. Receipts retain
`workspace_tests_stage`, `acceptance.stage` and the overall `stage`; the existing
test counts describe the editable suite, while frozen check counts are recorded
separately. A frozen RED/ERROR also sets the native MCP failure signal. Ordinary
TDD RED results without a frozen acceptance failure retain their prior semantics.
Unchanged repeated failed test calls now participate in the recovery redirect.

This is a workflow boundary for SMELTER's scoped coding tools, not an OS security
boundary against unrestricted external MCP tools or an operator editing the
controller repository. Passing 30 checks does not establish all possible input
behavior, code quality, adapter compatibility or live game behavior.

## Task outcome in the live trace

The WebSocket view continues to show response lifecycle as **Response ended**.
It additionally derives an outcome from current validation receipts:

- **Changes needed**: current RED/ERROR, including frozen acceptance failures.
- **Not verified**: absent, stale or incomplete validation.
- **Checks passed**: all observed required receipts are current GREEN, within
  their recorded scope.

The editable-suite and frozen-acceptance stages appear separately. No automatic
prompt, access approval, task resubmission or restart was added. This prevents
an ended response from being displayed as proven task success without treating
normal completion, rate limits, cancellation and a deadlock as equivalent.

## Current project checkpoint

Registered workspace: `897b9243-fd7e-42f4-a46a-d1b814a33a81`.
Current receipt: `5608029b-67de-4aa9-9453-6961f8578f56`.
Tree: `0f3ee8054d19e1e6bf612db8fe1c35db49845c414365286801eeb76248e7e224`.

The editable suite is GREEN (six Lua programs). Frozen acceptance is RED
(26/30 checks pass). The failing cases are:

1. An unused non-boolean entity trait must reject.
2. `required_traits=false` is malformed, not absent.
3. `any_traits=false` is malformed, not absent.
4. `blocked_kinds=false` is malformed, not absent.

The subject SHA is
`4ef6844341f176cef01ffc17cf32ff2379e12d0ad656d12b8ee8a7b440dc94b5`.
Source files and local regression fixtures were unchanged by this controller
task. SMELTER/Qwen should repair the shared evaluator and reconcile its obsolete
reason-code assertion without relaxing input validation. Preserve both controller
copies, native adapters, frozen verifier and unrelated files.

See [the flow diagram](diagrams/frozen-acceptance.mmd) and
[general recovery guardrails](RECOVERY_GUARDRAILS.md).
