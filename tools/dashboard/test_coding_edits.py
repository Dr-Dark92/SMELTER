"""Regression for snippet-as-file corruption, exact edits and durable recovery."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import coding_workspace as coding
from python_tools import ToolSession
from mcp_connections import sdk_status
import test_coding_workspace as base_tests


class ExactEditingTests(unittest.TestCase):
    def setUp(self): base_tests.CodingWorkspaceTests.setUp(self)
    def tearDown(self): base_tests.CodingWorkspaceTests.tearDown(self)
    prepare = base_tests.CodingWorkspaceTests.prepare
    change = base_tests.CodingWorkspaceTests.change

    def large(self):
        relative='mods/demo/controller.lua'
        raw=('\ufefflocal M = {}\r\n' + ''.join('-- retained line %03d with UTF-8 caf\u00e9 and unique context\r\n'%n for n in range(80)) +
             'function M.value() return 1 end\r\nreturn M\r\n').encode('utf-8')
        path=self.root/relative;path.parent.mkdir(parents=True);path.write_bytes(raw)
        sid,target=self.prepare()
        return sid,target,relative,raw

    def edit(self,sid,target,relative,old='return 1',new='return 2'):
        return {'workspace_id':sid,'changes':[{'relative_path':relative,
            'expected_sha256':coding.digest((target/relative).read_bytes()),'edits':[{'old_text':old,'new_text':new}]}]}

    def test_exact_edit_preserves_unrelated_crlf_unicode_bom_and_module_exports(self):
        sid,target,relative,raw=self.large()
        proposal=coding.propose_edits(self.root,self.edit(sid,target,relative))
        self.assertEqual((target/relative).read_bytes(),raw)
        self.assertEqual(proposal['files'][0]['before_lines'],proposal['files'][0]['after_lines'])
        result=coding.apply(self.root,{'workspace_id':sid,'proposal_id':proposal['proposal_id']})
        self.assertEqual((target/relative).read_bytes(),raw.replace(b'return 1',b'return 2'))
        checkpoint=result['checkpoints'][0]
        self.assertEqual(checkpoint['sha256'],coding.digest(raw))
        self.assertEqual(coding.read_checkpoint(self.root,sid,relative,checkpoint['sha256']),raw)

    def test_flat_single_edit_uses_the_same_atomic_proposal_and_checkpoint_engine(self):
        sid,target,relative,raw=self.large();session=ToolSession(self.root,{'coding_workspace':True})
        args={'workspace_id':sid,'relative_path':relative,'expected_sha256':coding.digest(raw),'old_text':'return 1','new_text':'return 2'}
        call=lambda n,a:session.execute({'function':{'name':n,'arguments':a}})
        proposed=call('propose_coding_edit',args)
        self.assertEqual(proposed['status'],'coding_patch_proposed');self.assertEqual((target/relative).read_bytes(),raw)
        self.assertIn('return 2',session.file_activity.snapshot()[0]['draft'])
        applied=call('apply_coding_patch',{'workspace_id':sid,'proposal_id':proposed['proposal_id']})
        self.assertEqual((target/relative).read_bytes(),raw.replace(b'return 1',b'return 2'))
        self.assertEqual(coding.read_checkpoint(self.root,sid,relative,applied['checkpoints'][0]['sha256']),raw)
        # Reusing the stale original SHA is rejected; the convenience tool never
        # guesses new hashes or weakens existing edit admission.
        self.assertEqual(call('propose_coding_edit',args)['status'],'error')

    def test_schema_errors_are_audited_budgeted_compact_and_do_not_execute(self):
        from recovery_guard import PersistentBudget
        sid,target,relative,raw=self.large();session=ToolSession(self.root,{'coding_workspace':True})
        session.validate_tool_arguments=True;session.persistent_budget=PersistentBudget()
        args={'workspace_id':sid,'relative_path':relative,'expected_sha256':coding.digest(raw),
              'changes':'private rejected code '*300}
        with patch.object(session,'_invoke') as invoke:
            first=session.execute({'function':{'name':'propose_coding_edits','arguments':args}})
            self.assertEqual(first['code'],'input_contract_error');self.assertEqual(first['recommended_tool'],'propose_coding_edit')
            self.assertNotIn('private rejected code',json.dumps(first));self.assertLess(len(json.dumps(first)),1800)
            self.assertFalse(session.events[-1]['executed']);self.assertEqual(session.persistent_budget.used,1)
            session.execute({'function':{'name':'propose_coding_edits','arguments':args}})
            third=session.execute({'function':{'name':'propose_coding_edits','arguments':args}})
            self.assertEqual(third['code'],'recovery_required');invoke.assert_not_called()
        events=[json.loads(line) for line in session.audit_path.read_text(encoding='utf-8').splitlines()]
        self.assertTrue(any(e.get('result',{}).get('code')=='input_contract_error' for e in events))
        self.assertEqual((target/relative).read_bytes(),raw)

    def test_missing_ambiguous_empty_and_stale_context_never_record_or_apply(self):
        sid,target,relative,raw=self.large()
        for old,expected in [('absent context','matched 0'),('return','matched 2'),('','nonempty')]:
            with self.subTest(old=old),self.assertRaisesRegex(ValueError,expected):
                coding.propose_edits(self.root,self.edit(sid,target,relative,old=old))
        args=self.edit(sid,target,relative);args['changes'][0]['expected_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'changed'):coding.propose_edits(self.root,args)
        self.assertEqual((target/relative).read_bytes(),raw)
        self.assertEqual(list((coding.base_path(self.root)/sid/'proposals').glob('*.json')),[])

    def test_second_unmatched_edit_leaves_entire_file_unchanged(self):
        sid,target,relative,raw=self.large();args=self.edit(sid,target,relative)
        args['changes'][0]['edits'].append({'old_text':'missing second context','new_text':'replacement'})
        with self.assertRaisesRegex(ValueError,'matched 0'):coding.propose_edits(self.root,args)
        self.assertEqual((target/relative).read_bytes(),raw)

    def test_lf_context_matches_crlf_and_preserves_other_bytes(self):
        text='\ufefffirst\r\nlocal a=1\r\nreturn a\r\nlast\n'
        changed=coding.replace_context(text,'local a=1\nreturn a\n','local a=2\nreturn a\n')
        self.assertEqual(changed,'\ufefffirst\r\nlocal a=2\r\nreturn a\r\nlast\n')
        self.assertEqual(coding.newline_style(changed),'mixed')

    def test_normalized_duplicate_context_rejected_even_with_one_exact_match(self):
        with self.assertRaisesRegex(ValueError,'matched 2'):
            coding.replace_context('a\r\nb\r\na\nb\n','a\nb\n','new\n')

    def test_bare_cr_and_non_newline_whitespace_are_not_normalized(self):
        for text,old in [('a\rb','a\nb'),('a  b','a b')]:
            with self.subTest(text=text),self.assertRaisesRegex(ValueError,'matched 0'):
                coding.replace_context(text,old,'new')

    def test_large_snippet_replacement_rejected_without_explicit_intent(self):
        sid,target,relative,raw=self.large();args=self.change(sid,target,relative,'local v = true\n')
        with self.assertRaisesRegex(ValueError,'snippet-as-file'):coding.propose(self.root,args)
        self.assertEqual((target/relative).read_bytes(),raw)
        args['allow_large_replacement']=True
        proposal=coding.propose(self.root,args)
        self.assertTrue(proposal['files'][0]['large_replacement'])
        result=coding.apply(self.root,{'workspace_id':sid,'proposal_id':proposal['proposal_id']})
        self.assertEqual(coding.read_checkpoint(self.root,sid,relative,result['checkpoints'][0]['sha256']),raw)

    def test_workspace_only_file_restores_checkpoint_without_checkout_baseline(self):
        sid,target=self.prepare();relative='mods/demo/workspace_only.lua'
        original='local M = {}\nfunction M.value() return 1 end\nreturn M\n'
        new=coding.propose(self.root,self.change(sid,target,relative,original))
        coding.apply(self.root,{'workspace_id':sid,'proposal_id':new['proposal_id']})
        proposed=coding.propose_edits(self.root,self.edit(sid,target,relative))
        applied=coding.apply(self.root,{'workspace_id':sid,'proposal_id':proposed['proposal_id']})
        sha=applied['checkpoints'][0]['sha256']
        self.assertFalse((self.root/relative).exists())
        with self.assertRaisesRegex(ValueError,'checkpoint_sha256'):
            coding.propose_restore(self.root,{'workspace_id':sid,'relative_paths':[relative]})
        restore=coding.propose_restore(self.root,{'workspace_id':sid,'relative_paths':[relative],'checkpoint_sha256':sha})
        coding.apply(self.root,{'workspace_id':sid,'proposal_id':restore['proposal_id']})
        self.assertEqual((target/relative).read_bytes(),original.encode())
        self.assertIn(sha,[c['sha256'] for c in coding.context(self.root,{'workspace_id':sid})['checkpoints']])

    def test_checkpoint_path_workspace_and_tampering_are_verified(self):
        sid,target,relative,raw=self.large()
        proposed=coding.propose_edits(self.root,self.edit(sid,target,relative))
        coding.apply(self.root,{'workspace_id':sid,'proposal_id':proposed['proposal_id']})
        sha=coding.digest(raw);second,_=self.prepare()
        for workspace,path in [(second,relative),(sid,'mods/demo/other.lua')]:
            with self.subTest(workspace=workspace,path=path),self.assertRaises(ValueError):
                coding.read_checkpoint(self.root,workspace,path,sha)
        checkpoint=coding._checkpoint_path(self.root,sid,relative,sha)
        value=json.loads(checkpoint.read_text(encoding='utf-8'));value['content']='tampered'
        checkpoint.write_text(json.dumps(value),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'bytes changed'):
            coding.propose_restore(self.root,{'workspace_id':sid,'relative_paths':[relative],'checkpoint_sha256':sha})

    def test_checkpoint_changed_after_restore_proposal_blocks_apply(self):
        sid,target,relative,raw=self.large()
        proposed=coding.propose_edits(self.root,self.edit(sid,target,relative))
        coding.apply(self.root,{'workspace_id':sid,'proposal_id':proposed['proposal_id']})
        sha=coding.digest(raw)
        restore=coding.propose_restore(self.root,{'workspace_id':sid,'relative_paths':[relative],'checkpoint_sha256':sha})
        checkpoint=coding._checkpoint_path(self.root,sid,relative,sha)
        value=json.loads(checkpoint.read_text(encoding='utf-8'));value['content']='tampered'
        checkpoint.write_text(json.dumps(value),encoding='utf-8')
        before=(target/relative).read_bytes()
        with self.assertRaises(ValueError):coding.apply(self.root,{'workspace_id':sid,'proposal_id':restore['proposal_id']})
        self.assertEqual((target/relative).read_bytes(),before)

    @unittest.skipUnless(sdk_status()['status']=='installed','Pinned MCP SDK required')
    def test_real_mcp_exact_edit_and_checkpoint_restore_update_full_file_cards(self):
        session=ToolSession(self.root,{'coding_workspace':True,'transport':'mcp'})
        call=lambda name,args:session.execute({'function':{'name':name,'arguments':args}})
        ready=call('prepare_coding_workspace',{});sid=ready['workspace_id'];target=Path(ready['path'])
        relative='tools/dashboard/example.py'
        proposed=call('propose_coding_edits',self.edit(sid,target,relative,old='return a - b',new='return a + b'))
        self.assertEqual(proposed['status'],'coding_patch_proposed')
        self.assertIn('def add',session.file_activity.snapshot()[0]['draft'])
        applied=call('apply_coding_patch',{'workspace_id':sid,'proposal_id':proposed['proposal_id']})
        self.assertEqual(applied['status'],'coding_patch_applied')
        restored=call('propose_coding_restore',{'workspace_id':sid,'relative_paths':[relative],'checkpoint_sha256':applied['checkpoints'][0]['sha256']})
        self.assertEqual(restored['status'],'coding_patch_proposed')
        result=call('apply_coding_patch',{'workspace_id':sid,'proposal_id':restored['proposal_id']})
        self.assertEqual(result['status'],'coding_patch_applied')
        self.assertEqual((target/relative).read_bytes(),self.original[relative])


if __name__=='__main__':unittest.main()
