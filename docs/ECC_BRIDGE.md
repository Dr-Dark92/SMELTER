# ECC coding bridge

The creator requested the reviewed ECC coding components and SMELTER-specific
debugging/gameplay guidance on 26 October 2026. This implementation keeps Qwen
3.5 35B-A3B and its selected 131072-token context / 8192-token output limits.

## Sources and installed profiles

ECC is pinned to [25278e7d7b6cf6e6a4e7a6c8e10f14ff22f0eb5b](https://github.com/affaan-m/ECC/tree/25278e7d7b6cf6e6a4e7a6c8e10f14ff22f0eb5b).
The eight original skill folders were pulled with the skill-installer helper;
reviewed agent definitions were read as Markdown. Only retained reference text,
MIT licenses and adapted instructions enter this bridge. No upstream scripts
or installers execute. `tools/setup/ecc-bridge-lock.json` records every bridged
file's SHA-256 and original upstream path. Upstream references remain inside
each skill's `references/` folder for optional reading.

| Profile | Purpose |
|---|---|
| `ecc-coding-standards` | Focused code quality; language-specific conventions take precedence |
| `ecc-tdd-workflow` | Executed reproducer, minimal fix, RED/GREEN evidence |
| `ecc-verification-loop` | Current-tree tests/builds and evidence limits |
| `ecc-planner` | Small milestones with exact paths and acceptance tests |
| `ecc-test-review` | Real behavior coverage and failure assertions |
| `ecc-code-review` | Concrete defects, callers and error propagation |
| `ecc-cpp-standards` | Ownership, ABI, resource lifetime and portable boundaries |
| `ecc-cpp-testing` | Existing compiler/test runner and focused build repairs |
| `ecc-retrieval` | Bounded discovery and authoritative source paths |
| `ecc-context` | File-backed handoffs and on-demand skill loading |
| `ecc-search-first` | Existing adapters and documented CLI/API compatibility |
| `smelter-debugging` | Windows/JSON/Linux paths, Lua imports and repeated-error recovery |
| `gameplay-testing` | Actual controller execution behind a fake engine boundary |

The last two are SMELTER-authored. The planner/reviewer profiles adapt ECC agent
definitions as instructions for the existing Qwen session; they do not register
Claude models, extra workers or delegation. C++ guidance preserves the actual
project standard/ABI. JavaScript examples and blanket immutability rules are not
transplanted into engine-state code.

## Reproducible setup

From this checkout:

```powershell
python tools/setup/install_ecc_bridge.py --preview
python tools/setup/install_ecc_bridge.py --apply
```

The installer is offline and uses Python's standard library. It checks all
vendored hashes before mutation, enables the 13 bundled skills, writes
`.smelter/ecc-bridge.json`, and copies exact matching Markdown/reference files
into the existing native OpenCode configuration's `skills/` directory. It adds
one small `smelter-ecc-coding.md` file to native `instructions`, preserving other
instructions, credentials, MCP registrations, permissions, plugins and model
settings. Changed native configuration is backed up beside the original.
User-modified destination instructions block installation for review instead
of being overwritten. Repeating an unchanged install is idempotent.

Without flags, the CLI applies the setup (the setup queue calls this mode).
`--preview` makes no writes. `--no-native` skips native installation;
`--native-config <path>` selects an explicit native configuration. The native
bridge expects this project's existing Qwen 128K/8K profile when native config
is present. `--no-auto-coding` disables implicit dashboard coding defaults;
enabled skills remain available for explicit selection or normal auto-routing.
The native instruction file remains an independent native-client default.

Requirements: setup step `ecc_bridge`, profile `ecc_coding`, and the existing
`qwen35b_agent` profile in `system-requirements.json`. No new pip/npm dependency,
test framework, game loader, compiler or model was added.

## Actual loading paths

**Direct Qwen and managed OpenCode:** when the task has the existing
`coding_workspace` grant and bridge defaults are enabled, task admission selects
up to two relevant ready/enabled startup snapshots. Explicit selections take
precedence. This leaves a third slot for an explicitly selected REA skill.
Non-coding tasks receive no implicit coding context. The same selector is used
at admission and by the direct/managed runtime. Execution metadata retains
actual loaded-text hashes. Changed/disabled skills remain subject to the
existing startup-snapshot safeguards. Refresh an idle dashboard to activate new
skill snapshots; an old coding copy need not be replaced.

**Native Melty/OpenCode:** global configuration loads only the small routing
file. OpenCode discovers the 13 names/descriptions, and its existing `skill` tool
loads the selected bodies on demand. General implementation uses TDD and
verification; syntax/import failures use debugging and verification; gameplay
adds actual-controller testing; C++ uses its specific standards/tests. Planning
and review are separate phases. The routing guidance caps a phase at two or
three skills and leaves upstream references unloaded until needed. A fresh
native process sees config changes; do not interrupt a running chat. Existing
native server config may be cached until its normal restart/reload.

MCP initialize instructions also advertise the enabled profiles for native
coding clients. MCP does not itself inject skills into an external client's
model prompt. Native discovery/loading and managed loaded-text snapshots are
separate evidence and must not be conflated with live Qwen task success.

## Validation and limits

Local activation completed on 26 October: all 13 profiles are enabled in
SMELTER, and native OpenCode's actual `debug skill` command from the Melty
project discovers all 13 with their instruction bodies (20 total native skills).
All 37 copied skill/reference/license files match the lock. The native config
comparison confirms that only the routing-instructions list changed; model,
credentials, permissions and MCP registrations match the saved pre-install copy.
Real stdio MCP initialize/list-tools advertises ECC and registers coding tests.
The direct-message and managed-agent integration test verifies matching loaded
instruction snapshots without model inference.

The shared coding tools now include `propose_coding_restore`, a deterministic
restoration adapter for original checkout files. It captures exact source bytes
and current destination hashes into a normal proposal, with source/destination
rechecks at apply time. This avoids asking Qwen to retype fixtures or infer hash
semantics, while keeping the existing coding grant and file-card review flow.
See [the coding contract](ECC_CODING_WORKSPACE.md). It adds no runtime dependency
and is declared in both requirement files.

Regression result: **642 dashboard tests, OK (24 skipped)** and **131 setup
tests, OK**. Docker Desktop's Linux engine was stopped, so container-dependent
checks were unavailable; existing platform/opt-in skips also remain. All 13
manifests passed the skill-creator validator using the existing Universal Modder
private Python/PyYAML runtime. No new validation dependency was installed.
Private installation, discovery, MCP and regression evidence is under
`.smelter/ecc-*`. No running chat or GUI was restarted, and no Qwen modding prompt
was submitted.

The creator subsequently ran a fresh native Qwen recovery attempt. Actual tool
records confirm completed loads of `smelter-debugging`, `ecc-tdd-workflow` and
`ecc-verification-loop`; no propose/apply operation followed. Docker was stopped
and its test call could not run. Codex restored the existing Docker service and
obtained a fresh unchanged-source ERROR receipt for the remaining Lua defect.
This confirms native loading, not a successful coding recovery. See the latest
section of [the Raptor review](../diagnostics/RAPTOR_PROGRESS_REVIEW_20261026.md)
and `.smelter/ecc-creator-recovery-attempt.json`.

Tests cover preflight/no-write preview, source tampering, path traversal,
preserving user-modified native skills, config preservation, idempotence,
profile routing, explicit selection, disabled/default behavior and snapshot
change detection. Native `opencode debug skill` can verify actual discovery
without inference. An initialize/list-tools MCP check validates the advertised
contract without submitting another modding prompt.

Lua source validation still runs before behavior tests. `loadfile` alone is
compile-only; real tests execute the returned module/controller and assert
observable outcomes. Model reviews and test passes do not establish in-game
compatibility. Existing failing Raptor code is untouched; its repair remains
SMELTER's task. No live Qwen improvement benchmark is claimed by installation.

Full ECC executable-plugin/hook integration, automatic learning, extra memory
systems and multi-agent loops are outside this instruction bridge. The existing
hybrid project memory and confined test/build adapters remain in use.
