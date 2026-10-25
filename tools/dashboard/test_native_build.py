"""Confined Windows cross-builds: grants, frozen sources, diagnostics, and artifacts."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import native_build
from python_tools import permissions

ASI = '#include <windows.h>\nBOOL APIENTRY DllMain(HMODULE, DWORD, LPVOID) { return TRUE; }\n'


def toolchain():
    docker = shutil.which('docker')
    if not docker:
        return None
    try:
        done = subprocess.run([docker, 'image', 'inspect', '--format', '{{.Id}}', 'smelter-cpp:2'],
                              capture_output=True, text=True, timeout=5)
        if done.returncode == 0:
            return {'ready': True, 'docker': docker, 'configured': {'cpp_image': done.stdout.strip()}}
    except (OSError, subprocess.SubprocessError):
        pass
    return None


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.mod = Path(self.tmp.name) / 'demo'
        (self.mod / 'src').mkdir(parents=True)
        (self.mod / 'src/main.cpp').write_text(ASI)

    def write(self, targets):
        (self.mod / 'native.json').write_text(json.dumps({'schema_version': 1, 'targets': targets}))
        return native_build.manifest(self.mod)

    def test_valid_manifest(self):
        targets = self.write([{'name': 'Demo', 'kind': 'asi', 'sources': ['src/main.cpp'], 'libs': ['user32'],
                               'defines': ['FEATURE', 'LEVEL=2'], 'include_dirs': ['src']}])
        self.assertEqual(targets[0]['name'], 'Demo')

    def test_rejects_unsafe_fields(self):
        bad = [
            {'name': 'x', 'kind': 'dll', 'sources': ['src/main.cpp']},                       # unknown kind
            {'name': 'x', 'kind': 'asi', 'sources': ['../escape.cpp']},                      # traversal
            {'name': 'x', 'kind': 'asi', 'sources': ['C:/abs.cpp']},                         # absolute
            {'name': 'x', 'kind': 'asi', 'sources': ['src/build.bat']},                      # not C/C++
            {'name': 'x', 'kind': 'asi', 'sources': ['src/main.cpp'], 'libs': ['ws2_32']},   # library not allowlisted
            {'name': 'x', 'kind': 'asi', 'sources': ['src/main.cpp'], 'defines': ['X=$(cmd)']},
            {'name': 'x', 'kind': 'asi', 'sources': ['src/main.cpp'], 'flags': ['/link evil']},  # no free flags
            {'name': '../x', 'kind': 'asi', 'sources': ['src/main.cpp']},
            {'name': 'CON', 'kind': 'asi', 'sources': ['src/main.cpp']},
            {'name': 'x', 'kind': [], 'sources': ['src/main.cpp']},
            {'name': 'x', 'kind': 'asi', 'sources': ['src/main.cpp'], 'libs': [{}]},
            {'name': 'x', 'kind': 'asi', 'sources': ['src/main.cpp'], 'include_dirs': 'src'},
        ]
        for target in bad:
            with self.subTest(target), self.assertRaises(ValueError):
                self.write([target])
        with self.assertRaisesRegex(ValueError, 'needs a native.json'):
            native_build.manifest(Path(self.tmp.name))

    def test_freeze_refuses_dangerous_preprocessor_lines(self):
        for line in ('#import "evil.tlb"', '#pragma comment(linker, "/ENTRY:x")', '#pragma comment(lib, "ws2_32")',
                     '#include "C:/Windows/win.ini"', '#include "../../secrets.h"', '#using <mscorlib.dll>'):
            with self.subTest(line):
                (self.mod / 'src/bad.h').write_text(line + '\n')
                with self.assertRaisesRegex(ValueError, 'Refused'):
                    native_build._freeze(self.mod, Path(self.tmp.name) / ('out' + str(abs(hash(line)))))
        (self.mod / 'src/bad.h').write_text('#include <windows.h>\n#include "main_api.h"\n')
        (self.mod / 'tests').mkdir()
        (self.mod / 'tests/t.cpp').write_text('#include "../src/bad.h"\n')  # sibling folder inside the mod
        copied = native_build._freeze(self.mod, Path(self.tmp.name) / 'ok')
        self.assertEqual(copied, ['src/bad.h', 'src/main.cpp', 'tests/t.cpp'])
        (self.mod / 'tests/t.cpp').write_text('#include "../../outside.h"\n')  # leaves the mod
        with self.assertRaisesRegex(ValueError, 'Refused tests/t.cpp'):
            native_build._freeze(self.mod, Path(self.tmp.name) / 'escape')

    def test_grant_requires_the_coding_workspace(self):
        root = Path(self.tmp.name)
        with self.assertRaisesRegex(ValueError, 'approve the coding workspace'):
            permissions(root, {'native_build': True})
        self.assertTrue(permissions(root, {'native_build': True, 'coding_workspace': True})['native_build'])
        from tool_registry import schemas
        names = lambda g: {t['function']['name'] for t in schemas(g)}
        base = permissions(root, {'coding_workspace': True})
        self.assertNotIn('build_native_mod', names(base))
        self.assertIn('build_native_mod', names({**base, 'native_build': True}))
        with self.assertRaisesRegex(ValueError, 'not approved'):
            native_build.build(root, base, {'workspace_id': 'x', 'mod': 'demo'})


@unittest.skipUnless(toolchain(), 'Docker and the smelter-cpp:2 image are required')
class RealCompileTests(unittest.TestCase):
    """Cross-compiles only; produced Windows code is never executed."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'checkout'
        self.workspace = Path(self.tmp.name) / 'workspace'
        self.mod = self.workspace / 'mods/demo'
        (self.mod / 'src').mkdir(parents=True)
        (self.mod / 'src/main.cpp').write_text(ASI)
        self.root.mkdir()
        self.grants = {'native_build': True, 'coding_workspace': True}

    def build(self, targets):
        (self.mod / 'native.json').write_text(json.dumps({'schema_version': 1, 'targets': targets}))
        with patch('coding_workspace.load', return_value=({}, self.workspace)), \
             patch('access_policy.require'), patch('sandbox.status', return_value=toolchain()), \
             patch.object(native_build, 'msvc', side_effect=AssertionError('host compiler must never run')):
            return native_build.build(self.root, self.grants, {'workspace_id': 'w', 'mod': 'demo'})

    def test_compiles_an_asi_and_records_hashes_without_running_it(self):
        result = self.build([{'name': 'Demo', 'kind': 'asi', 'sources': ['src/main.cpp'], 'libs': ['user32']}])
        self.assertEqual(result['status'], 'native_build_succeeded', result)
        artifact = result['targets'][0]['artifacts'][0]
        self.assertEqual(artifact['file'], 'Demo.asi')
        self.assertEqual(len(artifact['sha256']), 64)
        self.assertFalse(result['executed_artifacts'])
        evidence = json.loads(Path(result['evidence_path']).read_text())
        self.assertIn('-Werror', evidence['flags'])
        self.assertEqual(evidence['sandbox'], 'docker-no-network')
        self.assertEqual(len(evidence['sources']['src/main.cpp']), 64)

    def test_compiler_errors_come_back_as_diagnostics(self):
        (self.mod / 'src/main.cpp').write_text(ASI + 'int broken( { return 0; }\n')
        result = self.build([{'name': 'Demo', 'kind': 'asi', 'sources': ['src/main.cpp']}])
        self.assertEqual(result['status'], 'native_build_failed')
        self.assertIn('error', result['targets'][0]['diagnostics'])
        self.assertEqual(result['targets'][0]['artifacts'], [])

    def test_warnings_fail_the_build(self):
        (self.mod / 'src/main.cpp').write_text(ASI + 'int unused(int a) { int b; return a; }\n')
        result = self.build([{'name': 'Demo', 'kind': 'asi', 'sources': ['src/main.cpp']}])
        self.assertEqual(result['status'], 'native_build_failed')
        self.assertIn('-Werror=unused-variable', result['targets'][0]['diagnostics'])

    def test_macro_include_cannot_read_a_host_file(self):
        secret = self.root / 'host_secret.h'
        secret.write_text('#error HOST_SECRET_MUST_NOT_ENTER_DIAGNOSTICS\n')
        (self.mod / 'src/main.cpp').write_text('#define HEADER "' + secret.as_posix() + '"\n#include HEADER\n' + ASI)
        result = self.build([{'name': 'Demo', 'kind': 'asi', 'sources': ['src/main.cpp']}])
        self.assertEqual(result['status'], 'native_build_failed')
        self.assertNotIn('HOST_SECRET_MUST_NOT_ENTER_DIAGNOSTICS', json.dumps(result))

    def test_repository_gta_ark_targets_cross_compile(self):
        source = Path(__file__).resolve().parents[2] / 'mods/gta-ark'
        if not source.is_dir():
            self.skipTest('Repository mod fixture is not present in this snapshot')
        shutil.copytree(source, self.mod, dirs_exist_ok=True, ignore=shutil.ignore_patterns('build', '__pycache__'))
        targets = json.loads((source / 'native.json').read_text())['targets']
        result = self.build(targets)
        self.assertEqual(result['status'], 'native_build_succeeded', result['targets'])


if __name__ == '__main__':
    unittest.main()
