import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from skill_runtime import SkillMonitor, initialize, runtime_manifest, _monitors
from skill_context import build_skill_context


class SkillRuntimeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.folder = self.root / 'skills/fixture'
        self.folder.mkdir(parents=True)
        self.manifest = self.folder / 'SKILL.md'
        self.manifest.write_text('# Fixture\n\n## Purpose\nInspect fixture data.\n')
        self.addCleanup(lambda: _monitors.pop(str(self.root.resolve()), None))

    def test_added_changed_removed_and_restart(self):
        monitor = initialize(self.root)
        self.assertFalse(monitor.status()['restart_required'])
        original = runtime_manifest(self.root, 'fixture')
        self.manifest.write_text(original + '\nUpdated instructions\n')
        self.assertEqual(monitor.status()['skills'][0]['activation'], 'restart_required')
        with self.assertRaisesRegex(ValueError, 'restart'):
            build_skill_context(self.root, ['fixture'])
        other = self.root / 'skills/another'
        other.mkdir()
        (other / 'SKILL.md').write_text('# Another\n\n## Purpose\nNew fixture.\n')
        self.assertIn({'id': 'another', 'change': 'added'}, monitor.status()['changes'])
        new = initialize(self.root)
        self.assertFalse(new.status()['restart_required'])
        self.assertIn('Updated instructions', build_skill_context(self.root, ['fixture']))
        self.manifest.unlink()
        self.assertIn({'id': 'fixture', 'change': 'removed'}, new.status()['changes'])

    def test_dependencies_are_declared_and_passively_detected(self):
        self.assertIsNone(SkillMonitor(self.root).status()['skills'][0]['dependencies'])
        (self.folder / 'smelter.json').write_text(json.dumps({'schema_version': 1, 'requires': ['fixture-engine']}))
        with patch('skill_runtime.shutil.which', return_value=None):
            status = SkillMonitor(self.root).status()['skills'][0]
        self.assertEqual(status['dependencies'][0]['status'], 'missing')
        self.assertEqual(status['activation'], 'enabled')

    def test_invalid_dependency_command_is_not_executed(self):
        (self.folder / 'smelter.json').write_text(json.dumps({'schema_version': 1, 'requires': ['node --eval unsafe']}))
        with patch('skill_runtime.shutil.which') as lookup:
            status = SkillMonitor(self.root).status()['skills'][0]
        self.assertEqual(status['activation'], 'invalid')
        lookup.assert_not_called()

    def test_symlink_manifest_not_loaded(self):
        self.manifest.unlink()
        target = self.root / 'outside.md'
        target.write_text('# Outside\n\n## Purpose\nExternal.\n')
        try:
            self.manifest.symlink_to(target)
        except OSError:
            self.skipTest('Symlink privilege unavailable')
        self.assertEqual(SkillMonitor(self.root).status()['skills'], [])

    def test_review_does_not_activate_added_manifest(self):
        monitor = initialize(self.root)
        other = self.root / 'skills/newskill'
        other.mkdir()
        (other / 'SKILL.md').write_text('# New Skill\n\n## Purpose\nInspect safely.\n')
        self.assertIn('Inspect safely', monitor.review('newskill')['text'])
        with self.assertRaises(ValueError):
            monitor.manifest('newskill')
        with self.assertRaises(ValueError):
            monitor.review('../outside')
