# First native-provider slice: read boundary

**Promoted, 30 October 2026:** `GtaEntityReader.cs` SHA `01677229…`; independent
fake SDK fixture 31/31, three deliberately broken variants rejected, real
pinned RPH SDK compilation successful. See
`diagnostics/GTA_ENTITY_READER_PROOF_20261030.json`. No reader deployment,
live reader claim, Lua callback binding or six-capability admission occurred.

Gate 2 passed live on 29 October, run `d0b90a7e8cf748ca82378d7e3e729d8b`.
The generic `EntityRegistry<T>` passes 46 operator C# checks. This next slice
does not spawn, command, enumerate, schedule or install anything. It does not
admit a partial six-capability provider. Qwen writes the game-specific reader;
the operator supplies the plain snapshot type, reviews source, runs a fake SDK
fixture and compiles against the pinned real SDK before promotion.

Subject: `mods/gta-ark/gta/rph/GtaEntityReader.cs`, C# 5, namespace `Smelter.Gta`.
Public sealed class `GtaEntityReader`:

```csharp
public GtaEntityReader(Func<string> runtimeGate, int capacity = 256);
public string Observe(Rage.Entity entity, out string reason);
public bool TryRead(string id, out Smelter.EntityIdentity.EntitySnapshot snapshot, out string reason);
```

Construction requires a nonnull gate, validates capacity using the generic
registry and captures the managed owner thread. It calls no gate/game API.
Each public operation first rejects other threads with `wrong_game_thread`,
then calls the injected gate. Only null means allowed. A nonempty reason is
preserved; empty means `runtime_gate_invalid`; thrown exceptions become
`runtime_gate_error:<detail>`. No entity API is touched after a refused gate.
The future bootstrap must construct this on the RPH game fiber and supply the
exact-executable/network/runtime guard; a thread ID alone does not prove that.

Use a private `EntityRegistry<Rage.Entity>`. Its validity callback checks
nonnull, `IsValid()` and nonzero `Handle.Value`; its fingerprint combines the
full `Handle.Value` (including the pool counter) and `MemoryAddress`. No ID
parsing, native handle construction, unsafe code, memory writes, reflection,
file/network/process access, sleep/yield or ambient fallback. Observe only
records read identities and never calls RegisterOwned. All delegate failures
use the registry's existing named refusal.

TryRead resolves the ID unowned, then returns a fresh complete snapshot:
Id, Kind (`character` for Ped, `vehicle` for Vehicle), Valid=true,
Alive=!IsDead, Human/Player from Ped.IsHuman/IsPlayer (both false for Vehicle),
and finite X/Y/Z from Position. Other entity classes reject
`unsupported_entity_kind`. Nonfinite coordinates reject `nonfinite_position`.
Contain SDK read exceptions as `native_read_error:<detail>`. Re-resolve the
identity after reads before exposing the snapshot, so a changed generation
during capture cannot escape. Failure always returns false with null snapshot;
success returns true with null reason. Do not fabricate police traits: cops
remain human characters and the existing human policy handles eligibility.

The pinned SDK's PoolHandle docs explain its 24-bit pool index and 8-bit reuse
counter. Retain the full Value, not Index alone. IsValid compares that counter.
Counter wrap plus identical address is an inherent alias limit; this reader
cannot promise independent detection of every possible pool reuse.

The operator-provided EntitySnapshot is plain engine-neutral data. Its fields
are not a Lua translator; host_position/host_describe binding is a later slice.
Real SDK compilation and fake SDK tests remain offline evidence. Live native
reader/command/animal behavior requires separate tests.
