# SMELTER Raptor progress review — 26 October 2026

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
