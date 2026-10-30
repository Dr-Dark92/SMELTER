# Managed Lua 5.4 host — offline bridge milestone

The same generic controller/policy/lifecycle modules now execute from a managed
host with six explicit C# callbacks. **All 128 frozen checks pass unchanged**
under the pinned Lua 5.4 binding. This closes an offline integration gap; no
RPH runtime, game-native provider or in-game scheduler is established by it.

## Selected implementation

The optional host is `mods/gta-ark/common/managed/LuaModuleHost.cs`, namespace
`Smelter.ManagedLua`, independent of RAGE, Unreal, creature IDs and game paths.
It uses [KeraLua 1.4.11](https://www.nuget.org/packages/KeraLua/1.4.11), the
[NLua project's low-level Lua binding](https://github.com/NLua/KeraLua).
NLua's CLR object translator is not installed or used. The selected package
provides `net46/KeraLua.dll` and Windows x64 `lua54.dll`. The actual fixture VM
reports **Lua 5.4**, including UTF-8 and integer-division behavior.

MoonSharp 2.0.0 was compared first. It lacked `utf8` in its standard library;
the frozen verifiers copy that library and are written for Lua 5.4. It was not
selected. The verifier was neither patched nor re-pinned for this experiment.

The NuGet archive and selected members are hash-pinned in
`tools/setup/managed-sdk-lock.json`. The cache is ignored under
`.smelter/tooling/keralua-sdk/1.4.11/`. This caches development/test files only;
it does not deploy a loader, interpreter or plugin to GTA. KeraLua is MIT;
retain its package LICENSE and [Lua's copyright/license](https://www.lua.org/license.html)
before any future runtime distribution. RPH/its SDK remain separately
non-redistributed dependencies.

## Host boundary

The constructor accepts **in-memory reviewed source strings**, keyed by explicit
module IDs. There is no module filesystem search, filename guessing, package
search path or automatic native/simulation selection. Sources are copied into
the interpreter before execution, so mutating the original C# dictionary does
not change the host. `require` admits only supplied IDs, caches table exports
and rejects missing imports, cycles and non-table exports.

Module environments have selected basic functions plus copies of math, string,
table and UTF-8 functions. They receive no `os`, `io`, `package`, `debug`,
`load`, `loadfile`, `dofile`, `_G` or `luanet`. The private host captures its
compiler and instruction hook before removing ambient root loading libraries.
Only the operator-owned host uses those private functions.

`SetCallback("host_<name>", LuaFunction)` binds an explicit, retained delegate.
The eventual engine adapter owns the native calls, handles, liveness, scheduling
and command semantics. The bridge owns no game logic. Callback implementations
must validate Lua types/arity **before** conversion: KeraLua's `ToString` can
format absent arguments instead of returning C# null. The stop fixture caught
this difference and now checks its exact one-argument interface.

`Execute(reviewedChunk)` uses protected Lua execution and converts only bounded
nil/boolean/finite-number/string/table results to C# values. Tables become
`Dictionary<object,object>`; string and numeric keys stay distinct. Functions,
userdata, threads, cycles, nonfinite values and oversized results reject.
Multiple return values preserve nil positions and explicit failure reasons.
Lua state is thread-owned, and callbacks stay rooted until disposal.

An uncaught script/import/budget/result error faults the host. Later calls
reject rather than replaying a partially completed tick. Callback exceptions
become `nil, host_callback_error:<type>:<message>`; the real controller can
handle them as refused operations. A callback time overrun faults the host
after the callback returns. It cannot interrupt or undo an admitted command.

This in-process interpreter is **not a security boundary for hostile code**.
Instruction hooks cover reviewed Lua execution, not blocking native/CLR calls
or all memory use. Native calls must remain bounded and on the engine's required
thread. Never automatically recreate/retry a faulted gameplay host: reconcile
registered actors and any already admitted commands first.

| Limit | Bound |
| --- | --- |
| Modules | 1–16, explicit simple dotted IDs |
| Source size | 128 KiB per module/chunk; 1 MiB total modules |
| Instruction count | Default 200,000 per execute; selectable 1,000–1,000,000 |
| Callback retention | 16 registrations per host |
| Callback timing | Default 100 ms; observed after return, not preemption |
| Returned values | 16, with 4,096 data nodes, depth 16, 64 KiB strings |

## Reproduce the offline proof

```powershell
python tools/setup/install_managed_sdk.py --sdk keralua
python tools/setup/check_managed_lua.py --workspace-id 897b9243-fd7e-42f4-a46a-d1b814a33a81
python -m unittest discover -s tools/setup -p test_managed_lua.py -v
python tools/setup/build_managed_mod.py --workspace-id 897b9243-fd7e-42f4-a46a-d1b814a33a81 --mod gta-ark --target SmelterLuaHost
```

The fixed builder compiles a library only. It accepts a pinned SDK override on
each target; a native DLL's lock entry has `reference=false`, so it is never
passed to the C# compiler as an assembly reference. No custom compiler switches,
MSBuild, output execution or runtime-copy fallback are introduced.

The separate **operator-only checker** snapshots the four real pure modules,
four original frozen verifiers and reviewed C# fixture/host sources. It copies
only KeraLua, Lua54 and license files to its private test folder, compiles the
fixture, then runs four fixed modes with a 15-second external timeout:

- Managed host access/import/thread/data/stack boundaries.
- Explicit script, callback, instruction-budget and result failures.
- Real policy/controller/entry with C# fake position/description/enumeration,
  move, attack, stop and clock callbacks: vehicle rejection, exact actor/target,
  cooldown, death loss, duplicate registration and removal.
- All four frozen verifiers: **30 + 52 + 26 + 20 = 128**, unchanged bytes.

Each verifier runs in a separate fixture Lua VM. A harness-only `os.exit`
adapter returns to C# for code 0 and raises failure for any nonzero code, so all
four tests can run in one process. Subject environments remain those defined
by the unchanged verifier. These trusted test VMs are separate from the
restricted runtime host; test-only loader/global access is not deployed.

A disposable missing-attack mutant exits nonzero and reports frozen failures.
Only its copied subject changes; neither main/controller nor frozen tests do.
The CLI is not an MCP tool or a way for the model to execute host commands.
Receipts and log hashes are under `.smelter/managed-lua-runs/<id>/`.

## Remaining game gate

The [read-only RPH probe](GTA_NATIVE_READ_PROBE.md) is still the first live gate.
The author download currently fails through backend requests; no runtime was
acquired, installed or run. The probe's three C# sources and staged DLL are
unchanged. `managed.json` now adds a second target, so its older manifest hash
is historical; the new host checkpoint records the extended manifest.

After a supervised probe succeeds, review the selected RPH runtime and actual
Lua54 DLL loading path/hash inside GTA. Then Qwen can author the six native
callbacks/bootstrap through SMELTER. This host does not supply those callbacks,
spawn a cougar, schedule ticks or load a creature asset. C# edits remain model
editable, but compilation stays operator-owned and separate from Lua GREEN.

## In-game probe (29 October)

After the [native read gate](GTA_NATIVE_READ_PROBE.md) passed live, the next gate
asks whether this host loads and runs **inside the RPH game process**.
`SmelterLuaHostProbe` reuses the read-probe harness unchanged: identity checks,
network check before each read, and four samples. Each sample is produced by a
reviewed in-memory Lua module calling the one read-only callback `host_player`.
`lua_host.json` beside `probe.json` records:
- the Lua version, the loaded `lua54.dll` path and SHA-256, and the KeraLua hash;
- the tick and thread IDs (every tick on the host's owning thread);
- integer division, the integer subtype, `utf8`, and that ambient libraries are absent.

It issues no commands and contains no Qwen gameplay code.

```powershell
python tools/setup/build_managed_mod.py --workspace-id 897b9243-fd7e-42f4-a46a-d1b814a33a81 --mod gta-ark --target SmelterLuaHostProbe
python -m unittest discover -s tools/setup -p "test_*lua*probe*.py"
python tools/setup/stage_native_read_probe.py plan --profile mods/gta-ark/gta/rph/lua_host_probe_expectations.json --package .smelter/mod-packages/gta-lua-host-probe-20261029
python tools/setup/verify_lua_host_probe.py --latest --loader-log "<game folder>\RagePluginHook.log"
```
