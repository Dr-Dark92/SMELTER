# Native Qwen tool mode

The 26 October Melty retry successfully searched mashups, looked up GTA Enhanced
and ARK, reused the existing SMELTER coding copy, and read mod sources. Its final
step nevertheless returned only a reasoning part: 486 output tokens, no visible
answer and no further tool call, with `finish=stop`. Ollama's prompt was 91,997
tokens inside the unchanged 131,072 ceiling. There was no context truncation.
Evidence: `.smelter/melty-retry-20261026T101317.json`.

Shell/task-continuation guidance helped the model reach real reads, but did not
resolve the missing final answer. A prompt-guidance update is not a completion
guard. The raw generated token stream was not captured; do not claim a proven
parser defect or reinterpret its private reasoning as a user-visible answer.

## Selected workaround

The native `ollama/qwen3.5:35b-a3b-128k` model now defaults to
`options.reasoningEffort = "none"`. This selects direct answers for tool work,
matching the existing GUI policy in `chat_inference.py` when tools are active.
It changes future generation mode; it does not expose or copy private reasoning.

The model is marked reasoning-capable and retains two explicit variants:

| Variant | reasoningEffort | Purpose |
| --- | --- | --- |
| smelter-tools | none | Direct answers and tool use |
| smelter-thinking | medium | Explicit thinking mode |

These are OpenCode configuration variants. Their availability as a selector in
Melty's UI has not been verified. Both use the same installed weights and retain
131,072 context / 8,192 output tokens. Historical reasoning replay was not
enabled. The native configuration is backed up before changes; other providers,
MCP registrations, credentials, permissions and existing variants are preserved.

```powershell
python tools/setup/configure_melty_cli.py --native-tool-mode
python tools/setup/configure_melty_cli.py --native-tool-mode --apply
```

The helper previews by default, refuses conflicting named variants and is
idempotent. It installs no software. The normal configuration helper also leaves
an already selected mode in place unless the operator explicitly changes it.

## Activate in an already running native server

OpenCode 1.19.3 caches its global configuration indefinitely. A file edit and
disposal of only the project instance do not invalidate that global cache.
Do not claim the new mode is active solely because it appears in the JSON file.

For this repair the existing idle native server's supported `PATCH /global/config`
API loaded the intended model settings. Its project instance cache was refreshed
as needed, and the three saved MCP registrations were reconnected. Read back
`GET /provider` and verify the effective model's `options.reasoningEffort`,
variants and token limits, then `GET /mcp` for all expected connections. A cache
refresh can close MCP clients; restore the saved registrations before calling
the connection ready. Use the documented API of the installed version and an
idle server; do not restart the app, delete the chat or assume cache refresh
preserves unsaved runtime-only registrations.

Actual post-repair state: `rea`, `smelter`, `melty` connected; model options
`reasoningEffort=none`; 128K/8K unchanged; same chat with 37 messages before and
after. Backup: `opencode.json.bak-smelter-cli-20261026T102014457096Z` next to the
native config. Receipt: `.smelter/native-qwen-tool-mode-verification.json`.

## Verification boundary

All 123 setup tests pass, including two new backup/idempotence/variant-conflict
regressions. Log: `.smelter/native-qwen-tool-mode-setup-tests.log`. The previously
completed 627-dashboard-test run (nine skipped) predates this configuration-only
workaround; no dashboard execution code changed in this pass.

The installed Ollama `/v1/chat/completions` endpoint was checked using
`_debug_render_only=true` with a synthetic fixture. Default/medium opened a
thinking block; `none` returned an explicitly closed empty thinking block ready
for ordinary content. All three responses reported zero input/output inference
tokens. Receipt: `.smelter/native-qwen-render-only-contract.json`.

The creator's next turn returned a visible 331-token runtime-blocker summary,
with no reasoning part or tool call, at 91,990 input tokens. This passes basic
visible-answer acceptance in the configured mode. It did not rerun tests, and
it misstated GAL1 as shared memory and the inert skeleton as unable to load.
The same-turn tool/test/visible-answer loop and autonomous implementation remain
unverified. Receipt: `.smelter/native-qwen-visible-answer-acceptance.json`.
The following creator validation task then passed a complete same-turn
tool/test/build/visible-answer cycle: Python/mods 14 run with one skip and no
failures, two Lua scripts passing, and three native targets compiling to four
verified artifacts. The final response was 1,020 tokens at a 95,573-token prompt
including cache, with no reasoning part. Both test log hashes and all four
artifact hashes/sizes were independently verified. Receipt:
`.smelter/native-qwen-validation-acceptance.json`.

This accepts the requested validation workflow. Source editing and in-game
behavior remain unverified; the Windows test executable was not run and the C++
writer/sample interoperability check is still skipped. Codex sent no additional
model generation. If a later task again ends without an answer, capture
bounded response metadata at the provider boundary and distinguish upstream
reasoning-only output from a client/parser loss before another mode change.

Sources: [OpenCode 1.19.3 configuration cache](https://github.com/anomalyco/opencode/blob/v1.19.3/packages/opencode/src/config/config.ts),
[OpenCode model-option merge](https://github.com/anomalyco/opencode/blob/v1.19.3/packages/opencode/src/session/llm/request.ts),
[Ollama 0.40.11 effort mapping](https://github.com/ollama/ollama/blob/v0.40.11/openai/openai.go),
and [Qwen's mode/history guidance](https://huggingface.co/Qwen/Qwen3.5-35B-A3B).
