"""Execute the real GAL1 Lua reader in the fixed no-network Lua runner."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from uuid import uuid4
import sandbox
from test_native_build import toolchain


@unittest.skipUnless(toolchain(), 'Docker and smelter-cpp:2 required')
class LuaProfileTests(unittest.TestCase):
    def test_shared_gal1_fixture_and_transform_vectors(self):
        source = Path(__file__).resolve().parents[2] / 'mods/gta-ark'
        if not source.is_dir():
            self.skipTest('Mod fixture is not available')
        ready = toolchain()
        from process_runner import run
        with tempfile.TemporaryDirectory() as tmp:
            code = Path(tmp) / 'code'; code.mkdir(); (code / '.smelter').mkdir()
            for relative in ('tests/test_gal_link.lua', 'tests/gal1_fixture.hex', 'ark/Mods/GtaArkLink/Scripts/gal_link.lua'):
                target = code / 'mods/gta-ark' / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source / relative, target)
            name = 'smelter-tests-' + uuid4().hex
            try:
                result = run(sandbox._flags(ready['docker'], name, code) + ['--rm', ready['configured']['cpp_image'],
                             'python', '-I', '-c', sandbox.CODING_LUA], timeout=70, max_output=65536, text=True)
                counts = json.loads(next(line.split('|', 1)[1] for line in result.stdout.splitlines()
                                         if line.startswith('SMELTER_TEST_RESULT|')))
                self.assertEqual((result.returncode, counts), (0, {'tests':1, 'failures':0, 'errors':0, 'skipped':0}), result.stdout+result.stderr)
            finally:
                self.assertTrue(sandbox._remove(ready['docker'], name))
