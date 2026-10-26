from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
import threading
import unittest
from unittest.mock import patch

import dashboard
import native_progress as progress
import test_native_progress


class NativeProgressApiTests(unittest.TestCase):
    def setUp(self):
        test_native_progress.NativeProgressTests.setUp(self)
        patcher = patch.object(dashboard, 'ROOT', self.root); patcher.start(); self.addCleanup(patcher.stop)
        patcher = patch('native_progress.manager', return_value=self.bridge); patcher.start(); self.addCleanup(patcher.stop)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), dashboard.handler('native-test'))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close); self.addCleanup(self.server.shutdown)

    def request(self, body=None, *, token=True, origin=None, query=''):
        connection = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        headers = {'Content-Type': 'application/json'}
        if token: headers['X-Smelter-Token'] = 'native-test'
        if origin: headers['Origin'] = origin
        connection.request('POST' if body is not None else 'GET', '/api/native-progress'+query,
                           json.dumps(body) if body is not None else None, headers)
        response=connection.getresponse(); result=response.status,json.load(response);connection.close();return result

    def test_authenticated_status_and_configuration_revision_control_pause(self):
        code, value = self.request(); self.assertEqual(code,200); self.assertTrue(value['read_only'])
        body = {'action': 'stop', 'expected_revision': value['configuration_revision']}
        self.assertEqual(self.request(token=False)[0],403)
        self.assertEqual(self.request(body,token=False)[0],403)
        self.assertEqual(self.request(body,origin='https://untrusted.example')[0],403)
        code, result = self.request(body); self.assertEqual(code,200); self.assertFalse(result['enabled'])
        self.assertEqual(self.request(body)[0],400)

    def test_no_prompt_abort_custom_url_or_extra_binding_fields_are_accepted(self):
        for body in ({'action':'prompt','text':'run'}, {'action':'abort'},
                     {'action':'start','expected_revision':self.bridge.view()['configuration_revision'],'url':'http://external.example'},
                     {'action':'bind','session_id':'ses_fixture','directory':str(self.native),'workspace_id':self.sid,
                      'expected_revision':self.bridge.view()['configuration_revision'],'permission':'allow'}):
            self.assertEqual(self.request(body)[0],400)
        self.assertEqual(self.request(query='?session_id=ses_other')[0],400)

    def test_discovery_returns_directory_filtered_ids_without_raw_title_or_content(self):
        code,value=self.request({'action':'sessions','directory':str(self.native)})
        self.assertEqual(code,200); self.assertEqual(value['sessions'][0]['session_id'],test_native_progress.SID)
        self.assertEqual(set(value['sessions'][0]),{'session_id','directory','updated'})


if __name__=='__main__':unittest.main()
