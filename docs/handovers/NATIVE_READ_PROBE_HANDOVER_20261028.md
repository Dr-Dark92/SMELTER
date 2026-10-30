# Resume the native read-probe gate

Later continuation: [the generic managed Lua host](../MANAGED_LUA_HOST.md) now
passes all 128 unchanged frozen checks under KeraLua/Lua 5.4 plus six-callback
real-controller tests. Read the new top of CURRENT_HANDOVER and
`diagnostics/MANAGED_LUA_HOST_20261028.json` first. The earlier probe's three
sources and staged DLL are unchanged, but `managed.json` adds a second host
target and its older hash is historical. No in-game Lua/native result is claimed.

Read `docs/CURRENT_HANDOVER.md`, `docs/GTA_NATIVE_READ_PROBE.md`, then
`diagnostics/NATIVE_READ_PROBE_20261028.json`. All work here is uncommitted on
`feature/agent-stack-game-mods`; HEAD still has two earlier unpushed commits.
Do not commit/push without a new user request or stage `dw3_decomp-main/`.
Claude owns workbench UI changes. Use backend commands/APIs; the user uses the PC.

## Ready now

- Operator-authored read-only RPH plugin with exact GTA 1158.16 executable hash
  gate, network-session checks before each of four player reads, game-fiber
  scheduling, explicit failures and bounded JSON receipts.
- Generic harness contains no engine API; GTA profile/callbacks are isolated.
- Hash-pinned NuGet development SDK 1.124.0, fixed compile-only operator tool,
  no MSBuild/custom compiler flags, SDK redistribution or plugin execution.
- Four source/manifest files are byte-identical in main and coding workspace
  `897b9243-fd7e-42f4-a46a-d1b814a33a81` (physical copy is under sibling
  `SMELTERV2/coding/`, not a Docker-only filesystem).
- Staged package: `.smelter/mod-packages/gta-native-read-probe-20261028/`.
  Only our DLL, README, manifest and checksums. No RPH/LSPDFR/SDK binary.
- Plugin hash `456c10067fddea64829be2fe3bc41d44b372f853332b93756f6a0d3470033705`.
  Build receipt under `.smelter/managed-builds/c8e65992-49e1-43eb-a25d-005da1f5b16a/`.

The 7 probe tests run a reviewed, fake-callback fixture executable with **no**
RPH reference. The plugin itself is never executed by tests/the builder. Setup
159 OK; dashboard 805 OK (9 skipped); final catalog 25 OK; coding-copy Lua
10/10, four frozen contracts 128/128, Python mods 14 tests (1 C++ sample skip).
Source/build tree is `ad0578912e6cbaed9c70429f826a4fa0f0e27d3ce85cac08ac22664de4a4dd65`.
Gameplay sources from the earlier promotion did not change in this work.

## Live gates still open

1. Acquire the **author-distributed Enhanced RPH runtime** whose release notes
   list 1158.16. Backend download returned a redirect loop; there is no archive
   hash or installed runtime. Do not use a Legacy runtime or substitute the SDK.
2. When the creator is ready for a supervised game run, record runtime/executable
   hashes, prepare only the documented runtime plus our probe, then load it in
   Story Mode. Do not change security settings as a hidden dependency.
3. Collect RPH loading logs and the `%LOCALAPPDATA%/SMELTER/runtime-probes/`
   report. Check exact executable/plugin hashes, runtime assembly, four valid
   samples and all network checks. A self-reported JSON file alone is not proof.
4. Then design/verify the Lua host or explicit transport and the six native
   provider capabilities. The C# diagnostic does not execute the Lua controller.
5. Only after those gates, ask Qwen through SMELTER to implement the native
   gameplay adapter/bootstrap in small scoped tasks, then a single controlled
   cougar placeholder. Raptor assets, ARK rendering/mesh integration, taming,
   shops and riding are later work; the full vision is in the GTA–ARK handover.

## Runtime and model coordination

Dashboard at `127.0.0.1:8769`; the private URL is in
`.smelter/dashboard-knowledge.stdout.log` (never commit the token).
The Codex-side database and existing grants are preserved. No new access grant.
Headless OpenCode 1.19.3 ACP is on port 4096; native session idle. Watchdog is
running; prior Qwen task `0bc75ea8f2094427a1fcc640b1bbf118` ended GREEN, retries 0.
Its receipt `4bc813be-893c-4eea-93c2-de81dfc5862d` predates this probe and is
historical Lua evidence. Fresh operator regression receipts are in the probe
checkpoint; do not claim Qwen finished the new C# task.

Automatic approval review rejected a new Qwen probe-edit dispatch, returning
only `blocked by policy`. No equivalent dispatch was retried. Operator-owned
diagnostic/tooling preparation was completed as the narrower alternative.
Keep Qwen at 131072 context / 8192 output and frozen contracts operator-owned.
No inference is queued. Never auto-grant or silently select simulation.

Both root requirement files and the mod runtime catalog document every new
tool/dependency. The SDK cache and private build/package/log files are ignored;
only our source, lock metadata, diagnostics and documentation belong in Git.
