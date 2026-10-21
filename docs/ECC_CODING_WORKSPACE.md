# ECC coding workspace

This connects selected ECC coding instructions to real, scoped editing and
testing tools. It does not load ECC's executable OpenCode plugin or expand native
shell/delegation permissions.

## Operator flow

Preview the commit-pinned coding pack from the SMELTERV1 checkout:

```powershell
Set-Location C:\SMELTER
python tools\dashboard\install_ecc_skills.py --pack coding
```

The coding pack adds `tdd-workflow` to coding standards, security review and
verification. After reviewing the linked sources/hashes:

```powershell
python tools\dashboard\install_ecc_skills.py --pack coding --install
```

Existing matching manifests are skipped. Imports stay disabled. Enable and
restart the dashboard to activate the new manifest, then select
`affaan-m-ecc/tdd-workflow` and **Use in next task**. Up to three instructions can
be selected; do not select the entire collection indiscriminately.

In Next-task tool access, select **Allow a new isolated coding copy** and approve
one managed OpenCode session. The registered sibling V2 location must permit
read, write, and execution of the registered `tests` operation. Each new copy
lives at `C:\SMELTERV2\coding\<UUID>`. Existing V2 files are preserved.

The runtime needs the reviewed OpenCode image and a Python and/or Node test image
for the selected test profile. No package or image is downloaded by a tool.
Readiness checks inspect a read-only original-source snapshot, so checking
OpenCode no longer requires an already prepared frontend V2.

## Tool contract

| Tool | Actual action |
|---|---|
| `prepare_coding_workspace` | New bounded copy of tools/, skills/ and selected top-level project documents |
| `list_coding_files` | Paginated actual paths/hashes and a snapshot fingerprint |
| `read_coding_file` | Paginated UTF-8 text and the hash of exact full-file bytes |
| `propose_coding_patch` | Record a reviewable 1–6-file proposal; no code application yet |
| `apply_coding_patch` | Recheck every original hash, stage files and apply only the recorded proposal |
| `run_coding_tests` | Fixed Python unittest or Node test profile in a no-network Docker snapshot |
| `review_coding_workspace` | Changed hashes and whether all detected test profiles passed on the current tree |

OpenCode sees these as `smelter_<tool>`. Tool schemas, grants, audit and dispatch
use the existing universal bridge, rather than a connector per ECC skill.

Edits create or replace UTF-8 source files. Existing-file replacement requires
the exact previous SHA-256; new files require `expected_sha256: null`. A stale
file invalidates the batch before application. Replaying an applied proposal is
idempotent; it cannot overwrite subsequent changes. Failed partial application
attempts restore previously installed files where their bytes still match this
operation. Interrupted or unconfirmed proposals cannot be blindly replayed.

Paths reject traversal, absolute paths, drive/UNC/ADS syntax, reparse points,
Windows reserved names, private runtime directories and credential files.
Only supported text source/document types can be edited. There are no deletion,
arbitrary-command, dependency-install, original-source merge, Git commit or code
preview tools. Existing frontend preview remains CSS-only.

Limits: 32 tool calls per message, 6 changed files per proposal, 128 KiB per file,
512 KiB per proposal, 20,000 files / 128 MiB per copy, ten retained coding copies,
and 128 MiB / 4,096 files of coding metadata. The tool preserves existing work
when a quota is reached. It does not delete user work to free space.

File cards show original text, proposed complete code and confirmed saved bytes.
Coding previews are bounded to 16,000 characters per version and six coding
cards. They appear when actual tool arguments arrive; there is no simulated
typing. A proposal is explicitly labelled unsaved until application succeeds.

## RED, GREEN and review

The Python profile runs unittest discovery for `tools/dashboard/test_*.py`.
The Node profile runs existing `tools/dashboard/test_*.js` files. No test command
or arguments are supplied by the model. Each invocation has a 60-second inner
deadline and 70-second host process bound, leaving room for checks and cleanup
inside the 120-second host MCP envelope. It uses read-only code, tmpfs state, dropped
capabilities, a non-root user, resource limits, no network, and owned cleanup.

| Result | Meaning |
|---|---|
| RED | A real assertion failed; Python import/runner errors are excluded |
| GREEN | Nonempty, non-skipped tests passed with an actual successful exit |
| ERROR | Import error, missing dependency/runner, timeout, empty/all-skipped suite or invalid result |

RED is a completed test observation, not a transport failure. Both RED and GREEN
logs are retained. Results record the exact tested tree, image ID, counts, exit
code, log hash and confirmed cleanup. Subsequent edits invalidate current GREEN
evidence. If both Python and Node tests are detected, both profiles must pass on
the same current tree before `all_current_tests_passed` is true.

ECC's 80% coverage target is **not measured by these runners**. Git checkpoints
and E2E browser coverage are not supplied by this adapter. A generated test can
also be weak or misleading; passing tests do not certify the code's quality or
security. Review the actual test and implementation diff.

## Home smoke

With Docker, images, Ollama and the existing Qwen ready:

```powershell
python tools\analysis\home_smoke.py --live --ecc --coding --prepare-demo
```

This adds a disposable coding task to the earlier bridge smoke. The task adds an
assertion that `add(2,3)==5`, observes a subtraction implementation fail, applies
the addition fix, reruns for GREEN and reviews the current tree. The saved test,
fix, audits, proposal records and both test logs remain in the new evidence
folder. No production source, existing V2 or game files are edited.

The coding smoke uses 32,768 context / 1,024 output tokens / 300 seconds /
thinking off. A slow or uncooperative model can fail that bounded task; retain its
evidence and distinguish model behavior from transport/tool errors. Here and in
CI, synthetic inference can test wiring without claiming Qwen quality.

For GUI testing, begin with a small function defect and ask:

```text
Use the selected ECC TDD skill and the approved coding MCP tools. Prepare one
new coding copy. Inspect the relevant files and identify one small reproducible
function defect. Propose and apply a failing test first, run the fixed test
profile and record actual RED. Propose/apply the smallest fix, rerun the tests
for GREEN, then review the workspace. Preserve original source and existing V2.
Report actual receipts and hashes. Mark coverage, Git checkpoints and browser
testing unavailable; do not invent them or use shell commands.
```

The GUI example leaves defect selection to the model; its quality must be
reviewed. The automated smoke uses fixed known input/output instead.

## Remaining ECC layers

Executable plugin hooks/tools, agent delegation, scoped memory, dependency
installation, coverage and external MCP adapters remain separate work. The
current milestone supplies the first general patch/test/review path. See
[compatibility](ECC_COMPATIBILITY.md), [home runbook](HOME_SMOKE_TEST.md) and
[bridge progress](AGENT_BRIDGE_PROGRESS.md).
