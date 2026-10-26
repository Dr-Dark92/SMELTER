# Melty host MCP connector

The intended route is OpenCode → SMELTER MCP gateway → host-owned Melty connector.
The OpenCode container keeps its no-network boundary. Authentication belongs to
the host connector, and only selected tools/results should enter model context.

## Lua validation hardening

The host Lua profile now compiles all Lua sources in tested mods before running
their test programs. Deleting a failing import test can no longer hide malformed
unimported modules. Source syntax failures return ERROR; receipts include syntax
diagnostics and a runner SHA-256. Workspace review marks earlier Lua receipts
stale. Behavioral coverage remains unmeasured and real module tests are still
required. The actual current Raptor workspace returns four syntax errors across
12 files, with zero behavioral tests run; its preceding basic-only GREEN did not
establish controller readiness. See
[review, receipts and regression results](../diagnostics/RAPTOR_PROGRESS_REVIEW_20261026.md).

The idle native `smelter` registration was refreshed, all MCP servers remain
connected, and the idle dashboard was gracefully reloaded. No gameplay source
was changed, model prompt submitted or package/image installed. Context/output
remain 131,072/8,192.

## Validation workflow acceptance

The creator's next task passed the full native Melty/Qwen/SMELTER validation
cycle: real `mods` and `lua` test calls, a real `gta-ark` native build and a
visible final summary. The mods receipt reports 14 run, one skip and zero
failures/errors; both Lua scripts pass. All three native targets compile, with
four artifact sizes/SHA-256 values independently checked. Final prompt including
cache: 95,573 tokens, below 131,072; visible output: 1,020 tokens. All MCP servers
remain connected. Evidence: `.smelter/native-qwen-validation-acceptance.json`.
The C++ executable was compiled, not run; its writer/sample check remains skipped.
This does not establish source-editing capability or in-game compatibility.
Codex submitted no model prompt and preserved the existing chat.

## Native Qwen final-response workaround

The creator's follow-up subsequently passed basic visible-answer acceptance:
331 output tokens, no reasoning part, 91,990 input tokens and no truncation.
All three connectors remain connected. This was a summary of prior reads, not
a new test/build or proof of autonomous mod implementation. Receipt:
`.smelter/native-qwen-visible-answer-acceptance.json`. The summary has two source
inaccuracies: GAL1 is a 64-byte file record, and the no-SHV skeleton can load
inertly through an ASI loader. Neither game runtime is verified. The requested
dinosaur gameplay is still separate from this camera-link prototype.

A subsequent creator turn successfully used Melty search/game lookup and read
the existing SMELTER workspace, runtime requirements and ARK Lua source. It then
ended in a reasoning-only completion with no visible final answer. The 91,997
token prompt remained within 128K. Native tool work now selects direct answers
through `reasoningEffort=none`, with an explicit thinking variant retained.
All three MCP connections are restored, the chat is preserved and 128K/8K are
unchanged. The full 123-test setup suite and a zero-inference render-only check
pass. Basic visible-answer acceptance later passed as recorded above; broader
task completion remains unverified, and this does not prove a parser fix.
See [configuration, cache activation and evidence](NATIVE_QWEN_TOOL_MODE.md).

## First retry after the catalog repair

The creator's actual Melty retry processed about 75K tokens without overflow,
confirming the catalog repair while retaining 128K/8K. It then stopped after a
PowerShell syntax error (`&&` is unsupported by Windows PowerShell 5.1) and a
successful folder existence check. OpenCode recorded a reasoning-only completed
step with no visible answer, not an unreported successful build. The app resent
its full 28,509-character setup template in the same chat. Evidence:
`.smelter/melty-retry-20261026T093007.json`.

The SMELTER initialization instructions now reinforce exact task continuation,
workspace reuse, visible results/blockers and conditional PowerShell 5.1 shell
guidance. Three initialization/scope/real-stdio regressions pass; the idle
`smelter` registration was refreshed, with all MCP servers connected. No model
prompt, model option change or chat restart was sent. Guidance effectiveness
still needs a creator-run turn; no automatic empty-answer recovery is claimed.

