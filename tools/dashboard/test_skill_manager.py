import tempfile
import unittest
from pathlib import Path
from skill_manager import add_skill, remove_skill, set_skill_enabled
from skills_catalog import catalog_skills
from skill_context import build_skill_context
from skill_router import route_skills

MANIFEST = "# Custom Skill\n\n## Purpose\nDocument project work.\n"


class SkillManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        bundled = self.root / "skills" / "documentation"
        bundled.mkdir(parents=True)
        (bundled / "SKILL.md").write_text(MANIFEST, encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_add_and_remove(self):
        add_skill(self.root, "custom", MANIFEST, True)
        self.assertIn("custom", [s["id"] for s in catalog_skills(self.root)["skills"]])
        remove_skill(self.root, "custom", True)
        self.assertNotIn("custom", [s["id"] for s in catalog_skills(self.root)["skills"]])

    def test_disabled_skill_cannot_load(self):
        set_skill_enabled(self.root, "documentation", False, True)
        with self.assertRaises(ValueError):
            build_skill_context(self.root, ["documentation"])
        self.assertEqual(route_skills(self.root, "Update the README"), [])

    def test_enable_persists(self):
        set_skill_enabled(self.root, "documentation", False, True)
        set_skill_enabled(self.root, "documentation", True, True)
        self.assertTrue(catalog_skills(self.root)["skills"][0]["enabled"])

    def test_bundled_removal_blocked(self):
        with self.assertRaises(ValueError):
            remove_skill(self.root, "documentation", True)

    def test_approval_required(self):
        with self.assertRaises(ValueError):
            add_skill(self.root, "custom", MANIFEST)
        with self.assertRaises(ValueError):
            set_skill_enabled(self.root, "documentation", False)

    def test_duplicate_rejected(self):
        add_skill(self.root, "custom", MANIFEST, True)
        with self.assertRaises(ValueError):
            add_skill(self.root, "custom", MANIFEST, True)

    def test_traversal_rejected(self):
        with self.assertRaises(ValueError):
            add_skill(self.root, "../escape", MANIFEST, True)

    def test_invalid_manifest_rejected(self):
        with self.assertRaises(ValueError):
            add_skill(self.root, "custom", "hello", True)

    def test_bulk_enable_disable_validates_all_before_writing(self):
        from skill_manager import manage_many
        add_skill(self.root,'custom',MANIFEST,True)
        result=manage_many(self.root,['documentation','custom'],'disable',True)
        self.assertEqual(len(result['changed']),2)
        with self.assertRaises(ValueError):manage_many(self.root,['custom','missing'],'enable',True)
        self.assertFalse(next(s for s in catalog_skills(self.root)['skills'] if s['id']=='custom')['enabled'])
        manage_many(self.root,['documentation','custom'],'enable',True)
        self.assertTrue(all(s['enabled'] for s in catalog_skills(self.root)['skills']))

    def test_bulk_removal_protects_bundled_before_removing_anything(self):
        from skill_manager import manage_many
        add_skill(self.root,'custom',MANIFEST,True)
        with self.assertRaises(ValueError):manage_many(self.root,['custom','documentation'],'remove',True)
        self.assertTrue((self.root/'.smelter/managed-skills/custom/SKILL.md').exists())
        self.assertEqual(manage_many(self.root,['custom'],'remove',True)['changed'],['custom'])

    def test_collection_subskill_removal_preserves_siblings(self):
        from skill_manager import manage_many
        group=self.root/'.smelter/managed-skills/collections/design'
        for name in ('first','second'):
            folder=group/name;folder.mkdir(parents=True);(folder/'SKILL.md').write_text(MANIFEST)
        manage_many(self.root,['design/first'],'remove',True)
        self.assertFalse((group/'first').exists());self.assertTrue((group/'second/SKILL.md').is_file())


if __name__ == "__main__":
    unittest.main()
