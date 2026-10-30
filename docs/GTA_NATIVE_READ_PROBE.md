# GTA native read probe — current status 29 October 2026

**The native-read gate passed live.** The staged probe ran under RPH
1.132.1428.17748 in GTA Enhanced 1.0.1158.16. A fresh operator revalidation now
also checks the deployed plugin hash and the exact report path in RPH's log;
it returns `native_reads_verified` with no failed gates. See
[the live gate record](../diagnostics/NATIVE_READ_GATE_20261029.json) and the
latest [Codex continuation](handovers/CODEX_CONTINUATION_20261029.md).

The Lua-host probe is installed but has not run in-game. The game is currently
closed. The six native gameplay callbacks, controlled cougar demo and Raptor
assets remain outstanding. Follow CURRENT_HANDOVER before changing any game
files; the original preparation notes below describe the 28 October checkpoint.

## Historical preparation — 28 October

The next runtime experiment is a **read-only diagnostic**, not a creature mod.
It is compiled and staged outside the game directory. No runtime loader has
been installed or executed, and no in-game result is claimed.

## Why this route

The installed `GTA5_Enhanced.exe` is **1.0.1158.16**, SHA-256
`b48e80f5fc899eb89e5dcc9f3b68e9551cc8dcfac78b2a940b207e569e9987ea`.
The [Script Hook V author page](https://www.dev-c.com/gtav/scripthookv/)
still lists Enhanced **1158.13**. That blocks the existing SHV route.

The RPH authors' [Enhanced release](https://www.lcpdfr.com/downloads/gta5mods/g17media/52970-lspd-first-response-enhanced-preview/)
states that its 17 September 2026 update includes RPH support for **1158.16**.
This author declaration justifies a controlled probe; it does not establish
local compatibility. The development SDK **1.124.0** is an older, separate
[author-owned NuGet package](https://www.nuget.org/packages/RagePluginHook/1.124.0),
not the Enhanced runtime. Source/API compatibility must still be tested with
the selected runtime. The SDK and RPH are never bundled with our output.

Direct backend retrieval of the author runtime encountered a redirect loop;
no runtime archive was obtained. Use the author distribution when preparing a
future supervised run. Do not substitute an SDK DLL for the actual runtime,
select a Legacy build, or install the full LSPDFR gameplay mod as a supposed
requirement of this diagnostic. Record the selected runtime files/version/hash
before deployment. No security-setting changes are part of this preparation.

## Source and ownership

These diagnostic sources are **operator-authored**, independent of Qwen's
completed Lua gameplay work:

| File | Responsibility |
| --- | --- |
| `mods/gta-ark/common/managed/RuntimeProbeHarness.cs` | Generic executable gates, bounded capture loop and JSON report; no engine API |
| `mods/gta-ark/gta/rph/GtaProbeProfile.cs` | Exact GTA executable identity, four samples, 250 ms gaps |
| `mods/gta-ark/gta/rph/ReadOnlyProbe.cs` | RPH entry, network status, player entity reads and game-fiber sleep |
| `mods/gta-ark/managed.json` | Exact three-source `SmelterNativeProbe` target |

The RPH callback reads `Game.LocalPlayer.Character`, `IsValid()`, `Handle`,
`IsHuman`, `IsDead` and `Position`. Network status uses
`NativeFunction.Natives.NETWORK_IS_SESSION_ACTIVE<bool>()`; the
[native signature](https://github.com/citizenfx/natives/blob/master/NETWORK/NetworkIsSessionActive.md)
is a no-argument boolean query. No spawn, movement, combat, task clearing,
memory patching or asset loading is requested by this plugin.

Before callbacks, the harness checks process executable name, file version and
SHA-256, then hashes the loaded plugin. Before **every** player sample it checks
network-session status. An active session or any exception stops capture; there
is no silent success or simulation fallback. Nonfinite coordinates, missing or
invalid entities and scheduler failures retain an explicit failure/partial report.

Reports go only to:

```text
%LOCALAPPDATA%\SMELTER\runtime-probes\gta-rph-read-probe\<run-id>\probe.json
```

The real entry has no output-path override. A separate internal overload lets
the reviewed fake-callback test executable use an isolated temporary directory.
The probe lasts roughly 750 ms plus executable hashing and API time; it has no
endless tick loop. The runtime itself is a separate, untested component.

## Build and offline proof

```powershell
python tools/setup/install_managed_sdk.py --sdk rph
python tools/setup/build_managed_mod.py --workspace-id 897b9243-fd7e-42f4-a46a-d1b814a33a81 --mod gta-ark --target SmelterNativeProbe
python -m unittest discover -s tools/setup -p test_runtime_probe.py -v
```

The SDK installer verifies archive/member hashes; the compiler uses fixed C#5,
x64 library options and framework references, with no MSBuild/custom switches,
and never runs its output. It is operator-only, outside the model's confined
native-build tool. The existing Windows Framework compiler/runtime is reused;
no new system compiler or Python package was installed.

`test_runtime_probe.py` builds and runs **only** a reviewed fixture with fake
callbacks and no RPH reference. Seven test methods cover success, every identity
field, active/unknown/changing network state, malformed samples/capture errors,
partial scheduler failure and profile/path bounds. These are instrumentation
tests, not GTA native evidence. The actual plugin is compile-only validated.

Current source/build hashes, regression receipts and the private staged package
location are in [the probe checkpoint](../diagnostics/NATIVE_READ_PROBE_20261028.json).
The staged package contains only our DLL plus instructions/checksums; it is not
installed in the game. Source reproducibility should be checked by hash; the
older Framework compiler may produce a different binary hash on a rebuild.

## First supervised live run

1. When the creator is ready to use the game, inspect the author-distributed
   Enhanced RPH runtime, record its hashes and confirm the executable still
   matches the pinned 1158.16 identity. Keep existing game files/backups intact.
2. Prepare the runtime using its own documented installation procedure. Copy
   only our staged `Plugins/SmelterNativeProbe.dll` to the selected plugin path.
   Do not copy the cached SDK or auto-load unrelated gameplay plugins.
3. Enter GTA **Story Mode** and use that runtime's documented plugin loader to
   load only this probe once. No multiplayer run or game launch is automated by
   this task. The probe itself refuses an active/unknown network session.
4. Retain RPH's loading log plus `probe.json`; compare the running executable,
   plugin hash and runtime assembly/version to the selected files. A report
   alone is self-reported data, not authenticated proof of a live session.
5. A read milestone requires `stage="native_reads_observed"`, four valid finite
   samples, four network checks, `native_reads_completed=true`, and matching
   executable/plugin hashes. Otherwise investigate the preserved error; never
   downgrade identity checks or replace failures with simulated values.

### Tooling for the run (operator-only, read-only)

Before deployment, inventory exactly what was downloaded. Members are hashed in
place, never extracted, and nothing is executed:

```powershell
python tools/setup/inspect_loader_runtime.py <downloaded-folder-or-zip> --label rph-enhanced
```

To deploy, extract the archive's top-level files into a separate folder, then
plan the copy. Neither step touches the game folder:

```powershell
python tools/setup/stage_native_read_probe.py extract --archive <author-zip>
python tools/setup/stage_native_read_probe.py plan --runtime-dir <extracted-runtime-folder>
python tools/setup/stage_native_read_probe.py apply --plan .smelter\native-read-gate\plans\<id>.json
python tools/setup/stage_native_read_probe.py remove --install .smelter\native-read-gate\installs\<id>.json
```

RPH Enhanced ships only inside the LSPDFR download. Its readme says to put
everything into the game folder except the `SDK` and `Licenses` folders, so
`plan` selects every top-level file (RAGEPluginHook.exe and its dependencies)
plus our staged probe. Everything in a subfolder is listed as excluded, so
LSPDFR's `plugins/` and `lspdfr/` stay out unless named with `--file` after
review. `apply` refuses any existing
target, re-hashes the executable and each source, and writes its install
manifest before copying. `remove` deletes only files whose bytes still match that
manifest and keeps anything the user changed since.

After the run, judge the report against the reviewed profile
`mods/gta-ark/gta/rph/read_probe_expectations.json`, using the loader's own log
from the game folder:

```powershell
python tools/setup/verify_runtime_probe.py --profile mods/gta-ark/gta/rph/read_probe_expectations.json --latest --loader-log "<game folder>\RagePluginHook.log"
```

It checks every step 5 criterion:
- stage and scope;
- four valid, finite, time-ordered samples and four network checks;
- no error, no claimed gameplay, no mutating calls;
- the report folder matches its run ID;
- the reported executable name, version and SHA-256, plus the staged plugin hash.

It also re-hashes the executable **on disk** and requires the log to mention the
plugin, with no exception on those lines. The receipt in
`.smelter/runtime-probe-verdicts/` records the hashes of the report, log, profile
and executable. Exit code 0 means `native_reads_verified`; any other result lists
every failed gate. A pass is still self-reported plugin data, not authenticated
proof of a live session. Re-check after any game update: the pinned executable
hash will reject a patched build.

Even a successful live read report retains `game_runtime_verified=false` and
`probe_mutating_calls=0`. It establishes only identity/player native reads.
The real Lua controller host/transport, six-capability provider and controlled
cougar spawn/move/attack/stop remain separate gates. Raptor mesh/rig/animation,
ARK integration, taming, shops and riding follow those gates.

Later on 28 October, the [generic managed Lua host](MANAGED_LUA_HOST.md) passed
all 128 unchanged frozen checks under Lua 5.4, plus a real-controller/C# fake
provider scenario. That is offline bridge evidence, not an in-game Lua host.
The manifest now adds a second `SmelterLuaHost` target; the existing probe's
three source files and staged DLL are unchanged. The earlier probe checkpoint's
manifest hash is historical. See the current
[managed host checkpoint](../diagnostics/MANAGED_LUA_HOST_20261028.json).
