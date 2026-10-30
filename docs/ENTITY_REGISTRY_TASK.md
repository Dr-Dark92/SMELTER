# Independent offline task: entity identity and ownership registry

**Completed and promoted, 29 October 2026:** source SHA `638ff4f4…`, 46 C#
checks. Three disposable mutants fail for ownership bypass, ID reuse after
Clear and stale-entry exception handling. Exact hashes/receipts are in
`diagnostics/ENTITY_REGISTRY_PROOF_20261029.json`. This contract remains the
required behavior; the component is not game/runtime proof.

This preparatory component does not call a game or load Lua. The separate
Lua-host live gate passed on 29 October 2026. This component is not the
six-capability native provider. Qwen authors
the pure C# implementation in the owned coding copy; an operator reviews and
tests it before promotion. Deployment/native callbacks remain gated separately.

Write `mods/gta-ark/common/managed/EntityRegistry.cs`, C# 5, namespace
`Smelter.EntityIdentity`, public sealed generic `EntityRegistry<T> where T:class`.
Use only ordinary .NET collections, GUIDs/counters and injected functions.
No RPH/Lua/game, file/network/process, reflection or unsafe dependency.

Required API:

```csharp
public EntityRegistry(Func<T,bool> valid, Func<T,string> fingerprint, int capacity=256);
public int Count { get; }
public string Observe(T entity, out string reason);
public string RegisterOwned(T entity, out string reason);
public bool TryResolve(string id, bool requireOwned, out T entity, out string reason);
public bool Retire(string id, out string reason);
public void Clear();
```

- Constructor rejects null functions and capacity outside 1–4096 with an
  ArgumentException subtype. Construction and Count must not invoke delegates.
- Successful methods set reason null. Observe/RegisterOwned return an opaque
  nonempty ID; failure returns null. TryResolve/Retire return bool, with null
  entity on any resolve failure. No parsing of IDs into engine handles.
- Observe validates the entity and fingerprint. Null/invalid entity rejects
  `entity_invalid`; null/empty/whitespace or >256-character fingerprint rejects
  `invalid_fingerprint`. Catch delegate exceptions as nonempty
  `validation_error:<detail>`; never throw them through the API.
- Deduplicate a still-valid fingerprint to the existing ID, including different
  wrappers of that same identity. Revalidate existing entries before reuse,
  then refresh its stored wrapper to the newly supplied equivalent entity.
  A stale/changed/throwing old entry is retired. A new observation gets a fresh
  ID and cannot inherit old ownership.
- Observe never grants or drops ownership. Only explicit RegisterOwned grants
  it; promoting the same live observed identity keeps its ID.
- TryResolve revalidates liveness and the stored fingerprint every time.
  Invalid/changed/throwing entries retire and reject with `entity_invalid`,
  `identity_changed` or `validation_error:<detail>`. An unowned valid entity
  rejects `not_owned` without retirement when requireOwned is true.
- Null/empty ID rejects `invalid_id`; a missing/retired ID rejects `unknown_id`.
- At capacity reject new identities with `capacity_reached`; do not evict a live
  entry or silently alter ownership. Existing identity reuse/promotion works.
- Retire removes both ID and fingerprint mappings. Clear removes all entries.
  Old IDs must never be reissued, including after Clear. Use a per-instance
  GUID prefix plus a monotonic counter retained across Clear; guard exhaustion.
- This object is caller-thread-owned, not a concurrent or security registry.
  Fingerprints must include the engine's generation/identity semantics; this
  class cannot independently detect a handle reused under an identical key.

The operator fixture is `tools/setup/fixtures/EntityRegistryFixture.cs` outside
the model-editable copy. The checker requires the exact reviewed source hash:

```powershell
python tools/setup/check_entity_registry.py --workspace-id <UUID> --reviewed-sha256 <SHA256>
```

Model task completion via Lua/mods GREEN means only those regression scopes.
It is not C# registry acceptance; operator fixture evidence is recorded
separately. Preserve all existing gameplay modules and frozen verifiers.
