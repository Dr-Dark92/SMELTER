# Portable mod-workspace checkpoint — 2026-10-27

Updated 2026-10-28 after SMELTER applied the verified correction. This is a
handover archive, outside production `mods/` and outside test discovery.
It does not install or merge a mod. See `manifest.json` for every path, SHA-256
and scope. `.gitattributes` preserves exact source bytes across operating systems.

- `current/` holds the isolated mod copy's full source inventory. Its policy is
  now **GREEN, 30/30 protected checks**, with six passing Lua programs and 14
  Python tests (one skipped) on the same tree. It includes historical duplicate controller copies and a backup;
  those are preserved as evidence, not designated canonical implementations.
- `reference/` holds only the two corrected files from disposable verification:
  **30/30 protected checks, 6 passing Lua programs, 14 Python tests with one skip**.
  The prepared proposal has now been applied through SMELTER. The two reference
  files match the saved current files; offline success is not in-game success.

On the same PC, use the existing managed workspace and prepared proposal after
checking hashes. On a fresh clone, verify this manifest and reconstruct a new
managed copy through the normal approved proposal workflow before applying the
committed diagnostic diff or reviewed reference changes. Do not overwrite an
existing managed copy or treat an archived UUID as a portable authorization.

Runtime databases, prompts, tokens, credentials, retry state and binaries are
not part of this archive. Native compilation/runtime integration still needs
its own validation. The canonical policy fixture path is
`mods/gta-ark/Mods/GtaArkLink/Scripts/entity_policy.lua`.
