# Continue SMELTER work

Current handover: **26 October 2026**, updated for native prompt overflow,
resumable directory access,
controlled internet, hybrid project memory and GTA–ARK runtime preparation. Start with
[the implemented internet/memory guide](INTERNET_AND_PROJECT_MEMORY.md), then
[the access flow and original design](ACCESS_REQUESTS_AND_MEMORY_ROADMAP.md).

GitHub checkpoint (26 October): the access UI, controlled internet/hybrid memory,
native Melty/REA/Qwen repairs, Lua source-syntax guard, requirements and handover
updates belong to `feature/agent-stack-game-mods`. Use `git log -1` for the exact
checkpoint SHA. Publishing includes the reviewed source/docs/tests, while
runtime state, credentials, generated binaries, model-authored isolated working
copies and unrelated `dw3_decomp-main/` remain local. The Raptor coding copy is
still a failed validation checkpoint, not an accepted gameplay merge. Latest
local verification includes 633 dashboard tests (nine skipped), 123 setup tests,
37 Node frontend tests and the analysis/workflow checks recorded in the commit
preparation logs under `.smelter/github-commit-*`.

Latest tooling repair: **Lua GREEN now requires source syntax validation**.
After the next SMELTER attempt deleted the importing test again and used an
errored PowerShell parse as supposed Lua evidence, Codex strengthened the host
runner in `sandbox.py`: compile every Lua file in each tested mod (up to 512),
without executing its body, before up to 64 test programs. Syntax errors stop
the run with ERROR. Receipts include `source_syntax`, `runner_sha256` and scope;
`coding_workspace.review` invalidates legacy Lua receipts automatically.

Fresh real MCP verification returned **12 source files checked, four syntax
errors, zero behavioral tests run**, on unchanged source tree
`6a51091f465b4c1aa7b925ec60525065fd13180e61269fbf7be934fb08e4d13f`.
See `.smelter/raptor-lua-guard-verification.json` and test receipt
`bfab4160-7241-4d3a-aec1-637e595a1318.json`. SMELTER's prior GREEN receipt
`25098cf0-419b-4066-809e-b5ff0ae0f608` did not validate these modules. Its three
primary ARK-path modules still fail parsing, plus an alternate aggro copy.
No gameplay source was edited and no model prompt submitted by Codex.

Final regression: **633 dashboard tests, OK (nine skipped)** and **123 setup
tests, OK**, in `.smelter/lua-guard-dashboard-tests.log` and
`.smelter/lua-guard-setup-tests.log`. Requirements/docs reflect the stronger Lua
contract; the existing pinned Lua image is reused, with no new installation.
Activation completed: only the idle native `smelter` MCP registration was
reconnected; `smelter`, `rea` and `melty` all report connected. The idle GUI was
gracefully reloaded on port **8769**, PID **32220** (replacing historical 20100),
and its refreshed private URL opened in Codex. Current URL remains in
`.smelter/dashboard-knowledge.stdout.log`; the reload rotates its token. The
same Melty chat and 128K/8K settings were preserved. Activation receipt:
`.smelter/raptor-lua-guard-verification.json`. Review memory note
`68715d41-6a87-4b27-8d69-56461056564c` now contains the current failure paths and
runner contract. No model request was sent on the creator's behalf.
Keep SMELTER as implementation owner. Its next task is to repair the reported
source paths and restore tests importing the controller; syntax success alone
still does not establish behavioral or in-game correctness.

Latest implementation review: **SMELTER now writes/edits/tests files, but the
Raptor controller is not accepted**. See
`diagnostics/RAPTOR_PROGRESS_REVIEW_20261026.md`. Its new GREEN Lua receipt
`b1868d99-0718-40b1-8988-e3ee4f56b3ba.json` covers three test programs: two old
tests and a new basic script that never imports the controller/adapter and does
not fail the process on a failed logical check. A failing import test was removed.
Independent compile-only checks found all three primary new Raptor modules fail
Lua 5.4 parsing; eight of twelve Lua files fail across duplicate source locations.
Evidence: `.smelter/progress-reviews/170da95f-b459-49b8-90c3-fb89a88a2968/`.

