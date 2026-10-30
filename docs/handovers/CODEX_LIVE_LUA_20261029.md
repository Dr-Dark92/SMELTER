# Codex live Lua gate and registry continuation — 29 October 2026

**30 October update:** the reader review below is completed. Exact source
`01677229…` passes 31 fake SDK checks and compiles with the real pinned RPH SDK;
gate-bypass, vehicle-as-human and missing-revalidation mutants all fail. The
source and compile-only manifest target are promoted, with no deployment.
Read `CODEX_COMMIT_20261030.md` and
`diagnostics/GTA_ENTITY_READER_PROOF_20261030.json` for the latest checkpoint.
The unfinished-reader notes below describe the earlier review stage.

The user resumed work, is AFK and explicitly authorized computer use. This
supersedes the earlier pause/backend-only restrictions. No new access grant,
security setting, game-file modification, Git staging, commit or push was made.
Branch remains `feature/agent-stack-game-mods`, HEAD `876352f`; never stage
`dw3_decomp-main/`. Preserve Claude's existing workbench changes.

## Live host gate passed

Codex opened the existing Steam installation, launched GTA Enhanced and chose
Story Mode. Direct executable launch produced ERR_NO_LAUNCHER; Steam launch
worked. RPH was then launched from the existing game folder and attached to
the already running game. Its console loaded `SmelterLuaHostProbe.dll`.
The game was in its early Story Mode scene; the probe only read the player.

`verify_lua_host_probe.py --latest --loader-log <game>/RagePluginHook.log`
returned **`lua_host_verified`**, with no reasons, for run
`d0b90a7e8cf748ca82378d7e3e729d8b`. Four Lua callbacks/ticks (1–4) ran on
managed host thread 13. Deployed plugin `3f311c67…`, KeraLua `5a8addbb…` and
loaded Lua54 `2d563db7…` match their unchanged pins. No KeraLua relocation or
reinstall was required. The exact runtime log names that report path.

- Public record: `diagnostics/LUA_HOST_GATE_20261029.json`.
- Private verdict: `.smelter/runtime-probe-verdicts/d0b90a7e8cf748ca82378d7e3e729d8b-20261029T093951871898Z.json`.
- Preserved raw reports/loader log: `.smelter/lua-host-gate/20261029/`.
- Probe report SHA: `0d97904d0ebaf0f8501a4fb95782a39152540bad5e87914289c27905fb3ad221`.
- Lua evidence SHA: `fc51fac0e753929de7ec4718d9707911b690fd9a134fdfdb47991e6c3c68edb7`.

Existing user-installed Script Hook V, trainer and DirectStorage files were
retained. No trainer command, actor spawn, movement, combat or asset loading
was used. This is live read-only host evidence, not a gameplay demo or proof
of the six-capability provider. Never enter GTA Online with this install.
After evidence was saved, the test game session was closed.

Do not run GTA and Qwen inference together unnecessarily: this 16 GB GPU
overcommitted and prompt processing fell to ~5 tokens/second. Closing GTA
restored ~160–190 prompt tokens/second and ~20 output tokens/second. Keep the
requested 131072 context / 8192 output profile; no model profile was changed.

## Generic registry promoted

`mods/gta-ark/common/managed/EntityRegistry.cs`, SHA
`638ff4f46570db098ce418cc787d8d656821b746637174d67754ff5cc42e8fb8`, is
identical in the owned copy and main tree. Operator-supplied C# 5 plumbing
surrounds Qwen's GetOrAdd/TryResolve methods. The final correction used a
single scalar exact edit through SMELTER rather than replacing a whole file.

The independent fixture compiled and passed **46 checks**. Three disposable
mutants compiled but failed the intended assertions: ownership bypass,
reissuing the oldest ID after Clear, and rejecting a fresh identity when the
old entry's validator threw. See `diagnostics/ENTITY_REGISTRY_PROOF_20261029.json`.
No game/SDK/native API is used by the registry.

Qwen session `ses_e78f63071ffeLUb5KBg2I55gKY` ended with explicit GREEN,
receipt `659a5c13-7de2-4b37-993b-c86413b26117`, zero watchdog retries. That
receipt separately covers Lua 10/10 and all 128 frozen checks; C# acceptance
is the operator fixture, not that Lua finish.

`check_entity_registry.py` now requires exactly one positive-count,
zero-failure summary matching the individual pass lines. Its five tests pass,
including the promoted real source. Both requirements files declare it.

## First native reader slice under review

Contract: `docs/GTA_ENTITY_READER_TASK.md`; model-readable copy is under
`mods/gta-ark/docs/` in owned workspace `897b9243-fd7e-42f4-a46a-d1b814a33a81`.
Source target is `mods/gta-ark/gta/rph/GtaEntityReader.cs`. The operator supplied
plain engine-neutral `EntitySnapshot.cs` and a compile-only target
`SmelterGtaEntityReader` in the owned manifest. Native reader behavior remains
Qwen-authored through SMELTER.

The first reader draft `d0e2a451…` is **not promoted**. Real SDK compile failed
for missing namespaces; review also caught gate inversion, C# 6/7 syntax,
Double.IsFinite unavailable in Framework, missing liveness validation and
nonnull snapshots on rejection. A focused corrective prompt is tracked in
`.smelter/codex-gta-reader-review-fix-dispatch-20261029.json`. Reconcile its
exact native session before submitting another task.

Operator fixture: `tools/setup/fixtures/GtaEntityReaderFixture.cs` with
`tools/setup/test_gta_entity_reader.py`. Its helper `exercise(target, hashes)`
requires all three exact reviewed C# source hashes, compiles against fake Rage
types and runs with 30/10-second bounds. It never loads RPH. Only run it after
reviewing the current source. Then separately compile:

```powershell
python tools/setup/build_managed_mod.py --workspace-id 897b9243-fd7e-42f4-a46a-d1b814a33a81 --mod gta-ark --target SmelterGtaEntityReader
```

This returns a JSON stage. The original CLI returned exit zero for
`compile_failed`; it now exits nonzero for any stage other than `compiled`,
with a regression test. Still inspect the stage and build log. Compilation does not establish runtime
behavior. Do not promote until fake SDK behavior and real SDK compilation pass.
Do not deploy this helper or admit it as a complete provider.

## Validation and next steps

Setup suite passed 208 tests before the reader fixture/catalog addition; the
then-unpromoted registry test was the sole skip. After registry promotion its
five checker tests pass without skips. The new requirements catalog tests
pass 28/28. Main Python mods: 14 tests, no failures, one unbuilt C++ sample skip.
Subsequent exact results belong in the final checkpoint record.

Next after reader review: explicit Lua position/describe translation, bounded
candidate enumeration, owned-actor movement/attack/stop, then a reviewed
bootstrap and controlled cougar. No six callbacks, cougar gameplay, Raptor
assets, ARK rendering, shop/taming/riding or cross-game runtime proof exist yet.
Keep game specifics in adapters/profiles and the shared controller unchanged.
The updated relationships are in `docs/diagrams/gta-ark-mashup.mmd`.

Dashboard uses the same Codex-side database and seven locations. Headless ACP
is operator-owned on 4096; watchdog remains bounded at three recoveries.
Private launcher logs carry the current dashboard token; never commit it.
No code granting access or security settings was changed. All new fixtures,
tools and their scopes are declared in both requirement files, with no new
package installation.
