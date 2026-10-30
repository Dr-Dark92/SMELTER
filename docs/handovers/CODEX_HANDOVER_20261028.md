# Handover to Codex — 2026-10-28, from Claude

**Later checkpoint: work is paused at the user's request. Read
[CODEX_PAUSE_CHECKPOINT_20261028.md](CODEX_PAUSE_CHECKPOINT_20261028.md) before
acting on the historical next steps below.**

Read this first, then [CURRENT_HANDOVER.md](../CURRENT_HANDOVER.md) (top
section) and [the GTA–ARK handover](GTA_ARK_MASHUP_HANDOVER_20261028.md).

## Where things stand

- Branch `feature/agent-stack-game-mods`. Handover commit **`876352f`** follows
  checkpoint **`17073e6`**. Both were local and unpushed at continuation start.
  See the top of `docs/CURRENT_HANDOVER.md` for newer uncommitted work.
- `dw3_decomp-main/` is the user's own untracked work. Never stage it.
- Everything verified is **offline**: fake adapters, plus Docker Lua 5.4 and
  Python. No GTA or ARK runtime behavior has been verified.

### Verified results (main tree, after promotion)

| Check | Result |
| --- | --- |
| Lua profile (`mods/gta-ark/tests/test_*.lua`) | GREEN, 7/7 programs |
| Mods profile (Python) | GREEN, 14/14 |
| Frozen `entity-policy-v1` | 30/30 |
| Frozen `predator-controller-v1` | **48/48** (verifier SHA `c5478a76…`) |
| Dashboard / setup / Node suites | 795 OK (9 skipped) / 144 OK / 78/78 |

The controller is `mods/gta-ark/Mods/GtaArkLink/Scripts/predator_controller.lua`
(SHA `789c37c8…`). Qwen wrote it through SMELTER, starting from
`scaffold_contract_subject`. The explicit GREEN finish receipt is
`d970f26f-b137-4779-93ff-a4ed69491909` (watch `93ad3ee2`). Claude
re-verified it independently and reviewed the code. The promotion manifest
is [diagnostics/PROMOTION_20261028.json](../../diagnostics/PROMOTION_20261028.json).

### The controller contract

The generic, game-neutral controller is
`new(deps) -> controller | nil, reason`, and its `deps` table is:

| Key | Contents |
| --- | --- |
| `adapter` | Six functions: `position(id)`, `describe(id)`, `candidates(actor_id, origin, radius)`, `move_to(actor_id, target_id)`, `attack(actor_id, target_id)`, `stop(actor_id)` |
| `evaluate` | `evaluate(entity, policy)`; normally the `entity_policy.evaluate` function |
| `policy` | The policy table passed to `evaluate` |
| `clock` | Function returning the current time |
| `profile` | `detect_radius`, `attack_radius`, `lose_radius`, `attack_cooldown` |

`controller:update(actor_id)` returns
`{action = idle|move|attack|wait|lost|error, target_id, reason}`.

Game-specific code (native calls, units, tuning) belongs in an adapter and
profile, never in the controller. The authoritative text and the interface
checklist are in `tools/dashboard/acceptance_contracts.py` (`DEFINITIONS`).

## Workspace and runtime facts

- **Coding workspace** `897b9243-fd7e-42f4-a46a-d1b814a33a81`, physical copy
  `C:\Users\Dr.Dark92\Documents\ChatGPT\SMELTERV2\coding\897b9243-…`. Its
  acceptance registry lists `entity-policy-v1` and `predator-controller-v1`.
  Verifier migrations are logged in `acceptance-migrations.jsonl` beside it.
- **Dashboard.** Claude started it after a PC reboot: port 8769, PID 46328.
  It still uses the **Codex-side database**
  (`…\Packages\OpenAI.Codex_2p2nqsd0c76g0\LocalCache\Local\SMELTER\data\smelter.sqlite3`)
  and has 7 access grants. Get the current link from
  `.smelter/dashboard-knowledge.stdout.log`, and never commit the token.
  - This process started at 09:14, before the latest tool edits. Reload it
    when convenient so its in-process code matches the commit.
- **Watchdog.** PID 51636, last restarted at 11:17 with the current code. The
  latest watch, `93ad3ee2`, ended GREEN.
- **Docker Desktop** was started manually after the reboot. It is needed for
  every test profile.
- **Melty / OpenCode.**
  - Melty reuses one long session, `ses_e873d493effeIa6L0ZxcaFq5nd`, in
    `C:\Users\Dr.Dark92\Melty\grand-theft-auto-v-enhanced-ark-survival-ascende-2`.
  - Its MCP tool process is spawned by `opencode acp`; the last restart was
    11:44.

### Rules learned the hard way

1. **After changing SMELTER tool code, restart Melty.** Its MCP process
   imports modules once. A changed `acceptance_contracts.DEFINITIONS` (for
   example, a new check count) otherwise causes count-mismatch ERRORs.
2. **Restart the watchdog after changing `watchdog_native.py`.** Its
   resumable-tool list loads once; unknown tools park recovery in
   `wait_scope_review`. Kill the PID shown by
   `python tools/setup/manage_task_watchdog.py status`, then run `... start`.
3. **Re-pin a changed verifier with**
   `python tools/setup/register_acceptance.py --workspace-id <id> --contract <id> --migrate "<review reason>"`.
   Do this only while Qwen is idle; a changed verifier fails closed until it
   is re-pinned.
