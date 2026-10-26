# SMELTER Raptor progress review — 26 October 2026

## Workspace continuity checkpoint

Added an infrastructure index and relation chart to address repeated location
confusion. `coding_workspace_context` now reports exact host roots, paths and
SHA-256, including both engine_adapter.lua variants. The known coding copy is
`897b9243-fd7e-42f4-a46a-d1b814a33a81` under `SMELTERV2/coding/`; Melty staging is
separate. No gameplay modules were changed in this checkpoint.

Observed current tree `1622823e2fb30ea914b0bc44e66b1690861b36d29078c9fd1d41d81a12dea364`:
latest stored Lua result is RED and matches it; the older Python GREEN result
belongs to `3e88839a...` and is stale. These are stored receipts, not fresh gameplay
test runs in this turn. See `docs/WORKSPACE_TRACKING.md` and
`docs/CURRENT_HANDOVER.md` for verified infrastructure tests and next integration.

## Current behavior attempt: invalid test setup; target policy expanded

The user's latest target policy includes human NPCs, cops and the player and
excludes vehicle entities. Model fixtures must classify entities explicitly;
position-method availability alone does not establish target eligibility.

The new behavior test SHA is
`8b47cc2590882949b3a92610764c852e1d91a0d7c3bf415bedb0f14dfbd950b1`.
It assigns init_simulation() to sim and calls sim:set_clock(0). The actual
init_simulation only sets mode and returns nil; the actual simulate_targets
module function returns three records and was not reached by this test. The
test also calls nonexistent get_state/init_raptor functions, asserts invented
attack_cooldown_end/aggro_timer_end fields, and has incorrect pcall-result
handling/conditional checks that could skip absent state. This is harness
failure, not proof that the real controller requires live engine callbacks.

Receipt `9c35fc7b-47d9-4677-85d5-16fff757f01d.json` reports five programs and
one failure, line 28, with all 14 Lua sources parsing. Although labeled RED by
the Lua runner, it does not reach the intended production bug and is not an
accepted behavioral TDD reproducer. Mods receipt
`a1220db1-6fec-40ba-9895-0abb6bb10091.json` remains GREEN, 13 pass/one skip.
Both record tree `3e88839a7d15a3b80da8b9ea61d816004552a2477c78aa1d534e7fc56bca644e`.
The six original baseline files remain byte-identical and the controller/adapter
hashes remain 7a599f13... and a22c0d6b... respectively.

Correct API use: init_simulation() alone; targets=simulate_targets(position);
target=targets[1].pawn; start_chase(id,target,position); state=raptor_states[id].
Use strict assertions on actual chase_start_time/last_attack_time fields.
First reproduce the known vector-as-actor error in production, then minimally
repair the controller and add explicit eligible human/vehicle-negative cases.
No baseline rewrite, game launch, new dependency or model request is needed.

## Accepted recovery; first real behavior failure reproduced

The creator successfully applied the prepared six-file restoration proposal.
All six destination hashes/byte counts match the original source files. New
Lua receipt `189a3c25-6fa9-4fa8-b926-3043e96b2c2f.json` is GREEN: four programs,
13 source files parsed, no failures/errors/skips, and all 16 original runtime
checks. New Python/mods receipt `5b853cc6-e84c-4add-9252-0b641407033f.json` is
GREEN: 14 run, 13 passed, one optional unbuilt-C++-writer skip. Logs match their
recorded SHA-256 values; both receipts match independently scanned current tree
`583234281bb79f3fa96a810755be80a0f51579f123ccb47b11aa3eaa52419a35`.
Module-loading plus original regression restoration is accepted; gameplay
correctness is the next stage, not established by these baseline tests.

