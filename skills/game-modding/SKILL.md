---
name: game-modding
description: Inspect an existing game's engine and assets, choose compatible CLI modding tools, and build a reviewable mod or mashup in an isolated coding workspace.
---
# Game modding through CLI tools

Start with the actual game, executable build, platform, engine/version and intended mod. A filename or entropy sample is a clue, not proof of engine, encryption or compatibility. Separate asset changes, script/plugin changes and live game integration.

Use `modding_tool_catalog` to obtain the researched CLI choices and their integration state. A catalog entry is not an installed executable or a granted tool. Use only this task's supplied MCP schemas in managed OpenCode. Native OpenCode has a different execution boundary: use its actual permissions and installed CLI tools. Never invent a shell capability in the managed route.

For approved folders, use inventory_directory / inspect_game_files first. Keep the observed archive format/version and source hashes. Route narrowly:

- UE4/UE5 PAK: repak; IoStore UTOC/UCAS: retoc. Asset JSON: UAssetGUI's documented tojson/fromjson CLI. Confirm engine versions, usmap mappings and authorized keys. Cooking needs a matching licensed editor/DevKit/project. UE4SS is a game runtime prerequisite, not a standalone extraction CLI.
- Unity: UnityDataTool for archive/SerializedFile metadata; AssetStudioCLI for supported exports. Managed assemblies use ilspycmd. IL2CPP uses the matching metadata/native pair and supported Cpp2IL or Il2CppDumper version, then native analysis if needed. BepInEx/Harmony are runtime/plugin dependencies, not universal CLI extractors.
- Godot: GDRE headless PCK recovery, matching Godot CLI for owned-project packs; GDExtension binaries use native analysis.
- Source/Source 2: Source2Viewer-CLI for supported VPK/resources. Quake/Hexen II: ericw map compilers. Bethesda: BSArch for archives, not plugin records. REDengine: WolvenKit.CLI. Ren'Py: rpatool. GameMaker: supported UndertaleModCli release. RAGE requires game-specific version-compatible runtime/native access; do not treat RPF as Unreal PAK.

Use REA/Ghidra instructions for shipped binaries whose behavior cannot be established from source. Keep the installed REA skill/package aligned; upstream main may advertise absent tools. Analysis output is evidence or reconstructed pseudocode, not proof of in-game behavior.

Prepare one coding workspace, read exact bytes/hashes, propose/apply patches, then run the relevant fixed tests and native build. Use mod-validation for receipt interpretation. Report missing adapters, unsupported game builds and remaining runtime checks explicitly. Publishing, installations into game folders and launching games are separate actions; a compile or lookup never proves them.