4. **Callers that need the graph must pass `detail: "full"`.** The default
   `coding_workspace_context` is now a compact summary. `native_progress.py`
   and `dashboard_api.py` were fixed to request the full view.
5. **Expect slow, compacting runs.** The Qwen 35B model (24.7 GB) only
   partly fits in 16 GB of VRAM. The Melty session sits at 110–128K
   tokens and compacts in most runs; each step at that size takes minutes.
6. **Qwen often ends a turn after announcing its next step.** The watchdog
   nudges it, with at most three nudges, and they get used up quickly.
   Prompts that say "always call a tool in each reply", with numbered small
   steps, worked best.

## What was built this session (all in `17073e6`)

| Area | Change |
| --- | --- |
| Promotion | Policy/controller/Raptor prototype scripts and 5 Lua tests copied into `mods/gta-ark` with hash checks. The production README and runtime_requirements were kept (they are newer); `ark/` alternate copies and the backup were excluded. |
| Frozen contract | `predator-controller-v1`: 48 checks, two fake adapters at ×1 and ×100 scale. It started at 42; three gaps found in review added 6. |
| Diagnostics | Frozen failures lead, with `observed:` values labelled by setup. Failing results and `coding_recovery_context` re-attach the contract text and interface checklist. |
| Syntax gate | `.lua` proposals are parsed with `luac5.4 -p` (never executed) before they are recorded. An already-broken file can still be fixed stepwise. Checkpoint restores are exempt. |
| Context budget | `coding_workspace_context` returns a summary by default (about 7.7K characters instead of 47K; the full view cost about 27K tokens). |
| Scaffold | `scaffold_contract_subject` (`contract_scaffold.py`) builds an interface-correct skeleton from a contract's structured `scaffold` spec, with TODO helpers. It is returned as a proposal and never auto-applied. |
| Recovery | Restores report `newer_versions_discarded`. `read_coding_file` prefers line paging. The watchdog counts OpenCode's synthetic `invalid` tool as a protocol error. |
| Docs | REQUIREMENTS.md, system-requirements.json, FROZEN_ACCEPTANCE.md, RECOVERY_GUARDRAILS.md, WORKSPACE_TRACKING.md, both handovers and the Mermaid diagram. |

## Next steps, in order

1. **Fix the re-describe edge (small, through Qwen).** After acquiring a
   target, `update` calls `current_distance` (which calls `describe`) a second
   time. If that fails, the code falls through to cooldown/attack without a
   verified range.
   - Fix: reuse the `d` returned by `select_target` or `current_distance`.
   - Add a frozen scenario for it first (a `describe` failure on the
     acquisition tick), then re-pin with `--migrate` and restart Melty.
2. **Write the editable test with the real policy (through Qwen).**
   `mods/gta-ark/tests/test_predator_controller.lua` currently only checks that
   the module loads. The new test should:
   - wire `require("entity_policy").evaluate` with a policy that allows
     `character` and blocks `vehicle`, using full entity records (`id`,
     `kind`, `traits`, `valid`, `alive`, `position`);
   - assert that a nearer vehicle is never targeted, that a human gets
     `move_to` and then `attack`, cooldown under a fake clock, and loss on
     death;
   - exit 1 on failure.
3. **Wire the controller into the mod.** `raptor_system_main.lua` and
   `engine_adapter.lua` still use the old prototype `raptor_aggro.lua`, which
   has fabricated targets, uses `os.time`, falls back silently to simulation,
   calls a missing `spawn_raptor`, and passes an ID to `table.remove`.
   - Build a real adapter for the chosen GTA runtime with the six
     capabilities, plus a profile in game units.
   - Unsupported capabilities must fail explicitly; never fall back silently.
4. **Clear the runtime gates in the GTA–ARK handover before any in-game
   claim.** Verify the loader, build and hashes; spawn one controlled actor;
   capture logs. A cougar placeholder must be labelled as such.
5. **Housekeeping.**
   - Reload the dashboard.
   - Consider a fresh OpenCode session per task to avoid compaction.
   - `review_coding_workspace` reports `python`/`node` profiles as never run,
     because the copy includes an unchanged `tools/dashboard`. That is
     expected, not a failure.

Keep the user's decisions: SMELTER stays universal; Qwen does the mod work
through SMELTER while the outside agent builds and verifies tools; the
131072-context / 8192-output profile is fixed; the frozen acceptance is
operator-owned; never auto-grant access; commit or push only when asked.

## Useful commands

```powershell
python tools/setup/manage_task_watchdog.py status
python tools/setup/register_acceptance.py --workspace-id 897b9243-fd7e-42f4-a46a-d1b814a33a81 --contract predator-controller-v1 --migrate "<reason>"
cd tools/dashboard; python -m unittest discover -p "test_*.py"
cd tools/setup; python -m unittest discover -p "test_*.py"
cd tools/dashboard; node --test test_*.js test_*.mjs
```

To run the production Lua/mods profiles on the main tree outside a workspace
(needs Docker), from `tools/dashboard`:

```powershell
python -c "import sys;sys.path.insert(0,'.');from pathlib import Path;import sandbox;r=Path('../..').resolve();x=sandbox.coding_test(r,r,'lua');print(x['stage'],x['counts'])"
```

To read native session progress read-only, open
`%USERPROFILE%\.local\share\opencode\opencode.db` with `?mode=ro`, then read
the `message` and `part` tables for `ses_e873…`.
