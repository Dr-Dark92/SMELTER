# RPH API notes for the native-provider task

Operator-reviewed API inventory, 29 October 2026. Names were checked in the
pinned **1.124.0 development SDK XML**, not inferred from another mod loader.
The installed **1.132.1428.17748** runtime is a different build. These names
still require compilation and live behavior checks; this note is not native
provider evidence. The separate Lua-host live gate passed on 29 October 2026,
run `d0b90a7e8cf748ca82378d7e3e729d8b`; it establishes host execution and
read-only callbacks, not these future provider methods.

SDK source: `.smelter/tooling/rph-sdk/1.124.0/RagePluginHook.xml`;
its SHA-256 is pinned in `tools/setup/managed-sdk-lock.json`.
The SDK is not copied into a model workspace or redistributed.

| Public member found in the SDK | Provider use / constraint |
| --- | --- |
| `Rage.Entity.IsValid()` | Revalidate stored wrappers, especially after the outer scheduler yields |
| `Rage.Entity.Handle` | Use its actual SDK type for identity checks; never parse a model-supplied ID into a handle |
| `Rage.Entity.Position` | Read the position and validate finite coordinates |
| `Rage.Entity.IsDead` | Supply boolean liveness; it has entity-specific semantics |
| `Rage.Ped.IsHuman` | Human trait |
| `Rage.Ped.IsPlayer` | Player classification; human NPCs and player remain eligible |
| `Rage.Ped.Tasks` | Task entry on a verified mod-owned actor |
| `Rage.Ped.GetNearbyPeds(int)` | SDK count range is **1–16**; returns the game's nearby cache, not a guarantee of complete radius coverage |
| `Rage.World.GetAllPeds()` | World-wide array; limiting emitted records does not bound the cost of this enumeration |
| `Rage.TaskInvoker.GoToOffsetFromEntity(Entity,int,float,float,float)` | Parameters describe entity, timeout in ms, offset in metres, angle in degrees and speed in m/s; actual animal behavior remains untested |
| `Rage.TaskInvoker.Clear()` | Candidate task-clear API; invoke only on the mod-owned predator, never the target/player |

No `TaskInvoker.Fight...` member was found in this XML inventory. Do not invent
a `FightAgainst` method based on examples from other loaders. Select a combat
API only after checking an actual public SDK signature or a primary native
definition and compiling it. Neither task admission nor a void return proves
that the animal moved or dealt damage.

Keep native callbacks short and non-yielding. The outer RPH game fiber owns
scheduling. Cached ped validity can change when the fiber yields; never keep a
prior validity result as authority for a later tick. The nearby-ped cache also
has coverage/latency limits: document them and test player/NPC targeting live.

KeraLua callbacks use `Lua.FromIntPtr(pointer)` and must check `GetTop()` plus
argument types before conversion. `ToString()` can format an absent argument;
it is not an argument-presence check. Return explicit Lua values and preserve
`nil, reason` refusals. No CLR reflection/object translator is involved.

This note deliberately supplies no spawning code, active scheduler or selected
combat task. Those remain scoped Qwen implementation and supervised proof work
after `lua_host_verified`.
