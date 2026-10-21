"""Directory navigation and optimistic policy Apply, without model/service use."""
import copy
from contextlib import closing
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.parse import urlencode
from unittest.mock import patch
from access_policy import current,defaults,save
from database import select_database
from location_browser import browse


class LocationTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.base=Path(temporary.name);self.root=self.base/'SMELTER';self.root.mkdir()
        select_database(self.root,str(self.base/'data'))
        self.assets=self.root/'Assets';self.assets.mkdir()
        for name in ('Beta','Alpha','.hidden'):(self.assets/name).mkdir()
        (self.assets/'private.txt').write_text('This content must not be returned.')

    def test_directory_names_only_sorted_and_hidden_is_explicit(self):
        result=browse(self.root,str(self.assets))
        self.assertEqual([r['name'] for r in result['directories']],['Alpha','Beta'])
        self.assertTrue(result['read_only']);self.assertTrue(result['selectable'])
        self.assertTrue(all(set(r)=={'name','path'} for r in result['directories']))
        self.assertNotIn('private',json.dumps(result))
        self.assertEqual([r['name'] for r in browse(self.root,str(self.assets),True)['directories']],['.hidden','Alpha','Beta'])

    def test_browse_does_not_register_or_grant_location(self):
        external=self.base/'External';external.mkdir();before=current(self.root)
        browse(self.root,str(external))
        self.assertEqual(current(self.root).revision,before.revision)
        with self.assertRaisesRegex(ValueError,'not registered'):current(self.root).authorize(external,'read')

    def test_links_traversal_files_and_relative_paths_rejected(self):
        for value in ('relative',str(self.root/'..'),str(self.assets/'private.txt'),str(self.base/'missing')):
            with self.subTest(value=value),self.assertRaises(ValueError):browse(self.root,value)
        linked=self.root/'linked'
        try:linked.symlink_to(self.assets,target_is_directory=True)
        except OSError:self.skipTest('Symlink privilege unavailable')
        with self.assertRaises(ValueError):browse(self.root,str(linked))
        self.assertNotIn('linked',[r['name'] for r in browse(self.root,str(self.root))['directories']])

    def test_metadata_budget_reports_truncation(self):
        with patch('location_browser.MAX_DIRECTORIES',1):result=browse(self.root,str(self.assets))
        self.assertEqual(len(result['directories']),1);self.assertTrue(result['truncated'])

    def test_root_navigation_never_selects_whole_filesystem(self):
        with patch('location_browser.os.scandir') as iterator:
            iterator.return_value.__enter__.return_value=iter([])
            result=browse(self.root,self.root.anchor)
        self.assertFalse(result['selectable']);self.assertIsNone(result['parent'])
        value=defaults(self.root);value['locations'][0]['path']=self.root.anchor
        with self.assertRaisesRegex(ValueError,'Whole-drive'):save(self.root,value,current(self.root).revision)

    def test_conditional_apply_and_stale_revision_preserve_current_policy(self):
        revision=current(self.root).revision;draft=defaults(self.root);draft['locations'][1]['write']=False
        result=save(self.root,draft,revision);self.assertNotEqual(result['revision'],revision)
        with self.assertRaisesRegex(ValueError,'another window'):save(self.root,defaults(self.root),revision)
        self.assertFalse(current(self.root).value['locations'][1]['write'])

    def test_two_concurrent_applies_have_only_one_winner(self):
        revision=current(self.root).revision;barrier=threading.Barrier(2);results=[];lock=threading.Lock()
        def worker(name):
            value=defaults(self.root);value['locations'][0]['name']=name;barrier.wait(3)
            try:save(self.root,value,revision);result='saved'
            except ValueError as error:result='conflict' if 'another window' in str(error) else str(error)
            with lock:results.append(result)
        threads=[threading.Thread(target=worker,args=(name,)) for name in ('One','Two')]
        for thread in threads:thread.start()
        for thread in threads:thread.join(5)
        self.assertFalse(any(t.is_alive() for t in threads));self.assertCountEqual(results,['saved','conflict'])

    def test_invalid_revision_does_not_mutate_state(self):
        before=current(self.root).revision
        for value in ('bad',False,[],123):
            with self.subTest(value=value),self.assertRaises(ValueError):save(self.root,defaults(self.root),value)
        self.assertEqual(current(self.root).revision,before)

    def test_authenticated_http_browser_and_apply_contract(self):
        import dashboard
        token='fixture-token'
        with patch.object(dashboard,'ROOT',self.root):
            server=ThreadingHTTPServer(('127.0.0.1',0),dashboard.handler(token));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            def request(path,body=None,authorized=True):
                connection=HTTPConnection('127.0.0.1',server.server_port,timeout=3)
                headers={'X-Smelter-Token':token} if authorized else {}
                connection.request('GET' if body is None else 'POST',path,None if body is None else json.dumps(body),headers)
                response=connection.getresponse();result=response.status,json.load(response);connection.close();return result
            try:
                path='/api/location-browser?'+urlencode({'path':str(self.assets)})
                self.assertEqual(request(path,authorized=False)[0],403)
                status,result=request(path);self.assertEqual(status,200);self.assertEqual(Path(result['current_path']),self.assets.resolve())
                self.assertEqual(request('/api/location-browser?hidden=bad')[0],400)
                self.assertEqual(request('/api/location-browser?path=a&path=b')[0],400)
                revision=current(self.root).revision;value=defaults(self.root);value['locations'][0]['name']='HTTP fixture'
                self.assertEqual(request('/api/access-policy',{'policy':value,'expected_revision':revision})[0],200)
                self.assertEqual(request('/api/access-policy',{'policy':defaults(self.root),'expected_revision':revision})[0],400)
                self.assertEqual(current(self.root).value['locations'][0]['name'],'HTTP fixture')
            finally:server.shutdown();server.server_close();thread.join(3)


if __name__=='__main__':unittest.main()
