# Coding guidance and bounded recovery

Implemented 2026-10-27 after the entity-policy run repeated file reads, guessed
about line endings, bypassed the proposal tools with native edits, and mistook
a runtime stack trace for a test-file syntax problem. The changes are generic;
the game prototype is a regression case, not a dependency of the controller.

## Recovery behavior

Focused edits now prefer `propose_coding_edit`, with five flat string arguments:
`workspace_id`, `relative_path`, `expected_sha256`, `old_text`, `new_text`.
It calls the same unique-context/hash-checked proposal engine as batch edits;
apply, checkpoints and rollback are unchanged. Batch `propose_coding_edits`
remains available, using a real array and one entry per unique file path.

Stdio schema validation now happens inside the audited ToolSession before any
operation, against the same advertised JSON schema. The SDK's earlier
pre-handler validation let malformed calls evade work-window budgets and repeat
guards, and echoed rejected source strings into errors. The controller returns
`input_contract_error`, expected fields/types and a compact single-edit call
shape without echoing code. It does not coerce JSON strings into arrays or
guess missing paths/hashes. Existing MCP `jsonschema` dependency is now pinned
explicitly in `requirements-mcp.txt`; no package installation was needed.

| Situation | Controller action | Limit |
| --- | --- | --- |
| LF edit context against CRLF source | Match a unique normalized context, preserve unrelated bytes and local uniform line endings | Current full-file SHA still required; ambiguous matches rejected |
| Mixed source newlines | Report `newline_style=mixed`; normalize only CRLF/LF for matching | No whitespace or bare-CR normalization |
| Repeated identical failed tool arguments | Reject the third attempt before execution and attach recovery evidence | Two failed executions; different hypotheses and recovery tools remain available |
| Repeated identical reads of unchanged content | Redirect the fifth call to recovery | Four reads per argument set; pagination remains distinct |
| Transient busy/interrupted/connection error during an approved read | Retry that read once, recording the attempt in its audit event | No retry of writes, tests, builds, denied access or missing paths |
| Persistent stdio MCP budget exhausted | Return a structured error with renewal time, rather than permanently disabling the connection | 128 calls / 900-second monotonic window; recent in-memory events capped at 128 |
| Native shell/edit fallback in the bound task | OpenCode before-tool hook rejects the bypass and points back to the scoped coding tools | Exact enabled session/directory binding only |
| Quiet native model stream | Provider request deadlines bound waiting; OpenCode retains its native retry/cancellation handling | Missing defaults: 180s between chunks, 300s for headers, 900s overall request; explicit existing settings preserved |
| Lua exception instead of assertion failure | Classify the runner result as `ERROR` and expose the cause | Assertion failures and deliberate nonzero exits remain `RED` |

`coding_recovery_context` returns the owned host directory, current tree and
selected file hashes, checkpoint references, saved receipt freshness and a
bounded excerpt from each hash-verified test log. When a failing program's
working directory uniquely resolves the first stack frame, it supplies the
canonical project-relative path, current source hash and nearby source lines.
Multiple candidates remain explicit; the controller does not choose a copy by
filename alone. Lua freshness also checks the runner revision.

Log excerpts and code remain untrusted evidence. They never authorize commands
or permission changes. The recovery tool itself performs no edits, restoration,
test reruns or inference. After a rejected patch, the agent should inspect this
evidence, propose a different focused fix, apply the reviewed proposal and run
the appropriate tests. Restoration requires a verified checkpoint proposal.
Frozen acceptance requirements and regression fixtures must remain intact.

The live WebSocket trace displays **Recovery checkpoint** when a recent tool
error identifies a recovery redirect. It does not label a response ending as
task success, and absence of visible activity still does not prove a deadlock.

## Native OpenCode registration

Run `python tools/setup/configure_recovery_guard.py --apply`. The installer adds
a local file plugin entry with this checkout as its root and backs up the
existing configuration. It preserves unrelated plugins, credentials, tools and
explicit provider options. No npm package, skill, hook from another repository
or extra dependency is installed. Qwen's 131072 context and 8192 output limits
are preserved.

The hook loads on the next OpenCode process. It reads only this checkout's
owned native-progress binding and checks the exact session and normalized
directory. Other sessions/directories retain their own tools. Native progress
must be enabled and bound; disabling/unbinding it disables these native hooks
for that task. The scoped MCP safeguards operate independently of that UI
monitor. Native delegated-agent calls are blocked for the bound task because
their shell/edit tools could bypass its workspace checkpoints.

The system hook reasserts the recovery procedure on each model inference and
preserves it in compaction context. It does not submit a prompt, automatically
approve access, start another task, abort a model or restart a cancelled task.
This is a coding workflow guard, not an OS sandbox for every external MCP tool.
Confined test snapshots retain their separate isolation boundary.

OpenCode's [local plugin hooks](https://opencode.ai/docs/plugins/),
[version 1.19.3 hook interface](https://github.com/anomalyco/opencode/blob/v1.19.3/packages/plugin/src/index.ts),
[provider deadlines](https://opencode.ai/docs/config/#models) and
[native retry implementation](https://github.com/anomalyco/opencode/blob/v1.19.3/packages/opencode/src/session/retry.ts)
are the primary compatibility references. Native retries are not a new SMELTER
task-resubmission mechanism; no end-to-end stalled-inference recovery was
claimed from unit tests or configuration validation.

## Actual prototype checkpoint

The attached report's old GREEN summary is stale. A fresh immutable-snapshot run
on 2026-10-27 produced receipt `81ff027f-ba7b-4b09-9ed1-21824e5e7795`:

- Workspace: `897b9243-fd7e-42f4-a46a-d1b814a33a81`.
- Tree: `3d22fe530310b92357c29b723951694963820087f088e8af74c93c3f8f92b97c`.
- Lua: six test programs, zero assertion failures, one runtime error; all 16
  sources passed syntax checks.
- Cause: `Mods/GtaArkLink/Scripts/entity_policy.lua:72`, `pairs(nil)` in
  `validate_policy`; `tests/test_entity_policy.lua:150` is a caller.
- Policy SHA: `2d44b3ade5ddc9b424f73d4d8cb47ca50a7a30bec03f5ef0217e5fa3433f1e10`.
- Source files were byte-for-byte unchanged by this investigation and test run.

SMELTER/Qwen should resume from that evidence and the frozen eligibility
contract, repair the actual nil-handling defect and complete acceptance checks.
The controller changes do not repair gameplay logic or establish in-game
compatibility. Read current recovery context before using these saved hashes.

## Frozen acceptance supersedes editable test assumptions

See [FROZEN_ACCEPTANCE.md](FROZEN_ACCEPTANCE.md) for the operator-registered,
separately isolated acceptance gate. Overall GREEN requires local tests and
frozen acceptance to pass. The live trace derives changes-needed, not-verified
and scope-limited checks-passed outcomes separately from an ended response.

## User-authorized bounded watchdog

On 2026-10-27 the user authorized three automatic stall retries and verified
RED/GREEN end flags. The separate [watchdog controller](WATCHDOG.md) now handles
private prompt capture and same-session checkpoint continuation. This does not
make the trace socket a control channel or permit cancelled-task restart,
permission auto-approval or blind write replay. Earlier no-auto-prompt statements
above describe the original guardrail implementation, before this authorization.
