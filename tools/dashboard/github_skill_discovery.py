"""Discover GitHub SKILL.md before approved, pinned-content installation.

GitHub API only, no arbitrary URLs, no archive extraction or code execution.
"""
from __future__ import annotations
import base64
import hashlib
import json
import re
from urllib.parse import urlsplit, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from skill_manager import add_skill, set_skill_enabled

SEG = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
MAX_API = 100 * 1024


def parse_github_skill(url):
    if not isinstance(url, str) or len(url) > 1200:
        raise ValueError("Invalid GitHub URL")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc.lower() != "github.com" or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Only plain https://github.com URLs are accepted")
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2 or not all(SEG.fullmatch(x) for x in parts[:2]):
        raise ValueError("Expected GitHub owner/repository")
    owner, repo = parts[:2]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if len(parts) == 2:
        return owner, repo, "main", "SKILL.md"
    if len(parts) >= 5 and parts[2] == "blob" and SEG.fullmatch(parts[3]) and parts[-1] == "SKILL.md":
        if any(not SEG.fullmatch(p) for p in parts[4:]):
            raise ValueError("Unsupported skill path")
        return owner, repo, parts[3], "/".join(parts[4:])
    raise ValueError("Use a repository root or GitHub blob link ending in SKILL.md (single-segment branch)")


def discover_github_skill(url, opener=urlopen):
    owner, repo, ref, path = parse_github_skill(url)
    endpoint = "https://api.github.com/repos/{}/{}/contents/{}?ref={}".format(
        quote(owner), quote(repo), "/".join(quote(x) for x in path.split("/")), quote(ref))
    request = Request(endpoint, headers={"Accept": "application/vnd.github+json", "User-Agent": "SMELTER-skill-discovery"})
    try:
        with opener(request, timeout=12) as response:
            raw = response.read(MAX_API + 1)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise ValueError("GitHub discovery unavailable: " + type(exc).__name__) from exc
    if len(raw) > MAX_API:
        raise ValueError("GitHub response too large")
    try:
        data = json.loads(raw)
        if data.get("type") != "file" or data.get("encoding") != "base64":
            raise ValueError("Expected a GitHub SKILL.md file")
        content = base64.b64decode(data["content"], validate=False).decode("utf-8")
    except (KeyError, TypeError, UnicodeError, ValueError) as exc:
        raise ValueError("Invalid GitHub skill content") from exc
    if len(content.encode("utf-8")) > 48 * 1024:
        raise ValueError("Skill exceeds maximum size")
    if not re.search(r"^#\s+\S+", content, re.M) or not re.search(r"^##\s+Purpose\s*\n+\S+", content, re.M | re.I):
        raise ValueError("Skill requires a title and Purpose section")
    warnings = []
    for label, pattern in (
        ("shell commands", r"(?im)^\s*(?:sudo|curl|wget|powershell|bash|sh|pip|npm)\b"),
        ("external links", r"https?://"),
        ("possible secret references", r"(?i)\b(?:api[_ -]?key|secret|token|password)\b"),
    ):
        if re.search(pattern, content):
            warnings.append(label)
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return {"url": url, "owner": owner, "repository": repo, "ref": ref, "path": path,
            "sha256": digest, "content": content, "bytes": len(content.encode("utf-8")),
            "warnings": warnings, "execution_allowed": False, "discovery_only": True}


def install_discovered_skill(root, name, url, sha256, approval=False, opener=urlopen):
    if approval is not True:
        raise ValueError("Explicit approval required")
    if not isinstance(sha256, str) or not re.fullmatch(r"[a-f0-9]{64}", sha256):
        raise ValueError("Invalid discovery digest")
    discovered = discover_github_skill(url, opener)
    if discovered["sha256"] != sha256:
        raise ValueError("GitHub skill changed since discovery; review again")
    result = add_skill(root, name, discovered["content"], approval=True)
    set_skill_enabled(root, name, False, approval=True)
    return {**result, "enabled": False, "source": "github", "source_url": url, "sha256": sha256}


MAX_TREE_BYTES = 1024 * 1024
MAX_DISCOVERED = 40


def discover_github_repository(url, opener=urlopen):
    """List SKILL.md paths using GitHub's default branch tree; never fetch scripts."""
    owner, repo, ref, path = parse_github_skill(url)
    if path != "SKILL.md" or "/blob/" in url:
        raise ValueError("Repository discovery requires a GitHub repository root URL")
    repo_endpoint = "https://api.github.com/repos/{}/{}".format(quote(owner), quote(repo))
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "SMELTER-skill-discovery"}
    def get_json(endpoint, limit):
        request = Request(endpoint, headers=headers)
        try:
            with opener(request, timeout=12) as response:
                raw = response.read(limit + 1)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise ValueError("GitHub discovery unavailable: " + type(exc).__name__) from exc
        if len(raw) > limit:
            raise ValueError("GitHub discovery response too large")
        try:
            data = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise ValueError("Invalid GitHub discovery response") from exc
        if not isinstance(data, dict):
            raise ValueError("Invalid GitHub discovery response")
        return data
    metadata = get_json(repo_endpoint, MAX_API)
    branch = metadata.get("default_branch")
    if not isinstance(branch, str) or not branch or len(branch) > 150:
        raise ValueError("GitHub repository has no valid default branch")
    tree_endpoint = repo_endpoint + "/git/trees/" + quote(branch, safe="") + "?recursive=1"
    tree = get_json(tree_endpoint, MAX_TREE_BYTES)
    if tree.get("truncated") is True:
        raise ValueError("Repository tree is truncated; cannot guarantee complete discovery")
    entries = tree.get("tree")
    if not isinstance(entries, list):
        raise ValueError("Invalid repository tree")
    paths = []
    for item in entries:
        if not isinstance(item, dict) or item.get("type") != "blob":
            continue
        candidate = item.get("path")
        if not isinstance(candidate, str) or candidate.split("/")[-1] != "SKILL.md":
            continue
        if len(candidate) > 500 or any(not SEG.fullmatch(p) for p in candidate.split("/")):
            continue
        paths.append(candidate)
    paths.sort()
    if len(paths) > MAX_DISCOVERED:
        raise ValueError("Too many skills; narrow the repository before discovery")
    return {
        "owner": owner, "repository": repo, "ref": branch,
        "skills": [{"path": p, "url": "https://github.com/{}/{}/blob/{}/{}".format(
            owner, repo, quote(branch, safe=""), p)} for p in paths],
        "count": len(paths), "discovery_only": True,
        "execution_allowed": False,
    }
