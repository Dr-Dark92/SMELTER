"""Run the engine-neutral Lua host probe offline with fake reads and the pinned Lua 5.4 binding."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

import build_managed_mod as managed
import install_managed_sdk as sdk

ROOT = Path(__file__).resolve().parents[2]
SOURCES = ['mods/gta-ark/common/managed/RuntimeProbeHarness.cs', 'mods/gta-ark/common/managed/LuaModuleHost.cs',
           'mods/gta-ark/common/managed/LuaTickProbe.cs', 'tools/setup/fixtures/LuaTickProbeFixture.cs']


@unittest.skipUnless(os.name == 'nt' and (ROOT / '.smelter/tooling/keralua-sdk/1.4.11/KeraLua.dll').is_file(),
                     'Pinned KeraLua development cache and Windows compiler required')
class LuaTickProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='smelter-lua-tick-')
        cls.base = Path(cls.temp.name)
        files = sdk.inspect(ROOT, 'keralua')['files']
        for name in ('KeraLua.dll', 'lua54.dll'):
            (cls.base / name).write_bytes(Path(files[name]).read_bytes())
        compiler, refs, _ = managed.compiler()
        cls.exe = cls.base / 'LuaTickProbeFixture.exe'
        command = [str(compiler), *[f for f in managed.FLAGS if f != '/target:library'], '/target:exe', '/out:' + str(cls.exe),
                   *['/reference:' + str(p) for p in refs], '/reference:' + str(cls.base / 'KeraLua.dll'),
                   *[str(ROOT / s) for s in SOURCES]]
        result = subprocess.run(command, cwd=cls.base, capture_output=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            cls.temp.cleanup(); raise AssertionError((result.stdout + result.stderr).decode(errors='replace'))
        cls.lua54 = sdk.spec(ROOT, 'keralua')['files']['lua54.dll']['sha256']

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_probe(self, scenario):
        out = self.base / scenario
        result = subprocess.run([str(self.exe), scenario, str(out)], cwd=self.base, capture_output=True, text=True,
                                timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(result.returncode, 0, result.stderr)
        evidence = json.loads((out / 'lua_host.json').read_text(encoding='utf-8-sig'))
        return result.stdout.splitlines(), evidence

    def test_four_reads_go_through_lua_54_on_one_thread(self):
        lines, ev = self.run_probe('ok')
        samples = [l.split('|') for l in lines if l.startswith('SAMPLE|')]
        self.assertEqual(len(samples), 4, lines)
        self.assertEqual([s[1] for s in samples], ['fake-ped-7'] * 4)
        self.assertEqual([float(s[2]) for s in samples], [1.5, 3.0, 4.5, 6.0])
        self.assertEqual(ev['lua_version'], 'Lua 5.4'); self.assertEqual(ev['callback_calls'], 4)
        self.assertEqual(ev['tick_numbers'], [1, 2, 3, 4]); self.assertEqual(set(ev['tick_thread_ids']), {ev['host_thread_id']})
        self.assertTrue(ev['integer_division'] and ev['integer_subtype'] and ev['utf8_library'] and ev['ambient_libraries_absent'])
        self.assertEqual(ev['lua54_sha256'], self.lua54); self.assertEqual(ev['host_mutating_callbacks'], 0)
        self.assertTrue(ev['lua54_module_path'].lower().endswith('lua54.dll'))

    def test_unavailable_or_failing_reads_stop_without_a_sample(self):
        for scenario, reason in [('unavailable', 'player_ped_unavailable'), ('throws', 'engine_read_failed')]:
            with self.subTest(scenario):
                lines, ev = self.run_probe(scenario)
                self.assertFalse([l for l in lines if l.startswith('SAMPLE|')])
                error = [l for l in lines if l.startswith('ERROR|')]
                self.assertTrue(error and 'lua_tick_failed' in error[0] and reason in error[0], lines)
                self.assertEqual(ev['callback_calls'], 1)


if __name__ == '__main__':
    unittest.main()
