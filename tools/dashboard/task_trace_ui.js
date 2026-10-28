/* Read-only task trace over an authenticated same-origin WebSocket. */
const SmelterTaskTrace=(()=>{
 const labels={telemetry_delayed:'Telemetry delayed',waiting_access:'Waiting for access',waiting_answer:'Waiting for answer',tool_budget_exhausted:'Tool budget exhausted',waiting_child:'Waiting for delegated task',awaiting_model:'Waiting for model',using_tool:'Using tools',completed:'Response ended',cancelled:'Cancelled',failed:'Failed',unknown:'Unknown'};
 const el=(doc,tag,text)=>{const node=doc.createElement(tag);if(text!==undefined)node.textContent=text;return node};
 const age=seconds=>seconds==null?'unknown':seconds<60?seconds+'s':Math.floor(seconds/60)+'m '+seconds%60+'s';
 function render(data,host,doc=document,compact=false,feed='connected'){
  const expanded=new Map([...(host.querySelectorAll?.('details')||[])].map(n=>[n.getAttribute('data-trace-section'),n.open])),scroll=host.scrollTop;
  host.replaceChildren();
  const status=data?.status||{},phase=labels[status.phase]||status.phase||'Connecting';
  host.append(el(doc,'h3','Live task · '+(data?.available?phase:'Telemetry unavailable')));
  const transport=el(doc,'p','WebSocket: '+feed+' · Observer: '+(data?.observed_at?new Date(data.observed_at).toLocaleTimeString():'waiting'));
  transport.setAttribute('role','status');host.append(transport);
  if(!data?.available){host.append(el(doc,'p',data?.reason||'Waiting for the first task snapshot.'));return}
  host.append(el(doc,'p','Task ID: '+(data.task_id||'no submitted turn')+' · '+data.task_id_source));
  if(data.binding.melty_task_id)host.append(el(doc,'small','Native turn ID: '+data.native_turn_id));
  const validation=data.validation||[];
  host.append(el(doc,'p','Validation receipts: '+(validation.map(t=>t.profile+' '+t.stage+' ('+(t.current?'current tree':'stale tree')+')'+(t.acceptance_stage?' · editable tests '+t.workspace_tests_stage+' / frozen acceptance '+t.acceptance_stage:'')).join(', ')||'none observed')));
  if(status.outcome_hint){const outcome=el(doc,'p','Task outcome · '+status.task_outcome.replaceAll('_',' ')+' · '+status.outcome_hint);outcome.setAttribute('role','status');host.append(outcome)}
  if(status.phase==='completed')host.append(el(doc,'small','The assistant response ended. Task success depends on current receipts and acceptance coverage.'));
  if(status.recovery_redirect){const recovery=el(doc,'p','Recovery checkpoint · '+status.recovery_hint);recovery.setAttribute('role','status');recovery.style.color='var(--warning, #e9ba68)';host.append(recovery)}
  const alert=el(doc,'p',(status.possible_stall?'⚠ Possible stall · ':'')+(status.hint||phase)+' · Last native activity '+age(status.quiet_seconds)+' ago');
  alert.setAttribute('role',status.possible_stall||status.phase==='waiting_access'?'alert':'status');
  alert.style.color=status.possible_stall||status.phase==='waiting_access'?'var(--warning, #e9ba68)':'var(--muted)';host.append(alert);
  const active=data.tools.filter(t=>['pending','running'].includes(t.phase)),model=data.sessions.find(s=>s.model),terminal=['completed','cancelled','failed'].includes(status.phase);
  const flow=el(doc,'div');flow.style.display='flex';flow.style.flexWrap='wrap';flow.style.gap='8px';flow.setAttribute('aria-label','Task component flow');
  const components=[['Melty',data.binding.melty_task_id?'ID linked':'native session linked'],['OpenCode',phase],['Ollama',data.ollama.connection],['Model',model?.model||'not observed'],['SMELTER',active.some(t=>t.tool.startsWith('smelter_'))&&!terminal?'tool active':'observing'],['Skills',data.skills.join(', ')||'none observed this turn'],['Tools',terminal?'turn ended':active.map(t=>t.tool).join(', ')||'no active call']];
  for(const [name,state] of components){const card=el(doc,'div'),highlight=!terminal&&(['OpenCode','Tools'].includes(name)||['Ollama','Model'].includes(name)&&status.phase==='awaiting_model'||name==='SMELTER'&&active.some(t=>t.tool.startsWith('smelter_')));Object.assign(card.style,{padding:'8px 10px',border:'1px solid '+(highlight?'var(--accent)':'var(--border)'),borderRadius:'8px',flex:'1 1 115px',overflowWrap:'anywhere'});card.append(el(doc,'strong',name),el(doc,'div',state));flow.append(card)}host.append(flow);
  const links=el(doc,'small','Flow: Melty → OpenCode → Ollama → model; OpenCode → SMELTER skills/tools → files. Components may overlap.');host.append(links);
  for(const pending of data.permissions){const row=el(doc,'p','Access requested · '+pending.kind+' · '+pending.paths.join(', ')+' · Session '+pending.session_id);row.setAttribute('role','alert');host.append(row)}
  for(const pending of data.questions||[])host.append(el(doc,'p','Answer requested in native client · Session '+pending.session_id));
  if(!terminal)for(const tool of active.slice(0,compact?2:8)){const seconds=Math.max(0,Math.floor((Date.now()-Date.parse(tool.started_at||tool.updated_at))/1000));host.append(el(doc,'p','Current operation: '+tool.tool+' · '+tool.phase+' · '+age(Number.isFinite(seconds)?seconds:null)+' · '+tool.session_id))}
  if(data.permission_source==='unavailable')host.append(el(doc,'small','Native permission feed unavailable; a quiet tool may be waiting for access.'));
  const fileMap=new Map();for(const tool of data.tools)if(tool.file&&!fileMap.has(tool.file))fileMap.set(tool.file,tool);
  const files=[...fileMap.values()].slice(0,compact?3:20);
  const section=el(doc,'div');section.append(el(doc,'h4','File activity'));
  if(!files.length)section.append(el(doc,'p','No named file activity observed this turn. Shell command contents are not inspected.'));
  for(const tool of files){const row=el(doc,'div');row.title=tool.file;Object.assign(row.style,{overflowWrap:'anywhere',padding:'8px 0'});row.append(el(doc,'strong',tool.file.split(/[\\/]/).at(-1)),el(doc,'div',tool.tool+' · '+tool.phase));
   if(!compact){row.append(el(doc,'div',tool.file));if(tool.indexed_sha256){row.append(el(doc,'small','Indexed SHA-256: '+tool.indexed_sha256+' · Index captured '+tool.index_updated_at))}}section.append(row)}host.append(section);
  if(!compact){
   const tasks=el(doc,'details');tasks.setAttribute('data-trace-section','sessions');tasks.open=expanded.get('sessions')??true;tasks.append(el(doc,'summary','Sessions and delegated tasks ('+data.sessions.length+')'));
   for(const session of data.sessions)tasks.append(el(doc,'p',session.session_id+' · '+(data.permissions.some(p=>p.session_id===session.session_id)?'waiting for access':session.state)+' · '+(session.agent||'agent not reported')+' · '+(session.provider||'provider not reported')+(session.parent_id?' · parent '+session.parent_id:'')));host.append(tasks);
   const timeline=el(doc,'details');timeline.setAttribute('data-trace-section','timeline');timeline.open=expanded.get('timeline')??false;timeline.append(el(doc,'summary','Recent tool activity'));const list=el(doc,'ol');
   for(const tool of data.tools.slice(0,40)){list.append(el(doc,'li',tool.tool+' · '+tool.phase+(tool.error_code?' · '+tool.error_code:'')+' · '+new Date(tool.updated_at).toLocaleTimeString()+' · '+tool.session_id))}timeline.append(list);host.append(timeline);
   const loaded=el(doc,'small','Loaded models: '+(data.ollama.loaded_models.map(m=>m.name+(m.context_length?' ('+m.context_length+' context)':'')).join(', ')||'none')+' · '+data.ollama.scope);loaded.style.display='block';host.append(loaded);
   const identity=el(doc,'small','Session '+data.binding.session_id+' · Workspace '+data.binding.workspace_id+' · '+data.workspace_root);Object.assign(identity.style,{display:'block',overflowWrap:'anywhere'});host.append(identity);
  }
  if(scroll!==undefined)host.scrollTop=scroll;
 }
 function mount(doc=document,ready=()=>true,environment=window,api=null){
  const settings=SmelterSettings.current;if(!settings)return;
  // One socket feeds the compact card, the settings panel and the optional workbench.
  let workbench=null;const openWorkbench=()=>{if(typeof SmelterTraceWorkbench==='undefined')return;if(doc.getElementById('settingsDialog')?.open)doc.getElementById('settingsDialog').close();workbench??=SmelterTraceWorkbench.create(doc,api);workbench.update(data,feed,lastFrame);workbench.open()};
  const panel=el(doc,'section'),body=el(doc,'div'),launch=el(doc,'button','Open trace workbench');launch.onclick=openWorkbench;panel.append(el(doc,'p','Watch component activity, files and native access waits. Configure the exact session in Native task progress.'),launch,body);
  settings.addPanel('taskTracePanel','Live task trace',panel,'Debugging');
  const card=el(doc,'section');card.className='task-trace-card';Object.assign(card.style,{margin:'10px 18px',padding:'12px',border:'1px solid var(--border)',borderRadius:'12px',background:'var(--surface)',maxHeight:'43vh',overflow:'auto',flexShrink:'0'});
  const log=doc.getElementById('chatlog');log?.parentNode.insertBefore(card,log);
  let socket=null,timer=null,disposed=false,attempt=0,lastFrame=0,data=null,feed='connecting';
  function show(){card.hidden=!data?.binding;render(data,body,doc,false,feed);workbench?.update(data,feed,lastFrame);if(data?.binding){render(data,card,doc,true,feed);const button=el(doc,'button','Open live task trace');button.onclick=()=>settings.open('taskTracePanel');const buttons=[button];if(typeof SmelterTraceWorkbench!=='undefined'){const graph=el(doc,'button','Open trace workbench');graph.onclick=openWorkbench;buttons.unshift(graph)}
   // Keep the actions under the heading so they stay reachable in a long, scrolling card.
   const after=card.children?.[1];for(const b of buttons.reverse())after&&card.insertBefore?card.insertBefore(b,card.children[1]):card.append(b)}}
  function connect(){
   if(disposed)return;if(!ready()){timer=environment.setTimeout(connect,1000);return}
   const secret=SmelterAuth.token(environment.location);if(!secret){feed='authorization required';show();timer=environment.setTimeout(connect,3000);return}
   const protocol=environment.location.protocol==='https:'?'wss:':'ws:';
   socket=new environment.WebSocket(protocol+'//'+environment.location.host+'/api/task-trace/ws',['smelter.trace.v1','smelter.auth.'+secret]);
   socket.onopen=()=>{feed='connected';attempt=0;lastFrame=Date.now();show()};
   socket.onmessage=event=>{try{const frame=JSON.parse(event.data);if(frame.type!=='task.snapshot')return;lastFrame=Date.now();data=frame.trace;feed='connected';show()}catch{feed='invalid snapshot';show()}};
   socket.onclose=()=>{if(disposed)return;feed='disconnected; reconnecting';show();timer=environment.setTimeout(connect,Math.min(20000,1000*2**Math.min(attempt++,5)))};
   socket.onerror=()=>{feed='connection error';show()};
  }
  const watchdog=environment.setInterval(()=>{if(lastFrame&&Date.now()-lastFrame>12000&&socket?.readyState===1){feed='stale feed; reconnecting';show();socket.close()}},3000);
  connect();return{open:openWorkbench,dispose(){disposed=true;workbench?.dispose();environment.clearTimeout(timer);environment.clearInterval(watchdog);socket?.close()}};
 }
 return{render,mount,age};
})();
if(typeof module!=='undefined')module.exports=SmelterTaskTrace;
