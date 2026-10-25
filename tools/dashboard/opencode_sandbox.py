"""Managed no-network OpenCode container with a narrow local-model relay.

Container model requests use a tmpfs queue, polled over fixed Docker exec. No
container network, host credentials, socket mounts or host filesystem writes are
provided. The host relay reaches only the fixed loopback Ollama endpoint and
operator-selected model. Check/inspect sessions never submit a model prompt.
"""
import base64
import http.client
import json
import os
import re
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from process_runner import run
from sandbox import _flags,_remove,snapshot,status,record_owner
from tool_contract import BRIDGE_RPC_TIMEOUT

BOOT=r'''
const fs=require('node:fs'),http=require('node:http'),crypto=require('node:crypto'),cp=require('node:child_process');
const queue='/run/model-queue';fs.mkdirSync(queue,{recursive:true});
function taskGeneration(){try{return JSON.parse(fs.readFileSync('/run/smelter-task.json','utf8')).generation}catch{return null}}
const proxy=http.createServer((req,res)=>{
 if(![['POST','/v1/chat/completions'],['GET','/v1/models']].some(([method,path])=>method===req.method&&path===req.url)){res.writeHead(403);return res.end('Denied model route')}
 const generation=taskGeneration();let bytes=0,parts=[];
 req.on('data',chunk=>{bytes+=chunk.length;if(bytes>2*1024*1024){res.writeHead(413);res.end('Request too large');req.destroy()}else parts.push(chunk)});
 req.on('end',()=>{if(bytes>2*1024*1024)return;const id=crypto.randomUUID(),input=queue+'/'+id+'.request',output=queue+'/'+id+'.response';fs.writeFileSync(input,JSON.stringify({id,generation,path:req.url,method:req.method,body:Buffer.concat(parts).toString('base64')}),{flag:'wx'});
 const limit=Date.now()+Number(process.env.SMELTER_TIMEOUT)*1000;
 const timer=setInterval(()=>{if(fs.existsSync(output)){try{const r=JSON.parse(fs.readFileSync(output));fs.unlinkSync(output);clearInterval(timer);res.writeHead(r.status,{'content-type':r.content_type});res.end(Buffer.from(r.body,'base64'))}catch(error){clearInterval(timer);res.writeHead(502);res.end('Relay failure')}}else if(Date.now()>limit){clearInterval(timer);res.writeHead(504);res.end('Model relay timed out')}},100);
 res.on('close',()=>{clearInterval(timer);for(const file of [input,output])try{fs.unlinkSync(file)}catch{}});
 });
});
proxy.listen(11434,'127.0.0.1',()=>{
 const config={provider:{local:{npm:'@ai-sdk/openai-compatible',name:'SMELTER confined local model',options:{baseURL:'http://127.0.0.1:11434/v1',apiKey:'local'},models:{[process.env.SMELTER_MODEL]:{name:process.env.SMELTER_MODEL}}}}};
 // The RPC envelope includes the longest registered host operation and cleanup.
 if(process.env.SMELTER_BRIDGE==='1') config.mcp={smelter:{type:'local',command:['node','/opt/smelter-bridge/proxy.mjs'],enabled:true,timeout:__SMELTER_MCP_RPC_TIMEOUT_MS__}};
 const child=cp.spawn('/usr/local/bin/opencode',['serve','--pure','--hostname','127.0.0.1','--port','4096'],{cwd:'/workspace',env:{...process.env,OPENCODE_CONFIG_CONTENT:JSON.stringify(config),OPENCODE_SERVER_PASSWORD:process.env.SMELTER_AGENT_PASSWORD},stdio:'inherit'});
 child.on('error',()=>process.exit(1));child.on('exit',code=>process.exit(code??1));
 // Server lifetime follows the whole task; SMELTER_TIMEOUT bounds each relayed model turn.
 setTimeout(()=>process.exit(124),(Number(process.env.SMELTER_TASK_TIMEOUT)+30)*1000).unref();
});
'''

