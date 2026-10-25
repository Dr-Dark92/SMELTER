> Latest status: read [review fixes and continuation](../../REVIEW_FIXES_20261025.md) first. This document contains earlier observations; the current native builder is confined MinGW-w64, and Qwen context remains 128K.

# Ready-to-paste continuation prompt

```text
Continue the existing SMELTER work in:
C:\Users\Dr.Dark92\Documents\ChatGPT\SMELTER

Read docs/CURRENT_HANDOVER.md, then in order:
docs/handovers/2026-10-25/HANDOVER.md
docs/handovers/2026-10-25/PROGRESS.md
docs/handovers/2026-10-25/NEXT_STEPS.md
docs/GAME_MOD_TOOLS.md
docs/discovery/GTA_ARK_M1_DESIGN.md

State: branch fix/r07-r08-setup-lifecycle, HEAD 982950b (R07+R08 only; main is at
3f72721). Everything else is uncommitted, including untracked new modules, docs and
mods/gta-ark. Preserve it: no reset, clean, reclone or HEAD-only worktree.
dw3_decomp-main/ is unrelated operator content; don't touch or stage it.

Goal: a local workbench where Qwen3.5 35B-A3B (128K context, 8,192 output) in
managed, no-network OpenCode does game-mod work through fixed, grant-gated SMELTER
tools. The maintaining agent builds and verifies tools; SMELTER does the mod work.
Current tools:
- REA/Ghidra;
- Melty read-only lookup (on by default);
- inspect_game_files;
- the coding copy covering tools/, skills/ and mods/<mod>/, with confined test
  profiles python, node, mods and cpp (g++ image smelter-cpp:1);
- build_native_mod (MSVC, fixed flags; built files never run).
Melty's desktop app also uses the local model through the host OpenCode config,
with only a Melty-lookup SMELTER MCP grant.

Mashup target: GTA V Enhanced (host, Story Mode only) x ARK: Survival Ascended
(companion, single player), using the live-passthrough route. M1 = GTA camera drives
ARK's view. The offline parts are in mods/gta-ark. Script Hook V doesn't support GTA
1.0.1158.16 yet; UE4SS and the ARK BattlEye-off method are undecided. Installing into
game folders and launching games need explicit operator approval.

Read the handover's known traps first: Codex MSIX data copies, launching the
dashboard outside the command sandbox, shell quirks, compile is not correctness.
Next work, in order (NEXT_STEPS.md): exact-text edit tool, reviewed merge of mods/
from a coding copy, confined Lua profile, then M1 through SMELTER.

Every new tool or dependency updates system-requirements.json, REQUIREMENTS.md and
the relevant docs in the same change. Report installed, connected and verified
separately. No upload, publish, account change, commit or push without the
operator's explicit request.
```
