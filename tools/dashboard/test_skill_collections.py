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

    def test_duplicate_ids_skipped(self):
        with tempfile.TemporaryDirectory() as root:
            result=install_collection(root, URL, [{"id": "demo", "url": SKILL_URL, "sha256": DIGEST}]*2, True, discover)
            self.assertEqual(result["count"],1)
            self.assertEqual(result["skipped_count"],1)
            self.assertEqual(result["skipped"][0]["reason"],"identity_exists")

    def test_cross_repository_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                install_collection(root, URL, [{"id": "demo", "url": "https://github.com/other/repo/blob/main/SKILL.md", "sha256": DIGEST}], True, discover)

    def test_approval_required(self):
        with self.assertRaises(ValueError):
            install_collection(".", URL, [{"id": "demo", "url": SKILL_URL, "sha256": DIGEST}], False, discover)

    def test_reimport_skips_existing_and_adds_only_new_subskills(self):
        with tempfile.TemporaryDirectory() as root:
            first={'id':'demo','url':SKILL_URL,'sha256':DIGEST}
            install_collection(root,URL,[first],True,discover)
            set_skill_enabled(root,'example-skills/demo',True,True)
            text=TEXT+'\nNew subskill.\n';url=URL+'/blob/main/skills/new/SKILL.md'
            new={'id':'new','url':url,'sha256':hashlib.sha256(text.encode()).hexdigest()}
            result=install_collection(root,URL,[first,new],True,lambda requested:{'content':text,'sha256':new['sha256']})
            self.assertEqual(result['installed'],['new']);self.assertEqual(result['skipped_count'],1)
            skills={s['id']:s for s in catalog_skills(root)['skills']}
            self.assertTrue(skills['example-skills/demo']['enabled']);self.assertFalse(skills['example-skills/new']['enabled'])
            self.assertEqual((Path(root)/'.smelter/managed-skills/collections/example-skills/demo/SKILL.md').read_text(),TEXT)

    def test_content_duplicates_across_sources_do_not_block_unique_import(self):
        with tempfile.TemporaryDirectory() as root:
            folder=Path(root)/'skills/existing';folder.mkdir(parents=True);(folder/'SKILL.md').write_bytes(TEXT.replace('\n','\r\n').encode())
            fresh=TEXT+'\nDifferent instructions.\n';digest=hashlib.sha256(fresh.encode()).hexdigest()
            selected=[{'id':'copy','url':SKILL_URL,'sha256':DIGEST},{'id':'fresh','url':URL+'/blob/main/skills/fresh/SKILL.md','sha256':digest}]
            result=install_collection(root,URL,selected,True,lambda url:{'content':TEXT if url==SKILL_URL else fresh,'sha256':DIGEST if url==SKILL_URL else digest})
            self.assertEqual(result['installed'],['fresh']);self.assertEqual(result['skipped'][0]['existing_id'],'existing')

    def test_duplicate_content_inside_batch_and_all_duplicate_rerun(self):
        with tempfile.TemporaryDirectory() as root:
            selected=[{'id':name,'url':URL+'/blob/main/skills/'+name+'/SKILL.md','sha256':DIGEST} for name in ('first','copy')]
            first=install_collection(root,URL,selected,True,discover);self.assertEqual(first['count'],1);self.assertEqual(first['skipped_count'],1)
            again=install_collection(root,URL,selected,True,discover);self.assertEqual(again['count'],0);self.assertEqual(again['skipped_count'],2)

    def test_failed_append_preserves_existing_collection(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as root:
            install_collection(root,URL,[{'id':'demo','url':SKILL_URL,'sha256':DIGEST}],True,discover)
            text=TEXT+'\nDifferent.\n';digest=hashlib.sha256(text.encode()).hexdigest()
            with patch('skill_collections._write_state',side_effect=OSError('fixture full disk')):
                with self.assertRaises(OSError):install_collection(root,URL,[{'id':'new','url':SKILL_URL,'sha256':digest}],True,lambda url:{'content':text,'sha256':digest})
            base=Path(root)/'.smelter/managed-skills/collections/example-skills'
            self.assertEqual((base/'demo/SKILL.md').read_text(),TEXT);self.assertFalse((base/'new').exists())


if __name__ == "__main__":
    unittest.main()
