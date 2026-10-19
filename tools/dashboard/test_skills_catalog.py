import tempfile
import unittest
from pathlib import Path
from skills_catalog import catalog_skills


class SkillsCatalogTests(unittest.TestCase):
    def test_missing_skills_directory(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(catalog_skills(root)["count"], 0)

    def test_valid_skill_discovered_without_execution(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / "skills" / "documentation"
            folder.mkdir(parents=True)
            (folder / "SKILL.md").write_text("# Documentation Skill\n\n## Purpose\nDocument projects.\n", encoding="utf-8")
            result = catalog_skills(root)
            self.assertEqual(result["count"], 1)
            self.assertEqual(result["skills"][0]["status"], "ready")
            self.assertFalse(result["skills"][0]["loaded_into_model"])
            self.assertFalse(result["skills"][0]["executable"])

    def test_incomplete_manifest_flagged(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / "skills" / "incomplete"
            folder.mkdir(parents=True)
            (folder / "SKILL.md").write_text("no headings", encoding="utf-8")
            self.assertEqual(catalog_skills(root)["skills"][0]["status"], "incomplete")

    def test_oversized_manifest_flagged(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / "skills" / "big"
            folder.mkdir(parents=True)
            (folder / "SKILL.md").write_bytes(b"x" * 65537)
            self.assertEqual(catalog_skills(root)["skills"][0]["status"], "oversized")


if __name__ == "__main__":
    unittest.main()
