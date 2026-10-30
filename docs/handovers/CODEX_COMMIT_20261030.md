# SMELTER GitHub checkpoint — 30 October 2026

Branch: `feature/agent-stack-game-mods`. Prepared after the user explicitly
requested proceeding and committing to GitHub. This includes the existing
Claude workbench changes and the reviewed operator/Qwen work. No SDK/runtime
binaries, private launch tokens, `.smelter/` state or `dw3_decomp-main/` are
included. Read this first, then `CODEX_LIVE_LUA_20261029.md` for the live run.

## What is established

| Component | Evidence | Scope |
| --- | --- | --- |
| Native player read probe | `diagnostics/NATIVE_READ_GATE_20261029.json` | Passed live in GTA Enhanced 1158.16 through RPH |
| Managed Lua 5.4 host | `diagnostics/LUA_HOST_GATE_20261029.json` | Passed live: four read-only callbacks/ticks on one host thread, pinned loaded DLLs |
| Generic identity/ownership registry | `diagnostics/ENTITY_REGISTRY_PROOF_20261029.json` | 46 C# checks; three bad variants rejected; promoted |
| GTA read boundary | `diagnostics/GTA_ENTITY_READER_PROOF_20261030.json` | 31 fake SDK checks, three bad variants rejected, real pinned SDK compile; promoted, not deployed |
| Shared controller/policy/provider admission/lifecycle | Existing frozen receipts | 128 offline checks, with no game API in the shared Lua core |

Reader source: `mods/gta-ark/gta/rph/GtaEntityReader.cs`, SHA
`016772291e5be70b8f7404f7f67b0cbb7413ae6f22e819bbf7a697488dbafa61`.
Registry SHA:
`638ff4f46570db098ce418cc787d8d656821b746637174d67754ff5cc42e8fb8`.
The reader's real SDK build produced DLL SHA
`c9592aad4286b30832c3dc3a3cc793ea0ce17708fde40b189947fc3fc899fc0c`;
the DLL was neither executed nor installed. The SDK remains outside Git.

## Changes and verification

The reader now rejects wrong-thread calls before touching its gate or SDK,
preserves explicit runtime refusals, treats only a null gate result as allowed,
keeps failure snapshots null, uses the full pool counter in identity, validates
finite coordinates and rechecks identity after capture. Vehicles remain vehicles,
with truthful liveness. Observing an entity does not grant command ownership.
The injected runtime guard still needs a real bootstrap; a managed thread ID
alone is not proof of the correct game fiber.

Operator fixtures reject access bypass, vehicle-as-human and removed identity
revalidation mutants. The earlier Qwen drafts failed compilation/behavior and
were kept out of the main tree. A Lua-only model GREEN was never accepted as
C# or native proof. Final corrections went through SMELTER's exact-edit tools.

The fixed managed-builder CLI now returns nonzero for compilation failure;
its JSON receipt is retained. Registry success requires one well-formed
zero-failure summary matching the pass lines. Both have regression tests.
All new helpers/fixtures and scopes are in REQUIREMENTS.md and
system-requirements.json; no new dependency was installed. C# and Lua sources
retain LF bytes on checkout so source hashes remain portable.

Verified suites for this checkpoint:

- Dashboard Python: **807 tests, no failures, 9 skipped** with Docker running.
- Setup Python: **212 tests, no failures or skips**.
- Analysis Python: **30 tests, no failures or skips**.
- Dashboard JavaScript: **74 tests, no failures or skips**.
- Main mod Python: **14 tests, no failures, 1 unbuilt C++ sample skipped**.
- Lua: **10 programs and all 128 frozen checks**, in the current owned copy.
- Registry/reader: **46/31** independent C# checks respectively, plus separate
  rejected mutants and the reader's real SDK compilation.

Full logs and receipts remain private in `.smelter/`; the public diagnostics
carry hashes and explicitly state their evidence limits. Optional dashboard
integration skips do not establish unavailable external-app behavior.

## Services and next task

Dashboard is on 127.0.0.1:8769, headless OpenCode ACP on 4096, and the existing
Docker service was restarted. The selected Codex-side database and seven
locations are retained. Current authenticated dashboard URL is only in
`.smelter/dashboard-knowledge.stdout.log`. Keep Qwen's 131072/8192 profile.
Run inference and GTA sequentially when possible to avoid GPU-memory contention.

Next implement explicit Lua `host_position`/`host_describe` translation over
the reader, then bounded candidate enumeration and owned-actor movement,
attack and stop. Complete all six capabilities before admitting a real provider.
Only then build a reviewed bootstrap and capture one controlled cougar test.
There is still no cougar/Raptor demo, ARK rendering integration, shop, taming
or riding evidence. Keep game-specific behavior in adapters/profiles.

Do not enter GTA Online with the existing modded installation. Do not change
access grants or security settings automatically. Keep frozen acceptance
operator-owned. Review Qwen's code independently and compile C# explicitly.
Always use a fresh validation receipt after a new task origin before its
explicit finish flag; a finish-only follow-up cannot reuse older task evidence.

The relationship diagram is `docs/diagrams/gta-ark-mashup.mmd`. Earlier pause
and pending-reader documents are historical and superseded by this checkpoint.