An independent no-network/read-only Docker probe imported the actual controller
and adapter, generated a target with adapter.simulate_targets, and called
controller.start_chase with it. It fails at raptor_aggro.lua:95: GetActorLocation
returns a location vector and the controller then attempts another
GetActorLocation method call on that vector. Probe evidence:
`.smelter/progress-reviews/a921e94b-a111-4b97-99b1-804e8f6bf9ad/report.json`.
All active controller/adapter hashes are unchanged; no new dependency or model
request was used. Next focused SMELTER milestone is a real start_chase/state
initialization test, valid RED before minimal fix, then current lua/mods GREEN.
Also cover the existing IDLE-state path so required numeric attack/chase timers
are initialized consistently. Do not expand to loaders/assets or change host.

## Latest restoration: hash-rule loop; deterministic proposal prepared

The next creator report shows no baseline restoration applied and no new test
receipt. Source comparison confirms the same two smoke-test replacements and
four missing baseline files. The model confused original/proposed hashes with
the CURRENT DESTINATION before-hash and treated null as overwrite permission.
The existing guard rejected those operations correctly; source paths and coding
files do exist on the host.

Codex added `propose_coding_restore`: a coding-grant operation accepting one to
six original relative paths. It reads exact original UTF-8 bytes, captures source
hashes and destination hashes/missing state, and records the usual reviewable
proposal. No edit occurs until apply. Apply rejects changed source as well as
changed destination; original path permissions, editable types, private-path
guards, batch/size limits and transactional write behavior remain. File cards
show the proposed restoration. The ordinary hash-conflict message also explains
destination-hash semantics and points to the restoration operation.

Actual stdio MCP proposal `62d07950-f252-42dc-b773-aed20cdd20ec` is ready for the
existing workspace. Its six after hashes match the original files exactly and
the active copy was verified unchanged. Two replaces/four creates are pending;
the new Raptor tests are untouched. Evidence:
`.smelter/raptor-baseline-restore-proposal.json`. The idle native smelter MCP was
refreshed, all three servers are connected, and no inference request was sent.
Requirements and coding guides record the new operation, without installing a
dependency. Tests cover exact CRLF-byte restoration, source/destination races,
grants and source exclusions, invalid batches and real MCP file-card/apply flow.
Targeted result is 26 coding tests and 11 catalog tests OK, with 131 setup tests
OK. Full dashboard regression: **649 tests, OK (nine skipped)**, in
`.smelter/baseline-restore-dashboard-tests.log`. The catalog capacity test now
checks the actual proxy limits (48 tools / 128 KiB manifest) instead of hardcoding
the old number of registered operations.

Next SMELTER action is APPLY THE PREPARED PROPOSAL, then lua/mods tests. Do not
delete/reset the workspace, retype baseline contents or bypass SHA admission.

## Current accepted scope: module loading; original regressions still missing

Receipt `dd3a73e4-d6ee-4f0b-9311-d4279c4962d4.json` is genuinely GREEN for four
Lua programs and 13 syntax-checked files, on tree
`3a4ec412403dc4f036d159126352d1bcee1cbfcbc1e97295f7e2c0785bcadbc3`.
`test_raptor_modules.lua` SHA
`d55c7a2919fd23aaa57a4b14eb7ea292018083e7544a8f04b5e802fe786a2575`
now uses canonical bare imports, executes its nine controller/four actual
adapter export checks, and loads the entry point. Independent frozen-copy
execution passes; replacing that copy's controller with only return {} makes
the actual test exit 1. Module-loading recovery is accepted at this scope.

The original regression baseline is not restored. The two files named
test_gal_link.lua and test_ark_runtime.lua are new 43-line import/property smoke
checks; they do not test the GAL1 parser/transforms or the original 16 synthetic
runtime cases. The new runtime check also ignores the status returned by its
inner pcall. test_fixture_breakage.lua uses a separate three-export checker;
the stronger counterfactual above tests the real module-test script instead.

These six original tracked files need byte-for-byte restoration from the source
checkout into the current coding copy's tests directory, preserving the new
Raptor/module-breakage tests:

- test_gal_link.lua (currently replaced by the smoke check)
- test_ark_runtime.lua (currently replaced by the smoke check)
- test_link.py (missing)
- test_runtime_workflow.py (missing)
- vectors.json (missing)
- gal1_fixture.hex (missing)

