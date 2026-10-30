# Claude → Codex handover — 29 October 2026

Branch `feature/agent-stack-game-mods`, HEAD `876352f`. **Nothing committed or
pushed.** About 80 paths are modified or untracked: yours, mine and the
user's. Never stage `dw3_decomp-main/`. Commit only when the user asks.

Earlier context: [system review and fix pass](CLAUDE_SYSTEM_REVIEW_20261028.md).
Your handover, which I continued: the paste the user gave me, plus
`docs/CURRENT_HANDOVER.md`.

## Where things stand

| Gate | State | Evidence |
|---|---|---|
| 1. Native read probe in GTA Enhanced | **Passed live**, verdict `native_reads_verified` | [`diagnostics/NATIVE_READ_GATE_20261029.json`](../../diagnostics/NATIVE_READ_GATE_20261029.json) |
| 2. Managed Lua 5.4 host inside the RPH process | **Built, tested offline, installed; not yet run in game** | this document |
| 3. Six native callbacks/bootstrap (Qwen) | Not started | — |
| 4. Controlled cougar demo | Not started | — |
| 5. Raptor assets, ARK, shop, taming, riding | Not started | — |

## Gate 1: what happened (done)

1. **Runtime.** RPH for Enhanced ships **only inside the LSPDFR download**. The
   author site needs a signed-in account, which is why your backend requests
   were redirected. The user downloaded
   `lspdfr_049_9695_Manual_Install_Enhanced_1158_16.zip`
   (`8524e534f219c7f33634ed45ced055f3c7b0b461fa8302ff2f0ac46470c7ed34`).
   `RAGEPluginHook.exe` is 1.132.1428.17748 (`73f05b3f…42ac`). Your
   `inspect_loader_runtime.py` inventory:
   `.smelter/runtime-inventories/rph-enhanced-20261029T031054483442Z.json`.
2. **Install.** I used `tools/setup/stage_native_read_probe.py`, my tool; see
   "Tooling" below. RPH's readme says to install everything except `SDK` and
   `Licenses`, so the tool copies **all top-level files**: 24 files, which are
   RPH plus its dependencies. Subfolders stay out, so **LSPDFR was not
   installed**.
3. **First attempt stalled.** The game had never been launched, so RPH sat idle.
   I removed the install (`fe97fe29…`, 25/25 removed, none changed), the user
   did one normal first launch into Story Mode, and I re-applied it as install
   **`046eae2c…`**.
4. **Run.** RPH logged "Supported version detected" for 1.0.1158.16 Enhanced
   (Steam). `LoadPlugin SmelterNativeProbe.dll` read handle `00000002` four
   times at 250 ms, with four network checks. Your verifier passed with no
   reasons. The deployed plugin hash equals the reported one.

**Same-process caveat.** RPH warned about DirectStorage, and the user installed
these by hand, outside the tracked install:
- `ScriptHookV.dll` (`126be57c…`), which logs *VER_EN_1_0_1158_13* on a .16
  executable;
- its `XInput1_4.dll` ASI loader (`a1a8bde4…`), which **replaced RPH's
  `XInput1_4.dll`**;
- `dinput8.dll` (`9fd9e023…`), `zlib1.dll` (`3efbe55f…`) and `args.txt`
  (`-nobattleye -noBE`);
- `DirectStorageFix.asi` (`7f50b8a9…`) and **`NativeTrainer.asi`**
  (`f2302573…`, a Script Hook V trainer).

