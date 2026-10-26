# OpenCode agent: selected skills and approved MCP tools

Lua validation now syntax-compiles all Lua sources in each tested mod (up to 512
files) before executing its test programs (up to 64). Unimported broken modules
stop the run with ERROR. The syntax check uses Lua 5.4 `loadfile` without executing
the module. Receipts expose `source_syntax`, the host runner SHA-256 and the
validation scope. Coding-workspace review requires that identity to match the
current Lua runner, so older GREEN receipts must be retested. Behavioral coverage
remains unmeasured; tests must import real implementations and fail assertions.
No extra package or image was installed. See the
[Raptor review and regression evidence](../../diagnostics/RAPTOR_PROGRESS_REVIEW_20261026.md).

26 October extension: [resumable directory access](../../docs/ACCESS_REQUESTS_AND_MEMORY_ROADMAP.md)
and [controlled internet/project memory](../../docs/INTERNET_AND_PROJECT_MEMORY.md)
use the existing controller/MCP route. The bridge now permits 48 descriptors
and a 900-second RPC ceiling; operations retain their own smaller budgets,
including bounded human waits. The full interactive manifest has 36 tools.
The earlier audit checkpoint and 450-second envelope below are historical.

Verified application: `cee565b24726a9c217eab21c8a75bac88cad8c9c`. See the
[full smoke runbook](../../docs/FULL_SMOKE_TEST.md) and
[current audit](../../docs/reviews/2026-10-21/workflow-audit/REVIEW.md).

The primary GUI agent route is:

GUI -> SMELTER admission/controller -> confined OpenCode -> local Ollama -> Qwen.
OpenCode receives selected skill snapshots as reference instructions and calls
approved host capabilities through its `smelter` stdio MCP connection. Direct
Ollama chat remains an explicitly selectable alternative. A failed OpenCode
check never silently switches engines or starts an unrestricted host agent.

## Prerequisites and readiness

Install the optional pinned MCP SDK into the dashboard Python environment:

```text
python -m pip install -r tools/dashboard/requirements-mcp.txt
```

The production adapter requires the locally installed Docker engine and an
explicit immutable OpenCode image ID in Settings. The image must provide
OpenCode 1.19.3 and Node. The existing Dockerfile is an operator-build example;
SMELTER never builds or pulls an image during a task or connection check.
Use a reviewed immutable base digest for production image builds.

In Settings > Task access select **Check managed OpenCode**. This creates a
short-lived owned inspection container and verifies health, exact version,
working directory, API permission schema and the configured local model.
It does not submit a model prompt or perform host tool actions. Inspection
containers are removed afterwards. Readiness establishes configuration,
not successful inference. The provider catalogue has a dedicated 8 MiB cap;
other API responses retain a 4 MiB cap.

## Run a task

1. Select/create a titled conversation and select **OpenCode - skills + approved
   tools** in the composer.
2. Select ready/enabled skills in the Skills manager, or use automatic selection.
   New/changed manifests require review and dashboard restart as before.
3. In Task access select the desired subset of registered location permissions
   and built-in tools for the next Send. An approval cannot expand the registered
   policy. OpenCode host tools always use the built-in MCP transport.
4. Check the managed runtime and approve this one OpenCode session.
5. Send the request and inspect actual controller receipts and file activity.

Skill selections and exact loaded instruction hashes are recorded in execution
metadata. Skill text is lower-trust reference data and grants no tools. The same
selection resolver is used by direct chat and OpenCode. Images are not forwarded;
explicitly approved saved GLBs can be inspected as metadata through the existing
tool. No visual interpretation of GLB bytes is implied.

## Execution boundary

The container has no network, host credentials or Docker socket. Its code
snapshot stays read-only. Readiness and every managed task snapshot the current
original checkout; a plain task no longer depends on an existing V2. Live coding
or frontend destination reads go through the approved MCP tools. Native source
reads are scoped to README.md, tools/
and skills/ with registered exclusions. Native edits, shell commands, subagents,
external directories and unapproved MCP tools remain denied. Only exact
`smelter_<tool>` permissions are admitted for the selected built-in descriptors.