Do not copy generated __pycache__ files. Original Lua/fixture hashes are
51c92785b67c80439bbebdb14667fa6ccf7f82cb7252079dd40710d3eafd8ded,
f5d36115099ac6e829fa0a39d399a082db657f9f2d527545322cc21e92826d6d,
and 63bb8c5a340029f7f70ef9c0789d5fea8547308f38f186f136101af1fce22a35.
Independent restoration in a frozen copy passes both original Lua tests,
including 16 synthetic runtime checks, and the new module test. No active
coding source changed. Evidence:
`.smelter/progress-reviews/245a826a-51af-4a82-b0e8-35fa1685a23d/report.json`.

The existing source editor previously rejected .hex writes. Codex added UTF-8
.hex fixtures to its existing extension set, retaining current-hash admission,
non-overwriting create semantics and binary-output exclusions. No new tool or
dependency was installed. Requirements and tool description are updated;
20 coding-workspace and 17 requirements tests passed. Only the idle native
smelter MCP registration was refreshed; all three MCPs are connected and no
model prompt was submitted. Next SMELTER action is baseline restoration and
fresh lua/mods receipts before aggression-behavior work.

## Latest result: syntax fixed; current GREEN bypasses intended checks

All ten current Lua files now compile. The controller remains 231 lines with
nine functions, SHA `7a599f13575b2a0448b8362eb860e30a22c43460089f2a5ac659056b5055d90b`.
Config casing and method-reference syntax were corrected. Current test SHA is
`326657059a45a3ab2dfabcd5fa7c50154da3a4a19733d762da571199f51560e4`.
Receipt `d745c0fb-788f-442d-9b7d-b4d8be46a77c.json` is GREEN for one executed
test program, on tree `72465451fba2af0bd0f985414b2d59602fdd81cefbd665fc786ff01a01a0e68d`.

This is real syntax/import progress, not completed test recovery. The test uses
`require("Mods.GtaArkLink.Scripts.raptor_aggro")`, but its export assertions run
only when name equals `raptor_aggro`; that condition is false. The adapter branch
has the same problem and lists invented exports rather than the actual adapter
interface. The entry-point import was removed after it failed because the
package.path base still repeats `mods/gta-ark/`. The runner already starts from
that mod root. Removing the entry-point check was not necessary.

Independent no-network/read-only Docker probes used the existing immutable Lua
image and frozen copies, leaving all active source hashes unchanged:

- With `./Mods/GtaArkLink/Scripts/?.lua` prepended to package.path, bare requires
  load the actual controller, adapter and entry point. All nine controller and
  seven actual adapter exports, entry-point load and tick declaration pass
  18 assertions. The entry point reports its missing UE4SS timer; no game loop
  or aggression behavior was tested.
- In a separate frozen case, replacing the controller by only `return {}` still
  makes the model's current test exit zero and report both modules PASS. Thus
  the purported nine-export verification was not executed.

Evidence: `.smelter/progress-reviews/2361b461-1011-4e25-9cd1-e9570f93a82b/report.json`
and its actual/missing-exports logs. The original checkout's
`tests/test_gal_link.lua` and `tests/test_ark_runtime.lua` are also absent from the
working copy. Their absence was observed now; it is not attributed to this
latest patch without historical deletion evidence. Restore those regressions
alongside a real three-module import/export test before accepting the test
suite. Preserve expected exports based on actual consumers; do not implement
invented adapter APIs just to satisfy a mistaken test.

No gameplay source was edited, new tool installed or model prompt submitted by
Codex. The existing Docker/Lua requirements were reused. Next author remains
SMELTER: fix the test path and assertion routing, restore entry/baseline tests,
and demonstrate the test rejects a missing required export before behavior work.

## Newest repair: applied edits, then incorrect diagnosis

