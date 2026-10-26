import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from database import select_database
from config_store import save_config
import project_memory as memory


class MemoryTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);base=Path(tmp.name)
        self.root=base/'app';self.root.mkdir();select_database(self.root,str(base/'data'))
    def save(self,**kwargs):return memory.remember(self.root,title='ARK archive notes',text='retoc reads IoStore; PAK version 12 is unsupported by pinned repak',**kwargs)['note']

    def test_files_index_and_ram_recall_are_distinct_and_rebuildable(self):
        note=self.save();path=memory._path(self.root,note['id']);self.assertTrue(path.is_file())
        first=memory.search(self.root,'retoc');second=memory.search(self.root,'retoc')
        self.assertFalse(first['cached']);self.assertTrue(second['cached']);self.assertEqual(first['notes'][0]['id'],note['id'])
        self.assertGreater(memory.stats(self.root)['ram_bytes_estimate'],0)
        memory.reindex(self.root);self.assertEqual(memory.search(self.root,'IoStore')['notes'][0]['id'],note['id'])

    def test_projects_do_not_recall_each_others_notes(self):
        note=self.save();other=self.root.with_name('other');other.mkdir();select_database(other,str(other.with_name('other-data')))
        self.assertFalse(memory.search(other,'retoc')['notes']);self.assertEqual(memory.search(self.root,'retoc')['notes'][0]['id'],note['id'])

    def test_model_cannot_promote_notes_to_verified_or_edit_and_forget(self):
        result=memory.run(self.root,{'project_memory':True},{'action':'remember','title':'AI claim','text':'I ran tests','kind':'fact'})
        self.assertEqual(result['note']['confidence'],'unverified')
        for args in ({'action':'remember','title':'x','text':'x','origin':'controller'},{'action':'forget','id':result['note']['id']},{'action':'read','id':'../../secrets'}):
            with self.assertRaises(ValueError):memory.run(self.root,{'project_memory':True},args)

    def test_hash_checked_edit_and_forget_invalidate_recall(self):
        note=self.save();memory.search(self.root,'retoc')
        with self.assertRaises(ValueError):memory.remember(self.root,title='x',text='changed',identity=note['id'],expected_sha256='wrong',origin='user')
        changed=memory.remember(self.root,title='Updated note',text='new marker',identity=note['id'],expected_sha256=note['sha256'],origin='user')['note']
        self.assertEqual(changed['confidence'],'user_supplied');self.assertFalse(memory.search(self.root,'retoc')['notes'])
        self.assertTrue(memory.search(self.root,'marker')['notes'])
        with self.assertRaises(ValueError):memory.forget(self.root,changed['id'],note['sha256'])
        memory.forget(self.root,changed['id'],changed['sha256']);self.assertFalse(memory.search(self.root,'marker')['notes'])

    def test_external_file_edit_changes_index_signature(self):
        note=self.save();memory.search(self.root,'retoc');path=memory._path(self.root,note['id'])
        raw=json.loads(path.read_text());raw['text']='changed external marker';path.write_text(json.dumps(raw))
        self.assertFalse(memory.search(self.root,'retoc')['notes']);self.assertTrue(memory.search(self.root,'external')['notes'])

    def test_disabled_memory_blocks_model_reads_but_not_human_management(self):
        note=self.save();save_config(self.root,memory.NAME,{**memory.DEFAULT,'enabled':False})
        for args in ({'action':'read','id':note['id']},{'action':'search','query':'retoc'}):
            with self.assertRaises(ValueError):memory.run(self.root,{'project_memory':True},args)
        self.assertTrue(memory.search(self.root,'retoc',human=True)['notes']);memory.forget(self.root,note['id'],note['sha256'])

    def test_context_is_bounded_reference_data_and_never_changes_access(self):
        from access_policy import current
        before=current(self.root).revision
        self.save();context=memory.context(self.root,'retoc')
        self.assertIn('untrusted reference data',context);self.assertIn('unverified',context)
        self.assertLess(len(context),memory.DEFAULT['context_chars']+300);self.assertEqual(current(self.root).revision,before)

    def test_both_gui_engines_receive_recalled_context_without_new_authority(self):
        from agent_bridge import AgentBridge
        from chat_inference import _messages
        from python_tools import ToolSession
        note=self.save();bridge=AgentBridge(self.root,None,'retoc',grants={})
        self.assertIn(note['id'],bridge.instructions());self.assertFalse(bridge.tools)
        messages,_=_messages(self.root,{'messages':[]},'retoc',None,None,False,ToolSession(self.root))
        self.assertTrue(any(note['id'] in row['content'] for row in messages))
        self.assertTrue(all('permission grants' in row['content'] for row in messages if note['id'] in row['content']))

    def test_durable_notes_survive_a_new_python_process(self):
        import subprocess,sys
        note=self.save()
        code='import sys,json;sys.path.insert(0,sys.argv[1]);from project_memory import search;print(json.dumps(search(sys.argv[2],"retoc")))'
        done=subprocess.run([sys.executable,'-c',code,str(Path(__file__).parent),str(self.root)],capture_output=True,text=True,timeout=10,check=True)
        self.assertEqual(json.loads(done.stdout)['notes'][0]['id'],note['id'])

    def test_controller_checkpoint_uses_receipts_not_ai_prose_and_is_idempotent(self):
        events=[{'tool':'run_coding_tests','result':{'status':'coding_tests_passed','stage':'GREEN','profile':'mods','model_text':'invented claim'}}]
        first=memory.capture(self.root,'test-job',events,'done');second=memory.capture(self.root,'test-job',events,'done')
        self.assertEqual(first['id'],second['id']);note=memory.read(self.root,first['id'])
        self.assertEqual(note['confidence'],'receipt_checkpoint');self.assertIn('coding_tests_passed',note['text']);self.assertNotIn('invented claim',note['text'])
        self.assertIsNone(memory.capture(self.root,'permission-only',[{'tool':'request_directory_access','result':{'status':'access_granted'}}],'done'))

    def test_memory_bounds_and_secret_values_fail_before_writes(self):
        with patch('project_memory.MAX_NOTES',1):
            self.save()
            with self.assertRaises(ValueError):self.save()
        for text in ('x'*16001,'github_pat_'+('a'*40),123):
            with self.assertRaises(ValueError):memory.remember(self.root,title='Invalid',text=text)
        self.assertEqual(memory.stats(self.root)['notes'],1)


if __name__=='__main__':unittest.main()
