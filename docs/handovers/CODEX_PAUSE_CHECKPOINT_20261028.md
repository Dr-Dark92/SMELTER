# Paused checkpoint — 28 October 2026

The user requested a checkpoint and a pause. **Do not resume work or inference
until the user asks.** The watchdog is disabled and stopped; the native observer
is stopped. The dashboard remains available on port 8769. The current private
launch URL is in `.smelter/dashboard-knowledge.stdout.log`; never commit it.

Branch: `feature/agent-stack-game-mods`. HEAD remains `876352f` after `17073e6`.
This continuation is uncommitted and unpushed. No files were staged. Never stage
or archive the unrelated `dw3_decomp-main/`.

Read this checkpoint first, then the top of `docs/CURRENT_HANDOVER.md` and
`docs/GTA_PREDATOR_ADAPTER.md`. Older handovers describe earlier revisions.

## Verified main-tree progress

- Qwen fixed the redundant target-description range bug. The reviewed controller
  is `mods/gta-ark/Mods/GtaArkLink/Scripts/predator_controller.lua`, SHA-256
  `5e2077c84320490218688cb42f94127cc20d436eb2735622ab137873ff3e95ab`.
- Operator-owned `predator-controller-v1` now has **52 checks**. Its new
  acquisition/retention scenarios run at both existing unit scales. A disposable
  reference passes; the redundant-description mutant fails exactly four new
  checks while passing the prior 48. Verifier SHA-256:
  `3a3b3b8d4069b3ce238cd309e7c878bce911e4e497fc7d60118027ab228a3b02`.
  The workspace registry was migrated with an audited reason. Policy remains
  **30/30**, verifier `b303d3d738ee98a847174e706d15264c091731c23459d2c2ba9a4c59854680ea`.
- Qwen's real-policy editable test was recovered from its passing checkpoint and
  promoted: `mods/gta-ark/tests/test_predator_controller.lua`, SHA-256
  `18b8b86d0a64d6b7a1d90809c055754a2be452eb3d45faddb944913d3e271358`.
  It imports the real modules and tests human movement/attack, fake-clock
  cooldown and loss on death. The operator's independent baseline passes;
  bypassing eligibility and using the wrong actor for movement both exit 1.
  These intentional mutants are classified ERROR by the current custom-assert
  classifier; neither is a production failure or a claimed RED receipt.
  Proof: `diagnostics/PREDATOR_POLICY_TEST_PROOF_20261028.json`.
- Test limitation: the npc/police/player labels currently repeat the same
  normalized human fixture. Distinct native role classification and explicit
  command-target spies remain future checks. Combined frozen checks independently
  cover target identity. Do not call this native NPC/cop/player verification.
- Main-tree profiles after promotion: **Lua 7 programs GREEN; mods 14 tests GREEN**.
  Logs/summary: `.smelter/codex-main-{lua,mods}-20261028.log` and
  `.smelter/codex-main-profiles-20261028.json`.
- Infrastructure after the operator changes: **796 dashboard tests OK (9 skipped),
  144 setup tests OK, 78 Node tests pass**. Private logs are
  `.smelter/codex-{dashboard,setup,node}-20261028.log`.
- Promotion identities and source hashes: `diagnostics/PROMOTION_20261028.json`.
  Requirements and frozen-acceptance documentation were updated. No tool/package
  was installed. All evidence is offline; no game was launched or modified.

## Coding copy: unpromoted adapter draft is ERROR

Workspace: `897b9243-fd7e-42f4-a46a-d1b814a33a81`.
Physical root:
`C:\Users\Dr.Dark92\Documents\ChatGPT\SMELTERV2\coding\897b9243-fd7e-42f4-a46a-d1b814a33a81`.

Current coding-copy tree:
`b6233f0219d2b100403ebe3c6b5c4909b0bcb4ad6d5a73665e5ed359d3295156`.
Latest Lua receipt: `a70f79db-57ac-45eb-8b89-e9e8586bb615`, **ERROR** in the
editable suite. Protected controller/policy acceptance remains GREEN. Earlier
GREEN receipts do not describe this new adapter-draft tree.

Unpromoted draft files:

| Relative path | SHA-256 |
| --- | --- |
| `mods/gta-ark/Mods/GtaArkLink/Scripts/engine_adapter.lua` | `cecd559ce428bd179e068467b6970a9a7b1673e53676a5af5396fcdf92b27fcb` |
| `mods/gta-ark/tests/test_engine_adapter.lua` | `94aa5c79e17fdaf323f6ef9d5e354f7642cad2c3057f52d82147de8497298e62` |
| `mods/gta-ark/Mods/GtaArkLink/profiles/gta_cougar.lua` | `ac49c9fdbda545271eb05547704f3002593c6eebe7028f70a33c1f52075fe1f0` |

