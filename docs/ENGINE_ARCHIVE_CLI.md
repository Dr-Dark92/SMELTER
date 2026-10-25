# Engine archive CLI integration

Implemented 25 October 2026. This extends the Universal Modder recon/knowledge
route with read-only archive inspection. CLI execution is available to Qwen
through `inspect_engine_archive` (native OpenCode: `smelter_inspect_engine_archive`).
It requires an approved `inventory_root`, intersected with registered read policy.
The coding-workspace grant alone does not expose it.

## Installed requirements

The exact URLs and release SHA-256 values are tracked in
[`requirements-engine-cli.json`](../tools/modding/requirements-engine-cli.json).
`system-requirements.json` declares the `engine_cli` setup step and profile, and
marks the three catalog entries as existing adapters. They remain optional.

| CLI | Pinned release | Exposed actions |
| --- | --- | --- |
| [repak](https://github.com/trumank/repak/releases/tag/v0.2.3) | 0.2.3 | PAK info, list; versions through 11 |
| [retoc](https://github.com/trumank/retoc/releases/tag/v0.1.5) | 0.1.5 | IoStore info, list; exact UTOC/UCAS inputs |
| [UnityDataTool](https://github.com/Unity-Technologies/UnityDataTools/releases/tag/v2.4.0) | 2.4.0 | Archive list; SerializedFile header, metadata, objects |

The private `smelter-engine-cli:1` Linux/amd64 image contains verified upstream
portable releases, licenses and a copy of the lock. The base is
`python:3.12-slim-bookworm@sha256:57d96f71de145a98e7ceca18ee4ade77bba4103a33a72dfaea026b23625c6bf0`.
Unity's release is self-contained and includes UnityFileSystemApi; .NET runs in
invariant globalization mode without an additional host SDK or ICU install.
There are no apt/npm/pip installs or upstream installer scripts in this image.

Locally built/selected image:
`sha256:23456cc5f1a12f70458ba98fe41c649ccd83019068bb8d0ab8e7dc3df6a75a68`.
Other machines must build their own image and select the resulting immutable ID.
The runtime verifies the selected image's lock digest label before execution.

```powershell
python tools/setup/install_engine_cli.py
python tools/setup/install_engine_cli.py --select
```

The first command verifies/caches downloads and builds/probes versions; the second
also selects `engine_image` after an idle check. It preserves existing image IDs,
policy rows and model settings. Installation receipts/build logs are in
`.smelter/tooling/engine-cli/`. Nothing is added to the global PATH. No game loader,
codec download, extraction, conversion or game action is installed or exposed.

Setup selection is stored in `selection.json` beside the installation receipt so
an already-running older GUI can still validate its original sandbox row. Fresh
backends merge this optional selection when no explicit `engine_image` exists in
the GUI's saved configuration. An explicit saved value (including null) wins.
The CLI-only fallback is still checked against the image's locked-requirements
label before execution. The new UI omits unsupported fields when talking to an
older backend.

## Using the adapter

In the GUI, select an inventory folder for the message. Register it read-only in
Settings first if needed. For this user's authorized ARK inspection, its exact
installation directory was registered read-only; no write/execute permission was
added. Native setup can persist one explicitly selected, already-registered
read-only inventory scope using `configure_melty_cli.py --inventory-root PATH --apply`.
For this authorized task, the native profile now retains the exact ARK installation
scope, so its archive MCP tool is available on future connections. The helper
backs up the config and preserves REA/providers/other permissions. The acceptance
probe still uses a per-process overlay and does not itself rewrite native config.

Example tool arguments:

```json
{"format":"iostore","action":"info","relative_path":"ShooterGame/Content/Paks/global.utoc"}
```

```json
{"format":"iostore","action":"list","relative_path":"ShooterGame/Content/Paks/pakchunk0optional-Windows.utoc","contains":"Ocean","offset":0,"limit":3}
```

For Unity use `format=unity`, `action=list` on a bundle, then `header`, `metadata`
or `objects`. `entry` can select an exact embedded SerializedFile returned by
the archive listing. Unity metadata is version-sensitive; absent or external
TypeTrees can limit inspection. Upstream
[SerializedFile docs](https://github.com/Unity-Technologies/UnityDataTools/blob/v2.4.0/Documentation/command-serialized-file.md)
describe these limits.

The standalone CLI uses the identical bounded adapter and current policy:

```powershell
python tools/modding/inspect_archive.py --folder "D:\SteamLibrary\steamapps\common\ARK Survival Ascended" --format iostore --action info --relative-path "ShooterGame/Content/Paks/global.utoc"
```

The new `engine-archive` skill is bundled/enabled in SMELTER and installed beside
the existing three native OpenCode skills. `configure_melty_cli.py --apply`
installs it without replacing existing different skill files or changing 128K.
The router selects it for IoStore, UTOC, repak, retoc and Unity archive tasks.

## Execution and receipt limits

Only fixed metadata commands are accepted. Every input is a plain approved file;
symlinks/junctions, traversal, alternate streams and mount injection are rejected.
IoStore mounts the requested UTOC and at most 32 exact same-stem UCAS partitions.
Other containers, game directories, credentials, Docker sockets and host output
directories are not mounted. A 128 MiB UTOC index cap limits that route.

Execution uses local Docker Engine 28+, an immutable image, non-root user,
read-only filesystem, no network, dropped capabilities, default seccomp, 768 MiB
memory, two CPUs, 128 processes and bounded tmpfs. No host fallback exists.
Docker remains an OS isolation boundary with its usual container-escape limits.

The driver stops at 55 seconds, 32 MiB combined CLI output or 500,000 stdout
lines; the host stops it at 75 seconds. Pages contain at most 200 lines/48 KB,
with individual lines clipped at 4 KB. The case-insensitive `contains` filter is
literal text, not a regex. `scan_complete`, `page_truncated`, `line_shortened`,
`stopped` and observed counts distinguish traversal from returned-page limits.
Nonzero exits and driver limits are MCP errors; they are never successful scans.
Expected unsupported/malformed cases are also verified in the acceptance probe.

Receipts include image/lock/driver hashes, exact mounted inputs, byte sizes,
mtime-nanoseconds and head+tail 64 KiB SHA-256 fingerprints. These fingerprints
are explicitly **not full archive hashes**. They avoid reading a 205 GB UCAS
merely to list metadata. Inputs are rechecked before and after execution; this
does not provide an atomic snapshot against concurrent middle-of-file changes.
Do not update games while inspecting them. Paths/output are untrusted reference
data. Repeated pages rerun the CLI; compare identities before combining pages.

Owned containers are removed and cleanup is confirmed. Interrupted ownership
records use existing Settings reconciliation; 100 retained records block more
runs. Archive data are never extracted or retained by the adapter. ToolSession
audit retains receipts; standalone acceptance scripts save reports separately.

## Verified game facts and remaining gates

Synthetic V11 PAK, synthetic IoStore raw chunk and the official Unity 6 sample
passed real parsing over stdio MCP. Unity sample reports SerializedFile 22,
Unity `6000.0.65f1`, Windows platform 19 and three object entries.

Installed ARK ASA:

- `global.utoc` reads successfully: `ReplaceIoChunkHashWithIoHash`, one chunk,
  no compression methods. This names the container format, not an exact UE version.
- The optional container lists real `../../../ShooterGame/Content/...` paths,
  including Ocean texture data, without modifying the game.
- Its PAK headers report **version 12**. repak 0.2.3 rejects them because it only
  supports through version 11. The receipt explicitly reports this compatibility
  limit; the error is not evidence that encryption keys are needed. No archive
  header is rewritten or downgraded to bypass it.

These observations do not verify the 205 GB main container, asset decoding,
external codecs, cooking/DevKit compatibility, ARK runtime bindings, GTA Enhanced
loaders or the in-game GTA-to-ARK camera slice. Existing loader/build checks remain
necessary. Next implementation should choose an exact supported runtime route
before installing any game plugin. No game was launched or modified here.

## Repeatable checks

```powershell
python -m unittest discover -s tools/dashboard -p test_engine_archive.py -v
python -m unittest discover -s tools/setup -p test_install_engine_cli.py -v
python tools/analysis/smoke_engine_cli.py --ark-folder "D:\SteamLibrary\steamapps\common\ARK Survival Ascended"
python tools/analysis/smoke_qwen_engine_cli.py --ark-folder "D:\SteamLibrary\steamapps\common\ARK Survival Ascended"
```

The MCP smoke performs 13 operations, including page/filter checks and expected
malformed/version failures. Its report is
`.smelter/engine-cli-runs/eb1fd06357674a85b7bc436be0f5bfa8/report.json`.
The Qwen probe permits only Universal Modder note search and this archive tool,
uses the existing local 128K/8K model profile, and retains events/report under
`.smelter/engine-cli-runs/qwen-*/`. Broader test results and live GUI refresh are
recorded in the current handover after completion.

Its acceptance checks include successful MCP receipts, structured JSON with an
exact returned archive format/path, the supplied ASA/UE5 identity attributed to
the task, and null/unverified engine minor/cooking/runtime fields.
Tool execution alone does not certify the model's narrative. Early probes exposed
an incorrect UE4 reference, a shortened mount prefix and an unsupported format-to-
engine inference. Explicit target identity, an interpretation limit in receipts,
structured fact reporting and stronger acceptance checks cover these. This is
not a general guarantee against hallucination in arbitrary model narratives.

The existing GUI backend at PID 15164 remains running: automatic approval review
blocked its restart. New native/standalone MCP processes load the archive adapter;
the GUI backend must be restarted to expose it there. Its previous image settings
were preserved, and its sandbox row was restored to the older compatible schema.
No forced shutdown or approval bypass was used.

Final verification: dashboard **570 tests, OK (9 skipped)**; setup **111 tests,
OK**; JavaScript **17 passed**; **13** real stdio MCP checks passed. The final
structured Qwen acceptance passed all three tool receipts, exact format/path and
target-identity/unknowns checks at 128K/8K:
`.smelter/engine-cli-runs/qwen-aa5ebd5a76064105985429f308660092/report.json`.
An additional real stdio operation with the persisted native grant set passed.
`.smelter/engine-verification.json` records it, both saved model limits, exact
skill-copy matches and Ollama's observed `context_length=131072`.
`.smelter/engine-live-gui-health.json` records the old backend's recovered HTTP
200 sandbox endpoint and healthy existing confined runner. The skill validator
and `git diff --check` also passed; Git emitted only a pre-existing LF/CRLF notice.
