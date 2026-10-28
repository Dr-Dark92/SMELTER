import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from contextlib import closing
import os
import sqlite3
from types import SimpleNamespace
from manage_task_watchdog import install,adopt,resume


class WatchdogSetupTests(unittest.TestCase):
    def test_adopt_selects_real_human_prompt_not_synthetic_compaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();folder=root/'.smelter/native-progress';folder.mkdir(parents=True)
            bound={'source_root':str(root),'enabled':True,'configuration_revision':'rev','binding':{'session_id':'ses_bound','directory':str(root),'workspace_id':'workspace'}}
            (folder/'state.json').write_text(json.dumps(bound),encoding='utf-8')
            path=root/'native.db'
            with closing(sqlite3.connect(path)) as db,db:
                db.executescript('CREATE TABLE message(id TEXT,session_id TEXT,time_created INTEGER,data TEXT);CREATE TABLE part(id TEXT,message_id TEXT,session_id TEXT,data TEXT);')
                for mid,stamp,synthetic in [('msg_human',1,False),('msg_compact',2,True)]:
                    value={'role':'user','agent':'build','model':{'providerID':'ollama','modelID':'qwen'},'tools':{'bash':False}}
                    db.execute('INSERT INTO message VALUES(?,?,?,?)',(mid,'ses_bound',stamp,json.dumps(value)))
                    db.execute('INSERT INTO part VALUES(?,?,?,?)',('part_'+mid,mid,'ses_bound',json.dumps({'type':'text','text':'original objective' if not synthetic else 'synthetic summary','synthetic':synthetic})))
            native=SimpleNamespace(path=path,snapshot=lambda *args:{'available':True,'native_phase':'idle','endings':[]})
            with patch('manage_task_watchdog.candidates',return_value=(bound['binding'],12345)),patch('watchdog_native.Native',return_value=native),patch('manage_task_watchdog.subprocess.run',return_value=SimpleNamespace(stdout=str(os.getpid()))):
                self.assertEqual(adopt(root)['status'],'captured')
                from watchdog_store import Store
                store=Store(root);task=store.current();store.update(task['id'],'red','verified_end_flag')
                native.snapshot=lambda *args:{'available':True,'native_phase':'idle','endings':[('explicit end',)]}
                with self.assertRaises(ValueError):resume(root)
                native.snapshot=lambda *args:{'available':True,'native_phase':'idle','endings':[],'cancelled':True}
                with self.assertRaises(ValueError):resume(root)
                native.snapshot=lambda *args:{'available':True,'native_phase':'idle','endings':[]}
                self.assertEqual(resume(root)['status'],'legacy_red_rearmed')
            from watchdog_store import Store
            task=Store(root).current();self.assertEqual(task['origin_id'],'msg_human');self.assertEqual(json.loads(task['request_options'])['tools'],{'bash':False})

    def test_install_backs_up_and_preserves_existing_model_permissions_and_plugins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve();folder=root/'tools/dashboard';folder.mkdir(parents=True)
            (folder/'watchdog_capture_plugin.mjs').write_text('export default async()=>({});',encoding='utf-8')
            path=root/'opencode.json';original={'mcp':{'smelter':{'type':'local'}},'model':'existing-model',
                'permission':{'edit':'ask'},'plugin':['existing-plugin'],'provider':{'ollama':{'options':{'timeout':900000}}}}
            path.write_text(json.dumps(original),encoding='utf-8');before=path.read_bytes()
            result=install(root,path);saved=json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(Path(result['backup']).read_bytes(),before)
            for key in ('model','permission','provider','mcp'):self.assertEqual(saved[key],original[key])
            self.assertEqual(saved['plugin'][0],'existing-plugin');self.assertEqual(len(saved['plugin']),2)
            self.assertFalse(install(root,path)['config_changed'])
            old_url=saved['plugin'][1][0]
            (folder/'watchdog_capture_plugin.mjs').write_text('export default async()=>({event:async()=>{}});',encoding='utf-8')
            self.assertTrue(install(root,path)['config_changed'])
            changed=json.loads(path.read_text(encoding='utf-8'));self.assertNotEqual(changed['plugin'][1][0],old_url);self.assertEqual(len(changed['plugin']),2)
            self.assertEqual(json.loads((root/'.smelter/watchdog/config.json').read_text(encoding='utf-8'))['max_retries'],3)


if __name__=='__main__':unittest.main()
