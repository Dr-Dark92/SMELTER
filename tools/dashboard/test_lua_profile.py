"""Execute the real GAL1 Lua reader in the fixed no-network Lua runner."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from uuid import uuid4
import sandbox
from test_native_build import toolchain
import subprocess
from unittest.mock import patch


class LuaEvidenceTests(unittest.TestCase):
    def classify(self, syntax_marker):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'snapshot';folder.mkdir()
            output=('SMELTER_TEST_RESULT|'+json.dumps({'tests':1,'failures':0,'errors':0,'skipped':0})+'\n'+syntax_marker).encode()
            ready={'ready':True,'docker':'docker','configured':{'cpp_image':'sha256:'+'a'*64}}
            with patch('sandbox.status',return_value=ready),patch('sandbox.snapshot',return_value=(folder,folder)), \
                 patch('sandbox.run',return_value=subprocess.CompletedProcess([],0,output,b'')), \
                 patch('sandbox._remove',return_value=True),patch('sandbox.record_owner'):
                return sandbox.coding_test(Path(tmp),Path(tmp),'lua')

    def test_green_requires_one_complete_clean_syntax_receipt(self):
        clean='SMELTER_LUA_SYNTAX_RESULT|'+json.dumps({'files_total':2,'files_checked':2,'errors':0,'failed_files':[]})+'\n'
        self.assertEqual(self.classify(clean)['stage'],'GREEN')
        for marker in ('',clean+clean,'SMELTER_LUA_SYNTAX_RESULT|{}\n',
                       'SMELTER_LUA_SYNTAX_RESULT|'+json.dumps({'files_total':2,'files_checked':1,'errors':0,'failed_files':[]})+'\n',
                       'SMELTER_LUA_SYNTAX_RESULT|'+json.dumps({'files_total':2,'files_checked':2,'errors':1,'failed_files':[]})+'\n'):
            with self.subTest(marker=marker):self.assertEqual(self.classify(marker)['stage'],'ERROR')


@unittest.skipUnless(toolchain(), 'Docker and smelter-cpp:2 required')
class LuaProfileTests(unittest.TestCase):
    def run_fixture(self, files):
        ready=toolchain()
        from process_runner import run
        with tempfile.TemporaryDirectory() as tmp:
            code=Path(tmp)/'code';(code/'.smelter').mkdir(parents=True)
            for relative,content in files.items():
                path=code/'mods/demo'/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content,encoding='utf-8')
            name='smelter-tests-'+uuid4().hex
            try:
                result=run(sandbox._flags(ready['docker'],name,code)+['--rm',ready['configured']['cpp_image'],
                    'python','-I','-c',sandbox.CODING_LUA],timeout=70,max_output=65536,text=True,capture_output=True)
            finally:self.assertTrue(sandbox._remove(ready['docker'],name))
            output=result.stdout+result.stderr
            counts=json.loads(next(line.split('|',1)[1] for line in output.splitlines() if line.startswith('SMELTER_TEST_RESULT|')))
            syntax=json.loads(next(line.split('|',1)[1] for line in output.splitlines() if line.startswith('SMELTER_LUA_SYNTAX_RESULT|')))
            return result.returncode,counts,syntax,output

    def test_unimported_broken_module_blocks_print_only_passing_test(self):
        code,counts,syntax,output=self.run_fixture({'Scripts/raptor.lua':'local config = {DIS Engagement_RANGE_CM = 800}\n',
            'tests/test_basic.lua':'print("BASIC_TEST_EXECUTED")\n'})
        self.assertEqual(code,1);self.assertEqual(counts['tests'],0);self.assertEqual(counts['errors'],1)
        self.assertEqual(syntax['files_checked'],2);self.assertEqual(syntax['errors'],1)
        self.assertNotIn('BASIC_TEST_EXECUTED',output)
        self.assertEqual(syntax['failed_files'][0]['path'],'mods/demo/Scripts/raptor.lua')

    def test_syntax_check_does_not_execute_unimported_source(self):
        code,counts,syntax,output=self.run_fixture({'Scripts/not_loaded.lua':'error("UNIMPORTED_SOURCE_EXECUTED")\n',
            'tests/test_basic.lua':'assert(2+2==4)\n'})
        self.assertEqual((code,counts['tests'],counts['errors']),(0,1,0),output)
        self.assertEqual((syntax['files_checked'],syntax['errors']),(2,0))
        self.assertNotIn('UNIMPORTED_SOURCE_EXECUTED',output)

    def test_real_import_and_assertion_failures_stay_visible(self):
        fixture={'Scripts/raptor.lua':'return {damage=25}\n',
            'tests/test_controller.lua':'package.path="Scripts/?.lua;"..package.path\nlocal m=require("raptor")\nassert(m.damage==25)\n'}
        code,counts,syntax,output=self.run_fixture(fixture)
        self.assertEqual((code,counts['tests'],counts['failures']),(0,1,0),output)
        fixture['tests/test_controller.lua']=fixture['tests/test_controller.lua'].replace('m.damage==25','m.damage==99')
        code,counts,syntax,output=self.run_fixture(fixture)
        self.assertEqual((code,counts['tests'],counts['failures'],counts['errors']),(1,1,1,0),output)

    def test_oversized_source_set_does_not_silently_skip_validation(self):
        files={f'Scripts/source_{i}.lua':'return {}\n' for i in range(512)}
        files['tests/test_basic.lua']='assert(true)\n'
        code,counts,syntax,output=self.run_fixture(files)
        self.assertEqual((code,counts['tests'],counts['errors']),(1,0,1),output)
        self.assertEqual((syntax['files_total'],syntax['files_checked']),(513,0))

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