## Native REA prompt overflow repair (26 October 2026)

See [REA context gateway](REA_CONTEXT_GATEWAY.md). Actual Ollama logs showed
225K–227K-token prompts exceeding the selected 128K ceiling and being truncated.
REA's 207 upfront input schemas/descriptions occupied 835,332 characters. The
new gateway exposes three small tools (1,084 measured characters) and retrieves
the original REA schemas only on demand. It retains the original command and
Ghidra environment. The native profile helper supports `--compact-rea` with
preview, backup and idempotent apply. The idle native `rea` connection was
refreshed and all three MCP servers report connected. No new model prompt was
sent by the repair. 128K context and 8K output remain unchanged. The next creator
turn must establish model-level acceptance; connection success is not a completed mod.

## Native Melty repair: Windows database path (26 October)

The creator's real Melty task selected the local 128K Qwen model, but its
`smelter` MCP server failed at startup with `MCP error -32000: Connection closed`.
Qwen then produced generic replies without SMELTER's tools. Repeated prompts did
not repair that connection. A direct Python stdio probe from Codex had succeeded,
so that probe alone did not establish the Melty app's connection.

The child-process diagnostic exposed `Database is not ready: database_missing`.
Windows had redirected Codex's `%LOCALAPPDATA%/SMELTER/data/smelter.sqlite3` to its
package's `LocalCache/Local/SMELTER/data` directory. The saved database marker
used the original alias. Codex could read it; the native Melty child could not.
`Path.resolve(strict=True)` in the creating environment identified the physical
existing file. Updating the pointer to that same file restored native startup.

`select_database` now stores the canonical created file path. For an older
marker, use the maintenance helper from an environment that can see the database:

```powershell
python tools/setup/canonicalize_database.py
python tools/setup/canonicalize_database.py --apply
```

Preview writes nothing. Apply requires idle GUI tasks, verifies the same existing
file and SQLite integrity, and saves both the original marker and an online
SQLite backup before an atomic pointer update. The helper never creates a
replacement for a missing database, moves data or changes native permissions.
It refuses stale marker changes and is idempotent once canonicalized. The fix
uses the standard library; no new dependency was installed.

Local backup: `.smelter/database-pointer-backups/20261026T080329-e2e19ac2`.
Repair receipt: `.smelter/melty-database-pointer-fix.json`. Temporary diagnostics
remain private under `.smelter`; the native registration was restored to the
original `mcp_server.py` command. The global OpenCode profile was not replaced.

The existing Melty/OpenCode instance now reports `smelter: connected` after
re-registering only that server through the local API. No app restart, model
prompt, game launch, chat deletion or credential change was needed. A fresh
exact-profile stdio check lists **19 tools** and successfully calls project
memory search and a fresh upstream HTTPS fetch. The GUI reads the same database
and three durable notes. Native Qwen remains **131,072 context / 8,192 output**.
Evidence: `.smelter/melty-mcp-fixed-verification.json` and
`.smelter/melty-mcp-reconnect.json`.

Regression: **617 dashboard tests, OK (nine skipped)** and **119 setup tests,
OK**. These include canonical new selections, read-only preview, an intact
SQLite/marker backup, retained chat contents, refusal of missing databases,
idle-task enforcement and repeated repair without further changes. Logs:
`.smelter/melty-mcp-dashboard-tests.log` / `melty-mcp-setup-tests.log`.

This initial check verified connection recovery and direct tool operations.
The creator's subsequent model-driven calls are recorded below; no fresh Qwen
inference was submitted by the repair. Native tasks remain outside the
dashboard's chat history and confinement, as described below.

### Real Melty acceptance and workspace context

The creator's subsequent Qwen turn **did call SMELTER through Melty**:
`smelter_project_memory` returned the GTA–ARK note and checkpoint, and
`smelter_inventory_directory` inspected the approved ARK installation. Both
completed with the native Ollama model `qwen3.5:35b-a3b-128k`. Evidence:
`.smelter/melty-e2e-verified.json`, with exact native message-part IDs.
This supersedes the pending-tool-call statement above; building/running the mod
remains unverified.

