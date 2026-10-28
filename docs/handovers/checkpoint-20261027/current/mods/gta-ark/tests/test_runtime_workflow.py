import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

MOD = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gta_ark_runtime_workflow', MOD / 'tools/runtime_workflow.py')
workflow = importlib.util.module_from_spec(spec); spec.loader.exec_module(workflow)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); self.root = Path(tmp.name)
        self.gta, self.ark = self.root / 'gta', self.root / 'ark'
        self.gta.mkdir(); (self.ark / 'ShooterGame/Binaries/Win64').mkdir(parents=True)
        (self.gta / 'GTA5_Enhanced.exe').write_bytes(b'synthetic GTA fixture')
        (self.ark / 'ShooterGame/Binaries/Win64/ArkAscended.exe').write_bytes(b'synthetic ARK fixture')

    def test_read_only_exact_version_mismatch_and_missing_loaders(self):
        before = {str(p): p.read_bytes() for base in (self.gta, self.ark) for p in base.rglob('*') if p.is_file()}
        with patch.object(workflow, 'file_version', return_value='1.0.1158.16'):
            result = workflow.inspect(self.gta, self.ark)
        self.assertFalse(result['gta_version_supported_by_reviewed_shv'])
        self.assertIn('gta_script_hook_version_mismatch', result['blockers'])
        self.assertIn('ue4ss_not_installed', result['blockers'])
        self.assertFalse(result['game_runtime_verified']); self.assertFalse(result['game_files_modified'])
        self.assertTrue(all(Path(p).read_bytes() == data for p, data in before.items()))

    def test_supported_version_and_detected_loader_still_do_not_prove_runtime(self):
        (self.gta / 'ScriptHookV.dll').write_bytes(b'not a real loader')
        with patch.object(workflow, 'file_version', return_value='1.0.1158.13'):
            result = workflow.inspect(self.gta, self.ark)
        self.assertTrue(result['gta_version_supported_by_reviewed_shv'])
        self.assertNotIn('gta_script_hook_version_mismatch', result['blockers'])
        self.assertFalse(result['game_runtime_verified'])

    def test_unknown_version_and_missing_binary_do_not_invent_compatibility(self):
        with patch.object(workflow, 'file_version', return_value=None):
            self.assertIn('gta_version_unknown', workflow.inspect(self.gta, self.ark)['blockers'])
        (self.gta / 'GTA5_Enhanced.exe').unlink()
        self.assertIn('gta_executable_missing', workflow.inspect(self.gta, self.ark)['blockers'])

    def test_default_package_is_a_plan_without_writes(self):
        plan = workflow.package(root=self.root)
        self.assertFalse((self.root / '.smelter').exists())
        self.assertFalse(plan['staged']); self.assertFalse(plan['installable'])
        self.assertEqual(len(plan['files']), 3)
        self.assertFalse(any(row['path'].endswith(('.asi', '.dll', '.exe')) for row in plan['files']))

    def test_staged_source_hashes_match_and_existing_packages_are_preserved(self):
        first = workflow.package(root=self.root, stage=True)
        second = workflow.package(root=self.root, stage=True)
        self.assertNotEqual(first['path'], second['path'])
        for row in first['files']:
            self.assertEqual(hashlib.sha256((Path(first['path']) / row['path']).read_bytes()).hexdigest(), row['sha256'])
        saved = json.loads((Path(first['path']) / 'manifest.json').read_text())
        self.assertFalse(saved['installable']); self.assertEqual(saved['status'], 'source_staged')

    def test_links_cannot_redirect_package_writes(self):
        outside = self.root / 'outside'; outside.mkdir()
        link = self.root / '.smelter'
        try: link.symlink_to(outside, target_is_directory=True)
        except OSError as exc: self.skipTest('Directory symlinks unavailable: ' + str(exc))
        with self.assertRaisesRegex(ValueError, 'Linked/reparse'): workflow.package(root=self.root, stage=True)
        self.assertEqual(list(outside.iterdir()), [])


if __name__ == '__main__': unittest.main()
