import io
import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock,patch

import web_access as web
from database import select_database
from config_store import save_config
from chat_jobs import Control

PUBLIC=(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',443))


class Response:
    def __init__(self,raw=b'<html><title>Example</title><p>Verified text</p><script>bad()</script></html>',status=200,headers=None):
        self.raw=io.BytesIO(raw);self.status=status;self.headers=headers or {'Content-Type':'text/html'}
    def getheader(self,name,default=None):return self.headers.get(name,default)
    def read1(self,size):return self.raw.read(size)


class Connection:
    responses=[];calls=[]
    def __init__(self,host,address,timeout):self.sock=None;self.host=host;self.address=address
    def request(self,*args,**kwargs):self.calls.append((self.host,self.address,args,kwargs))
    def getresponse(self):return self.responses.pop(0)
    def close(self):pass
    def abort(self):pass


class WebTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)/'app';self.root.mkdir()
        select_database(self.root,str(Path(tmp.name)/'data'))
        self.policy={**web.DEFAULT,'mode':'docs','domains':['example.com']};save_config(self.root,web.NAME,self.policy)
        Connection.calls=[];Connection.responses=[Response()]

    def test_https_domains_credentials_ports_and_private_address_encodings(self):
        self.assertEqual(web.normalize('https://docs.example.com/x#part',self.policy)[0],'https://docs.example.com/x')
        bad=['http://example.com','https://user:pass@example.com','https://example.com:8443',
             'https://example.com.evil.net','https://127.0.0.1/','https://[::1]/','https://[::ffff:127.0.0.1]/',
             'https://169.254.169.254/','https://[64:ff9b::7f00:1]/','https://localhost/','https://example.com/?token=private']
        for url in bad:
            with self.subTest(url=url),self.assertRaises(ValueError):web.normalize(url,self.policy)
        for ip in ('127.0.0.1','10.0.0.1','169.254.169.254','224.0.0.1','::1','fc00::1','fe80::1','::ffff:192.168.1.1','2002:7f00:1::1'):
            self.assertFalse(web.public_ip(ip),ip)

    def test_dns_mixed_private_answer_is_rejected_before_connecting(self):
        private=(socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))
        with patch('web_access.socket.getaddrinfo',return_value=[PUBLIC,private]):
            with self.assertRaisesRegex(ValueError,'non-public'):web.resolve('example.com',time.monotonic()+3)

    def test_pinned_connection_keeps_original_tls_hostname(self):
        context=Mock();wrapped=Mock();context.wrap_socket.return_value=wrapped;raw=Mock()
        with patch('web_access.ssl.create_default_context',return_value=context),patch('web_access.socket.socket',return_value=raw):
            connection=web.PinnedHTTPS('example.com',PUBLIC,3);connection.connect()
        raw.connect.assert_called_once_with(('93.184.216.34',443))
        context.wrap_socket.assert_called_once_with(raw,server_hostname='example.com',do_handshake_on_connect=False)
        wrapped.do_handshake.assert_called_once()

    def test_public_page_is_plain_text_without_scripts_ambient_auth_or_proxy(self):
        with patch('web_access.resolve',return_value=[PUBLIC]),patch('web_access.PinnedHTTPS',Connection):
            result=web.fetch_live('https://example.com/docs',self.policy)
        self.assertIn('Verified text',result['text']);self.assertNotIn('bad()',result['text'])
        self.assertEqual(result['title'],'Example');self.assertTrue(result['body_hash_complete'])
        _,address,args,kwargs=Connection.calls[0];self.assertEqual(address,PUBLIC);self.assertEqual(args,('GET','/docs'))
        self.assertNotIn('Authorization',kwargs['headers']);self.assertNotIn('Cookie',kwargs['headers'])

    def test_redirect_target_is_rechecked_before_following(self):
        Connection.responses=[Response(status=302,headers={'Location':'https://127.0.0.1/private'})]
        with patch('web_access.resolve',return_value=[PUBLIC]) as resolver,patch('web_access.PinnedHTTPS',Connection):
            with self.assertRaises(ValueError):web.fetch_live('https://example.com/',self.policy)
        self.assertEqual(len(Connection.calls),1);self.assertEqual(resolver.call_count,1)

    def test_binary_and_compressed_responses_are_blocked(self):
        for headers in ({'Content-Type':'application/zip'},{'Content-Type':'text/html','Content-Encoding':'gzip'}):
            Connection.responses=[Response(headers=headers)]
            with patch('web_access.resolve',return_value=[PUBLIC]),patch('web_access.PinnedHTTPS',Connection):
                with self.assertRaises(ValueError):web.fetch_live('https://example.com/',self.policy)

    def test_single_long_html_text_node_reports_truncation(self):
        Connection.responses=[Response(b'<p>'+b'a'*(web.MAX_TEXT+100)+b'</p>')]
        with patch('web_access.resolve',return_value=[PUBLIC]),patch('web_access.PinnedHTTPS',Connection):
            result=web.fetch_live('https://example.com/',self.policy)
        self.assertEqual(len(result['text']),web.MAX_TEXT);self.assertTrue(result['truncated'])

    def test_cache_is_explicit_and_project_off_blocks_cached_reads(self):
        with patch('web_access.resolve',return_value=[PUBLIC]),patch('web_access.PinnedHTTPS',Connection):
            first=web.run(self.root,{'web_read':True},{'action':'fetch','url':'https://example.com/','limit':8})
            second=web.run(self.root,{'web_read':True},{'action':'fetch','url':'https://example.com/','offset':8,'limit':8})
        self.assertFalse(first['cached']);self.assertTrue(second['cached']);self.assertEqual(len(Connection.calls),1)
        save_config(self.root,web.NAME,{**self.policy,'mode':'off'})
        with self.assertRaises(ValueError):web.run(self.root,{'web_read':True},{'action':'fetch','url':'https://example.com/'})

    def test_explicit_refresh_reads_a_fresh_source(self):
        Connection.responses=[Response(b'<p>old</p>'),Response(b'<p>new</p>')]
        with patch('web_access.resolve',return_value=[PUBLIC]),patch('web_access.PinnedHTTPS',Connection):
            old=web.run(self.root,{'web_read':True},{'action':'fetch','url':'https://example.com/'})
            fresh=web.run(self.root,{'web_read':True},{'action':'fetch','url':'https://example.com/','refresh':True})
        self.assertFalse(fresh['cached']);self.assertNotEqual(old['body_sha256'],fresh['body_sha256']);self.assertEqual(fresh['text'],'new')

    def test_model_cannot_supply_headers_methods_or_secret_queries(self):
        for args in ({'action':'fetch','url':'https://example.com','headers':{}},{'action':'fetch','url':'https://example.com','method':'POST'},{'action':'search','query':'x','endpoint':'http://127.0.0.1'}):
            with self.subTest(args=args),self.assertRaises(ValueError):web.run(self.root,{'web_read':True},args)
        with self.assertRaises(ValueError):web.run(self.root,{}, {'action':'fetch','url':'https://example.com'})
        with self.assertRaises(ValueError):web.search('github_pat_'+('a'*40),self.policy)

    def test_cancel_interrupts_a_stalled_response(self):
        waiting,released=threading.Event(),threading.Event();control=Control();errors=[]
        class SlowResponse(Response):
            def read1(self,size):waiting.set();released.wait(3);raise OSError('interrupted')
        class SlowConnection(Connection):
            def getresponse(self):return SlowResponse()
            def abort(self):released.set()
        def fetch():
            try:web.fetch_live('https://example.com/',self.policy,control)
            except ValueError as exc:errors.append(str(exc))
        with patch('web_access.resolve',return_value=[PUBLIC]),patch('web_access.PinnedHTTPS',SlowConnection):
            thread=threading.Thread(target=fetch);thread.start();self.assertTrue(waiting.wait(2));control.cancel();thread.join(2)
        self.assertFalse(thread.is_alive());self.assertTrue(errors)

    def test_concurrent_native_calls_cannot_overrun_the_shared_budget(self):
        from python_tools import ToolSession
        session=ToolSession(self.root,{'web_read':True});session.call_limit=1;results=[];errors=[]
        def invoke(*args):time.sleep(.05);return {'status':'web_completed','action':'search','sources':[]}
        def execute():
            try:results.append(session.execute({'function':{'name':'web_access','arguments':{'action':'search','query':'example'}}}))
            except ValueError as exc:errors.append(str(exc))
        with patch.object(session,'_invoke',side_effect=invoke):
            threads=[threading.Thread(target=execute) for _ in range(2)]
            for thread in threads:thread.start()
            for thread in threads:thread.join(2)
        self.assertEqual(len(results),1);self.assertEqual(len(errors),1);self.assertEqual(len(session.events),1)


if __name__=='__main__':unittest.main()
