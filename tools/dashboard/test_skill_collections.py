import hashlib
import tempfile
import unittest
from pathlib import Path
from skill_collections import install_collection
from skills_catalog import catalog_skills
from skill_context import build_skill_context
from skill_manager import set_skill_enabled

TEXT = "# Test Skill\n\n## Purpose\nDocumentation and testing.\n"
URL = "https://github.com/example/skills"
SKILL_URL = URL + "/blob/main/skills/demo/SKILL.md"
DIGEST = hashlib.sha256(TEXT.encode()).hexdigest()


def discover(url):
    return {"sha256": DIGEST, "content": TEXT}


class CollectionTests(unittest.TestCase):
    def test_collection_install_disabled_then_enable(self):
        with tempfile.TemporaryDirectory() as root:
            result = install_collection(root, URL, [{"id": "demo", "url": SKILL_URL, "sha256": DIGEST}], True, discover)
            self.assertEqual(result["count"], 1)
            skill = next(s for s in catalog_skills(root)["skills"] if s["id"] == "example-skills/demo")
            self.assertFalse(skill["enabled"])
            with self.assertRaises(ValueError):
                build_skill_context(root, ["example-skills/demo"])
            set_skill_enabled(root, "example-skills/demo", True, True)
            self.assertIn("Documentation", build_skill_context(root, ["example-skills/demo"]))

    def test_digest_mismatch_no_files(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                install_collection(root, URL, [{"id": "demo", "url": SKILL_URL, "sha256": "0"*64}], True, discover)
            self.assertFalse((Path(root) / ".smelter" / "managed-skills" / "collections").exists())

    def test_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                install_collection(root, URL, [{"id": "demo", "url": SKILL_URL, "sha256": DIGEST}]*2, True, discover)

    def test_cross_repository_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                install_collection(root, URL, [{"id": "demo", "url": "https://github.com/other/repo/blob/main/SKILL.md", "sha256": DIGEST}], True, discover)

    def test_approval_required(self):
        with self.assertRaises(ValueError):
            install_collection(".", URL, [{"id": "demo", "url": SKILL_URL, "sha256": DIGEST}], False, discover)


if __name__ == "__main__":
    unittest.main()
