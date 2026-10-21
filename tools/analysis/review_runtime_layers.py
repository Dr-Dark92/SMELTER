"""Reproduce runtime-review findings in disposable fixtures; no model/Docker calls."""
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
from contextlib import ExitStack
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from unittest.mock import patch

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'tools/dashboard'))


def review():
    from access_policy import Policy,defaults,using
    from database import select_database
    from chats import create_chat,read_chat
    from python_tools import ToolSession
    from frontend_workspace import _source_files,prepare
    from chat_inference import ask
    from opencode_runtime import _progress
    from chat_jobs import Control,Jobs
    evidence={}
    with tempfile.TemporaryDirectory(prefix='smelter-layer-review-') as temporary,ExitStack() as patches:
        base=Path(temporary);root=base/'SMELTER';root.mkdir()
        select_database(root,str(base/'data'))
        (root/'tools/dashboard').mkdir(parents=True);(root/'tools/dashboard/dashboard.py').write_text('HTML="<style>body{}</style>"')
        (root/'README.md').write_text('synthetic denied content')
        cid=create_chat(root,'Runtime review fixture')['id']
        policy_value=defaults(root);policy_value['locations'][0]['exclusions'].append('README.md');policy_value['locations'][2]['exclusions']=['blocked*.md'];policy=Policy(policy_value)
        with using(policy):
            sources=_source_files(root)
            prepare(root,{})
        session=ToolSession(root,{'write_diagnostics':True},cid,policy=policy)
        result=session.execute({'function':{'name':'write_diagnostic_markdown','arguments':{'filename':'blocked-report.md','content':'# Synthetic denied target\n'}}})
        def denied(path,action):
            try:policy.authorize(path,action);return False
            except ValueError:return True
        evidence['R01']={'readme_denied_by_policy':denied(root/'README.md','read'),'readme_selected_for_copy':'README.md' in sources,'denied_readme_actually_copied':(root.with_name('SMELTERV2')/'README.md').read_text()=='synthetic denied content','report_denied_by_policy':denied(root/'diagnostics/blocked-report.md','write'),'write_status':result['status'],'denied_report_exists':(root/'diagnostics/blocked-report.md').is_file()}
        payload=json.dumps({'message':{'content':'truncated fixture answer'},'done_reason':'length'}).encode()
        answer=ask(root,cid,'Synthetic length fixture',opener=lambda *a,**k:io.BytesIO(payload))
        _,_,finished,_=_progress([{'info':{'role':'assistant','time':{'completed':1},'finish':'length'},'parts':[{'type':'text','text':'truncated fixture answer'}]}])
        evidence['R03']={'direct_status':answer['status'],'direct_text':answer['reply'],'opencode_length_recognized_finished':finished}
        # Actual local HTTP supplies malformed NDJSON; it is not a model service.
        class Stream(BaseHTTPRequestHandler):
            def log_message(self,*a):pass
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']));self.send_response(200);self.send_header('Content-Type','application/x-ndjson');self.end_headers();self.wfile.write(b'[]\n')
        stream=ThreadingHTTPServer(('127.0.0.1',0),Stream);thread=threading.Thread(target=stream.serve_forever,daemon=True);thread.start()
        connection=HTTPConnection
        try:
            with patch('chat_jobs.http.client.HTTPConnection',side_effect=lambda *a,**k:connection('127.0.0.1',stream.server_port,timeout=2)):
                try:Control().infer({'model':'synthetic','messages':[]},2,4096)
                except Exception as exc:evidence['R05']={'malformed_stream_error':type(exc).__name__,'detail':str(exc)}
        finally:stream.shutdown();stream.server_close();thread.join()
        # The same shape failure after a real fixture tool write loses transcript
        # finalization, though its JSONL result and file remain on disk.
        cid2=create_chat(root,'Partial tool fixture')['id'];control=Control();calls=0
        def fake_infer(*a,**k):
            nonlocal calls
            calls+=1
            if calls==1:return json.dumps({'message':{'content':'','tool_calls':[{'function':{'name':'write_diagnostic_markdown','arguments':{'filename':'partial-fixture.md','content':'# Actual fixture write\n'}}}]},'done_reason':'stop'}).encode()
            raise AttributeError("'list' object has no attribute 'get'")
        with patch.object(control,'infer',side_effect=fake_infer):
            try:ask(root,cid2,'Synthetic partial tool failure',tool_permissions={'write_diagnostics':True},control=control)
            except Exception as exc:evidence['R05'].update(after_tool_error=type(exc).__name__,transcript_messages=len(read_chat(root,cid2)['messages']),tool_file_exists=(root/'diagnostics/partial-fixture.md').is_file(),audit_result_recorded=any('partial-fixture.md' in p.read_text() and '"phase": "result"' in p.read_text() for p in (root/'.smelter/tool-runs').glob('*.jsonl')))
        value=defaults(root);value['locations']=[{**value['locations'][0],'id':'upper','path':str(base/'Case')},{**value['locations'][0],'id':'lower','path':str(base/'case')}]
        (base/'Case').mkdir();(base/'case').mkdir()
        try:Policy(value);case_error=None
        except ValueError as exc:case_error=str(exc)
        evidence['R06']={'platform':sys.platform,'distinct_directories':(base/'Case').stat().st_ino!=(base/'case').stat().st_ino,'policy_error':case_error}
        failed_root=base/'FailedSource';(failed_root/'tools/dashboard').mkdir(parents=True);(failed_root/'tools/dashboard/dashboard.py').write_text('HTML="<style>body{}</style>"');select_database(failed_root,str(base/'failed-source-data'))
        write_text=Path.write_text
        def fail_marker(path,*a,**k):
            if path.name=='frontend-workspace.json':raise OSError('Synthetic workspace marker failure')
            return write_text(path,*a,**k)
        with using(Policy(defaults(failed_root))),patch.object(Path,'write_text',fail_marker):
            try:prepare(failed_root,{})
            except OSError:pass
        with using(Policy(defaults(failed_root))):
            try:prepare(failed_root,{});retry_error=None
            except ValueError as exc:retry_error=str(exc)
        evidence['R07']={'new_workspace_removed':not failed_root.with_name('FailedSourceV2').exists(),'new_preview_data_left_behind':failed_root.with_name('FailedSourceV2-Data').exists(),'retry_error':retry_error}
        # A held operator POST serializes an unrelated Stop through STATE_LOCK.
        import dashboard
        jobs=Jobs();release_worker=threading.Event();entered=threading.Event();stop_started=threading.Event();release_probe=threading.Event()
        def worker(*a,**k):
            release_worker.wait(4);k['control'].check();return {'status':'completed'}
        job=jobs.start(root,{'id':cid,'content':'Synthetic blocked stop'},worker=worker)
        def probe(*a,**k):entered.set();release_probe.wait(3);return {'status':'fixture'}
        patches.enter_context(patch.object(dashboard,'ROOT',root));patches.enter_context(patch.object(dashboard,'JOBS',jobs));patches.enter_context(patch.object(dashboard,'mcp_exchange',probe));patches.enter_context(patch.object(dashboard,'validate_tool_permissions',return_value={}))
        http=ThreadingHTTPServer(('127.0.0.1',0),dashboard.handler('review-token'));http_thread=threading.Thread(target=http.serve_forever,daemon=True);http_thread.start();results={}
        def post(name,body):
            conn=connection('127.0.0.1',http.server_port,timeout=5)
            if name=='stop':stop_started.set()
            start=time.monotonic();conn.request('POST','/api/mcp' if name=='probe' else '/api/chats',json.dumps(body),{'Content-Type':'application/json','X-Smelter-Token':'review-token'});response=conn.getresponse();results[name]={'status':response.status,'seconds':round(time.monotonic()-start,3)};response.read();conn.close()
        probe_thread=threading.Thread(target=post,args=('probe',{'action':'probe','server':'smelter','permissions':{}}));probe_thread.start();assert entered.wait(2)
        stop_thread=threading.Thread(target=post,args=('stop',{'action':'stop','job_id':job['id']}));stop_thread.start();assert stop_started.wait(2);time.sleep(.35)
        blocked=not jobs.jobs[job['id']]['control'].cancelled.is_set();release_probe.set();probe_thread.join();stop_thread.join();release_worker.set()
        deadline=time.monotonic()+2
        while jobs.jobs[job['id']]['state']=='running' and time.monotonic()<deadline:time.sleep(.01)
        assert jobs.jobs[job['id']]['state']!='running'
        http.shutdown();http.server_close();http_thread.join()
        evidence['R02']={'stop_not_delivered_while_other_post_held_lock':blocked,'requests':results}
    return {'source_revision':'a609148fab2dec8915da24ca46550f9cd275b694','mode':'temporary fixtures only','live_qwen':False,'live_ollama':False,'live_docker':False,'observations':evidence}


if __name__=='__main__':print(json.dumps(review(),indent=2))
