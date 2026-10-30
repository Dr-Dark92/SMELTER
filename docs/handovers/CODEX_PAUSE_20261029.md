# User-requested Qwen pause — 29 October 2026

The user asked to pause Qwen and create a checkpoint, then said they were going
to play one last game before travel. **Do not resume inference or re-enable
watchdog recovery until the user asks to resume.** The model was unloaded with
`ollama stop qwen3.5:35b-a3b-128k`; `ollama ps` is empty. The existing Ollama
server and dashboard may remain available.

## Stop state

- Native session `ses_e794d9bc8ffeg0Xmfd8um5ZQLT` was aborted; `/session/status`
  is empty. Watchdog configuration is disabled and the daemon has exited.
- Watch `060cb0cebd374928b2b78d950337bed8` has zero retries. Its explicit GREEN
  flag covers **Lua/mods regressions only**, which completed around the stop.
  Do not interpret that flag as C# registry or gameplay acceptance.
- Owned coding workspace: `897b9243-fd7e-42f4-a46a-d1b814a33a81`, current tree
  `6c1e9ce6ae5a9a00d4aee55403c955ff7f9543ef4256bcf3f24cd7426aa6f875`.

## Independent registry draft — not promoted

Qwen drafted `mods/gta-ark/common/managed/EntityRegistry.cs` in the **owned copy**.
Main tree does not contain that class. This is an engine-neutral identity /
ownership foundation, not the native six-callback provider. Its drafting did
not depend on, or bypass, the still-pending Lua-host live gate.

Draft SHA-256:
`6835fc843a1216650ff6991566ce5343e8222cb3c2541565fa40c89ec75d0765`.

The operator's real C# 5 compilation is **RED**:
`.smelter/entity-registry-runs/6664ce16-c826-4baa-af42-3ed1d9a78d5e/receipt.json`.
The source uses unsupported target-typed `new`, `nameof`, expression-bodied
members and `out var`, plus invalid variable scopes / counter code. Review also
found missing ownership storage, no retained fingerprint for generation checks,
wrong fingerprint-map removal, missing resolved output and a counter reset in
Clear. **Do not promote or execute this draft.** It has not passed the registry
fixture. No correction was attempted before the user's pause request.

The operator-owned fixture is
`tools/setup/fixtures/EntityRegistryFixture.cs`; contract is
`docs/ENTITY_REGISTRY_TASK.md`, with a model-readable copy under
`mods/gta-ark/docs/ENTITY_REGISTRY_TASK.md`. A deliberate constructor/method
scaffold compiled and failed behavior first, providing a real RED baseline.

`tools/setup/check_entity_registry.py` compiles/runs only an explicitly reviewed
source hash with the pure C# fixture, without SDK/game/native references. It is
operator-only and not an MCP tool. It is declared in both requirement files.
Its CLI returns nonzero on RED. The new registry checker/fixture have not yet
had a dedicated Python unit-test pass; the prior full setup count **203**
predates this preparatory addition. Do not repeat that number as verification
of the draft or new checker.

## Stable game milestone

Gate 1 remains verified live. `SmelterLuaHostProbe.dll` is installed but still
has no live report. No game was launched, no game-folder/security/grant changes
were made, and no actual native provider, cougar demo or Raptor work started.
The prior [continuation](CODEX_CONTINUATION_20261029.md) and
[Claude handover](CLAUDE_HANDOVER_CODEX_20261029.md) remain the reference for
the live gate and installed files.

## Resume sequence

1. Wait for the user's explicit resume request. Check that native work is idle
   before enabling the watchdog; do not automatically revive the stopped task.
2. Inspect the registry draft and RED compiler receipt. Prefer a C# 5 entry/
   dictionary scaffold and small helper edits over another broad replacement.
   Qwen's Lua GREEN did not compile this source.
3. Recheck all new tooling and capture current receipts before any promotion.
4. Keep the Lua-host live probe as the prerequisite to actual native provider
   dispatch/deployment. The user launches RPH and runs the Story Mode command.
5. Keep 131072 context / 8192 output, frozen acceptance operator-owned, game
   specifics in adapters/profiles, and requirements/docs updated.

No staging/commit/push was requested or performed. Never include
`dw3_decomp-main/` in Git or checkpoints. The pause archive includes the failed
draft under an explicitly **UNPROMOTED** path, separate from main source.
