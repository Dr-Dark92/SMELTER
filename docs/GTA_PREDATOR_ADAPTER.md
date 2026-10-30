# GTA predator adapter and runtime boundary

**Current status, 29 October:** the RPH native-read probe has passed in the game
and was revalidated against the installed DLL and its exact loader-log receipt.
The Lua-host probe also passed live, verdict `lua_host_verified` for run
`d0b90a7e8cf748ca82378d7e3e729d8b`; see
[its evidence](../diagnostics/LUA_HOST_GATE_20261029.json). No native provider
or cougar gameplay is implemented yet. The next prepared task is
[the scoped Qwen provider plan](GTA_NATIVE_PROVIDER_TASK.md). The dated design
below remains a specification, not a claim that the native adapter exists.
Historical statements below about absent runtimes or an unverified Lua host
are superseded by this status and the dated gate records.

Design reviewed 28 October 2026. Native implementation and game behavior are
unverified. The universal controller remains unchanged by game selection.

## Runtime decision

The original native-action route is a game-thread Script Hook V ASI host.
The current installed Enhanced executable is 1.0.1158.16; the
[author's current support list](https://www.dev-c.com/gtav/scripthookv/) lists
1.0.1158.13. The checked loader paths are absent. This route is **blocked**
until exact-build compatibility and a controlled native probe are established.
An RPF asset loader does not supply native action calls.

A separate candidate is now documented by the RAGE Plugin Hook authors:
their [Enhanced release](https://www.lcpdfr.com/downloads/gta5mods/g17media/52970-lspd-first-response-enhanced-preview/)
dated 17 September 2026 explicitly lists bundled RPH support for **1158.16**.
An operator-owned, read-only RPH diagnostic now compiles against the pinned
development SDK. It gates on the exact installed executable hash, rejects an
active/unknown network session and samples the player's handle/position four
times. No runtime package was installed, game launched or native call verified.
This is an author-documented route, not evidence that the plugin loads here.
See [probe source, build and live evidence gates](GTA_NATIVE_READ_PROBE.md).

There is no installed/verified **in-game** GTA Lua host. A generic managed Lua
5.4 host is now offline verified against all 128 unchanged frozen checks and
the real Lua modules through six fake C# callbacks. It uses pinned KeraLua, has
no game API, and is not an RPH bootstrap/scheduler. See
[the managed host guide](MANAGED_LUA_HOST.md). The current Lua 5.4 Docker
image runs offline tests; it does not load scripts into GTA. An eventual ASI
host needs a reviewed Lua embedding or another explicitly implemented transport
to execute the real shared controller. Merely copying these Lua modules into
the game folder is not an installation strategy. The optional RPH development
SDK and KeraLua development/test runtime are recorded in both requirement files.
Neither is deployed to GTA; the runtime loader/native provider remain open gates.

## Six capabilities

The controller consumes only the existing six-function adapter. The native
provider owns native handles, liveness, main-thread scheduling and normalized
records. Every capability must be present before admitting a real session.
Missing functions return `nil, "unsupported_capability:<name>"`; missing runtime
returns `nil, "unsupported_runtime"`. Neither case selects a simulator.

The generic `provider-admission-v1` frozen contract adds 26 offline checks for
this boundary. `new(provider)` is passive and preserves provider values/reasons
and command arguments. Legacy `init_real_game(provider)` admits supplied
functions in `provider` mode; the name does not establish native compatibility.
Failed initialization clears the prior mode. Simulation also requires an
explicit complete provider. Spawning remains separately unsupported.

| Controller call | Proposed native provider responsibility | Required evidence |
| --- | --- | --- |
| `position(id)` | Resolve the exact live registered handle; obtain and normalize finite coordinates | Returned actor position with handle generation and capture tick |
| `describe(id)` | Revalidate identity/liveness; classify entity type and human/player/police traits; return the complete record | Native type/liveness reads bound to the same ID and tick |
| `candidates(actor, origin, radius)` | Bounded real entity enumeration and normalization; exclude stale handles, preserve policy filtering in the controller | Actual records and enumeration limit/truncation, no fabricated fallback |
| `move_to(actor, target)` | Resolve both handles and admit movement on the game thread | Exact actor/target and task-admission result; later position samples show progress |
| `attack(actor, target)` | Validate actor/target, range and Story Mode; admit one combat task | Exact actor/target and command result; animation/hit/cooldown evidence separate |
| `stop(actor)` | Stop only a mod-owned actor's task | Exact actor and task-clear result; do not clear an arbitrary target/player task |

The [Cfx native documentation](https://github.com/citizenfx/natives) supplies
candidate names/signatures, not exact-build Enhanced verification:
[TASK_GO_TO_ENTITY](https://github.com/citizenfx/natives/blob/master/TASK/TaskGoToEntity.md),
[TASK_COMBAT_PED](https://github.com/citizenfx/natives/blob/master/TASK/TaskCombatPed.md),
[CLEAR_PED_TASKS](https://github.com/citizenfx/natives/blob/master/TASK/ClearPedTasks.md)
and [IS_PED_HUMAN](https://github.com/citizenfx/natives/blob/master/PED/IsPedHuman.md).
Movement flags, animal combat support and task completion must be probed with
the chosen host. A native returning void is not evidence of completed movement
or damage; the adapter must distinguish command admission from that later proof.

IDs are opaque strings backed by a provider registry, not guessed name prefixes
or unchecked conversions to native handles. Retired/recycled native handles
must invalidate their prior IDs. Vehicle records have `kind="vehicle"` even
when they expose a position; humans have `kind="character"` and boolean traits.
NPCs, police and the player are eligible under the selected human-target policy.
There is no additional exclusion of human occupants of vehicles.

## Profile and wiring

The GTA profile owns unit assumptions, asset ID (`a_c_mtlion` for the labelled
placeholder), detection/attack/loss ranges, movement flags, cooldown and target
policy. Controller distances and provider coordinates must share the same unit;
the initial GTA convention is metres, pending live calibration. The injected
clock returns monotonic seconds; convert provider milliseconds at the boundary.
The fake-adapter centimetre scenario remains a separate portability check.

The entry module should export a constructor with explicit injected adapter,
policy, clock and profile, returning a controller-backed system. Loading the
module must not spawn actors, fabricate targets, register global tick functions
or automatically select simulation. A supported runtime bootstrap supplies the
adapter and scheduler after the native gates pass.

Track active actor IDs as a set or remove arrays by numeric index. Actor spawn
is an optional separate capability and returns a verified live ID, never a
boolean placeholder. The six-capability controller updates only registered
actors; no missing `raptor_aggro.spawn_raptor` call remains in the new path.

The generic lifecycle contract `predator-system-v1` adds 20 offline checks for
this entry boundary. Each registration gets a fresh controller instance so
removing/re-adding an ID cannot inherit stale target/cooldown state. Refused or
throwing stop retains registration and reports failure. One actor error must
not prevent other actor results. This is separate from native spawn/scheduling.

An explicit offline simulator may remain for tests, but a failed real-session
initialization stays failed. Legacy prototype scripts can be retained as
historical fixtures; the new entry path must not depend on their fabricated
targets or wall-clock state.

## Ordered proof gates

Offline milestone completed 28 October 2026: provider admission and passive
entry were reviewed/promoted, main Lua 10/10 and mods 14/14, all 128 frozen
checks GREEN. A retained regression also verifies nonstring refusal reasons
do not throw and thrown stop messages survive containment. Source hashes and
receipts: [promotion manifest](../diagnostics/PASSIVE_SYSTEM_PROMOTION_20261028.json).
The generated adapter/system tests repeat the pinned conformance contracts;
they do not provide independent native evidence. A disposable baseline passes
and refusal/false-removal mutants fail the intended test programs.

The caller supplies `engine_adapter`'s six functions, monotonic clock,
`profiles.gta_cougar.profile` and `.policy` to `raptor_system_main.new`.
The returned system exposes `add_actor(id)`, `remove_actor(id)` and `tick()`.
It neither spawns nor schedules itself. A verified provider/bootstrap is still
required before this API can be driven by a real game. No GTA native provider,
loader compatibility or Lua host was established by this milestone.

1. Frozen controller scenarios and editable real-policy integration test GREEN.
2. Offline entry/adapter tests exercise movement, attack, cooldown, death loss,
   unsupported runtime/capabilities, refusal/throw and actor/target identity.
3. Exact executable/loader/bridge/source hashes and supported build established:
   RPH has an author-documented candidate for 1158.16, with runtime still absent.
4. Run the prepared read-only native identity/position probe, then establish a
   separately verified Lua host/transport. Compilation satisfies neither gate.
5. One controlled cougar placeholder spawn and visible move/attack/stop capture.
6. Raptor assets, rig, animations, collision and gameplay tested separately.

Offline conformance is never reported as passing any native or visual gate.
See [the current runtime inventory](../diagnostics/PREDATOR_RANGE_REVIEW_20261028.md)
and [the GTA–ARK handover](handovers/GTA_ARK_MASHUP_HANDOVER_20261028.md).
