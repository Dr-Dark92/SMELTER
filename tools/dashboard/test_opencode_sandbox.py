"""Host relay contract tests; Docker integration remains an opt-in smoke test."""
import base64
import json
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from opencode_sandbox import ManagedClient
from sandbox import _remove


class ServerLifetimeTests(unittest.TestCase):
    """The OpenCode server must outlive the task, not one model turn (2026-10-24 failure)."""

    def start(self, runtime):
        import tempfile
        from pathlib import Path
        folder = Path(tempfile.mkdtemp());(folder/'code').mkdir()
        captured = {}
        class Stop(Exception):pass
        def run(command, env=None, **kwargs):
            captured.update(command=command, env=env);raise Stop()
        ready = {'ready': True, 'docker': 'docker', 'configured': {'opencode_image': 'sha256:' + 'a' * 64}}
        configuration = {'model': 'fixture:4b', 'runtime': runtime}
        with patch('opencode_sandbox.status', return_value=ready), \
             patch('access_policy.using', return_value=__import__('contextlib').nullcontext()), \
             patch('opencode_sandbox.snapshot', return_value=(folder, folder/'code')), \
             patch('opencode_sandbox.record_owner'), patch('opencode_sandbox.run', side_effect=run), \
             patch.object(ManagedClient, 'close'):
            with self.assertRaises(Stop):ManagedClient(folder, None, configuration)
        return captured

    def test_server_lifetime_follows_task_timeout_not_turn_timeout(self):
        captured = self.start({'context_tokens': 32768, 'max_output_tokens': 1024, 'timeout_seconds': 180,
                               'opencode_timeout_seconds': 900, 'thinking': False})
        self.assertEqual(captured['env']['SMELTER_TIMEOUT'], '180')
        self.assertEqual(captured['env']['SMELTER_TASK_TIMEOUT'], '900')
        self.assertIn('SMELTER_TASK_TIMEOUT', captured['command'])
        boot = captured['command'][-1]
        self.assertIn('Number(process.env.SMELTER_TASK_TIMEOUT)+30', boot)
        self.assertNotIn('Number(process.env.SMELTER_TIMEOUT)+30', boot)

    def test_older_runtime_without_task_timeout_keeps_turn_timeout(self):
        captured = self.start({'context_tokens': 32768, 'max_output_tokens': 1024, 'timeout_seconds': 300, 'thinking': False})
        self.assertEqual(captured['env']['SMELTER_TASK_TIMEOUT'], '300')


class PersistentSessionTests(unittest.TestCase):
    def test_refresh_replaces_mounted_code_in_place(self):
        import tempfile
        from pathlib import Path
        base = Path(tempfile.mkdtemp())
        code = base / 'mounted' / 'code';(code / '.smelter').mkdir(parents=True)
        (code / 'skills').mkdir();(code / 'skills' / 'old.md').write_text('old')
        fresh = base / 'fresh';(fresh / 'code' / 'skills').mkdir(parents=True);(fresh / 'code' / '.smelter').mkdir()
        (fresh / 'code' / 'skills' / 'new.md').write_text('new');(fresh / 'code' / 'README.md').write_text('readme')
        client = object.__new__(ManagedClient);client.root = base;client.host_directory = base;client.code = code
        with patch('opencode_sandbox.snapshot', return_value=(fresh, fresh / 'code')), \
             patch('access_policy.using', return_value=__import__('contextlib').nullcontext()):
            client.refresh(None)
        self.assertEqual(sorted(p.relative_to(code).as_posix() for p in code.rglob('*')),
                         ['.smelter', 'README.md', 'skills', 'skills/new.md'])
        self.assertFalse(fresh.exists())

    def test_attach_and_detach_reset_task_budgets(self):
        import threading
        client = object.__new__(ManagedClient);client.lock = threading.Lock();client.model_calls = 20;client.relay_calls = 100
        client.attach('control', 'bridge')
        self.assertEqual((client.control, client.bridge, client.model_calls, client.relay_calls), ('control', 'bridge', 0, 0))
        client.detach()
        self.assertEqual((client.control, client.bridge), (None, None))


