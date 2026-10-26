import json
from pathlib import Path
import shutil
import tempfile
import unittest

from install_workspace_tracking import ROOT, install


class WorkspaceTrackingInstallTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / 'SMELTER'
        for relative in ('skills/diagrams/SKILL.md', 'tools/dashboard/workspace_native_instructions.md'):
            path = self.root / relative; path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, path)
        self.config = Path(tmp.name) / 'native/opencode.json'
        self.config.parent.mkdir()
        self.original = {'provider': {'secret': 'private-fixture'}, 'mcp': {'rea': {'command': ['keep']}},
                         'permission': {'bash': 'ask'}, 'instructions': ['existing.md'], 'model': 'keep-128k'}
        self.config.write_text(json.dumps(self.original))

    def test_preview_then_install_preserves_native_settings_and_repeat_is_idempotent(self):
        before = self.config.read_bytes()
        preview = install(self.root, native_config=self.config)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertFalse((self.root / '.smelter').exists())
        self.assertNotIn('private-fixture', json.dumps(preview))
        result = install(self.root, native_config=self.config, apply=True)
        self.assertEqual(Path(result['backup']).read_bytes(), before)
        saved = json.loads(self.config.read_text())
        for key in ('provider', 'mcp', 'permission', 'model'):
            self.assertEqual(saved[key], self.original[key])
        self.assertTrue(json.loads((self.root / '.smelter/skill-state.json').read_text())['diagrams'])
        self.assertEqual((self.config.parent / 'skills/diagrams/SKILL.md').read_bytes(), (self.root / 'skills/diagrams/SKILL.md').read_bytes())
        repeat = install(self.root, native_config=self.config, apply=True)
        self.assertIsNone(repeat['backup']); self.assertEqual(repeat['native_files_to_create'], 0)

    def test_conflicting_native_skill_preserves_everything(self):
        destination = self.config.parent / 'skills/diagrams/SKILL.md'
        destination.parent.mkdir(parents=True); destination.write_text('user-owned')
        before = self.config.read_bytes()
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            install(self.root, native_config=self.config, apply=True)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertFalse((self.root / '.smelter').exists())
