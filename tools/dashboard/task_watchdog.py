"""Independent loopback watchdog: private capture, verified end flags, three retries."""
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import argparse
import hmac
import json
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time

from watchdog_store import Store,folder,config,binding,decide,TERMINAL
from watchdog_native import Native


@contextmanager
def leader(root):
    base=folder(root);base.mkdir(parents=True,exist_ok=True)
    stream=(base/'leader.lock').open('a+b');stream.seek(0);stream.write(b'0');stream.flush();stream.seek(0)
    try:
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        yield
    finally:stream.close()


class Controller:
    def __init__(self,root,store=None,native=None,clock=time.time):
        self.root=Path(root).resolve();self.store=store or Store(root);self.native=native or Native(root);self.clock=clock

    def tick(self):
        settings=config(self.root);task=self.store.current()
        if not settings.get('enabled') or not task or task['state'] in TERMINAL:return
        now=self.clock()
        try:
            bound=binding(self.root);b=bound['binding']
            from native_progress import same_directory
            if b['session_id']!=task['session_id'] or b['workspace_id']!=task['workspace_id'] or not same_directory(b['directory'],task['directory']):
                self.store.update(task['id'],'superseded','binding_changed');return
            if not bound.get('enabled'):
                self.store.update(task['id'],'paused','native_monitor_disabled');return
            attempts=self.store.attempts(task['id']);observed=self.native.snapshot(task,attempts)
            for attempt in attempts:
                if attempt['message_id'] in observed.get('delivered',set()) and attempt['state'] in ('reserved','unknown'):
                    self.store.delivery(attempt['id'],'sent')
            # Never replay an uncertain POST after a crash/timeout. Reconcile
            # its deterministic native message ID, or hold for operator review.
            unsettled=[a for a in attempts if a['state'] in ('reserved','unknown','sent') and a['message_id'] not in observed.get('delivered',set())]
            action=decide(task,observed,settings,now)
            if action in ('cancel','supersede'):
                self.store.update(task['id'],'cancelled' if action=='cancel' else 'superseded','native_cancelled' if action=='cancel' else 'new_human_prompt');return
            if observed.get('assistant_seen') and not task.get('started'):
                self.store.update(task['id'],task['state'],'original_assistant_observed',started=1);task['started']=1
            if not task.get('started'):
                self.store.update(task['id'],'wait_initial_assistant','no_reply_or_original_execution_not_started',last_observed=now);return
            if unsettled:
                self.store.update(task['id'],'delivery_unknown','awaiting_dispatch_reconciliation',last_observed=now);return
            if action in ('green','red'):
                self.store.update(task['id'],action,'explicit_verified_end_flag',flag=action.upper(),flag_receipt=observed.get('flag_receipt'),last_observed=now);return
            if action=='exhaust':
                self.store.update(task['id'],'exhausted','three_stall_retries_exhausted',last_observed=now);return
            if action!='retry':
                self.store.update(task['id'],action,'waiting_without_replaying_work',last_observed=now);return
            # Check again just before reserving/submitting: cancellation, new
            # input, pending access or active work revoke recovery admission.
            observed=self.native.snapshot(task,self.store.attempts(task['id']))
            if decide(task,observed,settings,self.clock())!='retry':return
            attempt=self.store.reserve(task['id'],now)
            if not attempt:return
            try:
                self.native.send(task,attempt)
            except Exception:
                self.store.delivery(attempt['id'],'unknown')
                self.store.update(task['id'],'delivery_unknown','native_delivery_uncertain',last_observed=now)
                return
            self.store.delivery(attempt['id'],'sent')
            self.store.update(task['id'],'watching','continuation_submitted',next_retry=now+min(120,30*2**(attempt['number']-1)),last_observed=now)
        except (OSError,ValueError,KeyError,TypeError,sqlite3.Error) as error:
            self.store.update(task['id'],'wait_runtime','observation_unavailable_'+type(error).__name__,last_observed=now)


def handler(controller,credential):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass  # Never log captured prompts or credentials.
        def reply(self,status,value):
            raw=json.dumps(value).encode('utf-8');self.send_response(status)
            self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            if not self.allowed():return self.reply(403,{'error':'watchdog authorization required'})
            if self.path!='/status':return self.reply(404,{'error':'not found'})
            return self.reply(200,controller.store.public())
        def allowed(self):
            supplied=self.headers.get('Authorization','')
            return not self.headers.get('Origin') and hmac.compare_digest(supplied,'Bearer '+credential)
        def do_POST(self):
            if not self.allowed():return self.reply(403,{'error':'watchdog authorization required'})
            if self.path not in ('/capture','/cancel'):return self.reply(404,{'error':'not found'})
            try:
                if self.headers.get('Transfer-Encoding'):raise ValueError('Chunked capture is unsupported')
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=64*1024:raise ValueError('Capture exceeds 64 KiB')
                self.connection.settimeout(3);value=json.loads(self.rfile.read(length))
                if not isinstance(value,dict):raise ValueError('Capture must be an object')
                if not config(controller.root).get('enabled'):raise ValueError('Watchdog disabled')
                if self.path=='/cancel':
                    task=controller.store.current()
                    if task and task['session_id']==value.get('session_id'):
                        observed=controller.native.metadata(task,controller.store.attempts(task['id']))
                        if observed.get('cancelled'):controller.store.update(task['id'],'cancelled','native_cancelled')
                    return self.reply(200,{'status':'cancellation_checked'})
                if value.get('server_port') not in controller.native.ports():raise ValueError('Originating ACP listener not verified')
                result=controller.store.capture(value,binding(controller.root));return self.reply(200,result)
            except (OSError,ValueError,KeyError,TypeError,sqlite3.Error):return self.reply(409,{'error':'watchdog capture/admission rejected'})
    return Handler


def run(root):
    from coding_workspace import _save
    from job_store import identity
    root=Path(root).resolve()
    with leader(root):
        control=Controller(root);credential=secrets.token_urlsafe(32)
        server=ThreadingHTTPServer(('127.0.0.1',0),handler(control,credential));server.daemon_threads=True
        runtime={'schema_version':1,'source_root':str(root),'pid':os.getpid(),'owner_identity':identity(os.getpid()),'port':server.server_port,'credential':credential}
        _save(folder(root)/'runtime.json',runtime)
        thread=threading.Thread(target=server.serve_forever,daemon=True,name='watchdog-capture');thread.start()
        try:
            while config(root).get('enabled'):
                control.tick()
                _save(folder(root)/'public.json',{**control.store.public(),'observed_at':time.time(),'pid':os.getpid()})
                time.sleep(config(root)['poll_seconds'])
        finally:
            server.shutdown();server.server_close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    run(parser.parse_args().root)
