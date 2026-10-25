# CLI modding toolkit and Qwen skills

Researched 25 October 2026. The machine-readable inventory is
`system-requirements.json` → `modding_cli.tools` (31 entries). Read it with:

```powershell
python tools/dashboard/modding_catalog.py
python tools/dashboard/modding_catalog.py --engine ue5
python tools/dashboard/modding_catalog.py --engine unity
```

Qwen can use `modding_tool_catalog` with the coding-workspace grant. This operation
only reads metadata. Entries marked `candidate` have not been installed, tested
against this user's games, or exposed as execution tools. CLI availability and
an MCP execution adapter are separate requirements. Managed OpenCode has no shell;
native OpenCode launched by Melty has a different, broader host boundary.

Update: repak 0.2.3, retoc 0.1.5 and UnityDataTool 2.4.0 now have a
[pinned install and bounded MCP archive adapter](ENGINE_ARCHIVE_CLI.md), with a
new `engine-archive` Qwen skill. ARK global/optional IoStore reads are verified.
Its PAK version 12 exceeds pinned repak's version-11 ceiling; no runtime/cooking
compatibility is implied. Other entries retain their declared integration state.

No tool works with every game engine. Choose by observed game/build, archive
format, engine version, platform, scripting backend and mod goal. An engine name
alone is insufficient. All selections below have a CLI path; GUI-only workflows
are excluded. UAssetGUI is included solely for its documented non-GUI commands.

## Common CLI layer

