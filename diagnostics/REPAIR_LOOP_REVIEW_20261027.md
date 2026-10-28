# Repair-loop diagnosis — 2026-10-27

The report was correct: patches were being applied, but protected behavior was
not converging. The watchdog sent exactly three continuations, not an unlimited
number. Within those turns the agent repeatedly failed the tool protocol and
changed logic without reducing the same frozen failures.

## Evidence

- Watch `19fb315a1d054d6380be8e23d0b6aa54`, workspace
  `897b9243-fd7e-42f4-a46a-d1b814a33a81`, retained retries **3/3**.
- Repeated malformed batch-edit arguments: top-level file/hash fields alongside
  a JSON-encoded `changes` string. MCP rejected these before execution.
- Repeated duplicate-path batches and whole-file replacements containing only
  snippets were rejected by the existing controller safeguards.
- Real patches also applied. Protected failures oscillated around 5–7 out of
  30, rather than reaching GREEN. One intermediate edit produced a Lua runtime
  exception from iterating a string.
- The preserved final tree is
  `3b95a5b1c9ce391f714dc01ed2c89fc037a153246a6eaf74eaf6fe0a74bcb2ae`.
  Receipt `77f473c5-83f7-4881-ae9b-e117c30e7536` matches that tree: Lua RED,
  six test programs, one failed program, no runner errors; frozen acceptance
  still has **6 failures / 30 checks**.

This is not evidence of missing installed modding tools. Most displayed tool
errors are deliberate argument/hash/edit safeguards. Passing controller tests
does not establish that the agent's gameplay implementation is correct.

## Intervention

The exact bound native turn was aborted through its supported same-session
API, and the watch recorded `operator_stopped_repair_loop`. The backend became
idle; files and checkpoints were retained. The retry journal was not reset and
no fourth prompt was submitted. The current source was not repaired manually
by Codex, and no frozen acceptance test was relaxed.

## Generic controller changes

1. `propose_coding_edit` exposes one exact replacement using five flat string
   arguments. It uses the existing proposal/hash/checkpoint/apply engine.
2. Stdio schema validation moved into the audited, budgeted ToolSession using
   the same advertised schema. Invalid calls return compact structured guidance
   without echoing rejected code. There is no automatic coercion or execution.
3. Three protocol errors among twelve recent task tool calls hold watchdog
   continuation. Three comparable frozen RED results without improvement also
   hold continuation. These are diagnosis waits, not fabricated RED/GREEN flags
   or extra terminal rules. The three-retry maximum remains.

The existing installed `jsonschema==4.26.0` is explicitly pinned in the MCP
requirements. New components and behavior are in the requirements catalog and
recovery documentation. No new executable or package was installed.

Use a new, narrow human task on the saved workspace for the next evaluation.
Choose one failing frozen behavior, read its actual inputs, use the scalar edit
tool, apply one proposal, then validate. Require a lower protected failure count
before expanding scope. Do not replay the old broad repair objective again.