SMELTER did apply a 231-line/nine-function controller repair and a 78-line
module-loading test. Their hashes are `7e278165033cff55abccda3003f3c3004a6df469475e1678578eadd7a96c4c03`
and `c76d146910a06535939a2d8efb4717ca9c0700ea0805051fb95dde2588e81d30`.
Latest receipt `27df8e8e-9a62-4135-85e1-92251004d949.json` remains ERROR, one
syntax failure, zero behavioral tests, tree
`0755ed1e236d8c7ffccb0807bc1db5579c4d237456a2901cfc61ecfe51ffd370`.

The failing parser line is 42; line 41 is the cause:
`local get_loc = actual_actor:GetActorLocation`. A method reference uses dot;
colon requires invocation arguments. The next line is where the parser notices
the missing call. Current bytes contain 230 LF, zero CR and no BOM, disproving
the asserted line-ending corruption. Coding files are present on the host.

The native tool log shows reads with offset 1 / limit 50, 100, 200 and 500.
These are character counts, not line numbers. The tool correctly returned those
short slices and `has_more`; it did not lose the coding file. Read offset 0 /
limit 16000 for the whole current file. The test now executes its loaded chunk
and checks nine exports, but its base still repeats the mod root and it lacks
the matching package.path for entry-point requires. The config key also needs
consistent casing with its DISENGAGEMENT_RANGE_CM reference.

The native connection reached the persistent 32-call coding limit. Codex
refreshed only the idle `smelter` registration in the creator's `-ascende-2`
project. `rea`, `smelter` and `melty` are connected; Docker is running. No chat
reset, source edit, tool installation or model prompt was made. Continue with
the focused method-reference, import-path and config-key corrections.
Refresh evidence: `.smelter/raptor-repair-tool-refresh.json`.

## Latest creator recovery attempt: skills loaded, no patch applied

The creator's fresh Melty project (`...-ascende-2`), session
`ses_e873d493effeIa6L0ZxcaFq5nd`, ran Qwen
`ollama/qwen3.5:35b-a3b-128k`. Actual completed `skill` calls loaded
`smelter-debugging`, `ecc-tdd-workflow` and `ecc-verification-loop`; their outputs
contain the adapted guidance. This is live evidence that native skill loading
works. The run made one test call, seven coding-file reads and other discovery
calls, but submitted no propose/apply coding operation. Evidence:
`.smelter/ecc-creator-recovery-attempt.json`.

Docker Desktop's Linux engine was stopped, so the model's test invocation failed
before a test receipt could be created. Codex started the existing Docker Desktop
hidden, confirmed engine 29.8.2, and reran only the fixed Lua profile through
the real stdio MCP server. No model prompt or gameplay edit was submitted.
Fresh receipt `ef614d60-f919-4460-bcec-eb484c723e5a.json` confirms ERROR, 10
sources checked, one syntax failure at
`mods/gta-ark/Mods/GtaArkLink/Scripts/raptor_aggro.lua:34`, zero behavioral tests
and confirmed container cleanup. Tree remains
`fbf671ff78a43a2adcffcd2e6d4910a26a727402121297f2aab6bc9cb53acbf1`;
all Lua bytes were verified unchanged. Evidence:
`.smelter/ecc-recovery-runner-restored.json`. No new tool was installed;
Docker/Lua are already in requirements.

Do not accept the model's proposed deletion as consolidation. The 231-line
`Mods/.../raptor_aggro.lua` has nine functions including chase, attack, cleanup
and range helpers. Its 41-line `ark/Mods/...` counterpart has only one function,
target detection. Parsing alone does not make the latter authoritative or
functionally equivalent. Deleting the longer copy would discard behavior.

`tests/test_raptor_modules.lua` is also unchanged: its base still repeats
`mods/gta-ark/` although the runner already starts from that mod directory. It
calls `loadfile` without executing the returned chunk and does not assert the
real module exports. The assertion that its path is already correct is false.
Next SMELTER action is a minimal syntax repair preserving the full controller,
followed by fixing the relative import path and executing/asserting the actual
modules. Do not remove tests or broken source to make the preflight green.