That turn then searched Melty's separate project folder for `mods/gta-ark` and
incorrectly treated absent relative paths there as evidence about SMELTER's
existing prototype. It also used the game inventory scope to investigate a
source-directory question. These are separate scopes, not another disconnect.

The MCP initialization response now supplies bounded, grant-aware instructions:
the calling client's working directory is independent of the SMELTER checkout;
memory source paths refer to SMELTER; game inventory is the approved game tree;
and source inspection uses `prepare_coding_workspace` once followed by
`list_coding_files`/`read_coding_file` with the returned ID. No permissions or
tool names were added. Coding-file restrictions, including `docs/` and private
`.smelter/` exclusions, remain explicit. OpenCode receives these as MCP server
instructions on connection.

The native server was reconnected while idle, keeping the creator's chat and
model settings. A real stdio regression starts in an empty Melty-like directory,
receives the instructions, prepares an isolated copy of an existing fixture mod
and reads its README without creating files in the client directory or editing
the original source. No additional model prompt was sent by Codex. The creator
can continue in the same Melty chat.

The final dashboard regression is **620 tests, OK (nine skipped)** in
`.smelter/mcp-workspace-context-tests.log`. The three new workspace-context tests
include actual MCP initialization and source reading. The latest setup suite
remains 119 OK from the database-pointer repair; no setup code changed here.

## Current implementation

`tools/dashboard/melty_connection.py` connects to the fixed HTTPS MCP endpoint
`https://melty.gg/api/mcp`, verified on 25 October 2026 from Melty's existing
integration metadata and an actual authenticated initialize/list-tools/account
check. The negotiated protocol was `2025-06-18`. The gateway allowlists only
`whoami`, `search_games` and `game_info`; it provides no uploads, game launches,
listing changes or publishing.

Local status distinguishes a configured credential from an authenticated live
connection. The GUI runs the read-only live probe (**Check Melty connection**)
automatically when it loads and shows the result under Tool permissions.
**Allow Melty read-only account/game lookup** is on by default and remembered in
the browser: it is not cleared after each Send, and unticking it keeps it off
until it is ticked again. File, folder and other tool grants still apply to one
Send. The server still requires the `melty_read` grant on every task, so an
unticked box means no Melty calls. Only the three read-only tools are covered.
A present kit or signed-in UI alone is not proof of the complete workflow.

Live check on 25 October 2026: the GUI auto-probe reported connected with all
three tools. A real OpenCode/Qwen 35B task then called `search_games` through the
built-in MCP gateway (57.1 s), and its answer matched the raw Melty result.

Credentials are host-held. Set `SMELTER_MELTY_TOKEN`, or explicitly create
`.smelter/melty-connection.json` containing only
`{"schema_version":1,"credential_source":"existing-codex-melty"}` to reference
the existing Melty-created `melty` entry in `~/.codex/config.toml`. The reference
is used only if its URL exactly matches the fixed endpoint and it is enabled.
No credential is copied to the checkout, model prompt, audit result or container;
the host reads it for HTTPS requests to the same service. This reference was
selected on this machine after the operator confirmed an existing Melty sign-in.

The client refuses arbitrary endpoints and HTTP redirects, ignores proxy
environment variables, caps streamed response bytes, restricts model arguments,
and reports sanitized errors. Remote text/field notes are untrusted data, not
instructions. Generic arbitrary external MCP execution remains blocked.

## Melty's desktop app as the front end (host OpenCode)

Melty's desktop app runs the user's host OpenCode CLI (npm global, 1.19.3) and
reads `~/.config/opencode/opencode.json`. Its model dropdown is that OpenCode's
model list. On 25 October 2026 that config was extended, with the operator's
approval, so Melty can use the local model and SMELTER's tools:

