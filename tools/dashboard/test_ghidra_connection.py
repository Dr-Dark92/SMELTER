"""Ghidra adapter contracts with disposable files and a fake headless process."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import ghidra_connection as ghidra
from access_policy import Policy, defaults, using


class GhidraConnectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.root = self.base / 'checkout'; self.root.mkdir()
        self.project_patch = patch('ghidra_connection._project_root', return_value=self.base / 'projects')
        self.project_patch.start(); self.addCleanup(self.project_patch.stop)
        self.game = self.base / 'game'; self.game.mkdir()
        self.target = self.game / 'sample.exe'; self.target.write_bytes(b'MZfixture')
        self.home = self.base / 'ghidra'; (self.home / 'support').mkdir(parents=True)
        self.launcher = self.home / 'support' / ('analyzeHeadless.bat' if os.name == 'nt' else 'analyzeHeadless')
        self.launcher.touch()
        (self.home / 'Ghidra').mkdir()
        (self.home / 'Ghidra/application.properties').write_text('application.version=12.1.4\n')
        self.grants = {'rea_analysis': True, 'rea_root': str(self.game)}
        self.calls = []
        self.behavior = 'ok'

    def runner(self, command, **kwargs):
        self.calls.append((command, kwargs))
        argv = json.loads(kwargs['env']['SMELTER_GHIDRA_ARGUMENTS']) if os.name == 'nt' else command[1:]
        index = argv.index('-postScript')
        operation, output = argv[index + 2:index + 4]
        if self.behavior == 'timeout': raise subprocess.TimeoutExpired(command, 180)
        if self.behavior == 'missing': return subprocess.CompletedProcess(command, 0, b'', b'')
        evidence = {'schema_version': 1, 'ok': True, 'operation': operation}
        if self.behavior == 'wrong': evidence['operation'] = 'unexpected'
        if self.behavior == 'huge': evidence['data'] = 'x' * (ghidra.MAX_RESULT + 1)
        if self.behavior == 'largevalid': evidence['data'] = 'x' * (128 * 1024)
        if self.behavior == 'changed': self.target.write_bytes(b'MZchanged')
        Path(output).write_text(json.dumps(evidence), encoding='utf-8')
        return subprocess.CompletedProcess(command, 1 if self.behavior == 'exit' else 0, b'engine log', b'fixture error')

    def invoke(self, name='rea_ghidra_analyze', arguments=None, grants=None):
        return ghidra.run_ghidra(self.root, self.grants if grants is None else grants,
                                  name, arguments or {'relative_path': 'sample.exe'},
                                  runner=self.runner, home=self.home)

    def test_analyze_retains_verified_snapshot_and_identity(self):
        result = self.invoke()
        self.assertEqual(result['provider'], 'ghidra')
        self.assertEqual(result['source_sha256'], hashlib.sha256(b'MZfixture').hexdigest())
        self.assertEqual(result['status'], 'rea_completed')
        evidence = Path(result['evidence_path'])
        self.assertEqual(result['evidence_sha256'], hashlib.sha256(evidence.read_bytes()).hexdigest())
        self.assertEqual((evidence.parent / 'input.exe').read_bytes(), b'MZfixture')
        self.assertTrue((evidence.parent / 'analysis.json').is_file())
        command, kwargs = self.calls[0]
        self.assertFalse(kwargs['shell'])
        self.assertEqual(kwargs['timeout'], 180)
        self.assertEqual(kwargs['env']['GHIDRA_HEADLESS_MAXMEM'], '1G')
        self.assertNotIn('JAVA_TOOL_OPTIONS', kwargs['env'])

    def test_queries_reuse_exact_analysis_and_are_paginated(self):
        first = self.invoke()
        result = self.invoke('rea_ghidra_functions', {'analysis_id': first['analysis_id'], 'query': 'main', 'limit': 3, 'offset': 1})
        self.assertEqual(result['analysis_id'], first['analysis_id'])
        command, kwargs = self.calls[-1]
        args = json.loads(kwargs['env']['SMELTER_GHIDRA_ARGUMENTS']) if os.name == 'nt' else command
        self.assertIn('-noanalysis', args); self.assertIn('-readOnly', args)
        self.assertNotIn('-import', args)
        self.assertEqual(kwargs['timeout'], 60)
        self.assertIn('bWFpbg==', args)

    def test_large_valid_evidence_is_retained_with_bounded_mcp_preview(self):
        self.behavior = 'largevalid'
        result = self.invoke()
        self.assertTrue(result['preview_truncated'])
        self.assertGreater(result['evidence_bytes'], ghidra.MAX_PREVIEW)
        self.assertLessEqual(len(json.dumps(result['result_preview'], ensure_ascii=True).encode('utf-8')), ghidra.MAX_PREVIEW)
        raw = Path(result['evidence_path']).read_bytes()
        self.assertEqual(len(json.loads(raw)['data']), 128 * 1024)
        self.assertEqual(result['evidence_sha256'], hashlib.sha256(raw).hexdigest())

    def test_failed_query_preserves_analysis_and_removes_only_its_output(self):
        initial = self.invoke()
        folder = Path(initial['evidence_path']).parent
        before = set(folder.iterdir())
        self.behavior = 'wrong'
        with self.assertRaisesRegex(ValueError, 'invalid or unsuccessful'):
            self.invoke('rea_ghidra_functions', {'analysis_id': initial['analysis_id']})
        self.assertEqual(set(folder.iterdir()), before)
        self.assertTrue((folder / 'analysis.json').is_file())
        self.behavior = 'ok'
        self.assertEqual(self.invoke('rea_ghidra_functions', {'analysis_id': initial['analysis_id']})['status'], 'rea_completed')

    def test_only_explicit_grant_can_start_native_parser(self):
        with self.assertRaisesRegex(ValueError, 'not approved'):
            self.invoke(grants={})
        self.assertEqual(self.calls, [])

    def test_traversal_absolute_ads_and_wrong_formats_rejected(self):
        (self.game / 'archive.oppc').write_bytes(b'archive')
        for value in ('../sample.exe', '/sample.exe', 'C:/sample.exe', 'a\\sample.exe', '-sample.exe', 'archive.oppc'):
            with self.subTest(value=value), self.assertRaises((ValueError, OSError)):
                self.invoke(arguments={'relative_path': value})
        self.assertFalse(self.calls)

    def test_elf_signature_is_supported_without_executable_extension(self):
        (self.game / 'fixture.data').write_bytes(b'\x7fELFfixture')
        result = self.invoke(arguments={'relative_path': 'fixture.data'})
        self.assertTrue((Path(result['evidence_path']).parent / 'input.elf').is_file())

    def test_size_and_missing_install_are_checked_before_launch(self):
        with patch.object(ghidra, 'MAX_INPUT', 1), self.assertRaises(ValueError): self.invoke()
        self.launcher.unlink()
        with self.assertRaisesRegex(ValueError, 'unavailable'): self.invoke()
        self.assertFalse(self.calls)

    def test_analysis_cannot_be_read_under_another_scope_or_after_change(self):
        result = self.invoke()
        original_calls = len(self.calls)
        other = self.base / 'other'; other.mkdir(); (other / 'sample.exe').write_bytes(b'MZfixture')
        with self.assertRaisesRegex(ValueError, 'different approved'):
            self.invoke('rea_ghidra_functions', {'analysis_id': result['analysis_id']}, grants={**self.grants, 'rea_root':str(other)})
        self.target.write_bytes(b'MZchanged')
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.invoke('rea_ghidra_functions', {'analysis_id': result['analysis_id']})
        self.assertEqual(len(self.calls), original_calls)

    def test_retained_input_tampering_rejected(self):
        result = self.invoke()
        (Path(result['evidence_path']).parent / 'input.exe').write_bytes(b'MZtampered')
        with self.assertRaisesRegex(ValueError, 'Retained binary changed'):
            self.invoke('rea_ghidra_strings', {'analysis_id': result['analysis_id']})

    def test_argument_injection_and_invalid_address_never_launch(self):
        for name, args in [('unknown', {}), ('rea_ghidra_analyze', {'relative_path':'sample.exe','script':'evil'}),
                           ('rea_ghidra_functions', {'analysis_id':'../escape'}),
                           ('rea_ghidra_decompile', {'analysis_id':'x', 'address':'1000;run'}),
                           ('rea_ghidra_strings', {'analysis_id':'x', 'limit':True})]:
            with self.subTest(name=name), self.assertRaises(ValueError): self.invoke(name, args)
        self.assertFalse(self.calls)

    def test_engine_failure_timeout_and_invalid_evidence_cleanup_owned_project(self):
        for behavior in ('exit', 'missing', 'timeout', 'wrong', 'huge', 'changed'):
            self.target.write_bytes(b'MZfixture'); self.behavior=behavior
            with self.subTest(behavior=behavior), self.assertRaises(ValueError): self.invoke()
        self.assertEqual(list((self.root / '.smelter/rea-evidence/ghidra').iterdir()), [])

    def test_policy_requires_target_read_and_registered_ghidra_execution(self):
        policy = defaults(self.root)
        def location(sid, path, execute=False):
            return {'id':sid,'name':sid,'path':str(path),'read':True,'write':False,'execute':execute,
                    'operations':['rea'] if execute else [],'exclusions':[],'enabled':True}
        policy['locations'].append(location('game',self.game))
        with using(Policy(policy)), self.assertRaisesRegex(ValueError, 'not registered'): self.invoke()
        policy['locations'].append(location('ghidra',self.home,True))
        with using(Policy(policy)): self.assertEqual(self.invoke()['status'], 'rea_completed')
        policy['locations'][-2]['read']=False
        with using(Policy(policy)), self.assertRaisesRegex(ValueError, 'Access denied'): self.invoke()

    def test_windows_batch_metacharacters_rejected_even_in_paths(self):
        if os.name != 'nt': self.skipTest('Windows batch contract')
        with self.assertRaisesRegex(ValueError, 'safely represent'):
            ghidra._command(self.launcher, ['a&whoami'], {})

    def test_concurrent_operation_is_rejected_without_a_second_process(self):
        ghidra._lock.acquire()
        try:
            with self.assertRaisesRegex(ValueError, 'already running'): self.invoke()
        finally: ghidra._lock.release()
        self.assertFalse(self.calls)

    def test_windows_environment_keeps_batch_launch_hidden_and_drops_java_agents(self):
        if os.name != 'nt': self.skipTest('Windows launcher environment')
        java = self.base/'jdk/bin/java.exe';java.parent.mkdir(parents=True);java.touch()
        with patch.dict(os.environ, {'JAVA_HOME':'"'+str(java.parent.parent)+'"',
                                     'PATHEXT':'.CPL','JAVA_TOOL_OPTIONS':'-javaagent:untrusted'}):
            env=ghidra._environment()
        self.assertEqual(env['JAVA_HOME'],str(java.parent.parent))
        self.assertIn('.BAT',env['PATHEXT'])
        self.assertNotIn('JAVA_TOOL_OPTIONS',env)

    def test_ghidra_receipt_has_engine_identity_without_rea_package_version(self):
        from python_tools import ToolSession
        result=self.invoke()
        session=object.__new__(ToolSession)
        session.events=[{'tool':'rea_ghidra_analyze','reused':False,'transport':'mcp','result':result}]
        session.audit_path='fixture-audit.jsonl'
        text=session.receipt()
        self.assertIn('Ghidra 12.1.4',text)
        self.assertIn(result['evidence_sha256'],text)


if __name__ == '__main__': unittest.main()
