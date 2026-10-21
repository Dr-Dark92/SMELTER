"""GitHub collection installation: preview all selected manifests, then approve batch.

Only SKILL.md is fetched and stored. No scripts or dependencies are executed.
"""
from __future__ import annotations
import re
from github_skill_discovery import discover_github_skill, parse_github_skill
from skill_manager import _paths, _state, _write_state
from skill_manifest import parse_skill_manifest

ID = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
MAX_BATCH = 40


def _validate(repo_url, selected):
    owner, repo, _, path = parse_github_skill(repo_url)
    if "/blob/" in repo_url or path != "SKILL.md":
        raise ValueError("Use repository root URL")
    if not isinstance(selected, list) or not 1 <= len(selected) <= MAX_BATCH:
        raise ValueError("Select 1-40 skills")
    if any(not isinstance(item, dict) or not isinstance(item.get("url"), str)
           or not isinstance(item.get("sha256"), str) or not isinstance(item.get("id"), str)
           for item in selected):
        raise ValueError("Invalid skill selection")
    ids = [x["id"] for x in selected]
    if len(ids) != len(set(ids)) or any(not ID.fullmatch(x) for x in ids):
        raise ValueError("Duplicate or invalid skill IDs")
    for item in selected:
        selected_owner, selected_repo, _, selected_path = parse_github_skill(item["url"])
        if (selected_owner, selected_repo) != (owner, repo) or not selected_path.endswith("SKILL.md"):
            raise ValueError("Skill source differs from collection repository")
    return owner, repo


def install_collection(root, repo_url, selected, approval=False, discover=discover_github_skill):
    if approval is not True:
        raise ValueError("Explicit approval required")
    owner, repo = _validate(repo_url, selected)
    collection = re.sub(r"[^a-z0-9_-]", "-", (owner + "-" + repo).lower())[:64].strip("-")
    if not ID.fullmatch(collection):
        raise ValueError("Invalid collection identifier")
    _, base = _paths(root)
    collections = base / "collections"
    folder = collections / collection
    if collections.is_symlink() or folder.exists() or folder.is_symlink():
        raise ValueError("Collection already exists; cannot overwrite")
    checked = []
    for item in selected:
        manifest = discover(item["url"])
        if manifest["sha256"] != item["sha256"]:
            raise ValueError("Skill changed since preview: " + item["id"])
        if not parse_skill_manifest(manifest["content"])["valid"]:
            raise ValueError("Invalid manifest: " + item["id"])
        checked.append((item["id"], manifest["content"]))
    # Validate everything before touching the filesystem.
    collections.mkdir(parents=True, exist_ok=True)
    folder.mkdir()
    created = []
    try:
        for name, content in checked:
            child = folder / name
            child.mkdir()
            (child / "SKILL.md").write_text(content, encoding="utf-8")
            created.append(child)
        state = _state(root)
        for name, _ in checked:
            state[collection + "/" + name] = False
        _write_state(root, state)
    except Exception:
        for child in created:
            (child / "SKILL.md").unlink(missing_ok=True)
            child.rmdir()
        folder.rmdir()
        raise
    return {"collection": collection, "count": len(checked), "installed": [n for n, _ in checked],
            "enabled": False, "source": repo_url}