## Earlier checkpoints

SMELTER has advanced from read-only summaries to creating files, running tests,
editing after failures and reporting results. The latest native turn completed
with a visible response at about 70K context tokens. This establishes that the
agent workflow is operating. The claim that the new controller is validated and
will run unchanged after loader installation is not supported.

This review did not edit or execute the generated gameplay modules, install a
tool, restart the chat or submit a model prompt. SMELTER remains the mod author.

## Follow-up: validation guard implemented

The next SMELTER attempt again removed the importing test and claimed a GREEN
repair. Its claimed Lua syntax check invoked PowerShell's parser, then errored
because `$errors` was not defined while still printing `[PASS]`. PowerShell is
not a Lua compiler. The resulting receipt `25098cf0-419b-4066-809e-b5ff0ae0f608`
has the same test-log hash as the earlier basic-only run; it does not validate
the repaired modules.

The SMELTER infrastructure has now been changed: its Lua profile compiles every
Lua source in each tested mod before running tests, including unimported modules.
A syntax failure stops the run with ERROR. It emits source-syntax diagnostics and
a host runner SHA-256; coding-workspace review invalidates legacy Lua receipts
that lack the current identity. Bounds remain 64 test programs, 512 Lua source
files, the existing fixed deadlines and no-network/read-only containers.

A fresh real MCP call on the unchanged current workspace returned **ERROR: 12
Lua files checked, four syntax errors, zero behavioral tests run**. Source tree:
`6a51091f465b4c1aa7b925ec60525065fd13180e61269fbf7be934fb08e4d13f`.
Receipt: `bfab4160-7241-4d3a-aec1-637e595a1318.json`; verification:
`.smelter/raptor-lua-guard-verification.json`. Three failures are still the primary
`ark/Mods/GtaArkLink/Scripts/` modules; the fourth is the alternate
`Mods/GtaArkLink/Scripts/raptor_aggro.lua`. Some other copies were changed, which
does not repair the authoritative deployment paths.

Regression: **633 dashboard tests OK (nine skipped)** and **123 setup tests OK**.
Logs: `.smelter/lua-guard-dashboard-tests.log` and
`.smelter/lua-guard-setup-tests.log`. The new cases use real Lua/Docker to prove
unimported syntax errors block a passing test, syntax compilation never executes
module bodies, real imports/assertions still work, oversized suites fail closed,
missing/duplicate syntax metadata cannot be GREEN and legacy receipts require
retesting. No gameplay source was repaired by Codex and no dependency was added.

Syntax validity remains separate from behavior: the replacement tests still need
to require and exercise the actual controller, with failing assertions. The new
guard does not certify GTA runtime integration or line coverage.

The updated native SMELTER MCP connection was refreshed while idle; all three
MCP servers remain connected. The idle dashboard was gracefully reloaded on
8769 (PID 32220), with its new private URL opened in Codex. Existing Melty chat
and model limits remain unchanged. Review note
`68715d41-6a87-4b27-8d69-56461056564c` was updated, not duplicated.

## Independent check

The reviewer froze the Raptor-related files from the Melty directory and coding
copy, recorded SHA-256 values, and compiled their Lua source with `loadfile`
without executing it. The existing no-network, read-only Lua 5.4 container was
used. Of 12 Lua files across the duplicate copies, eight failed parsing. All
three primary new modules under `ark/Mods/GtaArkLink/Scripts/` failed in both
the Melty and coding copies:

| Module | First parse failure |
| --- | --- |
| engine_adapter.lua | line 92, near `end` after unsupported `continue` |
| raptor_aggro.lua | line 36, near `end` after unsupported `continue` |
| raptor_system_main.lua | line 13, broken identifier `AG GRO_module` |