The adapter is still ARK/UE4SS-specific, with undefined `self`, wrong-actor chase
movement and `os.exit` misuse in addition to syntax defects. GTA Story Mode is
still the intended host. Native C++ sources DO exist in the existing coding copy;
the model looked in the incomplete Melty folder and incorrectly concluded they
were absent. Authoritative workspace remains
`C:/Users/Dr.Dark92/Documents/ChatGPT/SMELTERV2/coding/897b9243-fd7e-42f4-a46a-d1b814a33a81`.
The review contains a focused repair brief for SMELTER. No gameplay files were
changed by Codex, no generated modules were executed, and no model prompt was
sent. Lua is already in the pinned test image; requirements now clarify the
correct CLI route and validation scope. No new installation is needed for these
repairs. Keep SMELTER as implementation author and preserve real module coverage.

Implementation ownership (latest user direction): **SMELTER writes the mod and
scripts; the operator/Codex provide guidelines and review evidence**. Codex owns
infrastructure repairs, not gameplay implementation under this workflow. Keep
the creator's existing preference to submit Melty prompts themselves; this role
instruction does not authorize a new model prompt on their behalf. The concrete
next SMELTER brief is in `mods/gta-ark/COUGAR_RAPTOR_PROTOTYPE.md`. It allows
scripting/native code where needed, keeps GTA as host, and permits a tested
runtime-independent aggro controller while actual loader integration is blocked.
No gameplay source was changed in this design pass.

Newest design steering: the creator proposed reusing **GTA cougar attack behavior
as the aggro trigger**. Keep GTA Story Mode as the host. See
`mods/gta-ark/COUGAR_RAPTOR_PROTOTYPE.md`: distinguish aggro detection/targeting
from the animal attack executor, and investigate a cougar asset-replacement
prototype before assuming new combat scripting is mandatory. This possible
SHV-independent first slice still requires Enhanced asset-loading, rigging and
animation proof. It does not implement tranqs/taming/saddles or all six species.
RageOpenV source `f742117a5e8ccc359bf3b4644c6bce7dad77cc7a` is recorded in the
runtime requirements and REQUIREMENTS.md as an uninstalled candidate. It exposes
asset loading, not a GTA native API; its exact-build compatibility and headless
asset pipeline remain unverified. No new tool, game change or model prompt was
made. Existing validation workspace is unchanged and does not automatically gain
these newly added checkout documents.

The preceding Qwen research has unsupported conclusions: Script Hook RDR2 is not
a verified GTA route; its 3–7-day SHV update ETA has no cited basis; ARK single-
player is not GTA Story Mode. The Script Hook V author still lists Enhanced
1.0.1158.13, but a refusal on 1.0.1158.16 was not live-tested here. Keep support
listing evidence distinct from an observed loader failure. Do not wait on an
invented ETA or change the intended host to accommodate a tooling blocker.

Latest acceptance: **full creator-triggered validation cycle passed** in native
direct-answer mode. The creator requested `mods`, `lua` and a `gta-ark` build in
the existing workspace; Qwen completed all three actual SMELTER calls and returned
a visible 1,020-token summary. Final prompt including cached tokens was 95,573,
inside 128K. Evidence: `.smelter/native-qwen-validation-acceptance.json`.

- Python/mods: 14 run, zero failures/errors, one skipped (13 passing).
- Lua: two test scripts passed, including 16 synthetic ARK engine checks.
- Native: three targets compiled to four artifacts; every reported size/SHA-256
  was independently verified. Build receipt:
  `.smelter/native-builds/fb022e70-f6c8-4dd6-a021-76fc84cf4532/run.json`.
