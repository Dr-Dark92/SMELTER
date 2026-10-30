"""Review-hash, compiler and false-GREEN boundaries for the pure registry fixture."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import check_entity_registry as checker


class RegistryCheckerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='smelter-registry-check-')
        self.root=Path(self.temp.name)
        self.source=self.root/'EntityRegistry.cs';self.source.write_text('public class Placeholder {}')
        self.fixture=self.root/'tools/setup/fixtures/EntityRegistryFixture.cs'
        self.fixture.parent.mkdir(parents=True)
        self.fixture.write_bytes((checker.ROOT/'tools/setup/fixtures/EntityRegistryFixture.cs').read_bytes())

    def tearDown(self):self.temp.cleanup()

    def test_wrong_or_oversized_reviewed_source_never_invokes_compiler(self):
        with patch.object(checker.managed,'compiler') as compiler:
            with self.assertRaisesRegex(ValueError,'operator review'):
                checker.check(self.root,self.source,'0'*64)
            self.source.write_bytes(b'x'*131073)
            with self.assertRaises(ValueError):
                checker.check(self.root,self.source,hashlib.sha256(self.source.read_bytes()).hexdigest())
            compiler.assert_not_called()
        self.assertFalse((self.root/'.smelter/entity-registry-runs').exists())

    def test_exit_zero_without_fixture_success_marker_is_red(self):
        exe=self.root/'compiler.exe';exe.write_bytes(b'compiler fixture')
        results=[subprocess.CompletedProcess([],0,b'compiled',b''),subprocess.CompletedProcess([],0,b'no evidence',b'')]
        with patch.object(checker.managed,'compiler',return_value=(exe,[],534296)),patch.object(checker.subprocess,'run',side_effect=results) as run:
            result=checker.check(self.root,self.source,hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(result['stage'],'RED');self.assertFalse(result['sdk_referenced'])
        self.assertFalse(result['game_runtime_verified'])
        self.assertEqual(run.call_args_list[1].kwargs['timeout'],10)
        self.assertEqual(json.loads(Path(result['receipt']).read_text())['stage'],'RED')

    def test_compile_failure_never_runs_the_fixture(self):
        exe=self.root/'compiler.exe';exe.write_bytes(b'compiler fixture')
        with patch.object(checker.managed,'compiler',return_value=(exe,[],534296)),patch.object(checker.subprocess,'run',return_value=subprocess.CompletedProcess([],1,b'C# invalid',b'')) as run:
            result=checker.check(self.root,self.source,hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(result['stage'],'RED');self.assertEqual(run.call_count,1)

    def test_malformed_failed_duplicate_or_inconsistent_summary_is_red(self):
        exe=self.root/'compiler.exe';exe.write_bytes(b'compiler fixture')
        for log in (b'REGISTRY_RESULT|checks=1;failures=1\n',
                    b'REGISTRY_RESULT|checks=1;failures=0\n',
                    b'[REGISTRY PASS] a\nREGISTRY_RESULT|checks=2;failures=0\n',
                    b'[REGISTRY PASS] a\nREGISTRY_RESULT|checks=1;failures=0\nREGISTRY_RESULT|checks=1;failures=0\n'):
            with self.subTest(log=log),patch.object(checker.managed,'compiler',return_value=(exe,[],534296)),patch.object(checker.subprocess,'run',side_effect=[subprocess.CompletedProcess([],0,b'',b''),subprocess.CompletedProcess([],0,log,b'')]):
                result=checker.check(self.root,self.source,hashlib.sha256(self.source.read_bytes()).hexdigest())
            self.assertEqual(result['stage'],'RED')

    @unittest.skipUnless(os.name=='nt' and (checker.ROOT/checker.SUBJECT).is_file(),'Promoted reviewed registry and Windows compiler required')
    def test_reviewed_main_source_passes_the_real_pure_fixture(self):
        source=checker.ROOT/checker.SUBJECT
        result=checker.check(self.root,source,hashlib.sha256(source.read_bytes()).hexdigest())
        self.assertEqual(result['stage'],'GREEN',Path(result['log']).read_text(errors='replace'))
        self.assertIn('failures=0',Path(result['log']).read_text())


if __name__=='__main__':unittest.main()