| Tool | Role | Compatibility boundary |
| --- | --- | --- |
| [REA](https://github.com/morluto/rea) + [Ghidra headless](https://github.com/NationalSecurityAgency/ghidra) | Native analysis with evidence, symbols, xrefs, decompilation | Installed REA is pinned at 6.7.0; upstream main can expose capabilities absent from that release. Static analysis does not prove runtime behavior. |
| [Rizin](https://github.com/rizinorg/rizin) | Scriptable binary inspection and JSON output | Optional alternative; validate commands for the selected release. |
| [7-Zip CLI](https://www.7-zip.org/) | Standard archive inventory and packaging | Proprietary formats with a `.pak` suffix are not necessarily ZIP. |
| [ripgrep](https://github.com/BurntSushi/ripgrep) | Source/config search with JSON results | Useful after obtaining actual readable source/data. |
| [xdelta3](https://github.com/jmacd/xdelta/blob/main/site/docs/commandline.md) | Distributable binary differences | Pin input hashes; apply to a new destination and verify output. |
| [Blender background mode](https://docs.blender.org/manual/en/latest/advanced/command_line/) | Scripted model/animation conversion | A matching importer, skeleton, coordinate system and material workflow are still needed. |
| [FFmpeg / ffprobe](https://ffmpeg.org/ffmpeg.html) | Audio/video conversion and inspection | Proprietary game audio is not universally supported. |
| [texconv](https://github.com/microsoft/DirectXTex/wiki/Texconv) | DDS compression, texture formats and mipmaps | Match the game's texture format, color space and alpha handling. |
| [vgmstream-cli](https://github.com/vgmstream/vgmstream) | Decode supported game audio | Decoder support does not imply re-encoding support. |
| MinGW-w64, g++, Lua | Cross-build Windows artifacts and test portable C++/Lua | Supplied by the pinned `smelter-cpp:2` image. No game launch or host compiler fallback. |

## Engine-specific CLI choices

| Engine/family | CLI tools | Route and limits |
| --- | --- | --- |
| UE4 | [repak](https://github.com/trumank/repak), [retoc](https://github.com/trumank/retoc), [UAssetGUI CLI](https://github.com/atenfyr/UAssetGUI#command-line-arguments), matching UE4Editor-Cmd | repak handles supported PAK versions; retoc handles IoStore where used. Asset JSON requires correct version/mappings. Cooking requires a matching SDK/project. |
| UE5 | Same tools; matching UnrealEditor-Cmd/DevKit | Distinguish PAK from UTOC/UCAS. retoc documents strongest support for 5.3+. Unversioned assets may require `.usmap`; custom builds/codecs can remain unsupported. |
| Unity assets | [UnityDataTool](https://github.com/Unity-Technologies/UnityDataTools), [AssetStudioCLI](https://github.com/aelurum/AssetStudioMod/blob/AssetStudioMod/AssetStudioCLI/ReadMe.md) | Prefer official metadata/JSON inspection first. Validate asset export against the actual Unity version and type-tree availability. |
| Unity Mono/.NET | [ilspycmd](https://github.com/icsharpcode/ILSpy/tree/master/ICSharpCode.ILSpyCmd), [dotnet CLI](https://learn.microsoft.com/en-us/dotnet/core/tools/dotnet) | Inspect managed assemblies; compile plugins against matching game assemblies/loader ABI. |
| Unity IL2CPP | [Cpp2IL](https://github.com/SamboyCoding/Cpp2IL), [Il2CppDumper](https://github.com/Perfare/Il2CppDumper), then Ghidra when needed | Use a matching native binary/metadata pair. Il2CppDumper's documented range is Unity 5.3–2022.2. Recovered types/CIL are not original source or proof of complete reconstruction. |
| Godot | [GDRE headless](https://github.com/GDRETools/gdsdecomp), [Godot CLI](https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html) | PCK recovery/patching and owned-project pack builds. Use a matching engine version; native extensions need native analysis. |
| Source / Source 2 | [Source2Viewer-CLI](https://github.com/ValveResourceFormat/ValveResourceFormat/blob/master/docs/guides/command-line.md) | Supported VPK/resource inventory and export; format/version support varies. Use SDK-supplied compilers for actual game-specific builds. |
| Quake / Hexen II | [ericw-tools](https://github.com/ericwa/ericw-tools): qbsp, vis, light | Map compilation for supported classic formats, not every id Tech generation. Standard ZIP-based PK3/PK4 archives can use 7-Zip. |
| Bethesda Creation | [BSArch](https://github.com/TES5Edit/TES5Edit/blob/dev-4.1.6/BSArch.dpr) | BSA/BA2 archive work. ESP/ESM editing needs a separate game-specific implementation; xEdit's GUI is not counted as a CLI solution. |
| REDengine / Cyberpunk | [WolvenKit.CLI](https://github.com/CDPR-Modding-Documentation/WolvenKit-8-Wiki/blob/main/wolvenkit-cli/usage/command-list.md) | Unbundle/convert/import/pack supported assets; archive pack alone does not package every REDmod sidecar. |
| Ren'Py | [rpatool](https://github.com/Shiz/rpatool) | RPA inventory/extraction; script recovery/version compatibility is a separate concern. |
| GameMaker | [UndertaleModCli](https://github.com/UnderminersTeam/UndertaleModTool) | Supported `data.win` and script workflows; game and bytecode versions matter. |
| RPG Maker / LÖVE | 7-Zip, text tools, compatible script runtimes | ZIP/unpacked data and owned source are tractable; engine-specific protected formats need additional supported tools. Lua 5.4 does not validate LuaJIT/5.1 ABI compatibility. |
| RAGE / GTA | REA/Ghidra, native cross-build CLI | No verified general-purpose RPF execution adapter has been added. The current GTA build still requires a version-compatible native loader. OpenIV/CodeWalker GUI workflows do not satisfy this CLI-only requirement. |

Runtime loaders such as UE4SS, BepInEx, Harmony and Script Hook V may be necessary
for a particular mod. They are not standalone CLI archive tools, and this catalog
does not install/inject them or claim loader compatibility. AssetRipper's headless
web service and GUI asset browsers are not presented as direct batch-export CLIs.

## Skills for Qwen3.5 35B-A3B

The model is used through OpenCode; instructions must match its supplied tools.
Installing an unrelated coding-agent package does not add model capabilities.

| Skill | Selection |
| --- | --- |
| Existing `morluto-rea/reverse-engineer-anything` | Retain the pinned package-matched SMELTER version for native investigation. Do not replace it with upstream main without checking tool contracts. |
| New bundled `game-modding` | Engine/format identification, CLI routing, isolated mod workflow and honest capability reporting. |
| New bundled `mod-validation` | Cross-language fixtures, behavioral tests, units/coordinates, source-bound evidence and compile/runtime distinctions. |
| Optional [unity-ecs-patterns](https://github.com/wshobson/agents/blob/main/plugins/game-development/skills/unity-ecs-patterns/SKILL.md) | Reviewed as relevant to actual ECS/DOTS source work. Not installed: it is not a general Unity binary-modding skill. |
| Optional [godot-gdscript-patterns](https://github.com/wshobson/agents/blob/main/plugins/game-development/skills/godot-gdscript-patterns/SKILL.md) | Relevant when editing Godot 4 source, rather than inspecting a PCK. Not installed. |

Select the two bundled mod skills plus REA for a native task (three-skill limit).
Automatic routing suggests the relevant bundled skills when enabled; granting REA
adds its existing instruction pack. Restart the dashboard after adding manifests
so its startup snapshot discovers them. The explicit preview-first
`tools/setup/configure_melty_cli.py` helper has now installed the two skills under
`~/.config/opencode/skills/`, backed up the native configuration, and enabled the
fixed coding-copy/native-build grant set. Native grants persist across messages;
the existing REA registration and native permissions were preserved.

The native model retains **131,072 context tokens**. Its separate generated-output
ceiling is **8,192** so patches fit. `tools/setup/Modelfile.qwen35b-128k` records the
derived tag. Reload the OpenCode session in Melty after config/skill changes.

## Adding another CLI safely and reproducibly

1. Add its identity, primary source, CLI usage, engine/version limits and state to
   `system-requirements.json`. A researched candidate is not a ready installation.
2. Select a concrete release/commit, checksum and dependency/codec/license needs;
   add the matching reproducible setup/check action before installing it.
3. Implement fixed operation schemas, approved input roots, application-owned new
   outputs, process/output/time budgets and cleanup. Avoid model-supplied shell
   commands or unbounded extraction into a game folder.
4. Verify a small known fixture, capture tool/input/output identity, and document
   exact coverage. Only then label the adapter ready.

Next engine adapters to prioritize are repak (PAK list/info), retoc (IoStore
list/info), and UnityDataTool (JSON SerializedFile metadata). The catalog supplies
their selection evidence; it deliberately does not execute arbitrary templates.

The installed [Universal Modder integration](UNIVERSAL_MODDER.md) adds pinned standalone recon and a local field-note MCP adapter. It is distinct from the earlier Melty kit copy.
