# ECC inside SMELTERV1

Reviewed upstream: [affaan-m/ECC](https://github.com/affaan-m/ECC), commit
[`90606c8315ee09cafc303515c5f33024db6b9882`](https://github.com/affaan-m/ECC/tree/90606c8315ee09cafc303515c5f33024db6b9882),
package version **2.2.3**. Inspection is of that revision, not a promise about a
future upstream release. Its canonical `skills/` contains 311 manifests; the
whole checkout contains 1,062 including harness-specific copies.

**Current result: selected ECC instructions can run through SMELTERV1's agent
bridge. The full ECC executable plugin is not integrated.**

## Compatibility by layer

| ECC component | SMELTERV1 behavior | Evidence / limit |
|---|---|---|
| SKILL.md instructions | Supported as selected, enabled startup snapshots | Exact loaded-text hash in execution metadata; up to three skills / 48,000 characters per task |
| Large GitHub catalogue | Discover metadata, then review/import selected manifests | Up to 2,048 entries / 8 MiB tree; immutable branch commit; imports capped at 40; duplicates skipped |
| Referenced scripts, rules, documents | Not copied by instruction import | Read referenced source separately; a manifest alone does not install its dependencies |
| Existing built-in MCP actions | Available only under operator-approved task scopes | Diagnostic reports, inventory, static REA, GLB metadata and narrow CSS workspace operations |
| Native OpenCode coding tools | Source reads allowed; native edits/shell denied | No generic multi-file editing or arbitrary command runner |
| ECC OpenCode plugin, hooks and custom tools | Unsupported in the managed runner | Production starts OpenCode with `--pure`; plugin source/build dependencies are not loaded |
| ECC agents and orchestration commands | Not registered | Delegation is denied; copied instructions do not create roles or slash commands |
| Continuous learning, instincts and memory | Not connected | No persisted ECC hook runtime or automatic learned-skill promotion |
| External ECC MCP configuration | Not adopted | Existing external-server execution remains blocked pending a confined adapter |
| Qwen quality/performance | Must be tested on the home rig | Instructions do not retrain weights or guarantee model obedience |

Upstream's OpenCode integration is explicitly a partial/beta adapter. Its
`.opencode/opencode.json` requests plugin paths, instruction files, agents and
tools; `.opencode/package.json` declares Node 18+ and a TypeScript build. Those
are actual runtime requirements, not satisfied by importing a manifest. The
upstream reference enables tools/delegation that conflict with the current
SMELTER task boundary. Its config must not replace SMELTER's managed config.

Source files reviewed:
[OpenCode reference config](https://github.com/affaan-m/ECC/blob/90606c8315ee09cafc303515c5f33024db6b9882/.opencode/opencode.json),
[adapter README](https://github.com/affaan-m/ECC/blob/90606c8315ee09cafc303515c5f33024db6b9882/.opencode/README.md),
[adapter package](https://github.com/affaan-m/ECC/blob/90606c8315ee09cafc303515c5f33024db6b9882/.opencode/package.json).

## Try the supported instruction pack

PowerShell, from the current checkout:

```powershell
Set-Location C:\SMELTER
python tools\dashboard\install_ecc_skills.py
if ($LASTEXITCODE -ne 0) { throw 'ECC preview failed; nothing installed.' }
```

Review the three pinned source links and hashes. To import those reviewed
instructions:

```powershell
python tools\dashboard\install_ecc_skills.py --install
if ($LASTEXITCODE -ne 0) { throw 'ECC import failed.' }
```

The collection is `affaan-m-ecc`; skills are `coding-standards`, `security-review`
and `verification-loop`. Imports are disabled; duplicates are skipped without
overwriting existing skills. Review, enable, restart the dashboard to activate
new manifests, then select a row and **Use in next task**. Select only what the
task needs. Imported commands and installation examples remain reference text;
they cannot grant shell access or bypass path permissions.

For an isolated live test instead of production installation:

```powershell
python tools\analysis\home_smoke.py --live --ecc --prepare-demo
```

The runner does not install ECC into the original checkout. It saves pinned
references in its new evidence folder and optionally imports them disabled into
the new demo. Its runtime task verifies that selected ECC instructions reach
real OpenCode and a permitted action reaches the actual Python MCP server.

## Further implementation order

1. Keep the selected-instruction/MCP path verifiable with the home smoke and
   existing cross-platform contracts. Complete the live rig acceptance.
2. Add a general patch proposal/test/review contract in an isolated workspace,
   preserving the source and requiring hashes. Current CSS-only tooling cannot
   satisfy a general ECC TDD or refactoring workflow.
3. Audit and pin ECC's compiled plugin and dependency graph in a separate
   reviewed image. Define exactly which events/tools may run, with bounded
   output, deadlines and independently recorded results. Preserve `--pure` for
   the normal runner; make any plugin profile explicit and isolated.
4. Connect memory only as scoped data with reviewable writes and retention.
   Learned instructions require review, integrity checks and restart activation;
   model-generated text does not automatically become trusted executable code.
5. Design an external MCP server adapter with filesystem/network/process
   confinement before exposing ECC's external services. Never inherit upstream
   broad permission settings into the operator's host.

The last four steps are future implementation, not completed features. Do not
report full ECC compatibility until executable-plugin and task-permission
contracts, cleanup, native Windows/Linux checks and live acceptance pass.
