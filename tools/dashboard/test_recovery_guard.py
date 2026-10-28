"""Real coding copies/audits plus deterministic injected transient failures."""
import errno
import json
import unittest
from unittest.mock import patch, Mock

import coding_workspace as cw
from coding_recovery import diagnose, recover
from python_tools import ToolSession
from recovery_guard import PersistentBudget, RecoveryGuard
import test_coding_workspace as base_tests


class RecoveryTests(unittest.TestCase):
    def setUp(self):base_tests.CodingWorkspaceTests.setUp(self)
    def tearDown(self):base_tests.CodingWorkspaceTests.tearDown(self)
    prepare=base_tests.CodingWorkspaceTests.prepare

    def session(self):
        session=ToolSession(self.root,{'coding_workspace':True})
        return session,lambda n,a:session.execute({'function':{'name':n,'arguments':a}})

    def test_lua_cause_is_first_frame_not_callers_and_log_has_no_mutations(self):
        output='lua5.4: Scripts/policy.lua:72: table expected, got nil\nstack traceback:\n\t[C]: in function next\n\tScripts/policy.lua:72: in validate_policy\n\ttests/test_policy.lua:150: in main chunk\n'
        detail=diagnose(output)
        self.assertEqual((detail['path'],detail['line'],detail['classification']),('Scripts/policy.lua',72,'runtime_error'))
        self.assertEqual(diagnose('lua5.4: tests/test.lua:9: assertion failed!')['classification'],'assertion_failure')
        sid,target=self.prepare();folder=cw.base_path(self.root)/sid/'test-runs';folder.mkdir()
        log=folder/'failure.log';log.write_bytes(output.encode());receipt=log.with_suffix('.json')
        receipt.write_text(json.dumps({'log_sha256':cw.digest(log.read_bytes())}),encoding='utf-8')
        metadata,_=cw.load(self.root,sid);metadata['tests']['lua']={'path':str(receipt),'tree_sha256':'0'*64,'stage':'RED'}
        cw._save(cw.base_path(self.root)/sid/'workspace.json',metadata)
        before=(target/'tools/dashboard/example.py').read_bytes()
        context=recover(self.root,{'workspace_id':sid,'relative_paths':['tools/dashboard/example.py']})
        self.assertFalse(context['mutations_performed']);self.assertFalse(context['tests'][0]['current'])
        self.assertEqual(context['tests'][0]['diagnostic']['line'],72)
        self.assertEqual((target/'tools/dashboard/example.py').read_bytes(),before)
        log.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'no longer matches'):recover(self.root,{'workspace_id':sid})

    def test_recovery_cannot_read_external_receipt_or_path(self):
        sid,_=self.prepare();metadata,_=cw.load(self.root,sid)
        metadata['tests']['lua']={'path':str(self.root/'private.json')}
        cw._save(cw.base_path(self.root)/sid/'workspace.json',metadata)
        with self.assertRaisesRegex(ValueError,'owned test directory'):recover(self.root,{'workspace_id':sid})
        with self.assertRaises(ValueError):recover(self.root,{'workspace_id':sid,'relative_paths':['../private.txt']})

    def test_stack_path_resolves_from_failing_test_cwd_with_current_source_hash(self):
        sid,target=self.prepare();source=target/'mods/demo/Scripts/policy.lua';source.parent.mkdir(parents=True)
        source.write_bytes(b'local value=nil\nfor k,v in pairs(value) do end\n')
        folder=cw.base_path(self.root)/sid/'test-runs';folder.mkdir();log=folder/'runtime.log'
        log.write_bytes(b'lua5.4: Scripts/policy.lua:2: table expected, got nil\n')
        receipt=log.with_suffix('.json');receipt.write_text(json.dumps({'log_sha256':cw.digest(log.read_bytes()),
            'test_programs':[{'working_directory':'mods/demo','exit_code':1}]}),encoding='utf-8')
        metadata,_=cw.load(self.root,sid);metadata['tests']['lua']={'path':str(receipt)}
        cw._save(cw.base_path(self.root)/sid/'workspace.json',metadata)
        detail=recover(self.root,{'workspace_id':sid})['tests'][0]['diagnostic']
        self.assertEqual(detail['relative_path'],'mods/demo/Scripts/policy.lua')
        self.assertEqual(detail['current_sha256'],cw.digest(source.read_bytes()))
        self.assertIn('2: for k,v',detail['source_excerpt'])

    def test_repeated_failed_edits_redirect_without_any_write_or_third_execution(self):
        sid,target=self.prepare();session,call=self.session();relative='tools/dashboard/example.py';before=(target/relative).read_bytes()
        args={'workspace_id':sid,'changes':[{'relative_path':relative,'expected_sha256':cw.digest(before),
                'edits':[{'old_text':'missing context','new_text':'changed'}]}]}
        for _ in range(2):self.assertEqual(call('propose_coding_edits',args)['status'],'error')
        blocked=call('propose_coding_edits',args)
        self.assertEqual(blocked['code'],'recovery_required');self.assertFalse(session.events[-1]['executed'])
        self.assertEqual(blocked['recovery']['workspace_id'],sid)
        self.assertEqual((target/relative).read_bytes(),before)
        # Another hypothesis and the recovery operation still work in this task.
        self.assertEqual(call('coding_recovery_context',{'workspace_id':sid})['status'],'coding_recovery_context')
        self.assertEqual(call('read_coding_file',{'workspace_id':sid,'relative_path':relative})['status'],'coding_file_read')

    def test_unchanged_reads_are_bounded_but_distinct_pagination_is_allowed(self):
        sid,_=self.prepare();_,call=self.session();args={'workspace_id':sid,'relative_path':'tools/dashboard/example.py'}
        for _ in range(4):self.assertEqual(call('read_coding_file',args)['status'],'coding_file_read')
        self.assertEqual(call('read_coding_file',args)['code'],'recovery_required')
        self.assertEqual(call('read_coding_file',{**args,'start_line':1,'line_count':1})['status'],'coding_file_read')

    def test_only_transient_reads_get_one_automatic_retry_and_audited_attempt(self):
        sid,_=self.prepare();session,call=self.session();actual=session._invoke
        with patch.object(session,'_invoke',side_effect=[OSError(errno.EBUSY,'busy'),{'status':'coding_file_read','sha256':'fixture'}]) as invoke:
            result=call('read_coding_file',{'workspace_id':sid,'relative_path':'tools/dashboard/example.py'})
        self.assertEqual(result['status'],'coding_file_read');self.assertEqual(invoke.call_count,2)
        self.assertEqual(session.events[-1]['recovery_attempts'],1)
        for name,error in [('read_coding_file',PermissionError(errno.EACCES,'denied')),
                           ('apply_coding_patch',OSError(errno.EBUSY,'busy')),
                           ('run_coding_tests',OSError(errno.ETIMEDOUT,'timeout'))]:
            with self.subTest(name=name),patch.object(session,'_invoke',side_effect=error) as invoke:
                self.assertEqual(call(name,{'workspace_id':sid})['status'],'error')
                self.assertEqual(invoke.call_count,1)
        from chat_jobs import ChatCancelled
        session.control=Mock();session.control.check.side_effect=ChatCancelled('Request stopped')
        with patch.object(session,'_invoke',side_effect=OSError(errno.EBUSY,'busy')) as invoke:
            result=call('read_coding_file',{'workspace_id':sid,'relative_path':'tools/dashboard/example.py','offset':0})
        self.assertEqual(invoke.call_count,1);self.assertEqual(result['error'],'Request stopped')

    def test_stdio_budget_renews_without_grant_reset_and_gui_budget_is_unchanged(self):
        clock=[0];budget=PersistentBudget(lambda:clock[0],limit=2,seconds=60)
        self.assertIsNone(budget.consume());self.assertIsNone(budget.consume())
        blocked=budget.consume();self.assertEqual(blocked['code'],'call_budget_window')
        clock[0]=60;self.assertIsNone(budget.consume())
        session,call=self.session();session.persistent_budget=PersistentBudget()
        for _ in range(40):
            self.assertEqual(call('coding_workspace_context',{})['status'],'coding_workspace_registry')
        self.assertEqual(session.persistent_budget.used,40)
        self.assertTrue(session.grants['coding_workspace'])
        session.persistent_budget=None
        with self.assertRaisesRegex(ValueError,'call limit'):call('coding_workspace_context',{})

    def test_guard_storage_bounded_and_new_applied_bytes_reset_read_loops(self):
        guard=RecoveryGuard()
        for n in range(150):guard.after('read_coding_file',{'n':n},{'status':'coding_file_read','sha256':'hash'})
        self.assertEqual(len(guard.reads),128)
        guard.after('apply_coding_patch',{}, {'status':'coding_patch_applied'})
        self.assertEqual(guard.reads,{})


if __name__=='__main__':unittest.main()
