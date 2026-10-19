"""Install reviewed War-test skill manifests into local SMELTER collections.

Run on the workstation after reviewing the URLs below. This installs *only*
SKILL.md instructions; it does not install MCP servers, Blender, or extract assets.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from github_skill_discovery import discover_github_skill
from skill_collections import install_collection
from skill_manager import set_skill_enabled

ROOT = Path(__file__).resolve().parents[2]
SOURCES = [
    ("https://github.com/morluto/rea", [
        ("reverse-engineer-anything", "https://github.com/morluto/rea/blob/main/.agents/skills/reverse-engineer-anything/SKILL.md"),
    ]),
    ("https://github.com/majidmanzarpour/blender-game-skills", [
        ("blender-image-to-3d", "https://github.com/majidmanzarpour/blender-game-skills/blob/main/skills/blender-image-to-3d/SKILL.md"),
    ]),
]


def main():
    parser = argparse.ArgumentParser(description="Discover and install War test skill manifests")
    parser.add_argument("--install", action="store_true", help="Approve local manifest installation and enable")
    args = parser.parse_args()
    plans = []
    for repo, entries in SOURCES:
        selected = []
        for name, url in entries:
            try:
                preview = discover_github_skill(url)
            except ValueError as exc:
                print("DISCOVERY FAILED:", url, "-", exc)
                print("No skills installed or enabled. Check the repository path and retry.")
                return 1
            selected.append({"id": name, "url": url, "sha256": preview["sha256"]})
            print("SOURCE:", url)
            print("NAME:", preview["metadata"]["name"])
            print("PURPOSE:", preview["metadata"]["description"])
            print("WARNINGS:", ", ".join(preview["warnings"]) or "none detected")
            print("SHA256:", preview["sha256"])
            print("NOTE: instruction-only; external dependencies are NOT installed.")
            print()
        plans.append((repo, selected))
    if not args.install:
        print("Discovery complete; nothing installed. Re-run with --install after review.")
        return 0
    for repo, selected in plans:
        result = install_collection(ROOT, repo, selected, approval=True)
        for name in result["installed"]:
            set_skill_enabled(ROOT, result["collection"] + "/" + name, True, approval=True)
        print("INSTALLED AND ENABLED:", result["collection"], result["installed"])
    print("Skill manifests enabled. REA MCP and Blender automation remain unconfigured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
