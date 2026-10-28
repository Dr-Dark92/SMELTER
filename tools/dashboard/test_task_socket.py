import base64
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import io
import json
import os
import socket
import struct
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import dashboard
from task_socket import credential, control, frame


def client_frame(payload=b'', opcode=8, masked=True):
    mask=b'abcd'
    return bytes([0x80|opcode,(0x80 if masked else 0)|len(payload)])+(mask+bytes(v^mask[i%4] for i,v in enumerate(payload)) if masked else payload)


def receive(connection):
    def exact(size):
        chunks=b''
        while len(chunks)<size:
            chunk=connection.recv(size-len(chunks))
            if not chunk:raise EOFError()
            chunks+=chunk
        return chunks
    first,second=exact(2);size=second&127
    if size==126:size=struct.unpack('!H',exact(2))[0]
    elif size==127:size=struct.unpack('!Q',exact(8))[0]
    return first&15,exact(size)


class SocketProtocolTests(unittest.TestCase):
    def test_credentials_require_same_origin_and_never_come_from_query_parameters(self):
        headers={'Origin':'http://127.0.0.1:8769','Sec-WebSocket-Protocol':'smelter.trace.v1, smelter.auth.fixture-token'}
        self.assertEqual(credential(headers,headers['Origin']),'fixture-token')
        self.assertEqual(credential(headers,'https://evil.invalid'),'')
        self.assertEqual(credential({**headers,'Sec-WebSocket-Protocol':'smelter.trace.v1'},headers['Origin']),'')

    def test_control_frames_are_masked_bounded_final_and_control_only(self):
        self.assertEqual(control(io.BytesIO(client_frame(b'hi',9))),(9,b'hi'))
        for raw in (client_frame(b'hi',9,False),client_frame(b'command',1),b'\x09\x80',b'\x89\xfe',client_frame(b'x',8)):
            with self.assertRaises((ValueError,EOFError)):control(io.BytesIO(raw))
        self.assertEqual(control(io.BytesIO(client_frame(struct.pack('!H',1000),8))),(8,struct.pack('!H',1000)))
        with self.assertRaises(ValueError):control(io.BytesIO(client_frame(struct.pack('!H',1005),8)))

    def test_frame_length_boundaries(self):
        for size,prefix in ((4,4),(126,126),(65536,127)):
            value=frame(b'a'*size);self.assertEqual(value[0],0x81);self.assertEqual(value[1],prefix)
        with self.assertRaises(ValueError):frame(b'x'*(1024*1024+1))


class TaskSocketApiTests(unittest.TestCase):
    def setUp(self):
        self.data={'available':True,'task_id':'msg_fixture','status':{'phase':'waiting_access'}}
        patcher=patch('task_trace.manager',return_value=SimpleNamespace(view=lambda:self.data));patcher.start();self.addCleanup(patcher.stop)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),dashboard.handler('trace-test-token'))
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        self.addCleanup(self.server.server_close);self.addCleanup(self.server.shutdown)
        self.origin='http://127.0.0.1:'+str(self.server.server_port)

    def headers(self):
        return {'Host':'127.0.0.1:'+str(self.server.server_port),'Origin':self.origin,'Connection':'Upgrade','Upgrade':'websocket',
            'Sec-WebSocket-Version':'13','Sec-WebSocket-Key':base64.b64encode(os.urandom(16)).decode(),
            'Sec-WebSocket-Protocol':'smelter.trace.v1, smelter.auth.trace-test-token'}

    def test_unauthorized_origin_credentials_and_query_are_rejected(self):
        for override,path in (({'Origin':'https://evil.invalid'},'/api/task-trace/ws'),({'Sec-WebSocket-Protocol':'smelter.trace.v1, smelter.auth.wrong-token'},'/api/task-trace/ws'),({},'/api/task-trace/ws?token=trace-test-token')):
            connection=HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
            connection.request('GET',path,headers={**self.headers(),**override})
            response=connection.getresponse();self.assertEqual(response.status,403);response.read();connection.close()

    def connect(self):
        connection=socket.create_connection(('127.0.0.1',self.server.server_port),timeout=3);self.addCleanup(connection.close)
        text='GET /api/task-trace/ws HTTP/1.1\r\n'+''.join(k+': '+v+'\r\n' for k,v in self.headers().items())+'\r\n'
        connection.sendall(text.encode());header=b''
        while not header.endswith(b'\r\n\r\n'):header+=connection.recv(1)
        self.assertTrue(header.startswith(b'HTTP/1.1 101'))
        self.assertIn(b'Sec-WebSocket-Protocol: smelter.trace.v1',header)
        self.assertNotIn(b'trace-test-token',header)
        return connection

    def test_actual_upgrade_snapshot_ping_and_close_without_task_controls(self):
        connection=self.connect();opcode,payload=receive(connection)
        self.assertEqual(opcode,1);self.assertEqual(json.loads(payload)['trace'],self.data)
        connection.sendall(client_frame(b'ping',9));self.assertEqual(receive(connection),(10,b'ping'))
        connection.sendall(client_frame(struct.pack('!H',1000),8));self.assertEqual(receive(connection),(8,struct.pack('!H',1000)))

    def test_application_messages_cannot_control_tasks(self):
        connection=self.connect();receive(connection)
        connection.sendall(client_frame(b'abort',1));opcode,payload=receive(connection)
        self.assertEqual(opcode,8);self.assertEqual(struct.unpack('!H',payload)[0],1002)

    def test_authenticated_http_snapshot_uses_same_source(self):
        connection=HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
        connection.request('GET','/api/task-trace',headers={'X-Smelter-Token':'trace-test-token'})
        response=connection.getresponse();self.assertEqual(response.status,200);self.assertEqual(json.load(response),self.data);connection.close()


if __name__=='__main__':unittest.main()
