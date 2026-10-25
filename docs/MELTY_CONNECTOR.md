# Melty host MCP connector

The intended route is OpenCode → SMELTER MCP gateway → host-owned Melty connector.
The OpenCode container keeps its no-network boundary. Authentication belongs to
the host connector, and only selected tools/results should enter model context.

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
