# OpenCode read-only GUI pilot

This adapter connects to an already-running OpenCode **1.19.3** server at
`http://127.0.0.1:4096`. It does not launch the CLI, install dependencies,
change global/provider settings, edit the V2 copy, or stop an unrelated server.
It uses Python's standard-library HTTP client with redirects and proxies
disabled. Existing direct Ollama chat remains the default engine.

Start the server in a dedicated PowerShell terminal:

```powershell
Set-Location C:\SMELTERV2
opencode serve --pure --hostname 127.0.0.1 --port 4096
```

Restart the main SMELTER dashboard after updating its code. Existing V2 source
can be inspected without recreating it or refreshing its CSS workspace marker.
In **Configuration > AI & Models > OpenCode**, click **Check OpenCode server**.
Connection checks are GET requests only and do not submit an AI prompt.

The adapter verifies health/version, actual directory, the live OpenAPI
session-permission schema, and connected models explicitly configured with
`options.baseURL: http://127.0.0.1:11434/v1`. It returns model IDs and readiness
without exposing provider API keys. This establishes configuration; it does
not prove that inference works until a task runs.

If no model is listed, the running server has not exposed a compatible local
provider. Do not select a cloud model as a fallback. Configure the local
provider and restart OpenCode, then check again. The older isolated provider
configuration in SMELTER is only a staged file; staging does not apply it to a
running server.

Select **OpenCode > read-only pilot** beside the chat composer, select a local
model, and approve one session. Create/select a titled chat and send:

```text
Read README.md and tools/dashboard/dashboard.py. Explain how the frontend is
assembled and identify its styling and API integration points. Cite file paths.
Do not edit files, execute commands, or delegate work.
```

Each message creates its own OpenCode session. Before submitting the prompt,
SMELTER checks the session's returned directory and exact permission rules.
Unconfirmed permissions block inference. The default is deny; source reads
are allowed only for README.md, tools/, and skills/ under V2, using relative
and absolute patterns. Editing, shell commands, subagents, network tools,
external MCP tools and external directories are denied. This is an application
permission policy, **not an operating-system sandbox**. A `worktree: /` value
does not expand the adapter's read allowlist.

The first adapter intentionally does not forward SMELTER skill selections,
images, GLBs or per-message MCP grants. Native skill/MCP bridging, editing,
permission replies, browser review and generalized file snapshot cards remain
follow-up work. No claim of complete coding-agent parity is made.

Task submission uses `prompt_async`; SMELTER polls message/tool parts for live
text and tool activity, rather than consuming SSE in this first version. It
stores the final response, OpenCode session ID and tool receipts in the
existing chat database and writes an audit under `.smelter/tool-runs/`.
OpenCode-reported tool activity and model explanations are not independent
filesystem or factual verification.

Stop requests abort only this adapter's session. Tasks have a five-minute
polling deadline. An unconfirmed abort is reported for operator follow-up;
SMELTER does not kill the OpenCode server. Refresh reconnects to the existing
SMELTER job while the dashboard process remains running. There is no durable
job recovery across a dashboard restart in this pilot.

For an authenticated OpenCode server, start the dashboard with
`SMELTER_OPENCODE_PASSWORD` (or `OPENCODE_SERVER_PASSWORD`) in its environment;
the username defaults to `opencode`, overridable with
`OPENCODE_SERVER_USERNAME`. Credentials are not placed in browser responses.

Tests cover readiness without POSTs, local-provider restrictions, policy echo
verification, cancellation, intermediate tool-call steps, audit/chat
persistence, explicit approval and HTTP request construction. Browser QA uses
a local HTTP API fixture: it is not evidence that a real Qwen/OpenCode task
has succeeded on the user's Windows machine.
