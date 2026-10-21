# OpenCode, skills and MCP bridge plan

Date: 2026-10-21. Starting revision: bed7255ebe0d5b0f93dce7c6308beaf972345d3f.

Milestone 1 is implemented and smoke-tested. See [progress](AGENT_BRIDGE_PROGRESS.md)
and [handover](AGENT_BRIDGE_HANDOVER_20261021.md) for exact evidence and remaining work.

## Goal

GUI -> SMELTER admission/controller -> OpenCode -> Ollama -> Qwen. Selected
skill snapshots enter the task as reference instructions. OpenCode calls
approved SMELTER capabilities through MCP; the host controller validates and
audits each action. Protocol adapters belong to runtimes, not individual skills.

## Delivery sequence

1. Add a per-task bridge: freeze selected/automatic skills, tool descriptors,
   registered location policy and explicit per-message grants before inference.
2. Provide a bounded stdio MCP proxy inside the existing no-network OpenCode
   container. Relay calls to the host's existing MCP/ToolSession dispatcher.
   Keep source mounts read-only and native shell/edit/delegation denied.
3. Add the GUI agent route without dropping selected skills or tool grants.
   Expose real controller receipts and existing file activity, including fixed
   frontend CSS editing/validation when explicitly approved.
4. Smoke-test actual OpenCode and stdio MCP with deterministic model replies,
   real disposable report writes, hashes, denials, cancellation and persistence.
   Run Linux/Windows contracts and the browser fixture.
5. Supply an opt-in live smoke command that records exact runtime/configuration
   and checks saved bytes. A synthetic reply never establishes Qwen quality.

## Explicit boundaries

No automatic installs, arbitrary external MCP servers, generic host shell,
arbitrary source writes, additional model providers or scope expansion through
skill text. Existing source/V2/data are preserved. The existing frontend grant
permits CSS-only changes and fixed checks; generic workspace coding needs its
own patch/review and confined execution design after this bridge is verified.

## Acceptance

- The task contains the actual enabled, unchanged skill instructions and hashes.
- OpenCode discovers only approved tool schemas through its real MCP client.
- A real MCP report write is independently checked on disk and recorded in chat.
- An unapproved tool and an out-of-scope path cannot cause an action.
- No tool actions run during readiness checks; no new operation is admitted after cancellation.
- Completed actions survive a failed model follow-up or interrupted task.
- Production execution still requires the managed container; test fixtures are
  explicitly injected and never become an automatic host fallback.

## Follow-up

General confined multi-file coding, safe V2 refresh, arbitrary external MCP
adapters and model-quality benchmarks are separate milestones. Durable task
records already exist; recovery must continue to mark interruption without
replaying actions.