REQUEST=r'''
const http=require('node:http');let input='';process.stdin.on('data',c=>input+=c);process.stdin.on('end',()=>{const r=JSON.parse(input);const request=http.request({host:'127.0.0.1',port:4096,path:r.path,method:r.method,headers:r.headers,timeout:8000},response=>{let bytes=0,parts=[];response.on('data',c=>{bytes+=c.length;if(bytes>4*1024*1024)process.exit(2);parts.push(c)});response.on('end',()=>console.log(JSON.stringify({status:response.statusCode,body:Buffer.concat(parts).toString('base64')})))});request.on('error',()=>process.exit(3));request.on('timeout',()=>request.destroy());if(r.body)request.write(JSON.stringify(r.body));request.end()});
'''
QUEUE=r'''
const fs=require('node:fs'),dir='/run/model-queue';let result=null;if(fs.existsSync(dir)){for(const name of fs.readdirSync(dir).slice(0,128)){if(!/^[a-f0-9-]{36}\.request$/.test(name))continue;const path=dir+'/'+name;if(fs.statSync(path).size>3*1024*1024)process.exit(2);result=JSON.parse(fs.readFileSync(path));fs.unlinkSync(path);break}}console.log(JSON.stringify(result));
'''
RESPOND=r'''
const fs=require('node:fs');let input='';process.stdin.on('data',c=>input+=c);process.stdin.on('end',()=>{const value=JSON.parse(input);if(!/^[a-f0-9-]{36}$/.test(value.id))process.exit(2);const output='/run/model-queue/'+value.id+'.response',pending=output+'.pending';fs.writeFileSync(pending,JSON.stringify(value.response),{flag:'wx'});fs.renameSync(pending,output)});
'''
BIND_TASK=r'''
const fs=require('node:fs');let input='';process.stdin.on('data',c=>input+=c);process.stdin.on('end',()=>{const value=JSON.parse(input);if(value.generation!==null&&!/^[a-f0-9]{32}$/.test(value.generation))process.exit(2);const target='/run/smelter-task.json',pending=target+'.pending';fs.writeFileSync(pending,JSON.stringify(value),{flag:'w'});fs.renameSync(pending,target)});
'''


