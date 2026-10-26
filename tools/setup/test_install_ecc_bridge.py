import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from install_ecc_bridge import install, ROOT, LOCK_PATH, verified_bundle


class EccBridgeInstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'SMELTER'
        lock, _, _, _ = verified_bundle(ROOT)
        for name in lock['skills']:
            shutil.copytree(ROOT / 'skills' / name, self.root / 'skills' / name)
        for relative in (LOCK_PATH, Path(lock['native_instructions']['path'])):
            destination = self.root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, destination)
        self.config = self.base / 'native/opencode.json'
        self.config.parent.mkdir()
        self.original = {
            'provider': {'ollama': {'models': {'qwen3.5:35b-a3b-128k': {
                'limit': {'context': 131072, 'output': 8192}, 'options': {'reasoningEffort': 'none'}}}},
                'other': {'options': {'apiKey': 'private-fixture'}}},
            'mcp': {'rea': {'command': ['keep-rea'], 'environment': {'keep': 'private-fixture'}}},
            'permission': {'bash': 'ask'}, 'plugin': ['user-plugin'],
            'instructions': ['user-instructions.md']}
        self.config.write_text(json.dumps(self.original), encoding='utf-8')

    def run_install(self, **kwargs):
        return install(self.root, native_config=self.config, **kwargs)

    def test_preview_does_not_write_or_expose_credentials(self):
        before = self.config.read_bytes()
        result = self.run_install()
        self.assertEqual(self.config.read_bytes(), before)
        self.assertFalse((self.root / '.smelter').exists())
        self.assertFalse((self.config.parent / 'skills').exists())
        self.assertNotIn('private-fixture', json.dumps(result))

    def test_enable_native_copy_preserves_config_and_is_idempotent(self):
        original_bytes = self.config.read_bytes()
        first = self.run_install(apply=True)
        self.assertEqual(Path(first['backup']).read_bytes(), original_bytes)
        saved = json.loads(self.config.read_text())
        for key in ('provider', 'permission', 'plugin', 'mcp'):
            self.assertEqual(saved[key], self.original[key])
        self.assertEqual(saved['instructions'][0], 'user-instructions.md')
        self.assertEqual(len(saved['instructions']), 2)
        lock, _, files, _ = verified_bundle(self.root)
        for relative, raw in files.items():
            self.assertEqual((self.config.parent / relative).read_bytes(), raw)
        state = json.loads((self.root / '.smelter/skill-state.json').read_text())
        self.assertTrue(all(state[name] for name in lock['skills']))
        before = self.config.read_bytes()
        repeat = self.run_install(apply=True)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertIsNone(repeat['backup'])
        self.assertEqual(repeat['native_files_to_create'], 0)

    def test_user_modified_native_skill_blocks_entire_install(self):
        destination = self.config.parent / 'skills/ecc-tdd-workflow/SKILL.md'
        destination.parent.mkdir(parents=True)
        destination.write_text('user-owned instruction')
        before = self.config.read_bytes()
        with self.assertRaisesRegex(ValueError, 'differs'):
            self.run_install(apply=True)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertEqual(destination.read_text(), 'user-owned instruction')
        self.assertFalse((self.root / '.smelter').exists())
        self.assertFalse((self.config.parent / 'skills/ecc-verification-loop').exists())

    def test_tampered_upstream_source_blocks_all_changes(self):
        path = self.root / 'skills/ecc-tdd-workflow/references/upstream.md'
        path.write_text('tampered source')
        before = self.config.read_bytes()
        with self.assertRaisesRegex(ValueError, 'integrity mismatch'):
            self.run_install(apply=True)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertFalse((self.root / '.smelter').exists())

    def test_different_model_limits_are_not_overwritten(self):
        value = self.original
        value['provider']['ollama']['models']['qwen3.5:35b-a3b-128k']['limit']['context'] = 32768
        self.config.write_text(json.dumps(value))
        before = self.config.read_bytes()
        with self.assertRaisesRegex(ValueError, '128K/8K'):
            self.run_install(apply=True)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertFalse((self.root / '.smelter').exists())

    def test_managed_only_and_automatic_selection_can_be_disabled(self):
        before = self.config.read_bytes()
        result = install(self.root, native=False, apply=True, automatic_coding=False)
        self.assertIsNone(result['native_config'])
        self.assertEqual(self.config.read_bytes(), before)
        receipt = json.loads((self.root / '.smelter/ecc-bridge.json').read_text())
        self.assertFalse(receipt['automatic_coding'])
        self.assertFalse(receipt['executable_plugin'])

    def test_reference_traversal_in_lock_is_rejected(self):
        path = self.root / LOCK_PATH
        data = json.loads(path.read_text())
        data['skills']['ecc-tdd-workflow']['files']['../escape.md'] = {'sha256': '0' * 64}
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'source path'):
            self.run_install(apply=True)
        self.assertFalse((self.root / '.smelter').exists())


if __name__ == '__main__':
    unittest.main()
