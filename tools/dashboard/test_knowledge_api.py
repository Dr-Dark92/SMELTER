from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import dashboard
from database import select_database


class KnowledgeApiTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);base=Path(tmp.name);self.root=base/'app';self.root.mkdir();select_database(self.root,str(base/'data'))
        self.root_patch=patch.object(dashboard,'ROOT',self.root);self.root_patch.start();self.addCleanup(self.root_patch.stop)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),dashboard.handler('knowledge-token'));self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
    def request(self,path,body=None,token=True,origin=None):
        connection=HTTPConnection('127.0.0.1',self.server.server_port,timeout=5);headers={'Content-Type':'application/json'}
        if token:headers['X-Smelter-Token']='knowledge-token'
        if origin:headers['Origin']=origin
        connection.request('POST' if body is not None else 'GET',path,json.dumps(body) if body is not None else None,headers)
        response=connection.getresponse();result=response.status,json.load(response);connection.close();return result

    def test_web_settings_require_auth_and_current_revision(self):
        status,result=self.request('/api/web-access');self.assertEqual(status,200);self.assertEqual(result['settings']['mode'],'off')
        body={'action':'save','settings':{**result['settings'],'mode':'docs','domains':['example.com']},'expected_revision':result['revision']}
        self.assertEqual(self.request('/api/web-access',body,token=False)[0],403)
        self.assertEqual(self.request('/api/web-access',body,origin='https://untrusted.example')[0],403)
        self.assertEqual(self.request('/api/web-access',body)[0],200)
        self.assertEqual(self.request('/api/web-access',body)[0],400)

    def test_human_memory_edit_and_forget_use_hashes_and_never_accept_origin(self):
        status,saved=self.request('/api/project-memory',{'action':'remember','title':'Decision','text':'Use 128K context'})
        self.assertEqual(status,200);note=saved['note'];self.assertEqual(note['confidence'],'user_supplied')
        self.assertEqual(self.request('/api/project-memory',{'action':'remember','title':'Fake','text':'x','origin':'controller'})[0],400)
        edit={'action':'remember','id':note['id'],'expected_sha256':'wrong','title':'Updated','text':'new'}
        self.assertEqual(self.request('/api/project-memory',edit)[0],400)
        edit['expected_sha256']=note['sha256'];status,saved=self.request('/api/project-memory',edit);self.assertEqual(status,200)
        self.assertEqual(self.request('/api/project-memory',{'action':'forget','id':note['id'],'expected_sha256':saved['note']['sha256']},token=False)[0],403)
        self.assertEqual(self.request('/api/project-memory',{'action':'forget','id':note['id'],'expected_sha256':saved['note']['sha256']})[0],200)
        self.assertEqual(self.request('/api/project-memory',{'action':'search','query':'updated'})[1]['notes'],[])


if __name__=='__main__':unittest.main()
