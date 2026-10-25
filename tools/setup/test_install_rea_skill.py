import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from install_rea_skill import install, CONTEXT, SKILL_ID, VERSION


class ReaSkillInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        self.package=self.root/'.smelter/tooling/rea/node_modules/rea-agents'
        self.skill=self.package/'skills/reverse-engineer-anything/SKILL.md'
        self.skill.parent.mkdir(parents=True)
        self.raw=b'---\nname: REA\ndescription: Native reverse engineering instructions\n---\nReference only.\n'
        self.skill.write_bytes(self.raw)
        (self.package/'package.json').write_text(json.dumps({'name':'rea-agents','version':VERSION}))
        self.destination=self.root/'.smelter/managed-skills/collections'/SKILL_ID

    def test_disabled_install_preserves_exact_upstream_and_records_loaded_hash(self):
        result=install(self.root)
        self.assertFalse(result['enabled'])
        self.assertEqual((self.destination/'UPSTREAM-SKILL.md').read_bytes(),self.raw)
        self.assertEqual(result['upstream_sha256'],hashlib.sha256(self.raw).hexdigest())
        self.assertEqual((self.destination/'SKILL.md').read_text(encoding='utf-8'),CONTEXT)

    def test_explicit_enable_and_reinstall_preserve_user_enabled_state(self):
        self.assertTrue(install(self.root,enable=True)['enabled'])
        self.assertTrue(install(self.root)['enabled'])

    def test_existing_modified_instructions_and_activation_are_preserved(self):
        install(self.root,enable=True)
        manifest=self.destination/'SKILL.md';manifest.write_text('user edits')
        state=(self.root/'.smelter/skill-state.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'differ'):install(self.root)
        self.assertEqual(manifest.read_text(),'user edits')
        self.assertEqual((self.root/'.smelter/skill-state.json').read_bytes(),state)

    def test_wrong_package_version_does_not_create_skill(self):
        (self.package/'package.json').write_text(json.dumps({'name':'rea-agents','version':'0.0.0'}))
        with self.assertRaisesRegex(ValueError,'6.7.0'):install(self.root)
        self.assertFalse(self.destination.exists())

    def test_unidentifiable_upstream_does_not_install_fabricated_reference(self):
        self.skill.unlink()
        with self.assertRaisesRegex(ValueError,'identifiable'):install(self.root)
        self.assertFalse(self.destination.exists())
