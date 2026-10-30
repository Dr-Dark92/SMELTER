# Codex continuation after Claude's handover — 29 October 2026

Read [Claude's handover](CLAUDE_HANDOVER_CODEX_20261029.md) first. The user is
AFK and backend work remains authorized. No desktop/game UI control, game launch,
security changes, game-folder changes, new access grants, commit or push were
performed in this continuation. Keep `dw3_decomp-main/` untouched.

## Verified starting state

- Gate 1's public record, saved verifier receipt and raw report hashes match.
  `GTA5_Enhanced.exe`, the deployed native probe and the installed Lua-host
  probe/KeraLua/Lua54 match their pins. RPH version is 1.132.1428.17748.
- The game is closed. There is still no report under the Lua-host probe channel.
  Gate 2 is **pending**, not failed or passed. The four installed files from
  `c9334d2f93844c1f9155caa0c14d010e` were not changed.
- The user's Script Hook V/trainer/DirectStorage files, `args.txt` and BattlEye
  state are unchanged. Follow Claude's cleanup notes before any online use.

## Completed operator changes

The canonical read verifier now optionally applies the reviewed profile's
`plugin.deployed_relative_path` and `loader_log.receipt_prefix`. Both GTA
profiles require them. The deployed file is independently re-hashed, and the
loader log must name the **exact** report path/run. Windows case/slash/8.3 path
aliases normalize to the same path. Invalid report IDs cannot select output
receipt filenames.

The Lua verifier also independently re-hashes the reported KeraLua file, checks
the evidence schema, all four integer ticks and thread IDs, the positive host
thread ID, and integer callback counts. Malformed Lua evidence rejects with a
named reason instead of crashing. Probe binaries and frozen Lua contracts were
not changed, so no rebuild/reinstall was needed.

Gate 1 passes the stronger checks with no reasons. The new receipt is linked
from `diagnostics/CODEX_RESUME_20261029.json`; the original gate record is left
intact. The exact loader receipt line and deployed-plugin hash are recorded in
the new private verifier evidence.

Both requirement files document the added checks. No new dependency or tool
was installed. Existing Docker/backend services were restored.

## Qwen preparation, not dispatch

- Main-tree task: `docs/GTA_NATIVE_PROVIDER_TASK.md`.
- Public-SDK API inventory: `docs/GTA_RPH_SDK_API_NOTES.md`.
- Model-readable copies are in the owned copy under **`mods/gta-ark/docs/`**.
  The coding tool does not allow editing top-level `docs/`; its allowlist was
  preserved. The next prompt names those exact scoped paths and canonical Lua
  module paths. No path guessing, grant expansion or code-tool bypass.
- API note: `Ped.GetNearbyPeds(int)` has a documented 1–16 count range and
  cache/coverage limits. No `TaskInvoker.Fight...` member was found in this SDK
  XML; Qwen must not invent a combat method from another loader's examples.
- Updated expectation JSON copies are also in the owned copy.

**No Qwen prompt/inference was submitted.** Wait for `lua_host_verified` before
starting the native provider. Keep the 131072/8192 model profile. Six actual
native callbacks, the bootstrap and cougar demo are still unimplemented. A
Lua-only GREEN does not compile or validate a future C# adapter.

## Validation and services

The new current coding tree is `86f2d6e46551173969bccc5f9bc64ae1c4a01ca1b4d82586fa8ba1540f628a0d`.
Lua **10/10**, four frozen contracts **128/128**, Python mods **14 tests, no
failures, one unbuilt C++ sample skipped**. Source/gameplay modules are unchanged.
The protected Lua runner/verifiers were not edited; the RED-versus-ERROR issue
Claude left is still deferred. Exact setup/verifier test counts and log hashes
are in the new diagnostic record.
The final setup run passes **203 tests**. Those include the new malformed-ID
receipt containment case; no model-owned or frozen expectation was relaxed.

Docker was stopped; it is now running again (existing 29.8.2 install). Dashboard
port 8769 uses the same selected Codex-side SQLite database and seven existing
locations. Its URL rotated on startup; read the private launch log. Headless
OpenCode ACP is on 4096, with no queued task. The existing watchdog is running;
its older completed Qwen task remains GREEN with zero retries. The live-state
diagnostic distinguishes that historical task from the unstarted provider work.

## Next action when the creator returns

The creator starts RPH, enters **Story Mode**, then runs in its console:

```text
LoadPlugin SmelterLuaHostProbe.dll
```

The backend operator then runs:

```powershell
python tools/setup/verify_lua_host_probe.py --latest --loader-log "D:\SteamLibrary\steamapps\common\Grand Theft Auto V Enhanced\RagePluginHook.log"
```

If there is no report, inspect the new RPH log before changing anything. A
missing KeraLua assembly may need the dependency-placement repair described by
Claude; do not apply it speculatively or weaken the verifier. After a pass,
record a new Lua-host gate evidence file and dispatch the first prepared Qwen
slice through SMELTER. Keep the first actual gameplay capture free of trainer
effects, with the user supervising it.

No Git staging, commit or push occurred; the branch remains
`feature/agent-stack-game-mods`, two earlier commits ahead of origin.
