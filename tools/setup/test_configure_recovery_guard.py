import json
from pathlib import Path
import tempfile
import unittest

from configure_recovery_guard import configure


class RecoverySetupTests(unittest.TestCase):
    def test_native_timeouts_bound_stalls_and_preserve_explicit_user_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'tools/dashboard';folder.mkdir(parents=True)
            (folder/'native_recovery_plugin.mjs').write_text('export default async()=>({});',encoding='utf-8')
            config=root/'opencode.json';config.write_text(json.dumps({'mcp':{'smelter':{'type':'local'}},
                'provider':{'ollama':{'options':{'timeout':600000},'models':{'qwen':{'limit':{'context':131072}}}}}}),encoding='utf-8')
            result=configure(root,config,True)
            self.assertEqual(result['ollama_request_timeouts_ms'],{'timeout':600000,'headerTimeout':300000,'chunkTimeout':180000})
            self.assertEqual(json.loads(config.read_text(encoding='utf-8'))['provider']['ollama']['models']['qwen']['limit']['context'],131072)

    def test_preview_apply_backup_and_repeat_preserve_existing_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'project';folder=root/'tools/dashboard';folder.mkdir(parents=True)
            (folder/'native_recovery_plugin.mjs').write_text('export default async()=>({});',encoding='utf-8')
            path=Path(tmp)/'opencode.json'
            original={'mcp':{'smelter':{'type':'local','environment':{'example':'preserved'}}},
                      'plugin':['other-plugin'],'permission':{'edit':'ask'},'model':'existing'}
            path.write_text(json.dumps(original),encoding='utf-8');before=path.read_bytes()
            preview=configure(root,path)
            self.assertTrue(preview['changed']);self.assertEqual(path.read_bytes(),before)
            applied=configure(root,path,True);saved=json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(Path(applied['backup']).read_bytes(),before)
            for key in ('mcp','permission','model'):self.assertEqual(saved[key],original[key])
            self.assertEqual(saved['plugin'][0],'other-plugin');self.assertEqual(len(saved['plugin']),2)
            self.assertFalse(configure(root,path,True)['changed'])
            saved['plugin'][1][1]['root']='different';path.write_text(json.dumps(saved),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'options differ'):configure(root,path,True)


if __name__=='__main__':unittest.main()