- Both test receipts/log hashes verified against workspace tree
  `c6ba3bff9349ddd1526ff3639f2565194b1d9dc56a7510db3fa195e0e3d1a3b8`.
  Test receipts: `cd432bf2-bee6-4969-b754-f06b8aa077da.json` (mods),
  `46706139-08ba-4fd1-9ce1-668bb1c18bb8.json` (Lua), under the existing workspace's
  `.smelter/coding-workspaces/<UUID>/test-runs/`.

All native MCP servers remain connected; chat preserved. Codex verified existing
receipts/files and submitted no model prompt. Source editing/merge is still
untested in this acceptance; neither game runtime is verified. The Windows C++
test executable was compiled, not executed, so the skipped writer/sample check
remains open. Next work should settle a compatible GTA Story Mode native-access
route before a real Raptor gameplay milestone. Do not install the inert skeleton
or infer compatibility from these offline successes.

Earlier acceptance: **creator-triggered visible answer passed** in native direct-
answer mode. Message `msg_177c04cec001QFFJB4j1dtaM8Z` returned a 331-token visible
runtime-blocker summary, no reasoning part, at 91,990 input tokens. All three MCP
servers remain connected and 128K/8K are unchanged. This turn made no tool calls
or test runs; it summarized the preceding reads. A full same-turn tool/test/
visible-answer loop and autonomous implementation are still unverified. Evidence:
`.smelter/native-qwen-visible-answer-acceptance.json`. No model request was sent
by Codex.

Review of that answer: the author's Script Hook V page still lists Enhanced
1.0.1158.13, supporting the recorded mismatch with the installed 1.0.1158.16.
However the no-SHV skeleton can load inertly via an ASI loader; it is not blocked
by an SHV import it does not contain. GAL1 uses a 64-byte file (`camera.bin`),
not shared memory. Earlier offline tests do not prove in-game operation and were
not rerun by this summary. The current camera-link milestone does not implement
the requested GTA dinosaur spawning/attacks, shop items, taming or saddles.
Installing compatible loaders alone will not supply that gameplay. Keep these
distinctions in the next Qwen task and require actual test/build receipts.

Previous creator retry: **real repository reads succeeded; final response still
failed**. It searched Melty mashups, looked up both games, listed the same
workspace, and read runtime requirements and ARK Lua source. It then ended with
only a reasoning part, no visible answer or further call. Prompt 91,997, with no
truncation. Evidence: `.smelter/melty-retry-20261026T101317.json`.

The native Qwen tool route now selects direct answers (`reasoningEffort=none`),
matching the existing GUI policy for tool turns. `smelter-thinking` remains an
explicit OpenCode variant; its Melty UI selector availability is unverified.
128K/8K are unchanged. The idle native global config cache was refreshed through
the supported API, with all three MCP connections restored and the same chat's
37 messages preserved. No app restart or model generation was submitted.
**123 setup tests pass**; the installed Ollama render-only check used zero
inference tokens. The earlier 627-dashboard-test run predates this mode change.
The subsequent creator-triggered visible summary passed; broader task completion
is still unverified. This is not a proven parser repair. Start with [native tool mode](NATIVE_QWEN_TOOL_MODE.md) and
`.smelter/native-qwen-tool-mode-verification.json`. Backup alongside native
config: `opencode.json.bak-smelter-cli-20261026T102014457096Z`.

Earlier creator retry: **overflow repair accepted, task continuation failed**.
Ollama processed 74,969 tokens initially and 75,211/75,286 on the following
steps, inside the unchanged 131,072 context with no truncation. Native OpenCode
reused its prompt cache. Qwen called native `bash` with `&&`; Windows PowerShell
5.1 rejected it. A single `Test-Path` retry returned `True`, then the model ended
with `finish=stop`, only a reasoning part and no visible answer or further call.
No concrete mod work was done in that retry. The latest user message in Melty
was its 28,509-character setup template resent into the same session; the earlier
concrete roster remains in history. Evidence:
`.smelter/melty-retry-20261026T093007.json`. No private reasoning text is copied.

