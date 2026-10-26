# REA context gateway for native Melty/OpenCode

The native Qwen session was forgetting explicit tasks after successful tool
calls. On 26 October 2026, Ollama logged input prompts of 225,831–227,537 tokens
against the selected 131,072-token context. Its overflow/context-shift path kept
only four leading tokens and the tail, reducing the input to 65,538 tokens.
This removed most instructions. The 65,538 value was overflow handling, not a
new configured context ceiling.

The installed native REA server advertises 207 operations. Their input schemas
and descriptions alone occupied 835,332 characters, including a 168,238-character
input schema for `compare_web_captures`. OpenCode 1.19.3 includes MCP input schemas
and descriptions in its model tools. Advertising that whole catalog consumed
the prompt before the model could work reliably.

`tools/dashboard/rea_mcp_gateway.py` replaces that upfront catalog with three
tools (1,084 schema/description characters in the measured installation):

1. `rea_search_tools`: find operations by name/task; results include pagination.
2. `rea_describe_tool`: retrieve the selected operation's exact input schema.
   Large schemas return child JSON pointers and sizes; follow these pointers
   relative to the input schema root, including `$defs` for `$ref` references.
   Responses are bounded to 24,000 schema characters. An incomplete response
   explicitly says so; it never returns a cut JSON schema as complete.
3. `rea_call_tool`: pass the discovered operation name and `arguments_json`, a
   JSON string containing its argument object. The gateway validates the object
   against the original schema, then forwards it to the existing REA backend.

This preserves access to all 207 operations, including the configured Ghidra
backend. It does not change which installed analysis providers are functional.
The original fixed command, environment, working directory, result content,
structured result and tool error flag are retained. Progress and directory roots
are forwarded. Cancellation is explicitly relayed to the backend; the pinned
Python MCP SDK alone does not relay cancellation of a local request waiter.
Upstream schema/output validation remains enabled. The gateway is a tool-catalog
adapter, not a sandbox or an additional authorization layer.

## Configure and restore

Uses the already pinned `mcp==1.30.0` and its dependencies; no package is added.
Preview and apply while the native session is idle:

```powershell
python tools/setup/configure_melty_cli.py --compact-rea
python tools/setup/configure_melty_cli.py --compact-rea --apply
```

The helper backs up the entire native config, wraps the existing `rea.command`,
preserves provider settings, environment, enabled state and timeout, and is
idempotent. It refuses per-operation `rea_<name>` permission rules because a
generic call tool would collapse those permission names. Review those rules
before adopting the gateway. Other REA clients and the managed SMELTER tool
adapter are unaffected.

Refresh only the idle native `rea` MCP registration with the updated registration
through OpenCode's `POST /mcp` API. No chat restart, new session or model prompt
is required. A file edit alone does not prove the running MCP connection changed.
To restore, use the printed backup's original REA registration and reconnect it
while idle. Preserve unrelated settings changed since the backup.

The 128K context and 8K output ceiling remain 131,072/8,192. This repair reduces
the repeated tool overhead; long chat history or large tool results still count
toward the same context budget.

## Verification and limits

The real installed backend passed discovery of all 207 operations, schema lookup
and a read-only `binary_session` call through the gateway. Local regression uses
real nested stdio servers to verify environment/cwd, root forwarding, progress,
original errors, cancellation and a subsequent call on the same connection.
Additional tests cover schema navigation, pagination, invalid argument rejection,
configuration backup/idempotence and permission preservation. Evidence is in
`.smelter/rea-compact-gateway-verification.json`.

Final regression: 627 dashboard tests, OK (nine skipped), and 121 setup tests,
OK. Logs: `.smelter/rea-gateway-dashboard-tests.log` and
`.smelter/rea-gateway-setup-tests.log`. The native `rea` registration was
refreshed while idle; all three native MCP servers report connected and the
running gateway is a direct child of the existing `opencode.exe` process.

The creator's next Melty prompt confirmed approximately 75K input tokens without
truncation. It still stopped after a PowerShell error and a successful directory
existence check, producing no visible final answer. Connection and context-budget
acceptance therefore passed; successful model task completion remains unverified.
MCP guidance now reinforces task continuation and the native shell syntax, with
three scope/stdio regressions passing. This is advisory guidance; it does not
implement an automatic retry of a reasoning-only completion. Evidence:
`.smelter/melty-retry-20261026T093007.json`.
An earlier completed workspace-copy tool call is real; the model did not follow
it with the requested file read. The GTA–ARK gameplay is still unimplemented.

Upstream implementation references:
[OpenCode MCP tool conversion](https://github.com/anomalyco/opencode/blob/v1.19.3/packages/opencode/src/mcp/catalog.ts),
[Ollama 0.40.11 overflow truncation](https://github.com/ollama/ollama/blob/v0.40.11/llm/llama_server.go),
and [OpenCode MCP configuration](https://opencode.ai/docs/mcp-servers/).
Ollama installed version is 0.40.11; the source above matches that release.
