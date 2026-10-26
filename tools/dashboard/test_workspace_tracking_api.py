from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
import threading
import unittest
from unittest.mock import patch

import dashboard
import coding_workspace as coding
import test_workspace_tracking


class WorkspaceTrackingApiTests(unittest.TestCase):
    def setUp(self):
        test_workspace_tracking.WorkspaceTrackingTests.setUp(self)
        root_patch = patch.object(dashboard, 'ROOT', self.root)
        root_patch.start(); self.addCleanup(root_patch.stop)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), dashboard.handler('tracking-test'))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close); self.addCleanup(self.server.shutdown)

    def request(self, suffix='', body=None, token=True, origin=None):
        connection = HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        headers = {'Content-Type': 'application/json'}
        if token: headers['X-Smelter-Token'] = 'tracking-test'
        if origin: headers['Origin'] = origin
        connection.request('POST' if body is not None else 'GET', '/api/workspace-tracking' + suffix,
                           json.dumps(body) if body is not None else None, headers)
        response = connection.getresponse()
        result = response.status, json.load(response)
        connection.close()
        return result

    def test_cached_reads_do_not_rescan_and_refresh_observes_external_edits(self):
        self.assertEqual(self.request()[1]['workspaces'][0]['workspace_id'], self.sid)
        query = '?workspace_id=' + self.sid
        self.assertTrue(self.request(query)[1]['indexed'])
        (coding.base_path(self.root) / self.sid / 'file-index.json').unlink()
        self.assertFalse(self.request(query)[1]['indexed'])
        status, result = self.request(body={'action': 'refresh', 'workspace_id': self.sid})
        self.assertEqual(status, 200)
        with patch.object(coding, '_scan', side_effect=AssertionError('GET must not scan')):
            self.assertEqual(self.request(query)[1]['revision'], result['revision'])
        (self.target / 'mods/demo/tests/fixture.hex').write_text('00\n')
        refreshed = self.request(body={'action': 'refresh', 'workspace_id': self.sid})[1]
        self.assertNotEqual(refreshed['revision'], result['revision'])
        self.assertTrue(self.request(query + '&query=fixture.hex')[1]['files'][0]['status'] == 'modified')

    def test_auth_origin_ownership_and_query_validation(self):
        body = {'action': 'refresh', 'workspace_id': self.sid}
        self.assertEqual(self.request(token=False)[0], 403)
        self.assertEqual(self.request(body=body, token=False)[0], 403)
        self.assertEqual(self.request(body=body, origin='https://untrusted.example')[0], 403)
        for suffix in ('?query=x', '?workspace_id=../../escape', '?unknown=x',
                       '?workspace_id='+self.sid+'&workspace_id='+self.sid,
                       '?workspace_id='+self.sid+'&limit=0'):
            self.assertEqual(self.request(suffix)[0], 400, suffix)
        self.assertEqual(self.request(body={**body, 'path': 'ignored'})[0], 400)


if __name__ == '__main__': unittest.main()
