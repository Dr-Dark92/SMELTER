"""Exercise real OpenCode + stdio MCP + saved bytes in disposable state.

Default: production managed container with a synthetic loopback Ollama fixture.
--live: use the existing local Ollama service; never download a model.
--process-fixture: explicitly test real OpenCode as a local disposable process,
without claiming that Docker confinement or real Qwen inference was tested.
"""
import argparse
import base64
import contextlib
import hashlib
import http.server
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'tools/dashboard'))
from agent_bridge import AgentBridge
from access_policy import current
from chat_jobs import Control
from chats import create_chat,read_chat
from config_store import save_config
from database import select_database
from opencode_runtime import Client,ask,VERSION
from task_contract import configuration

CONTENT='# SMELTER bridge smoke\n\nVerified marker: SMELTER_AGENT_BRIDGE_SMOKE\n'
FILENAME='agent-bridge-smoke.md'


class ModelFixture(http.server.BaseHTTPRequestHandler):
    requests=[]
    expected_skill=''
    def log_message(self,*args):pass
    def respond(self,value,sse=False):
        data=value.encode() if isinstance(value,str) else json.dumps(value).encode()
        self.send_response(200);self.send_header('Content-Type','text/event-stream' if sse else 'application/json')
        self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):
        if self.path=='/v1/models':self.respond({'object':'list','data':[{'id':'qwen3.5:9b','object':'model'}]})
        else:self.send_error(404)
    def do_POST(self):
        body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.requests.append(body)
        if self.expected_skill not in json.dumps(body):
            self.send_error(400,'Selected skill instructions did not reach the model');return
        native=self.path=='/api/chat'
        if not native and self.path!='/v1/chat/completions':self.send_error(404);return
        definitions=body.get('tools',[])
        names=[item.get('function',{}).get('name') for item in definitions]
        returned=any(item.get('role')=='tool' for item in body.get('messages',[]))
        if not returned:
            name='smelter_write_diagnostic_markdown'
            if name not in names:self.send_error(400,'MCP write tool was not offered');return
            function={'name':name,'arguments':{'filename':FILENAME,'content':CONTENT}}
            message={'role':'assistant','content':'','tool_calls':[{'function':function}]}
        else:message={'role':'assistant','content':'Synthetic smoke completed; inspect the controller receipt and saved bytes.'}
        if native:
            self.respond({'message':message,'done':True,'done_reason':'stop'});return
        if message.get('tool_calls'):
            function=message['tool_calls'][0]['function']
            function={**function,'arguments':json.dumps(function['arguments'])}
            message['tool_calls']=[{'id':'call_smoke','type':'function','function':function}]
        finish='tool_calls' if message.get('tool_calls') else 'stop'
        value={'id':'chatcmpl-smoke','object':'chat.completion','created':int(time.time()),'model':'qwen3.5:9b'}
        if body.get('stream'):
            delta={**message}
            if delta.get('tool_calls'):delta['tool_calls']=[{'index':0,**delta['tool_calls'][0]}]
            first={**value,'object':'chat.completion.chunk','choices':[{'index':0,'delta':delta,'finish_reason':None}]}
            last={**value,'object':'chat.completion.chunk','choices':[{'index':0,'delta':{},'finish_reason':finish}]}
            self.respond('data: '+json.dumps(first)+'\n\ndata: '+json.dumps(last)+'\n\ndata: [DONE]\n\n',True)
        else:self.respond({**value,'choices':[{'index':0,'message':message,'finish_reason':finish}]})


def port_free(port):
    with socket.socket() as sock:
        try:sock.bind(('127.0.0.1',port))
        except OSError:raise ValueError(f'Fixture port {port} is occupied; no existing service was stopped')


@contextlib.contextmanager
def model_fixture(enabled,reference):
    if not enabled:yield;return
    port_free(11434)
    ModelFixture.requests=[];ModelFixture.expected_skill=reference
    server=http.server.ThreadingHTTPServer(('127.0.0.1',11434),ModelFixture)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield
    finally:server.shutdown();server.server_close();thread.join(timeout=5)


