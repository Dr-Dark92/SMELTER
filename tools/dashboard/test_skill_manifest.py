import unittest
from skill_manifest import parse_skill_manifest


class SkillManifestTests(unittest.TestCase):
    def test_smelt_format(self):
        result = parse_skill_manifest("# Documentation\n\n## Purpose\nWrite verified docs.\n")
        self.assertTrue(result["valid"])

    def test_frontmatter(self):
        result = parse_skill_manifest("---\nname: redesign-skill\ndescription: Redesign an existing interface.\n---\n\n# Workflow\n")
        self.assertTrue(result["valid"])
        self.assertEqual(result["name"], "redesign-skill")

    def test_markdown_paragraph(self):
        result = parse_skill_manifest("# Taste Skill\n\nBuild thoughtful design systems for applications.\n")
        self.assertTrue(result["valid"])

    def test_invalid(self):
        self.assertFalse(parse_skill_manifest("not a skill")["valid"])

    def test_incomplete_frontmatter(self):
        self.assertFalse(parse_skill_manifest("---\nname: incomplete\n---\n")["valid"])


if __name__ == "__main__":
    unittest.main()