MCP initialization guidance now explicitly says to continue the existing task
after setup, reuse its workspace, provide a visible result/blocker and use
PowerShell 5.1 syntax for a native client with that shell. Only the idle
`smelter` registration was reconnected; all three MCP servers remain connected.
The three scope/real-stdio regressions pass in
`.smelter/native-continuation-context-tests.log`. This is prompt guidance, not
an enforced empty-answer recovery; a later turn reached reads but again had no
visible final answer. No additional model request was sent by Codex. Preserve 128K/8K and the
chat. Do not claim that the earlier 627/121 suites prove Qwen can complete this
task. Avoid blindly replaying hidden reasoning as a repair: the
[official Qwen model guide](https://huggingface.co/Qwen/Qwen3.5-35B-A3B)
recommends omitting thinking content from multi-turn history. Model options
were left unchanged in that guidance-only pass; see the later explicit mode workaround above.

Latest task-following repair: [REA context gateway](REA_CONTEXT_GATEWAY.md).
Ollama 0.40.11 logged 225K–227K input prompts above the selected 128K ceiling,
then dropped most of the prompt through context-shift truncation (65,538 tokens,
only four retained from the leading instructions). Native REA advertised 207
tools with 835,332 input-schema/description characters on every turn. The new
three-tool discovery/schema/call gateway reduces that repeated cost to 1,084
measured characters and keeps all 207 operations available on demand. Actual
backend discovery, schema lookup and read-only `binary_session` passed. The idle
native `rea` registration alone was refreshed; `rea`, `smelter` and `melty` all
report connected. Existing chat and original REA/Ghidra environment are retained.
Config backup: `opencode.json.bak-smelter-cli-20261026T092056732169Z` alongside
the native config. Evidence: `.smelter/rea-compact-gateway-verification.json`.
128K/8K remain unchanged. No new model prompt was sent; the creator's next Melty
turn must verify task-following. GTA–ARK gameplay is still not implemented.
Final gateway regression: **627 dashboard tests, OK (nine skipped)** and
**121 setup tests, OK**. Logs: `.smelter/rea-gateway-dashboard-tests.log` and
`.smelter/rea-gateway-setup-tests.log`. The seven new gateway tests include real
nested stdio, backend cancellation followed by another call on the same
connection, schema navigation and validation. Two new setup tests cover the
backed-up/idempotent wrapper and refusing per-operation permission bypass.

Next acceptance: let the creator retry the existing request in the same Melty
chat. Check the new Ollama log entries for overflow and the actual OpenCode tool
receipts for `smelter_read_coding_file` on `mods/gta-ark/README.md`. A prepared
coding copy already exists with workspace ID
`897b9243-fd7e-42f4-a46a-d1b814a33a81`; do not create another merely to repeat
setup. Do not send a model prompt on the creator's behalf. The model previously
prepared this copy, then ignored the requested read and ended with a generic
question. This is the behavior that still needs acceptance after the repair.

Latest repair: [native Melty MCP startup](MELTY_CONNECTOR.md). The real Melty
child could not see the saved LocalAppData database alias because Windows
redirected Codex's copy into its package cache. The marker now names the same
physical existing SQLite file, after an online backup; data was not moved.
The original `smelter` command is restored and connected in the existing native
OpenCode server. A fresh stdio check lists 19 tools, recalls project memory and
fetches live upstream text. Both model limits remain 128K/8K. The creator then
demonstrated model-driven memory/inventory calls as recorded below. Continue to
leave prompt submission with them; preserve their chat. See
`.smelter/melty-mcp-fixed-verification.json`.
Final native-fix regression: **617 dashboard tests, OK (nine skipped)** and
**119 setup tests, OK**. Logs: `.smelter/melty-mcp-dashboard-tests.log` and
`.smelter/melty-mcp-setup-tests.log`. The 616/116 counts below are earlier
checkpoints. The global native registration and existing chat were preserved;
no new model run was submitted by the repair.
The creator's next turn subsequently passed real model-driven memory and ARK
inventory calls through Melty; see `.smelter/melty-e2e-verified.json`. It then
confused the empty Melty working folder with the SMELTER source checkout.
`mcp_server.py` now advertises grant-aware workspace/source/inventory instructions
in MCP initialization, with a real empty-client-directory regression. Only the
idle native MCP server was reconnected; no model prompt or chat restart was sent.
The native registration still exposes 19 tools with the same grants. This is
connection/recall/inventory acceptance, not a completed mod build or game test.
Latest full dashboard suite: **620 tests, OK (nine skipped)** in
`.smelter/mcp-workspace-context-tests.log`. Three new scope-context tests pass,
including a real stdio client starting from an empty Melty-like folder and
reading an existing fixture mod through the isolated coding tools. Setup remains
119 OK from the pointer repair. The earlier 617 count predates this addition.
The GUI task previously submitted by Codex was cancelled when the creator chose
to test through Melty. Preserve that chat's history, not a duplicate model run.

## Current local implementation

- Inline read-only folder approvals pause and resume the same GUI tool/job.
  Task/project grants, denial/subtrees, cancellation, expiry and operator
  exclusions are tested through Python, real MCP, Node proxy and authenticated
  HTTP. A bounded UTF-8 reader complements inventory/header/archive inspection.
- `web_access` supplies source-linked search and bounded public HTTPS text
  fetching, explicit cache/refresh, DNS pinning, redirect/address validation and
  cancellation. The current mode is **Documentation domains**; fresh projects
  default to Off. Queries go to public engines. The UI exposes source cards and
  **Settings → Internet & memory**.
- `project_memory` stores JSON source notes under `.smelter/project-memory/notes`,
  with rebuildable SQLite FTS5 and bounded 64 MiB estimated RAM per process.
  Both GUI engines recall a relevant pack capped at 12,000 characters inside
  the existing prompt budget. Native clients use the tools and skill. Model
  notes stay unverified; human notes and filtered completion checkpoints retain
  their distinct origins. The UI supports inspect/edit/forget/clear RAM/reindex.
- Final persistence checks found and fixed string-path normalization for fresh
  Python processes. Concurrent native calls now share a serialized tool budget.
  Human access-wait time is excluded from both GUI engines' overall deadlines.

The final GUI is on **port 8769, PID 20100**, with current private launch URL in
`.smelter/dashboard-knowledge.stdout.log` and errors in
`.smelter/dashboard-knowledge.stderr.log`. Use the new token after a restart.
The old PID **16028** still owns port 8768: it inherited ignored console
interrupts from the earlier helper, so graceful reload aborted and preserved it.
It has earlier knowledge code and must not be mistaken for the final backend.
No forced termination was used. The corrected helper resets interrupt inheritance
before spawning; two consecutive graceful reloads on 8769 passed. Earlier PIDs
15164, 25616, 29104, 14956 and 13076 are historical. Never stop arbitrary Python,
game, Melty or other console processes.

Docker Desktop is running (engine 29.8.2). The new **SearXNG** service is pinned to
version `2026.10.25-54ca1d9cf`, revision
`54ca1d9cfb08674f66261d7f351b063558dfcc62`, immutable image
`docker.io/searxng/searxng@sha256:a886f6511fd3faf2c9ed921b33a8f0df1c7646e47475b6b309e79cd2887abd9d`.
It binds `127.0.0.1:8842`, mounts only its configuration and has bounded
resources; its ordinary Docker bridge network supplies public engine access.
Agent containers retain no-network operation. The lock, installer and catalog
profile are recorded in requirements. No embedding model or new Python package
was installed.

Native OpenCode was configured with `--enable-knowledge --apply`; existing REA,
providers, permissions and exact ARK read scope were preserved. Five bundled
skills match installed copies, including `project-knowledge`. Native config
backup: `~/.config/opencode/opencode.json.bak-smelter-cli-20261026T044804788939Z`.
Reconnect an already-running native MCP session to discover new tools.
GUI/native limits remain **131,072 context / 8,192 output**, GUI thinking enabled,
300-second model timeout and 1,800-second OpenCode task limit. Both settings and
skill hashes were checked in `.smelter/knowledge-final-verification.json`.

Production memory contains one actual user decision note,
`e03a3746-9542-4719-b682-957da1a4c9c6`, title `User project decisions`. Preserve it.
Acceptance notes live in isolated fixture projects, not production memory.
Memory files are included in quotas/backups and excluded from routine age-based
retention. Forget does not erase old chat receipts or backups. GUI/native RAM
caches are independent and do not enlarge Qwen's context or GPU KV cache.

Earlier GitHub checkpoint `673eef6` predates the 26 October access/web/memory
and validation repairs now included in this source checkpoint. Preserve
unrelated `dw3_decomp-main/`, runtime/private credentials and the 128K profile.
The access flow applies to direct GUI chat and managed OpenCode; native
Melty/OpenCode keeps its separate host permission boundary.

## Verification and next action

Latest continuation: read [GTA–ARK runtime preparation](GTA_ARK_RUNTIME_WORKFLOW.md).
It adds a standard-library CLI preflight and a hash-listed, source-only package
under `.smelter/mod-packages/gta-ark-e00a1c2c-3951-429c-804c-2409864d992c`.
It is explicitly not installable. Current target fingerprints and blockers are
in `.smelter/gta-ark-runtime-preflight.json`; the source package receipt is
`.smelter/gta-ark-package.json`. GTA Enhanced 1.0.1158.16 still exceeds the author's
published SHV support (1.0.1158.13); neither checked loader was installed. No ARK
minor version is inferred from its missing executable-version resource.

Prototype fixes now cover local standalone players, both record flags, the
camera-eye/pawn origin error, respawn identity, movement failure and recurring
errors. Python/Lua reject non-finite values and invalid FOV. Actual engine calls
remain unverified. Frozen no-network acceptance passed **14 Python tests (one
optional Windows C++ sample skipped)** and **both Lua suites**, including **16
engine-binding checks**. Linux exercised actual directory-link rejection; the
host Windows run skipped that test when symlink creation was unavailable. Full
setup regression remains **116 OK** after the requirements catalog update.
Evidence: `.smelter/mod-runtime-runs/039e5a3c-143a-482a-b85f-3d08f5af4018/report.json`;
repeat `python tools/analysis/smoke_gta_ark_runtime.py`. No new dependency was
installed; runtime candidates and the CLI are recorded in requirements.

Project memory now also contains model note
`552e9b9d-2195-4652-9f5d-957e5ecc4677` (`GTA–ARK runtime gates and tested fixes`),
labelled **unverified** with source/evidence references. Recall was checked; it
adds no permissions or runtime proof. The earlier user-decision note remains,
so the current durable note count is two. The one-note GUI acceptance below
describes the earlier internet/memory checkpoint.

After the cancelled GUI task checkpoint, the database contains three durable
notes. Native/GUI memory was checked again after the database pointer repair.
Backup: `.smelter/database-pointer-backups/20261026T080329-e2e19ac2`; receipt:
`.smelter/melty-database-pointer-fix.json`. New database selections persist a
canonical path; older aliases use the backed-up `canonicalize_database.py`
maintenance helper. Temporary startup diagnostics are no longer the launcher.

Final full dashboard suite: **616 tests, OK (9 skipped)** with Docker running;
the skip gates do not claim vision/isolation opt-in acceptance. **116 setup tests,
OK; 37 JavaScript tests passed.** Results are in
`.smelter/knowledge-setup-tests.log` and `.smelter/knowledge-js-tests.log`.
The access-only checkpoint was 591/111/32;
those earlier counts are historical. Focused memory tests **11 OK** include a
new-process durability check; focused web tests **12 OK** include refresh,
private-address rejection, slow-response deadlines and concurrent call limits.

Real OpenCode/Qwen acceptance **passed at 128K/8K**: search, fresh upstream fetch,
save unverified note, recall and structured answer. No game runtime was claimed.
Evidence: `.smelter/knowledge-runs/qwen-1e834003f25047f8bfded52b5f292857/report.json`.
Repeat with `python tools/analysis/smoke_qwen_knowledge.py`. Other logs:
`.smelter/knowledge-dashboard-tests.log`, `memory-tests.log`, `web-tests.log` and
`knowledge-qwen-smoke.log`. See the guide for setup/regression commands.

Real Chromium desktop (1440 × 1000) and mobile (430 × 932) checks passed against
the final GUI, with no page errors: panel navigation, explicit input labels,
Documentation domains mode, 64 MiB memory selection and reading the durable user
decision note. Report: `.smelter/knowledge-browser-report.json`; screenshots:
`.smelter/knowledge-settings-desktop.png` / `knowledge-settings-mobile.png`.
Authenticated final discovery in `.smelter/knowledge-live-gui.json` confirms
interactive access, 49 capabilities, ready search and one durable memory note.
Human UI searches leave the controller RAM cache empty. The current launch URL
was queued in this chat's Codex browser panel; it opens when this chat is shown.

Next establish a supported GTA native route and an ARK loader probe that proves
the required timer/reflection APIs on this exact client before installing the
camera-link payload. Then validate camera calibration and removal/restore.
ARK IoStore metadata works, but its PAK v12 remains beyond pinned repak support.
The GTA/ARK prototype is still offline only. No game files were modified, game
processes launched or content published. Semantic retrieval remains optional
future work after measuring keyword recall quality.

## Earlier engine archive checkpoint (25 October)

1. Read the latest [engine archive integration](ENGINE_ARCHIVE_CLI.md), then
   [Universal Modder integration](UNIVERSAL_MODDER.md), followed by
   [review fixes and continuation](REVIEW_FIXES_20261025.md), then
   the earlier [handover](handovers/2026-10-25/HANDOVER.md) for historical context.
2. Check the [progress ledger](handovers/2026-10-25/PROGRESS.md).
3. Continue from the [ordered next steps](handovers/2026-10-25/NEXT_STEPS.md).
4. To assign another agent, use the [continuation prompt](handovers/2026-10-25/SECOND_AGENT_PROMPT.md).

Git checkpoint branch: `feature/agent-stack-game-mods`. Commits `7adb594` and
`cca4ecf` contain the earlier agent stack and lifecycle work; the subsequent
checkpoint includes the tools, prototype mods, review fixes and integration
documented here. Use `git log -1` to identify the exact current commit. Runtime
state/downloads and the unrelated `dw3_decomp-main/` folder are excluded.
Preserve this checkout; earlier checkpoints predate these fixes. Do not reset,
clean or overwrite unrelated local work. Latest continuation notes are in
[REVIEW_FIXES_20261025.md](REVIEW_FIXES_20261025.md).

Reference docs:
- [CLI toolkit and Qwen skills](MODDING_CLI_TOOLKIT.md): engine routes, candidate
  states, requirements and the two new bundled instruction packs;
- [game-mod tools](GAME_MOD_TOOLS.md): `inspect_game_files`, `mods/` coding copy,
  `mods`/`cpp` test profiles, `build_native_mod`;
- [GTA × ARK discovery](discovery/GTA_ARK_DISCOVERY_20261025.md) and
  [M1 design](discovery/GTA_ARK_M1_DESIGN.md);
- [Melty](MELTY_CONNECTOR.md): connector, desktop-app route, context measurements;
- [REA/Ghidra](REA_GHIDRA_INTEGRATION.md);
- [integration status](INTEGRATION_STATUS_20261025.md);
- [System status](SYSTEM_STATUS.md).

Latest integration (25 October, 20:52): Universal Modder GitHub source is pinned
and installed separately from the Melty kit, with a private CLI/runtime, local
knowledge MCP actions and the `universal-modder` Qwen skill. Standalone GTA/ARK
recon and a real Qwen 128K search/read-note task passed. See its integration doc
for exact pins/evidence. Both model routes remain 131,072 context / 8,192 output.
No game was launched/modified. Main remaining gate is game-specific loader/runtime
compatibility and the actual in-game vertical slice.

The earlier Universal Modder GUI refresh is still running (PID 15164, port 8768).
Its catalog includes Universal Modder. Latest launch logs remain
`.smelter/dashboard-um.stdout.log` / `.stderr.log`.

New: repak 0.2.3, retoc 0.1.5 and UnityDataTool 2.4.0 are pinned, installed in
`smelter-engine-cli:1` and exposed through one `inspect_engine_archive` MCP tool
under the inventory-folder grant. The full all-grants manifest fits the existing
32-tool bridge cap. The optional `engine-archive` skill is ready/enabled and its
exact source is installed in native OpenCode alongside the existing three skills.
The native profile now persists the exact registered ARK installation as its
read-only inventory scope; reopen its MCP connection to discover the archive tool.
The backed-up configuration preserves unrelated providers, REA and permissions.

The image ID is `sha256:23456cc5f1a12f70458ba98fe41c649ccd83019068bb8d0ab8e7dc3df6a75a68`.
Setup selection is separate in `.smelter/tooling/engine-cli/selection.json` so the
older running GUI can still read its original sandbox schema. An explicit new
GUI `engine_image` setting takes precedence. No model/runtime limits changed.

Real fixtures and 13 stdio MCP operations passed, including ARK global/optional
IoStore reads. ARK PAKs report version 12 and exceed pinned repak's version-11
support. The tool returns an explicit compatibility limit, not a missing-key claim.
Neither asset extraction/cooking nor a runtime game mod is verified.

GUI refresh is pending: automatic approval review rejected stopping/restarting
the running dashboard. Do not bypass it or kill unrelated Python/game/Melty
processes. The old GUI keeps its compatible image configuration; new native and
standalone MCP processes already load the implementation. A normal backend restart
will expose the new tool in the GUI too. See the engine integration document for
installer, CLI, exact limits and repeatable acceptance commands.

Final verification: **570 dashboard tests, OK (9 skipped)**; **111 setup tests,
OK**; **17 JavaScript tests passed**; **13 real stdio MCP checks passed**. The
Qwen structured acceptance passed at 128K/8K, with exact archive format/path,
task-attributed UE5 identity and explicitly unverified minor/cooking/runtime:
`.smelter/engine-cli-runs/qwen-aa5ebd5a76064105985429f308660092/report.json`.
MCP fixtures/game evidence:
`.smelter/engine-cli-runs/eb1fd06357674a85b7bc436be0f5bfa8/report.json`.
Final limits, native persisted-scope operation and skill-copy verification:
`.smelter/engine-verification.json`. Both saved routes and Ollama's observed
resident model context are 131,072 tokens / 8,192 output where applicable.

Native config backup before persisting the ARK read-only scope:
`~/.config/opencode/opencode.json.bak-smelter-cli-20261025T173834469911Z`.
The configured scope is exactly `D:\SteamLibrary\steamapps\common\ARK Survival Ascended`.
Original GUI sandbox settings before the compatible selection migration are in
`.smelter/tooling/engine-cli/sandbox-before-compatible-selection.json`.
No game files were modified, game processes launched or unrelated changes reset.