@contextlib.contextmanager
def process_fixture(base,root,target,bridge,binary):
    """Explicit test harness only. Production ask() never chooses this path."""
    port_free(4096)
    if not binary or not Path(binary).is_file():raise ValueError('Pass --opencode with an existing executable path')
    queue=base/'queue';queue.mkdir()
    manifest=base/'tools.json';manifest.write_text(json.dumps(bridge.manifest(90)))
    node=shutil.which('node')
    if not node:raise ValueError('Node is required for the stdio fixture')
    password=secrets.token_urlsafe(32)
    config={'provider':{'local':{'npm':'@ai-sdk/openai-compatible','options':{
        'baseURL':'http://127.0.0.1:11434/v1','apiKey':'fixture'},'models':{'qwen3.5:9b':{'name':'Smoke fixture'}}}},
        'mcp':{'smelter':{'type':'local','command':[node,str(REPO/'tools/dashboard/opencode_mcp_proxy.mjs'),
            '--manifest',str(manifest),'--queue',str(queue)],'enabled':True,'timeout':10000}}}
    home=base/'home';home.mkdir()
    env={key:value for key,value in os.environ.items() if key in ('PATH','SystemRoot','WINDIR','COMSPEC','PATHEXT','TEMP','TMP')}
    env.update(HOME=str(home),USERPROFILE=str(home),XDG_CONFIG_HOME=str(home/'config'),
        XDG_CACHE_HOME=str(home/'cache'),XDG_DATA_HOME=str(home/'data'),XDG_STATE_HOME=str(home/'state'),
        OPENCODE_CONFIG_CONTENT=json.dumps(config),OPENCODE_SERVER_PASSWORD=password,
        OPENCODE_DISABLE_MODELS_FETCH='true',OPENCODE_DISABLE_DEFAULT_PLUGINS='true')
    stopped=threading.Event();failures=[]
    def dispatch():
        while not stopped.wait(.03):
            for request in queue.glob('*.request'):
                try:
                    item=json.loads(request.read_text());request.unlink()
                    if item.get('kind')!='mcp':raise ValueError('Unexpected fixture queue packet')
                    result=bridge.call(item['name'],item['arguments'])
                    temporary=request.with_suffix('.pending')
                    temporary.write_text(json.dumps({'mcp_result':result}))
                    temporary.replace(request.with_suffix('.response'))
                except Exception as exc:failures.append(str(exc));return
    thread=threading.Thread(target=dispatch,daemon=True)
    flags={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {'start_new_session':True}
    with (base/'opencode.log').open('wb') as log:
        process=subprocess.Popen([binary,'serve','--pure','--hostname','127.0.0.1','--port','4096'],
            cwd=target,env=env,stdout=log,stderr=subprocess.STDOUT,**flags)
        old=os.environ.get('SMELTER_OPENCODE_PASSWORD');os.environ['SMELTER_OPENCODE_PASSWORD']=password
        thread.start()
        client=Client();client.directory=str(target)
        try:
            deadline=time.monotonic()+45
            while time.monotonic()<deadline:
                if process.poll() is not None:raise ValueError('Fixture OpenCode exited: '+(base/'opencode.log').read_text(errors='replace')[-4000:])
                try:
                    health=client.request('/global/health')
                    if health.get('healthy'):break
                except (ValueError,OSError):time.sleep(.1)
            else:raise ValueError('Fixture OpenCode startup timed out')
            yield client
            if failures:raise ValueError('Fixture queue failed: '+failures[0])
        finally:
            stopped.set();bridge.close();thread.join(timeout=15)
            if old is None:os.environ.pop('SMELTER_OPENCODE_PASSWORD',None)
            else:os.environ['SMELTER_OPENCODE_PASSWORD']=old
            # Only this fixture's process group is terminated, never all shells.
            if process.poll() is None:
                if os.name=='nt':process.terminate()
                else:
                    import signal
                    os.killpg(process.pid,signal.SIGTERM)
                try:process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    if os.name=='nt':process.kill()
                    else:os.killpg(process.pid,signal.SIGKILL)
                    process.wait(timeout=5)


def run(args):
    if args.live and args.process_fixture:raise ValueError('--live requires the managed container')
    if not args.process_fixture and not args.image:raise ValueError('Pass --image sha256:... for the managed OpenCode image')
    with tempfile.TemporaryDirectory(prefix='smelter-agent-smoke-') as name:
        base=Path(name);root=base/'SMELTER';root.mkdir();target=base/'SMELTERV2';target.mkdir()
        (root/'README.md').write_text('# Disposable smoke source\n')
        (target/'README.md').write_text('# Disposable smoke snapshot\n')
        for folder in (root,target):
            (folder/'tools/dashboard').mkdir(parents=True);(folder/'skills/documentation').mkdir(parents=True)
            (folder/'tools/dashboard/dashboard.py').write_text('HTML="<style>body{color:red}</style>"\n')
        reference=(REPO/'skills/documentation/SKILL.md').read_text(encoding='utf-8')
        (root/'skills/documentation/SKILL.md').write_text(reference,encoding='utf-8')
        (target/'skills/documentation/SKILL.md').write_text(reference,encoding='utf-8')
        select_database(root,str(base/'data'))
        if args.image:save_config(root,'sandbox.json',{'schema_version':1,'python_image':None,'node_image':None,'opencode_image':args.image})
        save_config(root,'runtime_settings.json',{'schema_version':1,'settings':{
            'context_tokens':16384,'max_output_tokens':512,'timeout_seconds':120,'thinking':False}})
        cid=create_chat(root,'OpenCode skills MCP smoke')['id']
        control=Control();control.access_policy=current(root);control.configuration=configuration(root)
        prompt=(f'Write the approved diagnostic report using smelter_write_diagnostic_markdown. '
                f'Filename: {FILENAME}. Content must be exactly this JSON string: {json.dumps(CONTENT)}. '
                'I approve this one report write. Call the tool once, then report its result. Do not use other tools.')
        bridge=AgentBridge(root,cid,prompt,skills=['documentation'],grants={'write_diagnostics':True},
                           policy=control.access_policy,control=control)
        with model_fixture(not args.live,'Maintain concise, accurate, version-controlled engineering documentation'):
            manager=process_fixture(base,root,target,bridge,args.opencode) if args.process_fixture else contextlib.nullcontext(None)
            with manager as client:
                result=ask(root,cid,prompt,model_key='local/qwen3.5:9b',approval=True,control=control,
                           agent_mode=True,bridge=bridge,client=client)
        if result['status']!='completed':raise ValueError('Agent task failed: '+result['reply'])
        saved=root/'diagnostics'/FILENAME
        if not saved.is_file() or saved.read_bytes()!=CONTENT.encode():raise ValueError('Saved report bytes do not match the requested content')
        execution=read_chat(root,cid)['messages'][-1]['execution']
        events=[event for event in execution['events'] if event.get('source')=='controller']
        if len(events)!=1 or events[0]['result']['status']!='written':raise ValueError('Missing or repeated controller write receipt')
        receipt=events[0]['result'];digest=hashlib.sha256(saved.read_bytes()).hexdigest()
        if receipt['sha256']!=digest:raise ValueError('Receipt hash does not match disk')
        if not Path(receipt['mcp_audit_path']).is_file():raise ValueError('Real MCP server audit is missing')
        if execution['skill_snapshots'][0]['sha256']!=hashlib.sha256(reference.encode()).hexdigest():raise ValueError('Selected skill snapshot differs')
        denied=AgentBridge(root,cid,'Denied action',policy=control.access_policy)
        denial=denied.call('write_diagnostic_markdown',{'filename':'denied.md','content':'must not exist'})
        if not denial['isError'] or (root/'diagnostics/denied.md').exists():raise ValueError('Unapproved write was not blocked')
        return {'status':'passed','opencode_required_version':VERSION,
                'model':'live qwen3.5:9b' if args.live else 'synthetic protocol fixture; no Qwen inference',
                'boundary':'managed no-network Docker container' if not args.process_fixture else 'explicit local process fixture; Docker not tested',
                'skills':execution['skill_snapshots'],'tool':events[0]['tool'],'transport':events[0]['transport'],
                'bytes':len(CONTENT.encode()),'sha256':digest,'independent_saved_bytes_check':True,
                'mcp_server_audit_checked':True,'chat_persistence_checked':True,'unapproved_write_denied':True,
                'cleanup_confirmed':execution['cleanup_confirmed'],'fixture_model_requests':len(ModelFixture.requests) if not args.live else None,
                'disposable_state_removed_on_exit':True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image',help='Existing immutable OpenCode Docker image ID; never pulled')
    parser.add_argument('--live',action='store_true',help='Use the existing local Qwen; requires --image')
    parser.add_argument('--process-fixture',action='store_true',help='Explicit real-process test without Docker or Qwen')
    parser.add_argument('--opencode',help='Existing executable path for --process-fixture')
    args=parser.parse_args()
    try:report=run(args)
    except Exception as exc:
        print(json.dumps({'status':'failed','error':str(exc)},indent=2));return 1
    print(json.dumps(report,indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
