import base64
import json
import tempfile
import unittest
from pathlib import Path
from github_skill_discovery import parse_github_skill, discover_github_skill, discover_github_repository, install_discovered_skill

MANIFEST = "# Test Skill\n\n## Purpose\nHelp with unit testing.\n"


class FakeResponse:
    def __init__(self, data):
        self.data = data
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def read(self, size):
        return self.data[:size]


def opener_for(content):
    def opener(request, timeout):
        data = json.dumps({"type": "file", "encoding": "base64",
                           "content": base64.b64encode(content.encode()).decode()}).encode()
        return FakeResponse(data)
    return opener


class GitHubSkillTests(unittest.TestCase):
    def test_repository_root(self):
        self.assertEqual(parse_github_skill("https://github.com/org/repo"), ("org", "repo", "main", "SKILL.md"))

    def test_blob_link(self):
        self.assertEqual(parse_github_skill("https://github.com/org/repo/blob/main/skills/test/SKILL.md"),
                         ("org", "repo", "main", "skills/test/SKILL.md"))

    def test_untrusted_hosts_rejected(self):
        for url in ("http://github.com/a/b", "https://evil.com/a/b", "https://github.com.evil.com/a/b",
                    "https://github.com/a/b?token=1"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                parse_github_skill(url)

    def test_preview_no_write(self):
        with tempfile.TemporaryDirectory() as root:
            preview = discover_github_skill("https://github.com/org/repo", opener_for(MANIFEST))
            self.assertTrue(preview["discovery_only"])
            self.assertFalse((Path(root) / ".smelter").exists())

    def test_reviewed_install(self):
        with tempfile.TemporaryDirectory() as root:
            url = "https://github.com/org/repo"
            preview = discover_github_skill(url, opener_for(MANIFEST))
            result = install_discovered_skill(root, "test-skill", url, preview["sha256"], True, opener_for(MANIFEST))
            self.assertTrue(result["added"])
            self.assertFalse(result["enabled"])
            self.assertTrue((Path(root) / ".smelter" / "managed-skills" / "test-skill" / "SKILL.md").is_file())

    def test_changed_content_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            url = "https://github.com/org/repo"
            preview = discover_github_skill(url, opener_for(MANIFEST))
            with self.assertRaises(ValueError):
                install_discovered_skill(root, "test-skill", url, preview["sha256"], True, opener_for(MANIFEST+"changed"))

    def test_install_requires_approval(self):
        with self.assertRaises(ValueError):
            install_discovered_skill(".", "test-skill", "https://github.com/org/repo", "0"*64, False, opener_for(MANIFEST))

    def test_bad_manifest_rejected(self):
        with self.assertRaises(ValueError):
            discover_github_skill("https://github.com/org/repo", opener_for("not a skill"))

    def test_repository_tree_discovery(self):
        def opener(request, timeout):
            url = request.full_url
            if url.endswith("/repos/org/repo"):
                payload = {"default_branch": "main"}
            else:
                payload = {"truncated": False, "tree": [
                    {"path": "skills/a/SKILL.md", "type": "blob"},
                    {"path": "skills/b/SKILL.md", "type": "blob"},
                    {"path": "tools/script.py", "type": "blob"}]}
            return FakeResponse(json.dumps(payload).encode())
        result = discover_github_repository("https://github.com/org/repo", opener)
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["skills"][0]["path"], "skills/a/SKILL.md")

    def test_truncated_repository_rejected(self):
        def opener(request, timeout):
            payload = {"default_branch": "main"} if request.full_url.endswith("/repos/org/repo") else {"truncated": True, "tree": []}
            return FakeResponse(json.dumps(payload).encode())
        with self.assertRaises(ValueError):
            discover_github_repository("https://github.com/org/repo", opener)

    def test_repository_discovery_requires_root(self):
        with self.assertRaises(ValueError):
            discover_github_repository("https://github.com/org/repo/blob/main/SKILL.md")

    def test_duplicate_content_import_is_skipped_without_copying(self):
        with tempfile.TemporaryDirectory() as root:
            url='https://github.com/org/repo';preview=discover_github_skill(url,opener_for(MANIFEST))
            install_discovered_skill(root,'original',url,preview['sha256'],True,opener_for(MANIFEST))
            result=install_discovered_skill(root,'copy',url,preview['sha256'],True,opener_for(MANIFEST))
            self.assertEqual(result['status'],'skipped');self.assertEqual(result['existing_id'],'original')
            self.assertFalse((Path(root)/'.smelter/managed-skills/copy').exists())

    def test_failed_disable_rolls_back_new_import(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as root:
            url='https://github.com/org/repo';preview=discover_github_skill(url,opener_for(MANIFEST))
            with patch('github_skill_discovery.set_skill_enabled',side_effect=OSError('fixture full disk')):
                with self.assertRaises(OSError):install_discovered_skill(root,'new',url,preview['sha256'],True,opener_for(MANIFEST))
            self.assertFalse((Path(root)/'.smelter/managed-skills/new').exists())


if __name__ == "__main__":
    unittest.main()