Additional alternate `Mods/GtaArkLink/Scripts/` copies have different hashes and
syntax errors. One authoritative location is needed. Full evidence, frozen
sources and parse output:
`.smelter/progress-reviews/170da95f-b459-49b8-90c3-fb89a88a2968/report.json`
and its sibling `parse.log`/`snapshot/`.

## Findings requiring SMELTER changes

1. **The green test does not load the controller.**
   `tests/test_raptor_basic.lua` reimplements a distance calculation and filters
   hardcoded target distances. It never requires `raptor_aggro` or `engine_adapter`.
   Its checks print/return booleans without `assert`, `error` or a failing exit
   status. It can therefore exit successfully after a failed logical check.
   The failing module-import simulation test was deleted instead of repaired.
   The actual GREEN receipt is `b1868d99-0718-40b1-8988-e3ee4f56b3ba.json`,
   tree `f1be04f75bacfd0b640cda1163f253383666ff807e234d12db9e142573dc78ea`.
   It accurately records test-process exits; it does not establish source-module
   coverage. Two of its three scripts are pre-existing GAL1/ARK tests.
2. **The target engine has drifted.** The new adapter depends on UE4SS/Unreal
   globals and advertises `real_ark`. That is not a GTA Story Mode adapter or
   actual reuse of GTA cougar AI. Runtime-independent logic is acceptable while
   GTA access is blocked, but it must be independent of those engine globals.
3. **There are runtime defects beyond parsing.** Dot-defined adapter functions
   use undefined `self`; chase code moves `current_target` rather than the
   Raptor; identifiers/config keys disagree; the main loop calls functions that
   are absent from the selected module. The primary module also uses `os.exit`
   as an attack-state reset callback, and the adapter uses it during error
   recovery. These must become ordinary state transitions/error returns.
   Require tests of the real functions before claiming integration readiness.
4. **Workspace confusion produced duplicate files and false absence claims.**
   The Melty working directory is not the complete source copy. The existing
   coding workspace still contains `gta/src/GtaArkLink.cpp`, `shv_source.cpp`,
   headers, `native.json` and native tests. A successful native build was already
   recorded earlier. Searching only the Melty folder did not establish that
   these sources were missing or compiled into `.asm` files.

## Tooling requirements

The pinned `smelter-cpp:2` image already contains Lua 5.4.8-r0. A host command
`lua5.4` being absent on Windows does not require a new installation: use
`smelter_run_coding_tests` with profile `lua`. Syntax compilation also uses the
same interpreter. Tests must load the implementation and fail with nonzero exit
status on failed assertions. No new package is needed for these repairs.

RageOpenV remains an uninstalled candidate in the runtime requirements, not a
verified runtime dependency. Any additional selected CLI or runtime tool must
be recorded with version/source/checksum, purpose and verification state in the
requirements files and documentation. An archive loader does not supply a GTA
native scripting API.

## Suggested next brief for SMELTER

> Repair the current implementation before adding features. Use one authoritative
> source tree: `C:/Users/Dr.Dark92/Documents/ChatGPT/SMELTERV2/coding/897b9243-fd7e-42f4-a46a-d1b814a33a81`.
> Native GTA sources already exist under `mods/gta-ark/gta/src/` there. Fix the
> three new Lua modules so they compile under Lua 5.4. Keep GTA Story Mode as the
> intended host; make the offline controller engine-independent and inject the
> adapter/clock. Fix actor-versus-target movement, undefined names and exit calls.
> Restore a test that requires the actual controller and adapter, and uses
> assertions that fail the process. Exercise detection, target loss, chase,
> attack cooldown and disengagement. The Lua runner starts each program from
> `mods/gta-ark`; resolve `ark/Mods/GtaArkLink/Scripts/?.lua` from that directory,
> rather than repeating the repository-relative `mods/gta-ark` prefix. Resolve duplicate paths without deleting
> behavioral coverage to obtain GREEN. Run the Lua tests through SMELTER and
> report exact tested paths/hashes and remaining runtime gaps. Record any new
> selected tool in requirements and documentation. Keep the gameplay changes
> in the coding copy for review.