class ManagedClient:
    expected_directory='/workspace'
    confined=True

    def __init__(self,root,policy,configuration,control=None,allow_inference=False,bridge=None,lifetime=None):
        import secrets
        import shutil
        ready=status(root,operation='opencode')
        if not ready['ready']:raise ValueError('Confined OpenCode unavailable: '+ready['reason'])
        from access_policy import using
        # Readiness and every task use the current checkout as their immutable
        # source reference. Live destinations are read through approved tools.
        self.root=Path(root);self.host_directory=Path(root).resolve()
        with using(policy):self.folder,self.code=snapshot(root,self.host_directory)
        self.docker=ready['docker'];self.name='smelter-opencode-'+__import__('uuid').uuid4().hex
        self.model=configuration['model'];self.settings=configuration['runtime'];self.control=None;self.allow_inference=allow_inference
        self.bridge=None;self.task_generation=None;self.accepting=False;self.active_responses=0
        self.password=secrets.token_urlsafe(32);self.stop_event=threading.Event();self.thread=None;self.model_socket=None;self.lock=threading.Lock();self.closed=False;self.error=None;self.model_calls=0;self.relay_calls=0;self.cleanup_confirmed=None
        self.quiescent=threading.Condition(self.lock)
        task_timeout=max(self.settings.get('opencode_timeout_seconds',self.settings['timeout_seconds']),self.settings['timeout_seconds'])
        # A persistent session (opencode_pool) outlives single tasks; each task keeps its own deadline.
        if lifetime:task_timeout=max(task_timeout,int(lifetime))
        environment=dict(os.environ);environment.update(SMELTER_MODEL=self.model,SMELTER_TIMEOUT=str(self.settings['timeout_seconds']),SMELTER_TASK_TIMEOUT=str(task_timeout),SMELTER_AGENT_PASSWORD=self.password)
        flags=_flags(self.docker,self.name,self.code)
        if bridge and bridge.tools:
            assets=self.folder/'bridge';assets.mkdir(mode=0o755)
            proxy=Path(__file__).with_name('opencode_mcp_proxy.mjs').read_bytes()
            (assets/'proxy.mjs').write_bytes(proxy)
            (assets/'tools.json').write_text(json.dumps(bridge.manifest(self.settings['timeout_seconds'])),encoding='utf-8')
            for item in assets.iterdir():item.chmod(0o644)
            flags+=['--mount','type=bind,source='+str(assets)+',target=/opt/smelter-bridge,readonly']
            environment['SMELTER_BRIDGE']='1'
        else:environment['SMELTER_BRIDGE']='0'
        boot=BOOT.replace('__SMELTER_MCP_RPC_TIMEOUT_MS__', str(BRIDGE_RPC_TIMEOUT*1000))
        command=flags+['--detach','--env','SMELTER_MODEL','--env','SMELTER_TIMEOUT','--env','SMELTER_TASK_TIMEOUT','--env','SMELTER_AGENT_PASSWORD','--env','SMELTER_BRIDGE',ready['configured']['opencode_image'],'node','-e',boot]
        self.image=ready['configured']['opencode_image']
        record_owner(self.folder,self.name,self.image,'opencode')
        try:
            run(command,env=environment,timeout=15,check=True,max_output=16384)
            self.thread=threading.Thread(target=self._relay,daemon=True);self.thread.start()
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                try:
                    if self.request('/global/health').get('healthy') is True:break
                except (ValueError,OSError):time.sleep(.2)
            else:raise ValueError('Confined OpenCode server did not become healthy')
            if control is not None:self.attach(control,bridge)
        except Exception:self.close();raise

    def attach(self,control,bridge):
        """Bind one task's control and tool bridge to a persistent session."""
        generation=__import__('uuid').uuid4().hex if control is not None else None
        with self.lock:
            if self.closed or self.active_responses:raise ValueError('Previous OpenCode relay has not finished')
            self.accepting=False
            self._exec(BIND_TASK,{'generation':generation},maximum=16384)
            self.control=control;self.bridge=bridge;self.task_generation=generation
            self.model_calls=0;self.relay_calls=0;self.accepting=control is not None

    def detach(self):
        """Revoke new packets, then retain ownership until active actions settle."""
        with self.lock:
            self.accepting=False;self.task_generation=None
            bridge=self.bridge
        try:self._exec(BIND_TASK,{'generation':None},maximum=16384)
        except (ValueError,OSError,__import__('subprocess').SubprocessError):
            self.error='OpenCode task revocation was not confirmed'
            return False
        if bridge:bridge.close()
        timeout=bridge.cleanup_wait_timeout() if bridge else self.settings['timeout_seconds']+15
        deadline=time.monotonic()+timeout
        with self.quiescent:
            while self.active_responses:
                remaining=deadline-time.monotonic()
                if remaining<=0:
                    self.error='Previous OpenCode relay did not settle; cleanup is required'
                    return False
                self.quiescent.wait(remaining)
            self.control=None;self.bridge=None
        return True

    @contextmanager
    def _task(self,item):
        """A packet belongs to exactly one attached task, never its successor."""
        with self.lock:
            if (not self.allow_inference or not self.accepting or self.control is None or getattr(self.control,'completed',False) or
                    self.closed or self.stop_event.is_set()):
                raise ValueError('Model/tool actions require an active admitted OpenCode task')
            if item.get('generation')!=self.task_generation:
                raise ValueError('Stale OpenCode task packet was rejected')
            control,bridge=self.control,self.bridge
            control.check()
            self.active_responses+=1
        try:yield control,bridge
        finally:
            with self.quiescent:
                self.active_responses-=1;self.quiescent.notify_all()

    def refresh(self,policy):
        """Replace the mounted code snapshot in place before the next task.

        A fresh snapshot is built with the usual filters and budgets, then moved
        into the folder the container already mounts read-only.
        """
        import shutil
        from access_policy import using
        with using(policy):folder,code=snapshot(self.root,self.host_directory)
        try:
            for entry in list(self.code.iterdir()):
                if entry.name=='.smelter':continue
                if entry.is_dir() and not entry.is_symlink():shutil.rmtree(entry)
                else:entry.unlink()
            for entry in list(code.iterdir()):
                if entry.name!='.smelter':shutil.move(str(entry),str(self.code/entry.name))
        finally:shutil.rmtree(folder,ignore_errors=True)

    def _exec(self,script,payload=None,maximum=8*1024*1024):
        args=[self.docker,'exec']+(['--interactive'] if payload is not None else [])+[self.name,'node','-e',script]
        return run(args,input=json.dumps(payload).encode() if payload is not None else None,timeout=12,max_output=maximum,check=True)

    def request(self,path,method='GET',body=None,timeout=3):
        if not isinstance(path,str) or not path.startswith('/') or path.startswith('//') or len(path)>4096:raise ValueError('Invalid confined OpenCode request')
        if self.error and not path.endswith('/abort'):raise ValueError(self.error)
        if method not in ('GET','POST'):raise ValueError('Unsupported agent method')
        headers={'Content-Type':'application/json','x-opencode-directory':'/workspace',
                 'Authorization':'Basic '+base64.b64encode(('opencode:'+self.password).encode()).decode()}
        try:
            maximum=8*1024*1024 if path=='/provider' and method=='GET' else 4*1024*1024
            script=REQUEST.replace('bytes>4*1024*1024','bytes>'+str(maximum))
            result=json.loads(self._exec(script,{'path':path,'method':method,'body':body,'headers':headers},maximum=maximum*2).stdout)
            raw=base64.b64decode(result['body'],validate=True)
            if result['status'] not in (200,201,202,204):raise ValueError('Confined OpenCode HTTP '+str(result['status']))
            return json.loads(raw) if raw.strip() else None
        except (__import__('subprocess').SubprocessError,OSError) as exc:raise ValueError('Confined OpenCode request failed') from exc

    def _response(self,item):
        if item.get('kind') == 'mcp':
            with self._task(item) as (control,bridge):
                if bridge is None:raise ValueError('MCP tool actions were not approved for this session')
                try:result=bridge.call(item.get('name'),item.get('arguments'))
                except ValueError as exc:
                    result={'content':[{'type':'text','text':str(exc)[:1000]}],'isError':True}
                return {'mcp_result':result}
        route=item.get('path');method=item.get('method')
        if (method,route) not in (('GET','/v1/models'),('POST','/v1/chat/completions')):raise ValueError('Denied model relay route')
        raw=base64.b64decode(item.get('body',''),validate=True)
        if len(raw)>2*1024*1024:raise ValueError('Model relay input exceeds budget')
        if method=='POST':
            if not self.allow_inference:raise ValueError('Model inference was not approved for this inspection session')
            with self._task(item) as (control,bridge):
                self.model_calls+=1
                if self.model_calls>24:raise ValueError('Confined model request budget exhausted')
                body=json.loads(raw)
                if not isinstance(body,dict) or body.get('model')!=self.model:raise ValueError('Only the admitted local model may be requested')
                requested=body.get('max_tokens',self.settings['max_output_tokens'])
                if type(requested) is not int or requested<1:raise ValueError('Invalid model output limit')
                body['max_tokens']=min(requested,self.settings['max_output_tokens'])
                return self._native_response(body,control)
        connection=http.client.HTTPConnection('127.0.0.1',11434,timeout=3)
        cancel_socket=None
        try:
            connection.connect();connection.sock.settimeout(self.settings['timeout_seconds'])
            cancel_socket=connection.sock.dup()
            with self.lock:self.model_socket=cancel_socket
            # Discovery has no task ownership and cannot borrow a successor's control.
            connection.request(method,route,body=raw if method=='POST' else None,headers={'Content-Type':'application/json'})
            response=connection.getresponse();output=response.read(2*1024*1024+1)
            if len(output)>2*1024*1024:raise ValueError('Local model response exceeded relay budget')
            content_type=response.getheader('Content-Type','application/json')
            if content_type.split(';')[0] not in ('application/json','text/event-stream'):raise ValueError('Unexpected local model response type')
            return {'status':response.status,'content_type':content_type,'body':base64.b64encode(output).decode()}
        finally:
            with self.lock:self.model_socket=None
            if cancel_socket:cancel_socket.close()
            connection.close()

    def _native_response(self,body,control):
        """Translate SDK chat to native Ollama so saved context/output limits apply."""
        if not isinstance(body.get('messages'),list):raise ValueError('Invalid model messages')
        messages=[];tool_names={}
        for original in body.get('messages',[]):
            if not isinstance(original,dict):raise ValueError('Invalid model message')
            role=original.get('role');content=original.get('content') or ''
            if isinstance(content,list):
                if any(not isinstance(part,dict) or part.get('type')!='text' for part in content):raise ValueError('Confined source inspection supports text content only')
                if any(not isinstance(part.get('text',''),str) for part in content):raise ValueError('Invalid text part')
                content='\n'.join(part.get('text','') for part in content)
            if role not in ('system','developer','user','assistant','tool') or not isinstance(content,str):raise ValueError('Invalid model message role/content')
            message={'role':'system' if role=='developer' else role,'content':content}
            if original.get('tool_calls'):
                calls=[]
                for call in original['tool_calls']:
                    if not isinstance(call,dict) or not isinstance(call.get('function'),dict):raise ValueError('Invalid tool-call history')
                    function=call['function'];arguments=function.get('arguments',{})
                    if isinstance(arguments,str):arguments=json.loads(arguments)
                    if not isinstance(arguments,dict) or not isinstance(function.get('name'),str):raise ValueError('Invalid tool-call history')
                    if not isinstance(call.get('id'),str):raise ValueError('Invalid tool-call identity')
                    tool_names[call['id']]=function['name'];calls.append({'function':{'name':function['name'],'arguments':arguments}})
                message['tool_calls']=calls
            if role=='tool':
                if not isinstance(original.get('tool_call_id'),str):raise ValueError('Invalid tool result identity')
                name=tool_names.get(original['tool_call_id'])
                if not name:raise ValueError('Tool result has no matching call')
                message['tool_name']=name
            messages.append(message)
        tools=body.get('tools')
        if tools is not None and not isinstance(tools,list):raise ValueError('Invalid model tool schemas')
        from context_budget import bounded
        messages,budget=bounded(messages,tools,self.settings['context_tokens'],body['max_tokens'])
        control.tool_call_limit=24-self.model_calls+1;control.context_budget=budget
        request={'model':self.model,'messages':messages,'think':False if tools else self.settings['thinking'],
                 'options':{'num_ctx':self.settings['context_tokens'],'num_predict':body['max_tokens']}}
        if tools:request['tools']=tools
        result=json.loads(control.infer(request,self.settings['timeout_seconds'],2*1024*1024))
        if not isinstance(result,dict):raise ValueError('Invalid local model response')
        message=result.get('message',{})
        if not isinstance(message,dict) or not isinstance(message.get('content',''),str):raise ValueError('Invalid local model message')
        answer={'role':'assistant','content':message.get('content','')}
        calls=message.get('tool_calls',[])
        if not isinstance(calls,list) or any(not isinstance(call,dict) or not isinstance(call.get('function'),dict) or not isinstance(call['function'].get('name'),str) or not isinstance(call['function'].get('arguments'),dict) for call in calls):raise ValueError('Invalid local model tool calls')
        if calls:
            answer['tool_calls']=[{'id':'call_'+__import__('uuid').uuid4().hex,'type':'function','function':{'name':c['function']['name'],'arguments':json.dumps(c['function']['arguments'])}} for c in calls]
        finish='tool_calls' if calls else 'length' if result.get('done_reason')=='length' else 'stop'
        value={'id':'chatcmpl-smelter-'+__import__('uuid').uuid4().hex,'created':int(time.time()),'model':self.model}
        if body.get('stream'):
            delta={**answer}
            if calls:delta['tool_calls']=[{'index':i,**c} for i,c in enumerate(answer['tool_calls'])]
            first={**value,'object':'chat.completion.chunk','choices':[{'index':0,'delta':delta,'finish_reason':None}]}
            last={**value,'object':'chat.completion.chunk','choices':[{'index':0,'delta':{},'finish_reason':finish}]}
            raw=('data: '+json.dumps(first)+'\n\ndata: '+json.dumps(last)+'\n\ndata: [DONE]\n\n').encode();kind='text/event-stream'
        else:
            raw=json.dumps({**value,'object':'chat.completion','choices':[{'index':0,'message':answer,'finish_reason':finish}]}).encode();kind='application/json'
        return {'status':200,'content_type':kind,'body':base64.b64encode(raw).decode()}

    def _relay(self):
        try:
            while not self.stop_event.is_set():
                item=json.loads(self._exec(QUEUE,maximum=4*1024*1024).stdout)
                if item:
                    self.relay_calls+=1
                    if self.relay_calls>128:raise ValueError('Agent relay packet budget exhausted')
                    if not isinstance(item,dict) or not isinstance(item.get('id'),str) or not re.fullmatch(r'[a-f0-9-]{36}',item['id']):raise ValueError('Invalid model relay packet')
                    response=self._response(item)
                    if not self.stop_event.is_set():self._exec(RESPOND,{'id':item['id'],'response':response},maximum=16384)
                self.stop_event.wait(.15)
        except (ValueError,TypeError,KeyError,OSError,__import__('subprocess').SubprocessError,__import__('chat_jobs').ChatCancelled) as exc:
            if not self.stop_event.is_set():self.error='Confined model relay failed: '+str(exc)[:300]

    def close(self):
        if self.closed and self.cleanup_confirmed:return True
        self.closed=True;self.stop_event.set()
        with self.lock:self.accepting=False;self.task_generation=None
        if getattr(self,'bridge',None):self.bridge.close()
        with self.lock:
            if self.model_socket:
                try:self.model_socket.shutdown(__import__('socket').SHUT_RDWR)
                except OSError:pass
        if self.control:
            with self.control.lock:
                if self.control.sock:
                    try:self.control.sock.shutdown(__import__('socket').SHUT_RDWR)
                    except OSError:pass
        record_owner(self.folder,self.name,self.image,'opencode',finished=True)
        self.cleanup_confirmed=_remove(self.docker,self.name)
        if self.thread and self.thread is not threading.current_thread():
            # This runs in the task worker, not the Stop HTTP handler. A host
            # MCP operation already admitted before Stop has its own 120s
            # transport bound; retain its final receipt before persistence.
            active=bool(getattr(self,'bridge',None) and self.bridge.active.is_set())
            self.thread.join(timeout=self.bridge.cleanup_wait_timeout() if active else 15)
            if self.thread.is_alive():self.cleanup_confirmed=False
        import shutil
        if self.cleanup_confirmed:
            with self.lock:self.control=None;self.bridge=None
            shutil.rmtree(self.folder,ignore_errors=True)
        return self.cleanup_confirmed
