"""Lua host probe verdicts on synthetic run folders; no game, loader or Lua runtime is run."""
import hashlib
import json
from pathlib import Path
import unittest

import test_runtime_probe_verdict as base
import verify_lua_host_probe as lua

ROOT = Path(__file__).resolve().parents[2]


class LuaHostVerdictTests(unittest.TestCase):
    tearDown = base.VerdictTests.tearDown
    report = base.VerdictTests.report
    def setUp(self):
        base.VerdictTests.setUp(self)
        profile = json.loads((ROOT / 'mods/gta-ark/gta/rph/lua_host_probe_expectations.json').read_text(encoding='utf-8'))
        self.lua54 = self.base / 'lua54.dll'; self.lua54.write_bytes(b'lua fixture')
        self.keralua = self.base / 'KeraLua.dll'; self.keralua.write_bytes(b'keralua fixture')
        profile['executable'] = self.profile['executable']; profile['plugin']['sha256'] = self.plugin_hash
        self.plugin = self.base / 'Plugins/SmelterLuaHostProbe.dll'; self.plugin.write_bytes(b'MZ fixture plugin')
        profile['lua_host'] = {**profile['lua_host'], 'lua54_sha256': hashlib.sha256(b'lua fixture').hexdigest(), 'keralua_sha256': lua.sha256(self.keralua)}
        self.profile = profile
        self.log.write_text('[INFO] Loaded plugin SmelterLuaHostProbe.dll\n', encoding='utf-8')

    def evidence(self, path, **changes):
        value = {'schema_version': 1, 'lua_version': 'Lua 5.4', 'lua54_module_path': str(self.lua54),
                 'lua54_sha256': self.profile['lua_host']['lua54_sha256'], 'keralua_path': str(self.keralua), 'keralua_sha256': self.profile['lua_host']['keralua_sha256'],
                 'host_thread_id': 9, 'tick_thread_ids': [9] * 4, 'tick_numbers': [1, 2, 3, 4], 'integer_division': True,
                 'integer_subtype': True, 'utf8_library': True, 'ambient_libraries_absent': True, 'callback_calls': 4,
                 'host_mutating_callbacks': 0}
        value.update(changes); (path.parent / 'lua_host.json').write_text(json.dumps(value), encoding='utf-8')
        return path

    def test_complete_lua_run_is_verified(self):
        verdict, reasons, evidence = lua.judge_lua(self.evidence(self.report()), self.profile, self.log)
        self.assertEqual((verdict, reasons), ('lua_host_verified', []))
        self.assertEqual(evidence['lua_host']['lua_version'], 'Lua 5.4')

    def test_each_lua_gate_is_named(self):
        cases = {'lua_version_mismatch': {'lua_version': 'Lua 5.1'}, 'loaded_lua54_hash_mismatch': {'lua54_sha256': '0' * 64},
                 'keralua_hash_mismatch': {'keralua_sha256': '1' * 64}, 'callback_calls_not_4': {'callback_calls': 3},
                 'ticks_not_sequential': {'tick_numbers': [1, 2, 2, 4]}, 'ticks_left_host_thread': {'tick_thread_ids': [9, 9, 10, 9]},
                 'mutating_callbacks_reported': {'host_mutating_callbacks': 1}, 'utf8_library_failed': {'utf8_library': False},
                 'ambient_libraries_absent_failed': {'ambient_libraries_absent': False}}
        for i, (reason, change) in enumerate(cases.items()):
            with self.subTest(reason):
                verdict, reasons, _ = lua.judge_lua(self.evidence(self.report('run%d' % i), **change), self.profile, self.log)
                self.assertEqual(verdict, 'rejected'); self.assertIn(reason, reasons)

    def test_missing_evidence_or_changed_dll_on_disk_rejects(self):
        verdict, reasons, _ = lua.judge_lua(self.report('bare'), self.profile, self.log)
        self.assertIn('lua_host_evidence_missing', reasons)
        path = self.evidence(self.report('swapped')); self.lua54.write_bytes(b'other')
        self.assertIn('lua54_on_disk_mismatch', lua.judge_lua(path, self.profile, self.log)[1])

    def test_base_read_gates_still_apply(self):
        path = self.evidence(self.report('net', network_session_checks=3))
        self.assertIn('network_checks_not_4', lua.judge_lua(path, self.profile, self.log)[1])

    def test_keralua_binding_is_independently_rehashed(self):
        path = self.evidence(self.report('binding'))
        self.keralua.write_bytes(b'changed binding')
        self.assertIn('keralua_on_disk_mismatch', lua.judge_lua(path, self.profile, self.log)[1])

    def test_thread_cardinality_and_integer_types_are_checked(self):
        cases = [('ticks_left_host_thread', {'tick_thread_ids': [9]}),
                 ('host_thread_id_invalid', {'host_thread_id': True, 'tick_thread_ids': [True]*4}),
                 ('ticks_not_sequential', {'tick_numbers': [True, 2, 3, 4]}),
                 ('mutating_callbacks_reported', {'host_mutating_callbacks': False}),
                 ('lua_host_schema_unsupported', {'schema_version': True})]
        for i, (reason, changes) in enumerate(cases):
            with self.subTest(reason=reason):
                path = self.evidence(self.report('types%d' % i), **changes)
                self.assertIn(reason, lua.judge_lua(path, self.profile, self.log)[1])

    def test_malformed_evidence_rejects_without_crashing(self):
        path = self.report('malformed')
        for text in ('{broken', '[]', 'null'):
            (path.parent/'lua_host.json').write_text(text)
            verdict, reasons, _ = lua.judge_lua(path, self.profile, self.log)
            self.assertEqual(verdict, 'rejected')
            self.assertIn('lua_host_evidence_invalid', reasons)

    def test_real_profile_pins_the_staged_package(self):
        profile = json.loads((ROOT / 'mods/gta-ark/gta/rph/lua_host_probe_expectations.json').read_text(encoding='utf-8'))
        package = ROOT / profile['package']['path']
        if not package.is_dir(): self.skipTest('staged package not present')
        manifest = json.loads((package / 'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(manifest['plugin_sha256'], profile['plugin']['sha256'])
        self.assertEqual(manifest['root_files']['lua54.dll'], profile['lua_host']['lua54_sha256'])
        self.assertEqual(manifest['root_files']['KeraLua.dll'], profile['lua_host']['keralua_sha256'])