All were loaded during gate 1. They don't affect the probe's own reads, but
gameplay evidence should be captured **without the trainer**. RPH also created
`RagePluginHook.ini`, `commandline.txt`, `startup.rphs` and `ExecuteCode\`
itself.

## Gate 2: Lua host in RPH (your next step)

**Goal.** Prove that `LuaModuleHost` loads and runs inside the GTA process, on
RPH's game fiber, with the pinned `lua54.dll`.

**Operator-owned probe** (not Qwen gameplay):

| File | SHA-256 | Role |
|---|---|---|
| `mods/gta-ark/common/managed/LuaTickProbe.cs` | `769b7614…` | Engine-neutral: one reviewed in-memory Lua module, one read-only callback `host_player`, writes `lua_host.json` (Lua version, loaded `lua54.dll` path and hash, KeraLua hash, tick and thread IDs, Lua 5.4 feature checks, ambient-library absence) |
| `mods/gta-ark/gta/rph/LuaHostProbe.cs` | `aa494d90…` | RPH entry: reuses `RuntimeProbeHarness` unchanged on channel `gta-rph-lua-host-probe`; the player read is the only native call |
| `mods/gta-ark/managed.json` | `326fb84e…` | New target `SmelterLuaHostProbe`, `"sdk": ["rph","keralua"]`, five sources |

All three are identical in the main tree and coding copy `897b9243…`; builds
read the coding copy.

- **Build:** `.smelter/managed-builds/012b8a4f-…/receipt.json`, DLL
  **`3f311c670481ce3eeca0323e24ea7a6b1cc69512b72890b6c1d60df5a101ac63`**
  (28,672 bytes).
- **Package:** `.smelter/mod-packages/gta-lua-host-probe-20261029/` contains the
  plugin plus `root/KeraLua.dll` (`5a8addbb…`), `root/lua54.dll` (`2d563db7…`)
  and `root/KeraLua.LICENSE.txt`, with a manifest and `SHA256SUMS`.
- **Profile:** `mods/gta-ark/gta/rph/lua_host_probe_expectations.json`
  (`564a81d1…`), your read profile plus a `lua_host` block.
- **Installed:** install **`c9334d2f…`** put 4 files in the game folder
  (`Plugins\SmelterLuaHostProbe.dll`, `KeraLua.dll`, `lua54.dll`, the license),
  with no overwrites.
- **Not yet run.** My 30-minute watch saw no report; the game was closed and the
  log unchanged.

**To run it:**
1. The user starts `RAGEPluginHook.exe` with BattlEye off and loads Story Mode.
2. In the F4 console: `LoadPlugin SmelterLuaHostProbe.dll`.
3. Then:
   ```powershell
   python tools/setup/verify_lua_host_probe.py --latest --loader-log "D:\SteamLibrary\steamapps\common\Grand Theft Auto V Enhanced\RagePluginHook.log"
   ```

A pass is `lua_host_verified`. It needs your `judge()` to pass, plus:
- `lua_host.json` present, with `Lua 5.4`;
- the loaded `lua54.dll` hash, both as reported **and on disk**, equal to the pin;
- KeraLua equal to its pin;
- four callback calls, ticks 1–4, all on the host's thread;
- feature flags true, and zero mutating callbacks.

**Possible failure to expect.** If RPH's AppDomain can't resolve `KeraLua.dll`
from the game root, the RPH log shows a `FileNotFoundException` or
`DllNotFoundException`, and no report is written. The fix is to also place
`KeraLua.dll` under `Plugins\`: add it to the package and re-plan. Don't
weaken the verifier. After a pass, record
`diagnostics/LUA_HOST_GATE_<date>.json` the same way as gate 1.

## Tooling added (all operator-only, standard library, in both requirement files)

- **`tools/setup/stage_native_read_probe.py`**
  - `extract --archive <zip>`: top-level files only.
  - `plan [--runtime-dir D] [--profile P] [--package K] [--file F…]`: selects
    every top-level runtime file and requires `RAGEPluginHook.exe`;
    subfolders are excluded unless named with `--file`. Without
    `--runtime-dir` it deploys only a package, including the manifest-pinned
    `root/` files.
  - `apply --plan`: refuses any existing target, re-hashes the executable and
    every source, and writes the manifest first.
  - `remove --install`: deletes only files whose bytes still match.
  - Catalog key `runtime_probe_deployment`; tests
    `test_stage_native_read_probe.py` (10).
- **`tools/setup/build_managed_mod.py`** (your file): a target's `sdk` may now
  be one id or a list of up to 3 distinct ids. A list adds
  `additional_sdks` to the receipt. Single-SDK behaviour is unchanged, and your
  8 tests pass, plus 1 new test.
- **`tools/setup/verify_lua_host_probe.py`**: wraps your `judge()` and
  `record()` unchanged. Catalog key `lua_host_probe`.
- **Tests:**
  - `test_lua_tick_probe.py` compiles `LuaTickProbe` with the real pinned
    KeraLua and Lua 5.4 and fake reads (2 tests: four reads on one thread with
    the matching `lua54.dll` hash; unavailable or throwing reads stop without a
    sample).
  - `test_verify_lua_host_probe.py` (5).
- I deleted my own duplicate read verifier, since yours is canonical. Two
  checks from it you may want in `verify_runtime_probe.py`:
  - the plugin deployed in `<game>\Plugins\` must match the staged hash;
  - the log line `[SMELTER] Native read-probe receipt: <path>` must name the
    exact report.

**Suites at last run:** setup all OK (186 plus the new tests); dashboard
807 OK, 9 skipped; JS 85/85.

## Fixes from the system review (28 October, uncommitted)

Details are in [the review](CLAUDE_SYSTEM_REVIEW_20261028.md#fix-pass-claude-28-october-evening).
- **Binding archive cap:**
  - `native_progress.export_archives()` and
    `tools/setup/export_native_archives.py` move archives into a dated folder
    with a SHA-256 manifest and never delete.
  - It already ran once (10 archives moved).
- **Child environment:** the Ghidra launcher and `smoke_agent_bridge` now keep
  `SystemDrive`/`ProgramData`. The bridge also dropped `SystemRoot`, because it
  matched Windows' upper-cased environment keys case-sensitively. The stray
  `%SystemDrive%\` folder was removed.
- **Stale-token pollers:** `session_auth.js` latches a rejected token and stops
  all requests made with it, and the shell shows the recovery screen once.
- **Hygiene:** `.gitattributes` now has `*.lua text eol=lf`; the mojibake in
  your resume checkpoint is fixed; `MASTER_HANDOVER.md` points to
  `CURRENT_HANDOVER.md`.
- **Trace workbench:** layered layout plus per-layer colour bands.
- **Deliberately left for you: Lua RED vs ERROR** (sandbox `CODING_LUA`
  classifies custom asserts as ERROR). Any edit changes `lua_runner_sha256()`
  and invalidates every Lua receipt, so land it between milestones and re-run
  the proofs.
- **Still open:**
  - script-style `test_*.py` files in `tools/core` and `tools/bootstraps`;
  - 90 legacy `C:\SMELTER` defaults (live script: `Get-RepositoryState.ps1`);
  - Melty and headless ACP sharing port 4096;
  - `.smelter` retention;
  - `CURRENT_HANDOVER.md` length.

## Game-folder state and safety

- **Tracked installs:**
  - `046eae2c…`: RPH, 25 files. `XInput1_4.dll` has been changed by the user, so
    `remove` will keep it.
  - `c9334d2f…`: Lua probe, 4 files.
  - Both records are under `.smelter/native-read-gate/installs/`.
- **Untracked, user-installed:** the Script Hook V files above. Removing them is
  the user's call.
- **BattlEye** is off; `args.txt` reads `-nobattleye -noBE`. **Never go online
  with these files present.** Before the user plays online, run `remove` for
  both installs, have the user delete their Script Hook V files, and turn
  BattlEye back on.
- **Backend only while the user is at the PC.** Don't drive the game UI. The
  user launches RPH and types console commands.

## After gate 2: the gameplay route

1. Write the six-capability provider task for **Qwen through SMELTER**, not by
   hand:
   - the callbacks are position, describe, candidates, move_to, attack and
     stop, as C# `host_*` callbacks;
   - use the generic `LuaModuleHost` bridge and the existing `provider-admission`
     and `predator-system` contracts;
   - the cougar profile is `profiles/gta_cougar.lua`.
2. Then add an operator-reviewed bootstrap plugin that loads the reviewed Lua
   modules into the host on the game fiber, with one controlled cougar
   (`a_c_mtlion`) placeholder. Capture evidence without the trainer.
3. Keep SMELTER universal: game details go in adapters and profiles, and the
   128K/8K model profile and frozen acceptance must stay intact.
4. Record new tools in both requirement files, and update the checkpoint after
   each milestone.
