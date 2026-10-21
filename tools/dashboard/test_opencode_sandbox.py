"""Host relay contract tests; Docker integration remains an opt-in smoke test."""
import base64
import json
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from opencode_sandbox import ManagedClient
from sandbox import _remove


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


if __name__=='__main__':unittest.main()