| Entry | Value |
| --- | --- |
| Provider `ollama` | `@ai-sdk/openai-compatible`, `http://127.0.0.1:11434/v1`; model `qwen3.5:35b-a3b-128k`, limits 131,072 context / 8,192 output (context retained; output raised after whole-file patch verification) |
| Ollama tag `qwen3.5:35b-a3b-128k` | `FROM qwen3.5:35b-a3b` + `PARAMETER num_ctx 131072`; shares the existing weights. Needed because the OpenAI-compatible endpoint cannot set context per request. (The first setup used a 16K tag; it was replaced and removed.) |
| MCP server `smelter` | Dashboard Python running `tools/dashboard/mcp_server.py --root <checkout>` with persistent `melty_read`, `coding_workspace`, `native_build` grants: read-only Melty lookup plus the isolated coding, CLI catalog, fixed tests and confined Windows cross-build tools |
| Backups | `~/.config/opencode/opencode.json.bak-20261025-smelter` (before any SMELTER entries) and `.bak-20261025-16k` (16K version); `.bak-smelter-cli-20261025T152015491910Z` before the CLI/skill/output update |

Verified: `opencode models ollama` lists the model; `opencode mcp list` shows
`smelter` connected; a headless `opencode run` on the local model called
`smelter_melty_search_games` and returned Melty's real results (73 s). After
"Restart OpenCode" in Melty, the operator confirmed that "Qwen3.5 35B-A3B (local,
16K)" appeared in Melty's model dropdown; the entry is now "Qwen3.5 35B-A3B
(local, 128K)" (restart OpenCode in Melty to refresh). A full Melty builder task on the local
model has not been run yet. The model
did not follow a "reply with only the slug" instruction, which is a quality
observation, not a connection failure.

Context sizing (measured 25 October 2026, RTX 5080 16 GB, 64 GB RAM, Ollama
0.40.7, `qwen3.5:35b-a3b`, native maximum 262,144). Each run filled about 70% of
the window with text, then asked a one-sentence question. All runs answered
correctly:

| Context | Memory | GPU share | Prompt tok/s | Generation tok/s |
| --- | --- | --- | --- | --- |
| 16K | 20.7 GiB | 62% | 1,557 | 52.4 |
| 32K | 21.0 GiB | 61% | 1,539 | 51.3 |
| 64K | 21.7 GiB | 60% | 1,469 | 49.9 |
| 128K | 23.1 GiB | 56% | 1,562 | 45.8 |
| 256K | 25.8 GiB | 50% | 1,258 | 34.8 |

128K was chosen: eight times the context for about 13% slower generation. 256K
costs a third of generation speed and over two minutes to read a full prompt.
Repeated filler text is a weak test of long-context reasoning. Recall quality on
real long tasks is not established. Two clean `opencode run` trials on the 128K
tag returned correct Melty data in 103 s and 138 s. One earlier run, started by
mistake inside the repo, drifted into unrelated searches (267 s). The model's
default temperature is 1, so expect run-to-run variation.

This route is outside SMELTER's confinement. Melty's OpenCode runs directly on
the host with network, shell and file editing. Grants are fixed in the config,
not chosen per message. These tasks do not appear in SMELTER's chat history. The
same host config already contained an unrestricted `rea` MCP server, which this
change did not add or alter. Add more SMELTER tools to the `smelter` grant only
deliberately, because there is no per-message approval on this route.

## Verified dependency metadata

