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