class ModelRelayTests(unittest.TestCase):
    def client(self,approved=True):
        client=object.__new__(ManagedClient)
        client.model='fixture:9b';client.settings={'context_tokens':32768,'max_output_tokens':128,'timeout_seconds':30,'thinking':False}
        client.allow_inference=approved;client.model_calls=0;client.relay_calls=0
        client.control=SimpleNamespace(tool_call_limit=0,context_budget=None)
        self.requests=[]
        def infer(body,timeout,maximum):
            self.requests.append((body,timeout,maximum))
            return json.dumps({'message':{'content':'Fixture answer'}}).encode()
        client.control.infer=infer
        return client

    def packet(self,**overrides):
        body={'model':'fixture:9b','messages':[{'role':'user','content':'Inspect README'}],'max_tokens':999,'stream':False,**overrides}
        return {'method':'POST','path':'/v1/chat/completions','body':base64.b64encode(json.dumps(body).encode()).decode()}

    def test_inspection_session_cannot_prompt_model(self):
        client=self.client(False)
        with self.assertRaisesRegex(ValueError,'not approved'):client._response(self.packet())
        self.assertEqual(self.requests,[])

    def test_model_and_route_allowlist_precedes_outgoing_inference(self):
        client=self.client()
        with self.assertRaisesRegex(ValueError,'admitted'):client._response(self.packet(model='remote/model'))
        with self.assertRaisesRegex(ValueError,'Denied'):client._response({'method':'POST','path':'/api/delete'})
        self.assertEqual(self.requests,[])

    def test_native_request_enforces_saved_context_and_output_limits(self):
        client=self.client();response=client._response(self.packet())
        request,timeout,maximum=self.requests[0]
        self.assertEqual(request['options'],{'num_ctx':32768,'num_predict':128})
        self.assertEqual(timeout,30)
        value=json.loads(base64.b64decode(response['body']))
        self.assertEqual(value['choices'][0]['message']['content'],'Fixture answer')
        self.assertNotIn('usage',value)

    def test_tool_history_and_sse_preserve_protocol(self):
        client=self.client()
        messages=[{'role':'assistant','content':None,'tool_calls':[{'id':'call_a','function':{'name':'read','arguments':'{"path":"README.md"}'}}]},
                  {'role':'tool','tool_call_id':'call_a','content':'Fixture README'}]
        client.control.infer=lambda *args:json.dumps({'message':{'content':'','tool_calls':[{'function':{'name':'read','arguments':{'path':'tools'}}}]}}).encode()
        response=client._response(self.packet(messages=messages,stream=True))
        text=base64.b64decode(response['body']).decode()
        chunks=[json.loads(line[6:]) for line in text.splitlines() if line.startswith('data: {')]
        call=chunks[0]['choices'][0]['delta']['tool_calls'][0]
        self.assertEqual(call['index'],0);self.assertTrue(call['id'].startswith('call_'))
        self.assertEqual(json.loads(call['function']['arguments']),{'path':'tools'})
        self.assertEqual(chunks[-1]['choices'][0]['finish_reason'],'tool_calls');self.assertTrue(text.endswith('data: [DONE]\n\n'))
        client.control.infer=lambda body,*args:self._capture(body)
        client._response(self.packet(messages=messages))
        self.assertEqual(self.last['messages'][-1]['tool_name'],'read')

    def _capture(self,body):
        self.last=body;return b'{"message":{"content":"ok"}}'

    def test_malformed_history_and_model_outputs_fail_closed(self):
        client=self.client()
        with self.assertRaisesRegex(ValueError,'messages'):client._response(self.packet(messages={}))
        with self.assertRaisesRegex(ValueError,'identity'):
            client._response(self.packet(messages=[{'role':'assistant','tool_calls':[{'id':[],'function':{'name':'read'}}]}]))
        client.control.infer=lambda *args:b'[]'
        with self.assertRaisesRegex(ValueError,'response'):client._response(self.packet())
        client.control.infer=lambda *args:b'{"message":{"tool_calls":"bad"}}'
        with self.assertRaisesRegex(ValueError,'tool calls'):client._response(self.packet())

    def test_exhausted_generation_is_reported_as_length(self):
        client=self.client();client.control.infer=lambda *args:b'{"message":{"content":"partial"},"done_reason":"length"}'
        value=json.loads(base64.b64decode(client._response(self.packet())['body']))
        self.assertEqual(value['choices'][0]['finish_reason'],'length')

    def test_owned_container_removal_requires_matching_label(self):
        name='smelter-opencode-'+'a'*32
        with patch('sandbox.run',return_value=SimpleNamespace(returncode=0,stdout='{"smelter.owner":"different"}',stderr='')) as runner:
            self.assertFalse(_remove('docker',name));self.assertEqual(runner.call_count,1)
        with patch('sandbox.run') as runner:
            self.assertFalse(_remove('docker','somebody-elses-container'));runner.assert_not_called()
        with patch('sandbox.run',side_effect=[SimpleNamespace(returncode=0,stdout=json.dumps({'smelter.owner':name})),SimpleNamespace(returncode=0)]) as runner:
            self.assertTrue(_remove('docker',name));self.assertEqual(runner.call_args.args[0],['docker','rm','--force',name])

    def test_auto_removed_container_is_confirmed_without_parsing_error_wording(self):
        name='smelter-tests-'+'a'*32
        for error in ('error: no such object: '+name, 'Error: No such object: '+name, 'localized absence message'):
            with self.subTest(error=error), patch('sandbox.run',side_effect=[
                    SimpleNamespace(returncode=1,stdout='',stderr=error),
                    SimpleNamespace(returncode=0,stdout='',stderr='')]) as runner:
                self.assertTrue(_remove('docker',name))
                self.assertEqual(runner.call_args.args[0],['docker','ps','--all','--filter',
                                 'name=^/'+name+'$','--format','{{.ID}}'])
                self.assertFalse(any(call.args[0][1]=='rm' for call in runner.call_args_list))

    def test_failed_daemon_request_cannot_be_interpreted_as_absence(self):
        name='smelter-tests-'+'a'*32
        with patch('sandbox.run',side_effect=[
                SimpleNamespace(returncode=1,stdout='',stderr='No such host'),
                SimpleNamespace(returncode=1,stdout='',stderr='Docker is unavailable')]) as runner:
            self.assertFalse(_remove('docker',name))
            self.assertEqual(runner.call_count,2)

    def test_nonempty_or_failed_absence_probe_keeps_cleanup_unconfirmed(self):
        name='smelter-tests-'+'a'*32
        for probe in (SimpleNamespace(returncode=0,stdout='b'*64,stderr=''),
                      SimpleNamespace(returncode=1,stdout='',stderr='permission denied')):
            with self.subTest(probe=probe), patch('sandbox.run',side_effect=[
                    SimpleNamespace(returncode=1,stdout='',stderr='error: no such object: '+name),probe]):
                self.assertFalse(_remove('docker',name))

    def test_auto_removal_race_requires_a_successful_absence_probe(self):
        name='smelter-tests-'+'a'*32
        for remains in (False,True):
            with self.subTest(remains=remains), patch('sandbox.run',side_effect=[
                    SimpleNamespace(returncode=0,stdout=json.dumps({'smelter.owner':name})),
                    SimpleNamespace(returncode=1,stderr='removal already in progress'),
                    SimpleNamespace(returncode=0,stdout='b'*64 if remains else '')]) as runner:
                self.assertEqual(_remove('docker',name),not remains)
                self.assertEqual(runner.call_args_list[1].args[0],['docker','rm','--force',name])


if __name__=='__main__':unittest.main()
