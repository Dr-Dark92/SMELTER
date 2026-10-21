> **Implementation update:** The UI/UX overhaul implements R01–R07. Read [current implementation and validation](../../UI_UX_OVERHAUL.md) and [current progress](PROGRESS.md). The following document records the original pinned review and plan; statements about open/unapplied repairs describe that historical baseline.

# SMELTER review action plan

Source reviewed: `a609148fab2dec8915da24ca46550f9cd275b694`, SMELTERV1, 2026-10-21. This is a proposed implementation sequence. **No production repair in this plan has been applied.** Findings/evidence: [review](REVIEW.md), [runtime fixtures](evidence.json), [GLB fixtures](glb-browser-evidence.json).

## Patch sequence and acceptance

| Order | Work / finding | Implementation scope | Acceptance evidence | State |
| --- | --- | --- | --- | --- |
| 1 | Final path policy, R01 | Authorize every report candidate and copied top-level file; audit concrete temp/destination paths, snapshot and direct/MCP callers | Denied glob/exact/nested source and destination targets remain unread/unwritten through direct and built-in MCP; permitted collision suffixes remain create-only | Pending |
| 2 | Model protocol and partial outcomes, R05 + R03 | Packet/message shape checks; typed adapter failures; one finish-reason mapping for direct/OpenCode | Array/null/scalar/malformed packets and after-tool errors preserve receipts; length becomes prompt partial terminal outcome; no duplicate action or polling until timeout | Pending |
| 3 | Responsive Stop and handler locks, R02 | Remove global lock around long IO; keep narrow config/admission mutations and per-operation ownership | Real HTTP Stop is delivered while probe/import/workflow is blocked; measured cancellation delivery target ≤500 ms in local fixture; no concurrent admission/save regression | Pending |
| 4 | GLB owner lifecycle, R04 | Generation/owner guards for load/error/PNG/video callbacks; reset busy/timers and suppress stale download/control updates | Release during load/snapshot/encoding, rapid switching, error/reload and navigation leave no active stale controls/timers; actual PNG/WebM still render | Pending |
| 5 | Workspace recovery, R07 | Track newly created V2 and V2-Data artifacts; ownership-aware rollback/journal | Marker/copy/config/database failures permit safe retry or explicit reconciliation; pre-existing target/data and source remain untouched | Pending |
| 6 | Platform path identity, R06 | Shared duplicate identity rule in backend and frontend | Linux Case/case accepted when distinct; Windows case aliases rejected; link/traversal/root protections retained | Pending |
| 7 | Capability/status GUI consistency | Explain managed OpenCode check, read-only mode, external MCP block, current CSS-only scope and stale V2 | Every visible action has an implemented backend path or explicit disabled reason; no suggestion that a skill grants new OS capabilities | Pending |
| 8 | Versioned frontend capability contract | Replace outdated fixed readable-file list with reviewed descriptors tied to current shell/components | Info/schema/UI agree; useful required files readable only in approved scope; no automatic generic writer/shell | Design pending |
| 9 | Maintainability | Split high-branch adapters/renderers behind preserved public contracts; deprecate legacy JSON helpers | Tests cover boundaries; graph/index refreshed against implementation commit; no deletion based only on static incoming count | Deferred until fixes |

The latency value above is a proposed fixture acceptance target, not a measured production guarantee. Do not widen permissions to make tests pass. Keep arbitrary external MCP blocked until it has a separately reviewed process/IO/confinement contract.

## Office validation available now

1. Add failing regression assertions derived from the recorded reproductions before patching the relevant boundary.
2. Repair one coherent group at a time, run its targeted tests, then the dashboard/JavaScript suites.
3. Keep fixtures synthetic. Test the direct and built-in MCP transports with the same policy vectors. Use actual local HTTP for locking/cancellation and real browser callbacks for GLB lifecycle races.
4. Record outcome, receipts, owner/container cleanup and database state, including failures. Successful narrative text is not evidence of a completed action.
5. Before publishing an application fix, update progress by finding ID, regenerate the source graph/function inventory against that application commit, and use a guarded branch update. Preserve existing workspaces/state.

The runtime review fixture intentionally observes defects in the pinned code; a repaired branch should change its observations. It is evidence generation, not a regression suite that passes only by retaining bugs.

## Rig validation after source fixes

| Layer | Live check | Gate |
| --- | --- | --- |
| Ollama/Qwen | Small text fixture, exact native tool-call schema, bounded image fixture if selected model supports it; capture digest/settings/timings/finish reason | Expected output/tool behavior recorded without invented actions; no silent input truncation |
| OpenCode | Build/review immutable image, managed connection check, one approved README read task | Exact version/permission contract, denied writes/commands/external files, correct finalization and cleanup |
| MCP | Real built-in discovery/call, partial failure/timeout and cancellation | Correct scoped tools, receipt/audit linkage, no surviving unowned child; no automatic external-server enablement |
| Docker | Existing opt-in hostile isolation fixture plus actual OpenCode/image mounts | No unmounted data/network/ambient credentials; limits and owned cleanup confirmed |
| Windows | Bounded process timeout/cancel/output flood, descendant creation, socket cancellation, drive browsing | No terminal storm or surviving owned descendants; readable errors; native path behavior correct |
| GLB | Same static/animated models in desktop browser, PNG, clip aliases, WebM and release/cancel | Visual artifact + metadata/audio-free video inspection; original hashes unchanged |

No model replacement decision should precede these measurements. Compare models only with identical approved tools, context/output limits and fixtures; otherwise the comparison measures different integrations.

## Future coding mode

An OpenCode coding mode needs a separate explicit capability profile: selected writable workspace, immutable read source, reviewed write/patch operations, bounded test commands, network policy, artifact review and owner cleanup. Bridge approved skill context explicitly, and show the effective engine/model/permissions before Send. Skills may guide an implementation; they may not grant their own permissions or install dependencies. Keep read-only mode independently usable.
