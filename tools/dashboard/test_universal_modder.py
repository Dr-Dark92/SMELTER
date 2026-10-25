import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from universal_modder import verified_installation, run, cli_command


class UniversalModderTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.base = self.root / '.smelter/tooling/universal-modder'
        self.source = self.base / 'source'; self.source.mkdir(parents=True)
        (self.source / 'fixture.py').write_text('pinned fixture')
        note = self.source / 'knowledge/games/fixture/note.md'
        note.parent.mkdir(parents=True); note.write_text('reference data only')
        requirements = self.root / 'requirements.txt'; requirements.write_text('fixture==1')
        pin = {'version':'0.2.0','revision':'a' * 40,'sha256':'b' * 64,'requirements':'requirements.txt'}
        (self.root / 'system-requirements.json').write_text(json.dumps({'setup':{'universal_modder':pin}}))
        python = self.base / 'venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
        python.parent.mkdir(parents=True); python.write_text('fixture executable; never run')
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        manifest = self.base / 'source-manifest.json'
        manifest.write_text(json.dumps({'files':{'fixture.py':sha(self.source / 'fixture.py'),
                                               'knowledge/games/fixture/note.md':sha(note)}}))
        self.identity = {'version':pin['version'],'revision':pin['revision'],'archive_sha256':pin['sha256'],
                         'source':str(self.source),'python':str(python),'manifest_sha256':sha(manifest),
                         'requirements_sha256':sha(requirements)}
        (self.base / 'installation.json').write_text(json.dumps(self.identity))

    def test_status_verifies_without_launching_any_process(self):
        with patch('process_runner.run') as process:
            result = run(self.root, {'coding_workspace':True}, {'action':'status'})
        self.assertFalse(result['executed']); process.assert_not_called()

    def test_drift_and_unexpected_source_files_are_rejected(self):
        (self.source / 'extra.py').write_text('unreviewed')
        with self.assertRaises(ValueError):verified_installation(self.root)

    def test_local_query_is_data_and_cannot_select_a_command(self):
        query = '--remote; publish everything'
        with patch('access_policy.require') as require, patch('process_runner.run', return_value=subprocess.CompletedProcess([],0,'[]','')) as process:
            result = run(self.root, {'coding_workspace':True}, {'action':'search_notes','query':query})
        argv = process.call_args.args[0]
        self.assertEqual(argv[-2:], ['--', query])
        self.assertIn(str(self.source / 'knowledge'), argv)
        self.assertIn('--limit', argv)
        require.assert_called_once_with(Path(self.identity['python']), 'execute', 'modding')
        self.assertEqual(result['notes'], [])

    def test_grants_actions_and_argument_shape_fail_closed(self):
        with patch('process_runner.run') as process:
            with self.assertRaises(ValueError):run(self.root, {}, {'action':'status'})
            for args in ({'action':'scan'}, {'action':'restore'}, {'action':'status','query':'x'}, {'action':'search_notes','query':'x\n'}):
                with self.assertRaises(ValueError):run(self.root, {'coding_workspace':True}, args)
            process.assert_not_called()

    def test_python_ignores_source_bytecode_and_user_site(self):
        command = cli_command(self.identity, ['--version'])
        self.assertIn('-I', command); self.assertIn('-B', command)
        self.assertTrue(any(s.startswith('pycache_prefix=') for s in command))

    def test_read_note_is_paginated_and_cannot_escape_the_pinned_kb(self):
        with patch('access_policy.require'), patch('process_runner.run', return_value=subprocess.CompletedProcess([],0,'reference data only\n','')) as process:
            result = run(self.root, {'coding_workspace':True}, {'action':'read_note','note':'games/fixture/note.md','offset':3,'limit':5})
            self.assertEqual(result['text'], 'erenc')
            self.assertTrue(result['truncated'])
            process.reset_mock()
            for note in ('../secret.md', '/etc/secret.md', 'C:/secret.md', '--remote', 'games/missing.md'):
                with self.assertRaises(ValueError):run(self.root, {'coding_workspace':True}, {'action':'read_note','note':note})
            process.assert_not_called()
