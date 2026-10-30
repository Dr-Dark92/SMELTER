"""Fixed compile-only managed builds and pinned SDK cache boundaries."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import build_managed_mod as managed
import install_managed_sdk as sdk
import test_coding_workspace as fixtures
import coding_workspace as cw


class ManagedBuildTests(unittest.TestCase):
    setUp=fixtures.CodingWorkspaceTests.setUp
    tearDown=fixtures.CodingWorkspaceTests.tearDown
    prepare=fixtures.CodingWorkspaceTests.prepare

    def test_cli_returns_failure_status_for_unsuccessful_compile_receipt(self):
        for stage,code in [('compiled',0),('compile_failed',1),('error',1)]:
            with self.subTest(stage=stage),patch.object(managed,'build',return_value={'stage':stage}),patch('sys.stdout',new_callable=io.StringIO) as output:
                self.assertEqual(managed.main(['--workspace-id','reviewed','--mod','demo','--target','Probe']),code)
                self.assertEqual(json.loads(output.getvalue())['stage'],stage)

    def fixture(self):
        lock=self.root/'tools/setup/managed-sdk-lock.json';lock.parent.mkdir(parents=True)
        data=b'reference fixture'
        item={'package':'Fixture','version':'1.0.0','source':'https://api.nuget.org/v3-flatcontainer/fixture/1.0.0/fixture.1.0.0.nupkg',
            'package_sha256':'0'*64,'max_package_bytes':1000,'files':{'Fixture.dll':{'member':'lib/Fixture.dll','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}},
            'development_only':True,'redistribute':False}
        lock.write_text(json.dumps({'schema_version':1,'sdks':{'fixture':item}}),encoding='utf-8')
        folder=sdk.folder(self.root,'fixture',item);folder.mkdir(parents=True)
        (folder/'Fixture.dll').write_bytes(data)
        mod=self.root/'mods/demo';mod.mkdir(parents=True)
        (mod/'Probe.cs').write_text('public class Probe {}\n',encoding='utf-8')
        config={'schema_version':1,'sdk':'fixture','targets':[{'name':'Probe','sources':['Probe.cs']}]}
        (mod/'managed.json').write_text(json.dumps(config),encoding='utf-8')
        sid,target=self.prepare()
        exe=self.root/'compiler.exe';exe.write_bytes(b'compiler fixture')
        return sid,target,exe,item

    def test_sdk_hash_failure_extracts_nothing_and_tampering_is_rejected(self):
        _,_,_,item=self.fixture();base=sdk.folder(self.root,'fixture',item)
        (base/'fixture.1.0.0.nupkg').write_bytes(b'wrong package')
        with self.assertRaisesRegex(ValueError,'SHA-256'):sdk.install(self.root,'fixture')
        (base/'Fixture.dll').write_bytes(b'tampered')
        with self.assertRaisesRegex(ValueError,'changed'):sdk.inspect(self.root,'fixture')
        lock=self.root/'tools/setup/managed-sdk-lock.json';d=json.loads(lock.read_text());d['sdks']['fixture']['version']='../../outside';lock.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,'package/version'):sdk.spec(self.root,'fixture')

    def test_manifest_rejects_flags_escape_and_case_duplicate_sources(self):
        _,target,_,_=self.fixture();mod=target/'mods/demo';path=mod/'managed.json'
        good=json.loads(path.read_text())
        cases=[{**good,'flags':['/analyzer:evil']},
               {**good,'schema_version':True},
               {**good,'targets':[{'name':'Probe','sources':['../outside.cs']}]},
               {**good,'targets':[{'name':'Probe','sources':['Probe.cs','probe.cs']}]},
               {**good,'targets':[{'name':'Probe','sources':['test.py']}]}]
        for value in cases:
            with self.subTest(value=value):
                path.write_text(json.dumps(value))
                with self.assertRaises(ValueError):managed.manifest(mod)

    def test_build_uses_fixed_flags_and_does_not_copy_sdk_or_execute_output(self):
        sid,target,exe,_=self.fixture();seen=[]
        def compile_only(args,**kwargs):
            seen.append((args,kwargs));out=Path(next(a[5:] for a in args if a.startswith('/out:')))
            out.write_bytes(b'MZ compiled fixture')
            return subprocess.CompletedProcess(args,0,b'compiled',b'')
        with patch.object(managed,'compiler',return_value=(exe,[],534296)),patch.object(managed.subprocess,'run',side_effect=compile_only):
            result=managed.build(self.root,sid,'demo','Probe')
        self.assertEqual(result['stage'],'compiled');self.assertFalse(result['artifact_executed'])
        self.assertFalse(result['game_runtime_verified']);self.assertFalse(result['sdk_copied_to_output'])
        self.assertEqual(len(seen),1)
        for flag in ['/noconfig','/nostdlib+','/unsafe-','/target:library']:self.assertIn(flag,seen[0][0])
        self.assertEqual(seen[0][1]['timeout'],60)
        self.assertEqual([p.name for p in Path(result['artifact']['path']).parent.iterdir()],['Probe.dll'])
        self.assertEqual((target/'mods/demo/Probe.cs').read_text(),'public class Probe {}\n')

    def test_target_can_select_pinned_sdk_and_native_dll_is_not_a_compiler_reference(self):
        sid,target,exe,item=self.fixture()
        lock=self.root/'tools/setup/managed-sdk-lock.json';value=json.loads(lock.read_text())
        native=b'native library fixture'
        value['sdks']['fixture']['files']['lua54.dll']={'member':'native/lua54.dll','bytes':len(native),'sha256':hashlib.sha256(native).hexdigest(),'reference':False}
        lock.write_text(json.dumps(value))
        (sdk.folder(self.root,'fixture',item)/'lua54.dll').write_bytes(native)
        path=target/'mods/demo/managed.json';config=json.loads(path.read_text())
        config['sdk']='not-installed';config['targets'][0]['sdk']='fixture';path.write_text(json.dumps(config))
        seen=[]
        def compile_only(args,**kwargs):
            seen.extend(args);Path(next(a[5:] for a in args if a.startswith('/out:'))).write_bytes(b'MZ')
            return subprocess.CompletedProcess(args,0,b'',b'')
        with patch.object(managed,'compiler',return_value=(exe,[],534296)),patch.object(managed.subprocess,'run',side_effect=compile_only):
            result=managed.build(self.root,sid,'demo','Probe')
        self.assertEqual(result['stage'],'compiled');self.assertEqual(result['sdk']['id'],'fixture')
        self.assertFalse(any('lua54.dll' in arg for arg in seen))
        self.assertTrue(any(arg.endswith('Fixture.dll') for arg in seen))
        value['sdks']['fixture']['files']['lua54.dll']['reference']='false';lock.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'role must be boolean'):sdk.spec(self.root,'fixture')

    def test_target_can_reference_several_pinned_sdks_in_order(self):
        sid,target,exe,item=self.fixture()
        lock=self.root/'tools/setup/managed-sdk-lock.json';value=json.loads(lock.read_text())
        data=b'second reference fixture'
        second={**item,'package':'Second','source':item['source'].replace('fixture','second'),
            'files':{'Second.dll':{'member':'lib/Second.dll','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}}}
        value['sdks']['second']=second;lock.write_text(json.dumps(value))
        folder=sdk.folder(self.root,'second',second);folder.mkdir(parents=True);(folder/'Second.dll').write_bytes(data)
        path=target/'mods/demo/managed.json';config=json.loads(path.read_text())
        config['targets'][0]['sdk']=['fixture','second'];path.write_text(json.dumps(config))
        seen=[]
        def compile_only(args,**kwargs):
            seen.extend(args);Path(next(a[5:] for a in args if a.startswith('/out:'))).write_bytes(b'MZ')
            return subprocess.CompletedProcess(args,0,b'',b'')
        with patch.object(managed,'compiler',return_value=(exe,[],534296)),patch.object(managed.subprocess,'run',side_effect=compile_only):
            result=managed.build(self.root,sid,'demo','Probe')
        self.assertEqual(result['stage'],'compiled');self.assertEqual(result['sdk']['id'],'fixture')
        self.assertEqual([s['id'] for s in result['additional_sdks']],['second'])
        refs=[a for a in seen if a.startswith('/reference:')]
        self.assertTrue(refs[-2].endswith('Fixture.dll') and refs[-1].endswith('Second.dll'))
        for bad in ([],['fixture','fixture'],['fixture','second','a','b'],['Bad']):
            config['targets'][0]['sdk']=bad;path.write_text(json.dumps(config))
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError,'SDK identity'):managed.manifest(target/'mods/demo')

    def test_source_change_during_compile_cannot_report_success(self):
        sid,target,exe,_=self.fixture()
        def changed(args,**kwargs):
            Path(next(a[5:] for a in args if a.startswith('/out:'))).write_bytes(b'MZ')
            (target/'mods/demo/Probe.cs').write_text('changed')
            return subprocess.CompletedProcess(args,0,b'',b'')
        with patch.object(managed,'compiler',return_value=(exe,[],534296)),patch.object(managed.subprocess,'run',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'changed during'):managed.build(self.root,sid,'demo','Probe')

    def test_compiler_failure_or_missing_output_is_not_compiled(self):
        sid,_,exe,_=self.fixture()
        for status in [1,0]:
            with self.subTest(exit_code=status),patch.object(managed,'compiler',return_value=(exe,[],534296)),patch.object(managed.subprocess,'run',return_value=subprocess.CompletedProcess([],status,b'error',b'')):
                result=managed.build(self.root,sid,'demo','Probe')
                self.assertEqual(result['stage'],'compile_failed');self.assertNotIn('artifact',result)

    def test_csharp_source_is_editable_but_compiled_dll_is_not(self):
        sid,target,_,_=self.fixture()
        path=target/'mods/demo/Probe.cs'
        proposed=cw.propose(self.root,{'workspace_id':sid,'changes':[{'relative_path':'mods/demo/Probe.cs','expected_sha256':cw.digest(path.read_bytes()),'content':'public class Edited {}\n'}]})
        cw.apply(self.root,{'workspace_id':sid,'proposal_id':proposed['proposal_id']})
        self.assertIn('Edited',path.read_text())
        with self.assertRaises(ValueError):cw.relative_path('mods/demo/Probe.dll',edit=True)

    @unittest.skipUnless(os.name=='nt' and (sdk.ROOT/'.smelter/tooling/rph-sdk/1.124.0/RagePluginHook.dll').is_file(),'Installed development SDK and Windows compiler required')
    def test_real_sdk_compiles_without_running_the_result(self):
        sid,target,_,_=self.fixture()
        real=json.loads((sdk.ROOT/'tools/setup/managed-sdk-lock.json').read_text(encoding='utf-8'))
        (self.root/'tools/setup/managed-sdk-lock.json').write_text(json.dumps(real),encoding='utf-8')
        item=real['sdks']['rph'];base=sdk.folder(self.root,'rph',item);base.mkdir(parents=True)
        actual=sdk.inspect(sdk.ROOT,'rph')
        for name,path in actual['files'].items():(base/name).write_bytes(Path(path).read_bytes())
        (target/'mods/demo/Probe.cs').write_text('public class Probe { public static Rage.Vector3 Value() { return new Rage.Vector3(1f,2f,3f); } public static void Write(System.IO.Stream s) { new System.Runtime.Serialization.Json.DataContractJsonSerializer(typeof(string)).WriteObject(s,"probe"); } }\n',encoding='utf-8')
        (target/'mods/demo/managed.json').write_text(json.dumps({'schema_version':1,'sdk':'rph','targets':[{'name':'Probe','sources':['Probe.cs']}]}))
        result=managed.build(self.root,sid,'demo','Probe')
        self.assertEqual(result['stage'],'compiled',Path(result['log_path']).read_text(errors='replace'))
        self.assertTrue(Path(result['artifact']['path']).read_bytes().startswith(b'MZ'))
        self.assertFalse(result['artifact_executed'])


if __name__=='__main__':unittest.main()
