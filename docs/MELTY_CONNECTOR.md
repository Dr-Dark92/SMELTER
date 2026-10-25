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
connection. **Check Melty connection** performs the explicit read-only live
probe. **Allow Melty read-only account/game lookup** grants those operations for
the next task (or retained sends when Keep permissions is selected). A present
kit or signed-in UI alone is not proof of the complete workflow.

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