The official public manifest at
[Melty's kit manifest](https://melty.gg/api/kit/modding-kit/manifest), checked on
24 October 2026, reported:

| Field | Value |
| --- | --- |
| Name | Melty's modding kit |
| Version | `2026.10.18-739f3496` |
| Content identity | `739f3496657b87ef8247b867affb289e1874e50580bd3db4e76cbcf23dab26e4` |
| Files | 555 |
| Declared bytes | 23,282,319 |
| Official archive | `https://melty.gg/api/kit/modding-kit` |
| SMELTER install location | `<checkout>/.smelter/tooling/melty` |
| Compressed archive SHA-256 | `907ea7f3ed2d4c3443c9f3190f5070db0e77a9c910c50eeaaedf6cd1694f9935` |

The content identity and compressed archive SHA-256 are distinct values. The
archive digest above was measured independently from the official download.
Its publishing skill refers to Melty MCP tools. The endpoint/auth contract was
subsequently verified using the existing host integration, independently of the
kit itself.

Local dashboard readiness checks validate the manifest's declared pin and compare the
mod-any-game skill, publish-mod skill and `bin/um` against their local manifest
file hashes. This verifies those observations only. It does not authenticate the
entire package or execute a working game/build workflow. When a checkout root is
supplied, readiness uses the isolated SMELTER location above. The lower-level
`kit_status()` without an explicit directory still observes Melty's conventional
user location `%LOCALAPPDATA%/Melty/modding-kit` for operator diagnostics.

## Explicit isolated kit installation

```powershell
python tools/setup/install_melty_kit.py
python tools/setup/install_melty_kit.py --check
```

The installer downloads only the fixed official HTTPS archive, allows its one
official signed redirect to the exact pinned archive path on Melty's observed
Supabase storage host, and refuses all other hosts, paths and redirect chains. It
caps compressed/expanded sizes and member counts, verifies the pinned archive
SHA-256, then validates all 555 declared file hashes. Tar links, special files,
absolute/traversal paths, Windows reserved names, duplicate paths and undeclared
content are rejected. The official archive has two additional known metadata
files: `MELTY-KIT.json` and `MELTY.md`.

Extraction occurs in a new staging directory under `.smelter/tooling`, followed by
a rename into the final directory. Existing divergent/unmanaged installs are
preserved and cause an error. Repeating an unchanged verified installation is
idempotent. The local receipt records the archive digest, metadata hashes and the
fact that kit code was not executed. No global Melty directory, credentials,
OpenCode configuration or game files are changed. `--archive PATH` can consume an
already downloaded archive only when it matches the same fixed SHA-256.

The installer uses Python's standard library and performs no package-manager
dependency installation. Installing kit files does not register its instructions
in the model's skill catalog or grant execution of `bin/um`.

## Next release-workflow adapters

Artifact upload, game installation testing and publishing require separately
registered adapters, explicit approval, real builds and gameplay evidence. The
current lookup grant authorizes none of those operations. The native OpenCode
provider sign-in and this host MCP credential are separate states, even when
both are presented inside Melty's UI.

Melty publishes mods and mashups of existing games. Game integration, owned game
versions, a playable build, actual gameplay evidence and release-test outcomes
remain distinct prerequisites; a kit install or a successful API call proves
none of those by itself. See [Melty](https://melty.gg/).

## Validation

```powershell
python -m unittest discover -s tools/dashboard -p test_melty_connection.py
python -m unittest discover -s tools/dashboard -p test_melty_gateway.py
python -m unittest discover -s tools/setup -p test_install_melty_kit.py
```

Unit tests use disposable files and mocked HTTP/MCP responses. They never connect
to an account, execute kit code or change a listing. A separate live host probe
confirmed authentication and the three advertised tools using the existing
sign-in; it performed no mod mutation or publication.

## CLI modding profile update (25 October, 19:25)

`tools/setup/configure_melty_cli.py` previews or applies the existing native
profile update, preserving other providers, credentials, permissions and REA.
It was applied after tests and a backup: two skills (`game-modding`,
`mod-validation`) are now in `~/.config/opencode/skills/`; fixed coding-copy and
native-build MCP grants are enabled. These grants persist across native sessions;
this does not add game installation, launch, publishing or artifact execution.
The native host OpenCode route retains its existing host access. Its build tool
itself uses the confined MinGW-w64 image without a host compiler fallback.

Context remains **131,072 (128K)**. Output is a separate **8,192** token ceiling.
The derived-model input is `tools/setup/Modelfile.qwen35b-128k`; reproduce the tag
with `ollama create qwen3.5:35b-a3b-128k -f tools/setup/Modelfile.qwen35b-128k`.
No model download or recreation was needed in this pass.

The real stdio MCP catalog call using this native grant set passed and returned
15 UE5/general CLI entries. A full new Melty builder/model task has not been run.
Reload Melty's OpenCode session to discover updated config and skill files.
See [review fixes](REVIEW_FIXES_20261025.md) for exact verification and next work.
