# Next Qwen task: native predator provider

Prepared 29 October 2026. **Native provider not submitted.** The prerequisite is a saved
`lua_host_verified` verdict for the installed `SmelterLuaHostProbe` run. A
passing native-read probe alone is not that prerequisite. The user subsequently
authorized desktop use while AFK. Gate 2 passed live on 29 October, run
`d0b90a7e8cf748ca82378d7e3e729d8b`, with no verifier rejection reasons.
See `diagnostics/LUA_HOST_GATE_20261029.json`. The installed binaries were
unchanged. The independent generic registry now passes 46 operator C# checks,
with ownership/ID-reset/stale-exception mutants rejected, and is promoted.
The `GtaEntityReader` slice is promoted as of 30 October: 31 fake SDK checks,
real pinned SDK compile and three rejected mutants. See
`GTA_ENTITY_READER_TASK.md`. This does not supply the six Lua callbacks or
native commands. Next implement the explicit Lua read translation, then
enumeration/commands before any bootstrap deployment.

## Operator preparation before dispatch

1. Run `verify_lua_host_probe.py --latest --loader-log <RagePluginHook.log>`.
   Record the exact successful receipt/source hashes in a new gate record.
2. Confirm the owned coding copy, pinned SDK files and current Lua receipts.
   Main and coding-copy modules must match; retain all four frozen contracts.
3. Review the local RPH SDK XML for every selected API and compile against the
   pinned SDK. Its API version differs from the installed runtime; compile
   success does not establish live behavior. Do not infer missing APIs.
4. Use small numbered tasks and fixed source paths. Begin with the registry /
   read boundary, then enumeration and commands. Keep C# changes scoped and
   require operator compilation after each applied slice. The existing Lua
   GREEN profile does not compile C# or establish native provider behavior.

## Contract to preserve

Provider functions are `position(id)`, `describe(id)`,
`candidates(actor_id, origin, radius)`, `move_to(actor_id, target_id)`,
`attack(actor_id, target_id)` and `stop(actor_id)`. Bind only explicit
`host_*` callbacks through `LuaModuleHost.SetCallback`. The shared Lua policy,
controller, lifecycle and host remain engine neutral and unchanged.

| Boundary | Required behavior |
| --- | --- |
| IDs | Opaque IDs backed by a scoped live-entity registry; validate/revalidate handles, retire stale identities, reject recycled/missing handles |
| Ownership | Native command actors must be explicitly registered mod-owned predators; targets are separate read records; never clear arbitrary player/NPC tasks |
| Reads | Finite `{x,y,z}` in the selected profile's units, plus complete `{id,kind,traits,valid,alive,position}` records |
| Classification | Human NPCs, cops and player eligible under the human policy; vehicle entities remain `kind="vehicle"`; traits, when present, are booleans |
| Enumeration | Bounded real enumeration, finite nonnegative radius, stable IDs and recorded truncation; policy performs eligibility selection |
| Commands | Validate ownership, actor/target identity and liveness, runtime/network state and game thread; explicit refusal/error, never simulation fallback |
| Outcomes | Distinguish task admission from completed movement/damage. Preserve refusal details and avoid claiming a void native proves success |
| Cleanup | Stop only the mod-owned actor. A refused/throwing stop retains registration, as required by the existing lifecycle contract |
| Clock | Inject monotonic seconds; keep the game-unit profile explicit |

Humans occupying vehicles are not automatically excluded by the user's
requirement; vehicle entities themselves are excluded. Do not introduce name
prefix classification, fake target records, fabricated handles or wall-clock
cooldown. The cougar model `a_c_mtlion` is a later bootstrap choice; the provider
must not spawn on import/construction or encode the predator controller itself.

## First bounded prompt (after the gate)

```text
Always call a tool in each reply.
1. Recover coding workspace 897b9243-fd7e-42f4-a46a-d1b814a33a81 using SMELTER.
   Read its indexed files and current tree; do not guess filesystem roots.
2. Read mods/gta-ark/docs/GTA_PREDATOR_ADAPTER.md and
   mods/gta-ark/docs/GTA_RPH_SDK_API_NOTES.md. The real Lua modules are in
   mods/gta-ark/Mods/GtaArkLink/Scripts/: engine_adapter.lua,
   predator_controller.lua, entity_policy.lua and raptor_system_main.lua.
3. Propose one focused C# provider slice for the scoped registry/read boundary
   under mods/gta-ark/gta/rph/GtaPredatorProvider.cs. Validate actual Lua argument
   types and arity before conversion. No spawning, startup loop or game install.
4. Use SMELTER read/propose/apply tools with current source hashes. Preserve
   the existing generic Lua modules and protected acceptance expectations.
5. Checkpoint the applied slice and exact file hash for operator C# compilation
   and review. A passing Lua-only receipt is not C# or native validation.
   Report missing APIs/capabilities explicitly; do not invent or simulate them.
```

The operator must supply this document/API notes in the model-readable coding
copy before dispatch. These main-tree notes are not automatically present in
an older owned copy. Put those copies under `mods/gta-ark/docs/`, which the
coding tool permits; top-level `docs/` is outside its edit allowlist. Do not
expand grants or ask Qwen to rediscover the notes through arbitrary paths.

## Subsequent slices

After registry/read compilation and offline tests, implement bounded candidate
enumeration; then movement/attack/stop with fake-adapter command assertions and
real SDK compilation. Review actor/target identity, liveness, ownership, refusal
and cleanup. Only after all six capabilities are complete should an explicit
reviewed RPH bootstrap register one cougar, inject the existing profile/clock
and schedule ticks. An unsupported real session must stay unsupported.

The first live gameplay capture should run without the user's trainer, with
the creator supervising Story Mode. Record selected runtime/plugin/Lua hashes,
actual actor and target IDs, command admission, visible movement/attack/stop and
cleanup. Raptor assets, animation/rig/collision, ARK rendering integration and
later shop/taming/riding remain separate tasks.

Keep Qwen at 131072 context / 8192 output. Record new tools/dependencies in both
requirements and documentation. Nothing in this plan authorizes changing access
grants, security settings, frozen expectations, or entering GTA Online.
