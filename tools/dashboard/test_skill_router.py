import tempfile
import unittest
from pathlib import Path
from skill_router import route_skills


class SkillRouterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        for name in ("documentation", "diagrams"):
            folder = Path(self.tmp.name) / "skills" / name
            folder.mkdir(parents=True)
            (folder / "SKILL.md").write_text("# " + name + "\n\n## Purpose\nHelp with " + name + ".\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_documentation(self):
        self.assertEqual(route_skills(self.tmp.name, "Update the README and handover"), ["documentation"])

    def test_diagram(self):
        self.assertEqual(route_skills(self.tmp.name, "Create a Mermaid sequence diagram"), ["diagrams"])

    def test_both(self):
        self.assertEqual(set(route_skills(self.tmp.name, "Document the architecture with a Mermaid diagram")), {"documentation", "diagrams"})

    def test_unknown_no_route(self):
        self.assertEqual(route_skills(self.tmp.name, "Hello there"), [])

    def test_missing_skill_not_selected(self):
        (Path(self.tmp.name) / "skills" / "diagrams" / "SKILL.md").unlink()
        self.assertEqual(route_skills(self.tmp.name, "Mermaid diagram"), [])

    def test_non_text_rejected(self):
        with self.assertRaises(ValueError):
            route_skills(self.tmp.name, None)


if __name__ == "__main__":
    unittest.main()
