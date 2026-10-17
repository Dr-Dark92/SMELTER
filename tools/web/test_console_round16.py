#!/usr/bin/env python3
"""Round 16 smoke test: read-only local console and OpenCode discovery."""
import http.client
import importlib.util
import json
from pathlib import Path
import threading
import unittest

SOURCE=Path(__file__).with_name("smelter_console.py")
spec=importlib.util.spec_from_file_location("smelter_console",SOURCE)
console=importlib.util.module_from_spec(spec)
spec.loader.exec_module(console)

class ConsoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=console.ThreadingHTTPServer(("127.0.0.1",0),console.Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)
    def request(self,method,path,host=None):
        conn=http.client.HTTPConnection("127.0.0.1",self.server.server_port,timeout=8)
        conn.request(method,path,headers={"Host":host or "127.0.0.1:8765"})
        res=conn.getresponse()
        status=res.status
        body=res.read()
        conn.close()
        return status,body
    def test_html(self):
        code,body=self.request("GET","/")
        self.assertEqual(code,200)
        self.assertIn(b"SMELTER",body)
    def test_opencode_status(self):
        code,body=self.request("GET","/api/opencode")
        self.assertEqual(code,200)
        obj=json.loads(body)
        self.assertEqual(obj["url"],"http://127.0.0.1:4096")
        self.assertIn("listener",obj)
    def test_skills_read_only(self):
        code,body=self.request("GET","/api/skills")
        self.assertEqual(code,200)
        self.assertEqual(json.loads(body)["remote_installation"],"disabled")
    def test_capability_catalog(self):
        code,body=self.request("GET","/api/catalog")
        self.assertEqual(code,200)
        obj=json.loads(body)
        self.assertEqual(obj["remote_installation"],"disabled")
        self.assertTrue(any("Python" in x["name"] for x in obj["capabilities"]))
    def test_repository_discovery_schema(self):
        code,body=self.request("GET","/api/repos")
        self.assertEqual(code,200)
        obj=json.loads(body)
        self.assertIn("repositories",obj)
        self.assertIsInstance(obj["repositories"],list)
        for item in obj["repositories"]:
            self.assertIn("nameWithOwner",item)
            self.assertNotIn("token",item)
    def test_catalog_does_not_modify_repository(self):
        code,body=self.request("GET","/api/catalog")
        self.assertEqual(code,200)
        self.assertNotIn(b"install_command",body)
    def test_post_denied(self):
        code,_=self.request("POST","/api/opencode")
        self.assertEqual(code,405)
    def test_host_rejected(self):
        code,_=self.request("GET","/api/status","untrusted.example:8765")
        self.assertEqual(code,403)
    def test_unknown(self):
        code,_=self.request("GET","/api/not-found")
        self.assertEqual(code,404)

if __name__=="__main__":
    unittest.main(verbosity=2)
