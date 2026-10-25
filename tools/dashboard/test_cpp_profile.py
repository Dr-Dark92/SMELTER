"""Confined C++ test profile: config migration, sandbox flags, profile detection and a real g++ run."""
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

import coding_workspace as cw
import sandbox

IMAGE_TAG = 'smelter-cpp:2'
GOOD = '#include <cassert>\n#include <cmath>\n#include "lib/fov.h"\nint main() {\n  assert(std::fabs(fov(50.0, 1.0) - 50.0) < 1e-9);\n  return 0;\n}\n'
FOV = '#pragma once\n#include <cmath>\ninline double fov(double v, double a) {\n  const double r = v * 3.14159265358979323846 / 180.0;\n  return 2.0 * std::atan(std::tan(r / 2.0) * a) * 180.0 / 3.14159265358979323846;\n}\n'


def image_id():
    docker = shutil.which('docker')
    if not docker:
        return None, None
    from process_runner import run
    try:
        done = run([docker, 'image', 'inspect', '--format', '{{.Id}}', IMAGE_TAG], timeout=10, text=True, capture_output=True)
    except (OSError, ValueError):
        return None, None
    return (docker, done.stdout.strip()) if done.returncode == 0 else (None, None)


class ConfigAndFlagsTests(unittest.TestCase):
    def test_saved_configuration_without_cpp_image_stays_valid(self):
        old = {'schema_version': 1, 'python_image': None, 'node_image': None, 'opencode_image': None}
        self.assertIs(sandbox.validate(old), old)
        with self.assertRaises(ValueError):
            sandbox.validate({**old, 'cpp_image': 'smelter-cpp:1'})  # tags are not accepted
        sandbox.validate({**old, 'cpp_image': 'sha256:' + 'a' * 64})
        with self.assertRaises(ValueError):
            sandbox.validate({**old, 'other_image': None})

    def test_only_the_cpp_profile_gets_an_exec_scratch(self):
        plain = sandbox._flags('docker', 'n', Path('/x'))
        cpp = sandbox._flags('docker', 'n', Path('/x'), exec_scratch=True)
        self.assertTrue(all('exec,' not in f or 'noexec' in f for f in plain))
        build = [f for f in cpp if f.startswith('/build:')]
        self.assertEqual(build, ['/build:rw,exec,nosuid,nodev,size=256m,mode=1777'])
        for flag in ('--network', 'none', '--read-only', '--cap-drop', 'ALL', '65534:65534'):
            self.assertIn(flag, cpp)

    def test_cpp_profile_is_detected_and_offered(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target / 'mods/demo/tests/cpp').mkdir(parents=True)
            self.assertEqual(cw.test_profiles(target), [])
            (target / 'mods/demo/tests/cpp/test_fov.cpp').write_text(GOOD)
            self.assertEqual(cw.test_profiles(target), ['cpp'])
        from tool_registry import schemas
        tool = next(t for t in schemas({'coding_workspace': True, 'inventory_root': None, 'write_diagnostics': False})
                    if t['function']['name'] == 'run_coding_tests')
        self.assertIn('cpp', tool['function']['parameters']['properties']['profile']['enum'])


@unittest.skipUnless(image_id()[0], 'Docker with the smelter-cpp:1 image is required')
class RealConfinedRunTests(unittest.TestCase):
    """The exact in-container runner, with the production sandbox flags, on a temporary snapshot."""

    def run_profile(self, tests):
        docker, image = image_id()
        from process_runner import run
        with tempfile.TemporaryDirectory() as tmp:
            code = Path(tmp) / 'code'
            (code / 'mods/demo/lib').mkdir(parents=True)
            (code / 'mods/demo/tests/cpp').mkdir(parents=True)
            (code / 'mods/demo/lib/fov.h').write_text(FOV)
            (code / '.smelter').mkdir()  # production snapshots have it; the sandbox mounts a tmpfs there
            for name, text in tests.items():
                (code / 'mods/demo/tests/cpp' / name).write_text(text)
            name = 'smelter-cpp-test-' + uuid4().hex
            try:
                done = run(sandbox._flags(docker, name, code, exec_scratch=True) + ['--rm', image, 'python', '-I', '-c', sandbox.CODING_CPP],
                           timeout=160, max_output=2 * 1024 * 1024, text=True, capture_output=True)
            finally:
                run([docker, 'rm', '-f', name], timeout=30, capture_output=True)
            output = done.stdout + done.stderr
            match = re.search(r'^SMELTER_TEST_RESULT\|(\{[^\n]+\})\s*$', output, re.M)
            self.assertIsNotNone(match, output[-3000:])
            return done.returncode, json.loads(match.group(1)), output

    def test_passing_program(self):
        code, counts, _ = self.run_profile({'test_fov.cpp': GOOD})
        self.assertEqual((code, counts), (0, {'tests': 1, 'failures': 0, 'errors': 0, 'skipped': 0}))

    def test_oversized_suite_cannot_report_green(self):
        code, counts, output = self.run_profile({'test_%02d.cpp' % i: GOOD for i in range(65)})
        self.assertEqual((code, counts['tests'], counts['errors']), (1, 0, 1))
        self.assertIn('nothing was silently omitted', output)

    def test_logic_bug_is_a_failure_not_a_pass(self):
        # The degrees-into-tan bug Qwen wrote for HorizontalFov: compiles cleanly, but the check catches it.
        buggy = GOOD.replace('fov(50.0, 1.0)', 'buggy(50.0, 16.0 / 9.0)').replace('- 50.0', '- 79.317') \
                    .replace('int main', 'inline double buggy(double v, double a) { return 2.0 * std::atan(std::tan(v / 2.0) * a); }\nint main')
        code, counts, output = self.run_profile({'test_buggy.cpp': buggy})
        self.assertEqual((code, counts['failures'], counts['errors']), (1, 1, 0), output[-2000:])

    def test_compile_error_and_warnings_are_errors(self):
        code, counts, output = self.run_profile({'test_broken.cpp': 'int main( { return 0; }\n',
                                                 'test_warn.cpp': 'int main() { int unused; return 0; }\n'})
        self.assertEqual((code, counts['errors'], counts['failures']), (1, 2, 0), output[-2000:])

    def test_no_network_inside(self):
        probe = ('#include <netdb.h>\n#include <cstdio>\nint main() { return gethostbyname("example.com") ? 1 : 0; }\n')
        code, counts, output = self.run_profile({'test_net.cpp': probe})
        self.assertEqual((code, counts['failures']), (0, 0), output[-2000:])


if __name__ == '__main__':
    unittest.main()
