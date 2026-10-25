"""Coding workspace support for mods/<mod>/: editable sources, protected scripts and outputs, mods test profile."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import coding_workspace as cw
import sandbox


class ModPathTests(unittest.TestCase):
    def test_mod_sources_are_editable(self):
        for path in ('mods/gta-ark/gta/src/GtaArkLink.cpp', 'mods/gta-ark/gta/src/link_record.h',
                     'mods/gta-ark/ark/Mods/GtaArkLink/Scripts/main.lua', 'mods/gta-ark/tools/gal_link.py',
                     'mods/gta-ark/native.json', 'mods/gta-ark/ark/Mods/GtaArkLink/enabled.txt'):
            with self.subTest(path):
                self.assertEqual(cw.relative_path(path, edit=True), path)

    def test_build_scripts_are_copied_but_not_editable(self):
        self.assertEqual(cw.relative_path('mods/gta-ark/gta/build.bat'), 'mods/gta-ark/gta/build.bat')
        for script in ('mods/gta-ark/gta/build.bat', 'mods/gta-ark/install.ps1', 'mods/gta-ark/run.cmd'):
            with self.subTest(script), self.assertRaisesRegex(ValueError, 'no coding editor'):
                cw.relative_path(script, edit=True)

    def test_build_outputs_and_shallow_paths_are_rejected(self):
        for bad in ('mods/gta-ark/gta/build/GtaArkLink.asi', 'mods/gta-ark/gta/build/test.exe',
                    'mods/gta-ark/gta/build/x.obj', 'mods/gta-ark/gta/build/cpp_sample.bin', 'mods/readme.md'):
            with self.subTest(bad), self.assertRaises(ValueError):
                cw.relative_path(bad)
        with self.assertRaises(ValueError):
            cw.relative_path('mods/gta-ark/.git/config')

    def test_mods_profile_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target / 'tools/dashboard').mkdir(parents=True)
            (target / 'tools/dashboard/test_x.py').write_text('')
            self.assertEqual(cw.test_profiles(target), ['python'])
            (target / 'mods/demo/tests').mkdir(parents=True)
            (target / 'mods/demo/tests/test_demo.py').write_text('')
            self.assertEqual(cw.test_profiles(target), ['python', 'mods'])


class ModsRunnerScriptTests(unittest.TestCase):
    """Runs the exact in-container script with the host interpreter on a fake checkout."""

    def run_script(self, tests):
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp) / 'mods/demo'
            (mod / 'tools').mkdir(parents=True)
            (mod / 'tests').mkdir()
            (mod / 'tools/demo_lib.py').write_text('def double(x):\n    return 2 * x\n')
            (mod / 'tests/test_demo.py').write_text(
                'import sys, unittest\nfrom pathlib import Path\n'
                'sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))\n'
                'import demo_lib\n' + tests)
            done = subprocess.run([sys.executable, '-I', '-c', sandbox.CODING_MODS], cwd=tmp,
                                  capture_output=True, text=True, timeout=60)
            line = [l for l in done.stdout.splitlines() if l.startswith('SMELTER_TEST_RESULT|')]
            return done.returncode, json.loads(line[0].split('|', 1)[1])

    def test_passing_mod_tests_report_green_counts(self):
        code, counts = self.run_script('class T(unittest.TestCase):\n    def test_ok(self):\n        self.assertEqual(demo_lib.double(2), 4)\n')
        self.assertEqual((code, counts), (0, {'tests': 1, 'failures': 0, 'errors': 0, 'skipped': 0}))

    def test_assertion_failure_is_reported(self):
        code, counts = self.run_script('class T(unittest.TestCase):\n    def test_bad(self):\n        self.assertEqual(demo_lib.double(2), 5)\n')
        self.assertEqual((code, counts['failures'], counts['errors']), (1, 1, 0))

    def test_different_mods_cannot_share_cached_helper_modules(self):
        with tempfile.TemporaryDirectory() as tmp:
            for modname, number in (('a', 1), ('b', 2)):
                mod = Path(tmp) / 'mods' / modname
                (mod / 'tests').mkdir(parents=True)
                (mod / 'tests/shared_helper.py').write_text('VALUE = ' + str(number))
                (mod / 'tests/test_helper.py').write_text('import unittest, shared_helper\nclass T(unittest.TestCase):\n def test_value(self): self.assertEqual(shared_helper.VALUE, ' + str(number) + ')\n')
            result = subprocess.run([sys.executable, '-I', '-c', sandbox.CODING_MODS], cwd=tmp, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
