import tempfile
import unittest
from pathlib import Path
from skill_context import build_skill_context


class SkillContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        folder = Path(self.tmp.name) / "skills" / "documentation"
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text("# Documentation Skill\n\n## Purpose\nWrite verified docs.\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_selected_skill_loaded(self):
        self.assertIn("Write verified docs.", build_skill_context(self.tmp.name, ["documentation"]))

    def test_no_selection_no_context(self):
        self.assertEqual(build_skill_context(self.tmp.name, []), "")

    def test_single_large_external_manifest_fits_bounded_context(self):
        path = Path(self.tmp.name) / "skills" / "documentation" / "SKILL.md"
        path.write_text("# Documentation Skill\n\n## Purpose\nWrite verified docs.\n" + "reference " * 2400, encoding="utf-8")
        self.assertIn("Write verified docs.", build_skill_context(self.tmp.name, ["documentation"]))

    def test_unknown_rejected(self):
        with self.assertRaises(ValueError):
            build_skill_context(self.tmp.name, ["missing"])

    def test_traversal_rejected(self):
        with self.assertRaises(ValueError):
            build_skill_context(self.tmp.name, ["../projects"])

    def test_duplicates_rejected(self):
        with self.assertRaises(ValueError):
            build_skill_context(self.tmp.name, ["documentation", "documentation"])

    def test_too_many_rejected(self):
        with self.assertRaises(ValueError):
            build_skill_context(self.tmp.name, ["documentation"] * 4)


if __name__ == "__main__":
    unittest.main()