A bounded Node stdio proxy inside the container passes MCP calls through a tmpfs
queue. The host relay uses the existing ToolSession -> built-in Python MCP server
path, with frozen location policy, grants, skill fingerprints, call budgets,
write deduplication and audits. Normal host operations have a 120-second bound
and 135-second proxy wait. Frontend validation has a fixed 420-second host bound
and 435-second proxy wait; the OpenCode MCP RPC envelope is 450 seconds. Active
cleanup wait follows the admitted operation deadline. CI delays the real tool call
by 12 seconds and verifies OpenCode acknowledges its completed result, guarding
against a short RPC timeout silently losing the tool response.
Preview launch remains owned by the dashboard;
it is not launched by the short-lived MCP server. Skills do not need individual
connectors. A capability needs a real registered backend implementation.

The frontend workspace grant still permits CSS-only destination changes, listed
reads, fixed sandbox validation and preview launch. It does not grant generic
multi-file editing under that frontend permission. The separate coding permission now provides [new code copies, hash-checked proposals/apply and fixed test/review](../../docs/ECC_CODING_WORKSPACE.md) through MCP. The snapshot does not refresh after host edits; the agent
must use read_frontend_file to inspect current destination content.

OpenCode-reported native activity is labelled as reported activity. Controller
MCP receipts establish actual built-in results and saved bytes. Model narrative
is not fact-checked. Completed receipts survive model-follow-up failures.
Cancellation blocks subsequent bridge calls; an admitted fixed operation can
finish within its own bound. Unconfirmed container cleanup is reported.

Arbitrary external MCP servers remain blocked. A host server discovered through
the MCP SDK is not automatically confined by SMELTER location flags.

## Smoke tests

Contract regressions, including real Python MCP writes and denials:

```text
python -m unittest discover -s tools/dashboard -p 'test_agent_bridge.py'
```

Full production transport with real OpenCode/MCP and a synthetic Ollama fixture:

```text
python tools/analysis/smoke_agent_bridge.py --image sha256:YOUR_EXISTING_IMAGE_ID
```

This uses disposable state and requires fixture port 11434 to be free. It fails
if occupied; no existing Ollama service is stopped. It validates selected skill
instructions, actual saved bytes/hash, controller/MCP audits, chat persistence,
unapproved-write denial and container cleanup. No Qwen inference occurs.

On the rig, an explicit live Qwen smoke uses the existing Ollama service:

```text
python tools/analysis/smoke_agent_bridge.py --image sha256:YOUR_EXISTING_IMAGE_ID --live
```

An explicit `--process-fixture --opencode /absolute/path/to/opencode` alternative
runs real OpenCode and MCP in disposable local process state with synthetic
model responses. This is a test harness, not a production host fallback; it does
not establish Docker confinement or Qwen quality. It needs free ports 4096 and
11434 and never stops existing services.

The legacy incoming engine ID opencode_readonly remains accepted for inspection
clients. New GUI tasks use opencode and forward selected skills and grants.
The production adapter does not connect to a manually started host OpenCode
server. Its HTTP Client remains available for injected tests only.

## ECC coding workflow

The optional coding grant exposes prepare/list/read/propose/apply/test/review MCP tools for a new registered V2/coding/UUID copy. It never grants native shell or edits to the original. Code cards carry actual proposed/saved text. The fixed Python/Node test profile records RED/GREEN/ERROR with counts, exact tree/image hashes, retained logs and owned cleanup; later edits invalidate current GREEN. Coverage, Git checkpoints and ECC plugin hooks/delegation/memory remain unavailable. The coding test process is bounded at 70 seconds (60-second inner guard), leaving headroom inside the 120-second host MCP / 135-second proxy operation and 450-second RPC envelope.