The profile is in the wrong location. Intended path is under
`Mods/GtaArkLink/Scripts/profiles/`, so the existing Lua path can load
`require("profiles.gta_cougar")`. Do not silently create more alternate copies.

Code review rejected the draft because it:

- calls `pairs` before checking non-table providers and misreports missing capabilities;
- wraps position as `{position=...}` and candidates as `{cand=...}`;
- equates `pcall` success with admitted movement/attack/stop, swallowing refusals;
- defines a duplicate, recursively self-calling `validate_provider`;
- selects simulation without an explicitly supplied fake provider and rejects
  every real provider unconditionally;
- has weak/incomplete adapter tests, an undefined `tolower`, and a wrong profile
  import path.

**None of these three files was promoted.** Main `engine_adapter.lua` and
`raptor_system_main.lua` still contain the older prototype behavior and remain
pending. Do not claim the adapter or entry wiring is finished.

Last saved GREEN coding copy before this draft:
`f5d3a4635a0986b91f9c140f31fdc803ce8795496556c2725cf89b181027f9a8`.
Lua `08a6f1b3-a405-44fa-a59d-cae855a05b7e`, mods
`ff186455-2417-4342-a88b-45810bf2d5fe`, explicit GREEN under watch
`077c2b84755b4e35a0bee0d23238d6f9`, zero nudges. Preserve this checkpoint and
the successful test; never restore the load-only test to manufacture GREEN.

## Native sessions and pause state

- Original Melty UI conversation `ses_e873d493effeIa6L0ZxcaFq5nd` is preserved.
- A fresh root OpenCode session in Melty's backend was used for the test:
  `ses_e7e475992ffecLCoawxqFI9uax`. This did not create a new Melty UI conversation.
- Last adapter session: `ses_e7e2fe04effe9czeNNkEuMhdgV`, same project directory
  and coding UUID. Its watch `03b28e3b6ac043c7a490d1fef775f7b5` is cancelled,
  retries 0, reason `native_cancelled`. Native `/session/status` was empty;
  permissions/questions were empty when paused. No fabricated end flag.
- The observer retains the last exact binding but is disabled/stopped. The
  watchdog config is disabled and its process was stopped. Journals were retained.
- Dashboard uses the existing Codex-side database and seven existing grants.
  Neither was reinitialized or expanded.
- Model alias remains `qwen3.5:35b-a3b-128k`, **131072 context / 8192 output**.
  Thinking/tools variants were used per task, without raising limits.
- Fresh sessions and per-session tool allowlists reduce irrelevant context and
  prevent rollback loops. Last coding task allowed only read/list/context/recovery,
  whole-file proposal, apply, test and finish. It denied other tools; this is an
  operator-selected task scope, not a new automatic SMELTER feature or access grant.

## Resume only when asked

1. Verify branch, main hashes, coding-copy draft hashes, Docker and the saved
   receipts. Preserve both the verified main tree and the failed draft archive.
2. The next planned operator work is a generic provider-admission frozen contract:
   reject malformed/missing providers and each absent capability; preserve exact
   read results, actor/target arguments and command refusals; require explicit
   simulation; fail unsupported real initialization and spawn honestly. **This
   contract has NOT been implemented or registered yet.** Only the policy and
   predator contracts currently exist. Prove a disposable reference and mutants
   before registration, then have Qwen repair the draft against that evidence.
3. Keep provider admission simple: validate a table and six function fields;
   forward their outputs without inventing wrappers or native success. Native
   provider implementation and runtime proof remain separate.
4. Correct the profile location and meaningful adapter tests through Qwen. Then
   wire a passive entry module to the real controller/policy with explicit
   injected adapter/profile/clock. Remove automatic simulation, fabricated
   spawns and string-ID `table.remove`. Test those paths before promotion.
5. After changing tool code, refresh Melty's MCP process and the watchdog; migrate
   changed verifiers explicitly. The dashboard also needs refreshed in-process
   definitions. Use fresh bounded root sessions and small numbered prompts that
   say "always call a tool in each reply". Do not automatically grant access.
6. Re-enable the watchdog explicitly on resume (operator API
   `watchdog_store.configure(Path.cwd(), True)`), then
   `python tools/setup/manage_task_watchdog.py start`. Re-start/rebind the
   observer through its revision-checked API before a new task. This is not
   permission to resume while the user has requested a pause.
7. Current GTA executable is 1.0.1158.16, while the author's checked support list
   remains 1.0.1158.13. Checked loader paths are absent; GTA Lua hosting is also
   unverified. Clear the gates in `docs/GTA_PREDATOR_ADAPTER.md` and the GTA–ARK
   handover before any in-game claim. Do not patch version checks or overwrite
   a later working setup based on historical notes.

Commit/push only if the user asks. No further model work is scheduled.
