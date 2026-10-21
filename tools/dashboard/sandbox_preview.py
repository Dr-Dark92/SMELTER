"""Loopback HTTP proxy through fixed Docker exec, without container networking.

The container has no published port or network. Each request is relayed through
an owned fixed command. No model-selected command, hostname or executable exists.
"""
import atexit
import base64
import subprocess
import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.request import Request,urlopen
from process_runner import run

RELAY=r'''
import base64,http.client,json,sys
request=json.load(sys.stdin)
connection=http.client.HTTPConnection('127.0.0.1',8770,timeout=8)
connection.request(request['method'],request['path'],base64.b64decode(request['body']),request['headers'])
response=connection.getresponse();raw=response.read(6*1024*1024+1)
if len(raw)>6*1024*1024:raise ValueError('Preview reply exceeds budget')
print(json.dumps({'status':response.status,'headers':dict(response.getheaders()),'body':base64.b64encode(raw).decode()}))
'''
_owners={}
_lock=threading.Lock()


def start(docker,container,token,cleanup):
    with _lock:
        if _owners:raise ValueError('A confined preview is already running; stop it in Settings first')
    slots=threading.BoundedSemaphore(8)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def relay(self):
            if not self.path.startswith('/') or self.path.startswith('//') or len(self.path)>4096:
                self.send_error(400);return
            if self.path.startswith('/api/') and not secrets.compare_digest(self.headers.get('X-Smelter-Token',''),token):
                self.send_error(403);return
            if not slots.acquire(blocking=False):self.send_error(503);return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<=length<=2*1024*1024:self.send_error(413);return
                payload={'method':self.command,'path':self.path,'body':base64.b64encode(self.rfile.read(length)).decode(),
                         'headers':{key:value for key,value in self.headers.items() if key.lower() in ('content-type','x-smelter-token','origin')}}
                result=run([docker,'exec','--interactive',container,'python','-c',RELAY],input=json.dumps(payload).encode(),timeout=12,max_output=10*1024*1024,check=True)
                response=json.loads(result.stdout);raw=base64.b64decode(response['body'],validate=True)
                self.send_response(response['status'])
                for key,value in response['headers'].items():
                    if key.lower() in ('content-type','content-security-policy','x-content-type-options','cache-control'):self.send_header(key,value)
                self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
            except (ValueError,OSError,subprocess.SubprocessError):self.send_error(502,'Confined preview request failed')
            finally:slots.release()
        do_GET=relay
        do_POST=relay
    server=ThreadingHTTPServer(('127.0.0.1',8770),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    with _lock:_owners[container]=(server,cleanup)
    url='http://127.0.0.1:8770/#token='+token
    try:
        deadline=time.monotonic()+12
        while time.monotonic()<deadline:
            try:
                with urlopen(Request('http://127.0.0.1:8770/api/chats',headers={'X-Smelter-Token':token}),timeout=3) as response:
                    if isinstance(json.load(response).get('conversations'),list):break
            except (OSError,ValueError):time.sleep(.2)
        else:raise ValueError('Confined preview readiness was not confirmed')
    except Exception:stop();raise
    timer=threading.Timer(3600,stop);timer.daemon=True;timer.start()
    return {'url':url,'lifetime_seconds':3600,'pid':None,'process_owner':'docker container and dashboard relay','message':'Confined preview ready. Host files and network are not exposed; data is temporary.','visual_inspection':'not performed'}


def stop():
    with _lock:owners=list(_owners.items());_owners.clear()
    pending=[]
    for name,(server,cleanup) in owners:
        server.shutdown();server.server_close()
        if not cleanup():
            pending.append(name)
            with _lock:_owners[name]=(server,cleanup)
    return {'stopped':bool(owners) and not pending,'cleanup_pending':pending}


atexit.register(stop)
