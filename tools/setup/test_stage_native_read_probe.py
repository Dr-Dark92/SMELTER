"""Deployment plan/apply/remove on temporary folders; never the real game folder."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import stage_native_read_probe as stage


class StageNativeReadProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='smelter-read-stage-')
        base = Path(self.temp.name)
        self.game = base / 'game'; self.game.mkdir(); (self.game / 'GTA5_Enhanced.exe').write_bytes(b'exe')
        (self.game / 'existing.dll').write_bytes(b'game file')
        self.runtime = base / 'runtime'; (self.runtime / 'lspdfr').mkdir(parents=True)
        (self.runtime / 'RAGEPluginHook.exe').write_bytes(b'rph'); (self.runtime / 'RagePluginHook.dll').write_bytes(b'rph dll')
        (self.runtime / 'EasyHook64.dll').write_bytes(b'dependency')
        (self.runtime / 'lspdfr' / 'data.xml').write_bytes(b'not wanted'); (self.runtime / 'Plugins').mkdir()
        (self.runtime / 'Plugins' / 'LSPD First Response.dll').write_bytes(b'not wanted')
        self.package = base / 'package'; (self.package / 'Plugins').mkdir(parents=True)
        (self.package / 'Plugins/SmelterNativeProbe.dll').write_bytes(b'probe')
        (self.package / 'manifest.json').write_text(json.dumps({'plugin_sha256': hashlib.sha256(b'probe').hexdigest()}))
        self.pins = {**stage.profile(), 'sha256': hashlib.sha256(b'exe').hexdigest(), 'plugin_sha256': hashlib.sha256(b'probe').hexdigest()}
        self.state = base / 'state'

    def tearDown(self):
        self.temp.cleanup()

    def make_plan(self, extra=()):
        return stage.plan(self.runtime, self.game, extra, self.package, self.pins)

    def test_plan_selects_only_the_runtime_and_probe(self):
        value = self.make_plan()
        self.assertEqual({c['target'] for c in value['copies']}, {'RAGEPluginHook.exe', 'RagePluginHook.dll', 'EasyHook64.dll', 'Plugins/SmelterNativeProbe.dll'})
        self.assertEqual(value['copies'][-1]['target'], 'Plugins/SmelterNativeProbe.dll')
        self.assertEqual(sorted(value['excluded']), ['Plugins/LSPD First Response.dll', 'lspdfr/data.xml'])
        self.assertTrue(value['applicable'])

    def test_apply_then_remove_leaves_the_game_folder_as_it_was(self):
        before = sorted(p.relative_to(self.game).as_posix() for p in self.game.rglob('*'))
        record = stage.apply(self.make_plan(), self.state)
        self.assertEqual((self.game / 'Plugins/SmelterNativeProbe.dll').read_bytes(), b'probe')
        install = json.loads(record.read_text())
        self.assertEqual(len(install['files']), 4); self.assertEqual(install['directories'], ['Plugins'])
        result = stage.remove(record)
        self.assertEqual(result['kept_changed'], [])
        self.assertEqual(sorted(p.relative_to(self.game).as_posix() for p in self.game.rglob('*')), before)

    def test_existing_targets_block_apply_and_nothing_is_copied(self):
        (self.game / 'RAGEPluginHook.exe').write_bytes(b'user install')
        value = self.make_plan()
        self.assertFalse(value['applicable']); self.assertEqual(value['existing_targets'], ['RAGEPluginHook.exe'])
        with self.assertRaisesRegex(ValueError, 'overwrite'):
            stage.apply(value, self.state)
        self.assertFalse((self.game / 'Plugins').exists())
        self.assertEqual((self.game / 'RAGEPluginHook.exe').read_bytes(), b'user install')

    def test_changed_sources_executable_and_installed_files_are_respected(self):
        value = self.make_plan(); (self.runtime / 'RagePluginHook.dll').write_bytes(b'swapped')
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            stage.apply(value, self.state)
        value = self.make_plan(); (self.game / 'GTA5_Enhanced.exe').write_bytes(b'patched')
        with self.assertRaisesRegex(ValueError, 'Executable changed'):
            stage.apply(value, self.state)
        (self.game / 'GTA5_Enhanced.exe').write_bytes(b'exe')
        record = stage.apply(self.make_plan(), self.state)
        (self.game / 'RagePluginHook.dll').write_bytes(b'updated by the user')
        result = stage.remove(record)
        self.assertEqual(result['kept_changed'], ['RagePluginHook.dll'])
        self.assertTrue((self.game / 'RagePluginHook.dll').exists())

    def test_plugin_must_match_manifest_and_profile(self):
        with self.assertRaisesRegex(ValueError, 'probe profile'):
            stage.plan(self.runtime, self.game, (), self.package, {**self.pins, 'plugin_sha256': '2' * 64})

    def test_real_profile_pins_the_staged_plugin(self):
        pins = stage.profile()
        manifest = json.loads((stage.PACKAGE / 'manifest.json').read_text())
        self.assertEqual(pins['plugin_sha256'], manifest['plugin_sha256'])
        self.assertEqual(stage.sha256(stage.PACKAGE / 'Plugins' / pins['plugin']), pins['plugin_sha256'])

    def test_extract_takes_only_top_level_files_and_plan_needs_the_hook(self):
        import zipfile
        archive = Path(self.temp.name) / 'author.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.writestr('RAGEPluginHook.exe', b'rph'); z.writestr('SlimDX.dll', b'dep')
            z.writestr('plugins/LSPD First Response.dll', b'no'); z.writestr('lspdfr/data/x.xml', b'no')
        folder = stage.extract(archive, self.state)
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ['RAGEPluginHook.exe', 'SlimDX.dll'])
        with self.assertRaises(FileExistsError):
            stage.extract(archive, self.state)
        (folder / 'RAGEPluginHook.exe').unlink()
        with self.assertRaisesRegex(ValueError, 'RAGEPluginHook.exe'):
            stage.plan(folder, self.game, (), self.package, self.pins)

    def test_package_only_plan_adds_pinned_root_files_without_a_runtime(self):
        (self.package / 'root').mkdir(); (self.package / 'root' / 'lua54.dll').write_bytes(b'lua')
        manifest = json.loads((self.package / 'manifest.json').read_text())
        manifest['root_files'] = {'lua54.dll': hashlib.sha256(b'lua').hexdigest()}
        (self.package / 'manifest.json').write_text(json.dumps(manifest))
        value = stage.plan(None, self.game, (), self.package, self.pins)
        self.assertEqual([c['target'] for c in value['copies']], ['Plugins/SmelterNativeProbe.dll', 'lua54.dll'])
        record = stage.apply(value, self.state)
        self.assertEqual((self.game / 'lua54.dll').read_bytes(), b'lua')
        self.assertEqual(stage.remove(record)['kept_changed'], []); self.assertFalse((self.game / 'lua54.dll').exists())
        (self.package / 'root' / 'lua54.dll').write_bytes(b'swapped')
        with self.assertRaisesRegex(ValueError, 'root file'):
            stage.plan(None, self.game, (), self.package, self.pins)
        with self.assertRaisesRegex(ValueError, 'runtime-dir'):
            stage.plan(None, self.game, ['x.dll'], self.package, self.pins)

    def test_tool_is_registered_as_operator_only_and_non_overwriting(self):
        from requirements_catalog import CATALOG, CATALOG_PATH
        value = CATALOG['runtime_probe_deployment']
        self.assertTrue(value['operator_only']); self.assertFalse(value['mcp_exposed'])
        self.assertFalse(value['overwrites_game_files']); self.assertFalse(value['game_runtime_verified'])
        for path in [value['module'], value['documentation'], value['profile'], *value['tests']]:
            self.assertTrue((CATALOG_PATH.parent / path).is_file(), path)

    def test_plan_refuses_wrong_executable_escaping_and_unknown_files(self):
        with self.assertRaisesRegex(ValueError, 'inside'):
            self.make_plan(['../game/existing.dll'])
        with self.assertRaisesRegex(ValueError, 'not in the runtime'):
            self.make_plan(['missing.dll'])
        self.assertIn('lspdfr/data.xml', [c['target'] for c in self.make_plan(['lspdfr/data.xml'])['copies']])
        with self.assertRaisesRegex(ValueError, 'executable'):
            stage.plan(self.runtime, self.game, (), self.package, {**self.pins, 'sha256': '0' * 64})


if __name__ == '__main__':
    unittest.main()
