import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from engine_archive import identity, inputs, inspect, request
from tool_registry import schemas
from python_tools import permissions
from access_policy import Policy, using


class EngineArchiveTests(unittest.TestCase):
    def test_fixed_commands_and_numeric_pagination_only(self):
        base = {'format':'pak','action':'info','relative_path':'game/content.pak'}
        self.assertEqual(request(base)['limit'], 100)
        for extra in ({'action':'unpack'}, {'command':'cmd'}, {'offset':True}, {'limit':201},
                      {'contains':'x\nflag'}, {'entry':'--help'}, {'format':'iostore','action':'objects'}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):request({**base, **extra})

    def test_path_escape_and_docker_mount_injection_rejected(self):
        for path in ('../secret.pak','/secret.pak','C:/secret.pak','a\\b.pak',
                     'a/../b.pak','-file.pak','a,,b.pak','a\n.pak','a//b.pak','./a.pak'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                request({'format':'pak','action':'info','relative_path':path})

    def test_tool_requires_inventory_even_with_coding_grant(self):
        root = Path(__file__).resolve().parents[2]
        grants = permissions(root, {'coding_workspace':True})
        self.assertNotIn('inspect_engine_archive', {t['function']['name'] for t in schemas(grants)})
        with self.assertRaisesRegex(ValueError, 'approved inventory'):
            inspect(root, grants, {'format':'pak','action':'info','relative_path':'x.pak'})

    def test_iostore_mounts_exact_sidecars_without_unrelated_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            scope = Path(tmp)
            for name in ('game.utoc','game.ucas','game_s1.ucas','other.ucas','secret.txt'):
                (scope / name).write_bytes(b'fixture')
            found = inputs(scope, request({'format':'iostore','action':'info','relative_path':'game.utoc'}))
            self.assertEqual([r['target'] for r in found], ['/input/archive.utoc','/input/archive.ucas','/input/archive_s1.ucas'])
            self.assertTrue(all(not r['identity']['full_file_hash'] for r in found))

    def test_excluded_sidecar_denies_entire_run_before_docker(self):
        with tempfile.TemporaryDirectory() as tmp:
            scope = Path(tmp)
            (scope/'game.utoc').write_bytes(b'fixture')
            (scope/'game.ucas').write_bytes(b'fixture')
            policy = Policy({'schema_version':1,'locations':[{'id':'game','name':'game','path':str(scope),
                            'enabled':True,'read':True,'write':False,'execute':False,'operations':[], 'exclusions':['game.ucas']}]})
            with using(policy), patch('process_runner.run') as process:
                with self.assertRaises(ValueError):inputs(scope, {'format':'iostore','relative_path':'game.utoc'})
                process.assert_not_called()

    def test_bounded_fingerprint_detects_size_and_sample_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'x'
            path.write_bytes(b'a'*200000)
            before = identity(path)
            path.write_bytes(b'b'+b'a'*199999)
            self.assertNotEqual(before, identity(path))
            self.assertFalse(before['full_file_hash'])

    def test_format_mismatch_and_directory_are_not_archives(self):
        with tempfile.TemporaryDirectory() as tmp:
            scope=Path(tmp); (scope/'data.bundle').write_bytes(b'fixture');(scope/'dir.pak').mkdir()
            for name in ('data.bundle','dir.pak'):
                with self.assertRaises(ValueError):inputs(scope, {'format':'pak','relative_path':name})

    def test_worker_failure_is_an_error_for_both_transports(self):
        from tool_contract import result_failed
        self.assertTrue(result_failed({'status':'engine_archive_failed'}))
        self.assertFalse(result_failed({'status':'engine_archive_completed'}))

    def test_optional_image_key_accepts_old_saved_configs(self):
        from sandbox import validate, DEFAULT
        old = {k:v for k,v in DEFAULT.items() if k not in ('engine_image','cpp_image')}
        validate(old)
        with self.assertRaises(ValueError):validate({**old,'engine_image':'smelter-engine-cli:latest'})

    def test_full_manifest_still_fits_bridge_limit(self):
        grants={'frontend_workspace':True,'coding_workspace':True,'model_ids':['fixture'],'rea_analysis':True,
                'melty_read':True,'native_build':True,'inventory_root':'fixture','write_diagnostics':True}
        self.assertEqual(len(schemas(grants)), 32)

    def test_separate_selection_keeps_old_config_readable_and_explicit_values_win(self):
        from sandbox import config
        image='sha256:'+'a'*64
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);selection=root/'.smelter/tooling/engine-cli/selection.json'
            selection.parent.mkdir(parents=True);selection.write_text(json.dumps({'image_id':image}))
            with patch('database.chosen_database',return_value=None):
                self.assertEqual(config(root)['engine_image'],image)
            with patch('database.chosen_database',return_value='fixture'),patch('config_store.load_config',return_value={'engine_image':None}):
                self.assertIsNone(config(root)['engine_image'])
            selection.write_text(json.dumps({'image_id':'untrusted:latest'}))
            with patch('database.chosen_database',return_value=None):self.assertIsNone(config(root)['engine_image'])


if __name__ == '__main__':unittest.main()
