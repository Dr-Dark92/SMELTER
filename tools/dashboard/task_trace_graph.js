/* Relationship projection and interactive SVG graph for the read-only task trace.
   project() turns one trace snapshot into stable nodes and evidence-labelled edges.
   Nothing here requests data, controls tasks or renders remote text as markup. */
const SmelterTraceGraph=(()=>{
 const LANES=['Task identity','Agent runtime','Services & skills','Operations','Files & evidence'];
 const TERMINAL=new Set(['completed','cancelled','failed']);
 const EVIDENCE={observed:'Observed at runtime',binding:'Explicit binding / configuration',inferred:'Inferred (naming or expected path)'};
 const DASH={observed:'',binding:'9 5',inferred:'2 5'};
 const VERBS={read:'read path',edit:'edited path',write:'wrote path',glob:'searched under path',grep:'searched under path',smelter_read_coding_file:'read coding file'};
 const MAX_FILES=40,MAX_TOOL_GROUPS=40,MAX_SESSIONS=16;
 const W=196,H=46,COL=236,ROW=60,PAD=36;
 // Busy lanes use two fixed sub-columns so slots never move when a lane grows.
 const COLUMNS=[1,1,1,2,2],LANE_X=COLUMNS.map((_,i)=>PAD+COLUMNS.slice(0,i).reduce((a,b)=>a+b,0)*COL);
 const short=(value,size=26)=>{value=String(value??'');return value.length>size?value.slice(0,size-1)+'…':value};
 const slash=path=>String(path).replaceAll('\\','/');
 // Windows paths are case-insensitive; identity folds case, display keeps the original.
 function fileIdentity(file,root,workspace){
  const path=slash(file),base=slash(root||'').replace(/\/+$/,'');
  const inside=base&&path.toLowerCase().startsWith(base.toLowerCase()+'/');
  const relative=inside?path.slice(base.length+1):path;
  return {id:'file:'+(workspace||'unbound')+':'+relative.toLowerCase(),relative,inside}
 }
 function seconds(from,to){const a=Date.parse(from),b=Date.parse(to);return Number.isFinite(a)&&Number.isFinite(b)?Math.max(0,Math.round((b-a)/1000)):null}
 function project(data,options={}){
  const now=options.now||new Date().toISOString(),nodes=new Map(),edges=new Map(),notes=[];
  const node=(id,fields)=>{const current=nodes.get(id);if(current)return Object.assign(current,fields);const value={id,state:'idle',detail:{},...fields};nodes.set(id,value);return value};
  const edge=(source,target,relation,evidence,extra={})=>{if(!nodes.has(source)||!nodes.has(target))return;const id=source+'→'+target+'·'+relation;if(!edges.has(id))edges.set(id,{id,source,target,relation,evidence,...extra})};
  if(!data?.available)return {nodes:[],edges:[],notes:[data?.reason||'No task snapshot yet.'],identity:null,truncated:false};
  const status=data.status||{},binding=data.binding||{},phase=status.phase||'unknown',terminal=TERMINAL.has(phase);
  const sessions=(data.sessions||[]).slice(0,MAX_SESSIONS),tools=data.tools||[],workspace=binding.workspace_id;
  const pendingAccess=new Set((data.permissions||[]).map(p=>p.session_id)),pendingAnswer=new Set((data.questions||[]).map(q=>q.session_id));
  node('task',{kind:'task',lane:0,label:'Task '+short(data.task_id||'no submitted turn',20),state:terminal?'done':'active',
   detail:{'Task ID':data.task_id||'No submitted turn observed','ID source':data.task_id_source,'Native turn ID':data.native_turn_id||'not observed','Turn started':data.turn_started_at||'unknown','Response lifecycle':phase,'Task outcome':status.task_outcome||'in_progress'}});
  node('melty',{kind:'component',lane:0,label:'Melty',state:binding.melty_task_id?'linked':'unknown',
   detail:{'Melty task ID':binding.melty_task_id||'Not supplied — automatic Melty task IDs are not integrated','Observation':'Melty is not observed directly; the native session was bound explicitly.'}});
  node('opencode',{kind:'component',lane:1,label:'OpenCode',state:terminal?'done':pendingAccess.size||pendingAnswer.size?'waiting':'active',
   detail:{'Bound session':binding.session_id,'Directory':binding.directory||'not reported','Response lifecycle':phase,'Configuration revision':data.configuration_revision||'unknown'}});
  edge('melty','opencode',binding.melty_task_id?'Melty task ID correlated with this session':'native session bound for this task','binding');
  const providers=[...new Set(sessions.map(s=>s.provider).filter(Boolean))],loaded=data.ollama?.loaded_models||[];
  node('ollama',{kind:'service',lane:2,label:'Ollama',state:data.ollama?.connection==='connected'?(phase==='awaiting_model'?'waiting':'idle'):'unknown',
   detail:{'Connection':data.ollama?.connection||'unknown','Loaded models (host-wide)':loaded.map(m=>m.name+(m.context_length?' · '+m.context_length+' context':'')).join(', ')||'none','Scope':data.ollama?.scope||'host-wide','Providers reported by sessions':providers.join(', ')||'none reported'}});
  if(providers.some(p=>/ollama/i.test(p)))edge('opencode','ollama','provider reported by assistant message','observed');
  else edge('opencode','ollama','expected provider path (no provider reported)','inferred');
  const smelterTools=tools.filter(t=>String(t.tool).startsWith('smelter_'));
  node('smelter',{kind:'component',lane:2,label:'SMELTER',state:!terminal&&smelterTools.some(t=>['pending','running'].includes(t.phase))?'active':smelterTools.length?'done':'idle',
   detail:{'SMELTER tool calls this turn':String(smelterTools.length),'Evidence':'Recognised by the smelter_ tool-name prefix; a registered tool is not necessarily running.'}});
  if(smelterTools.length)edge('opencode','smelter','SMELTER MCP tools called this turn (by tool name)','inferred');
  node('workspace',{kind:'workspace',lane:4,label:'Workspace '+short(workspace||'unbound',14),state:'idle',
   detail:{'Workspace ID':workspace||'unbound','Workspace root':data.workspace_root||'unknown','Index revision':data.index_revision||'not reported','Index captured':data.index_updated_at||'not reported'}});
  edge('opencode','workspace','workspace bound to this session','binding');
  const root=binding.session_id;
  for(const session of sessions){
   const id='session:'+session.session_id,waiting=pendingAccess.has(session.session_id)?'waiting for access':pendingAnswer.has(session.session_id)?'waiting for answer':null;
   // After the root response ends, a child's last non-final state is reported as unknown, not active.
   const state=waiting?'waiting':session.state==='failed'?'error':TERMINAL.has(session.state)?'done':terminal?'unknown':session.state==='awaiting_model'?'waiting':'active';
   node(id,{kind:'session',lane:1,label:(session.session_id===root?'Session ':'Child ')+short(session.session_id,18),state,
    detail:{'Session ID':session.session_id,'Parent':session.parent_id||'none (bound root)','State':waiting||session.state,'Agent':session.agent||'not reported','Provider':session.provider||'not reported','Model':session.model||'not reported','Last activity':session.last_activity_at||'unknown'}});
  }
  for(const session of sessions){
   const id='session:'+session.session_id;
   if(session.session_id===root){edge('opencode',id,'bound root session','binding');edge('task',id,'turn identity belongs to this session','observed')}
   else if(session.parent_id&&nodes.has('session:'+session.parent_id))edge('session:'+session.parent_id,id,'delegated child session','observed');
   if(session.model){const model='model:'+session.model;node(model,{kind:'model',lane:3,label:short(session.model,24),state:session.state==='awaiting_model'&&!terminal?'waiting':'idle',detail:{'Model':session.model,'Context (if loaded)':String(loaded.find(m=>m.name===session.model)?.context_length??'not reported'),'Note':'Loaded on the host is not proof this task is generating tokens.'}});
    edge(id,model,'assistant message reported this model','observed');
    if(loaded.some(m=>m.name===session.model))edge('ollama',model,'currently loaded (host-wide)','observed');else edge('ollama',model,'expected to serve this model','inferred')}
  }
  if(data.sessions_truncated)notes.push('Session tree truncated at sixteen sessions.');
  const groups=new Map();
  for(const tool of tools){const key='tool:'+tool.session_id+':'+tool.tool;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(tool)}
  let toolCount=0;
  for(const [key,calls] of groups){
   if(++toolCount>MAX_TOOL_GROUPS){notes.push('Tool groups limited to '+MAX_TOOL_GROUPS+'.');break}
   const name=calls[0].tool,active=calls.filter(c=>['pending','running'].includes(c.phase)),errors=calls.filter(c=>c.phase==='error');
   const oldest=active.map(c=>c.started_at||c.updated_at).sort()[0];
   node(key,{kind:'tool',lane:3,label:short(name,20)+(calls.length>1?' ×'+calls.length:''),state:!terminal&&active.length?'active':errors.length?'error':'done',
    calls:calls.map(c=>({call_id:c.call_id,phase:c.phase,started_at:c.started_at,updated_at:c.updated_at,error_code:c.error_code||null,file:c.file||null})),
    detail:{'Tool':name,'Session':calls[0].session_id,'Calls observed':String(calls.length),'Running or pending':terminal?'turn ended':String(active.length),'Longest active':oldest?seconds(oldest,now)+'s':'none','Errors':errors.map(e=>e.error_code||'tool_error').join(', ')||'none'}});
   if(nodes.has('session:'+calls[0].session_id))edge('session:'+calls[0].session_id,key,'called tool','observed');
   if(name.startsWith('smelter_'))edge('smelter',key,'SMELTER tool (by name prefix)','inferred');
   if(name==='task')for(const s of sessions)if(s.parent_id===calls[0].session_id)edge(key,'session:'+s.session_id,'task tool delegates to child sessions','inferred');
  }
  for(const skill of data.skills||[]){const id='skill:'+skill;node(id,{kind:'skill',lane:2,label:'Skill '+short(skill,18),state:'idle',detail:{'Skill':skill,'Evidence':'A completed skill tool call loaded this skill. Loading is not proof the skill performed an operation.'}});
   for(const [key,calls] of groups)if(calls[0].tool==='skill')edge(key,id,'loaded skill','observed')}
  const files=new Map();let fileOverflow=0;
  for(const tool of tools){
   if(!tool.file)continue;const identity=fileIdentity(tool.file,data.workspace_root,workspace);
   if(!files.has(identity.id)){if(files.size>=MAX_FILES){fileOverflow++;continue}files.set(identity.id,{identity,path:tool.file,touches:[]})}
   files.get(identity.id).touches.push(tool);
  }
  for(const [id,file] of files){
   const latest=file.touches[0],hash=file.touches.find(t=>t.indexed_sha256),written=file.touches.find(t=>['edit','write'].includes(t.tool)&&t.phase==='completed');
   const stale=hash&&written&&Date.parse(written.updated_at)>Date.parse(hash.index_updated_at);
   const active=!terminal&&file.touches.some(t=>['pending','running'].includes(t.phase));
   node(id,{kind:'file',lane:4,label:short(file.identity.relative.split('/').at(-1),24),state:active?'active':stale?'stale':hash?'idle':'unknown',
    detail:{'Canonical path':file.path,'Workspace-relative':file.identity.inside?file.identity.relative:'outside workspace root (other visible scope)','Workspace':workspace||'unbound','Indexed SHA-256':hash?.indexed_sha256||'not in index','Index captured':hash?.index_updated_at||'n/a','Hash freshness':!hash?'No indexed hash for this path':stale?'Index predates an observed write; hash may be stale':'Index observation (not proof of bytes read by a tool)','Last activity':latest.tool+' · '+latest.phase+' · '+latest.updated_at,'Operations':String(file.touches.length)}});
   if(file.identity.inside)edge('workspace',id,'inside bound workspace','binding');
   for(const touch of file.touches)edge('tool:'+touch.session_id+':'+touch.tool,id,VERBS[touch.tool]||'named path argument','observed');
  }
  if(fileOverflow)notes.push(fileOverflow+' further file operations are not drawn (limit '+MAX_FILES+' files).');
  for(const receipt of data.validation||[]){const id='test:'+receipt.profile;
   const red=[receipt.stage,receipt.acceptance_stage].some(s=>s==='RED'||s==='ERROR');
   node(id,{kind:'test',lane:4,label:'Tests '+short(receipt.profile,12)+' · '+receipt.stage,state:!receipt.current?'stale':red?'error':receipt.stage==='GREEN'?'done':'unknown',
    detail:{'Profile':receipt.profile,'Overall stage':receipt.stage,'Tree':receipt.current?'current tree':'stale tree','Editable tests':receipt.workspace_tests_stage||'not reported','Frozen acceptance':receipt.acceptance_stage||'not reported','Authority':'Frozen acceptance is authoritative; editable GREEN cannot override it.'}});
   edge('workspace',id,'validation receipt','observed')}
  // Explicitly registered artifacts for this task only; registration is not proof of game integration.
  for(const artifact of options.artifacts||[]){
   if(artifact.task?.session_id!==binding.session_id||artifact.task?.native_turn_id!==data.native_turn_id||artifact.workspace_id!==workspace)continue;
   const id='artifact:'+artifact.id,file='file:'+workspace+':'+String(artifact.relative_path).toLowerCase();
   node(id,{kind:'artifact',lane:4,label:(artifact.kind==='model'?'GLB ':'Image ')+short(String(artifact.relative_path).split('/').at(-1),18),state:artifact.state==='current'?'linked':artifact.state==='changed'?'stale':'error',artifact,
    detail:{'Artifact ID':artifact.id,'Path':artifact.relative_path,'Kind':artifact.mime,'Bytes':String(artifact.bytes),'SHA-256 at registration':artifact.sha256,'Current state':artifact.state,'Source revision':artifact.source_revision||'not recorded','Producer':artifact.producer?.source+(artifact.producer?.tool?' · '+artifact.producer.tool+' · '+artifact.producer.call_id:''),'Registered':artifact.registered_at}});
   if(nodes.has(file))edge(file,id,'registered as task artifact','binding');
   const producer=artifact.producer?.tool&&'tool:'+artifact.producer.session_id+':'+artifact.producer.tool;
   const observed=String(artifact.producer?.source).startsWith('observed');
   if(producer)edge(producer,id,observed?'produced (observed call naming this path)':'declared producer',observed?'observed':'inferred');
  }
  for(const artifact of options.artifacts||[])for(const parent of artifact.derived_from||[])edge('artifact:'+parent,'artifact:'+artifact.id,'converted into (declared lineage)','binding');
  for(const permission of data.permissions||[]){const id='wait:access:'+(permission.id||permission.session_id);
   node(id,{kind:'wait',lane:3,label:'Access · '+short(permission.kind,16),state:'waiting',detail:{'Request':permission.kind,'Session':permission.session_id,'Paths':(permission.paths||[]).join(', ')||'none reported','Source':data.permission_source||'unknown','Action':'Decide in the native client. The trace never approves access.'}});
   edge(id,'session:'+permission.session_id,'blocks session (access request)','observed')}
  for(const question of data.questions||[]){const id='wait:question:'+(question.id||question.session_id);
   node(id,{kind:'wait',lane:3,label:'Question pending',state:'waiting',detail:{'Session':question.session_id,'Action':'Answer in the native client.'}});
   edge(id,'session:'+question.session_id,'blocks session (question)','observed')}
  return {nodes:[...nodes.values()],edges:[...edges.values()],notes,truncated:notes.length>0,
   identity:{task_id:data.task_id||null,task_id_source:data.task_id_source||null,native_turn_id:data.native_turn_id||null,session_id:binding.session_id||null,workspace_id:workspace||null,melty_task_id:binding.melty_task_id||null}};
 }
 // Stable placement: nodes keep their slot until the task changes or the user tidies.
 function layout(graph,previous){
  const positions=previous||{slots:new Map(),lanes:LANES.map(()=>[])};
  const present=new Set(graph.nodes.map(n=>n.id));
  for(const node of graph.nodes){
   if(!positions.slots.has(node.id)){const lane=positions.lanes[node.lane],free=lane.indexOf(null);const slot=free>=0?free:lane.length;lane[slot]=node.id;positions.slots.set(node.id,{lane:node.lane,slot})}
  }
  for(const [id,place] of positions.slots)if(!present.has(id)&&positions.retired?.has(id)){positions.lanes[place.lane][place.slot]=null;positions.slots.delete(id)}
  positions.retired=new Set([...positions.slots.keys()].filter(id=>!present.has(id)));
  return positions;
 }
 function point(positions,id){const place=positions.slots.get(id);if(!place)return null;const columns=COLUMNS[place.lane];return {x:LANE_X[place.lane]+(place.slot%columns)*COL,y:PAD+28+Math.floor(place.slot/columns)*ROW}}
 function bounds(positions,ids){let maxX=0,maxY=0,minX=Infinity,minY=Infinity;for(const id of ids){const p=point(positions,id);if(!p)continue;minX=Math.min(minX,p.x);minY=Math.min(minY,p.y);maxX=Math.max(maxX,p.x+W);maxY=Math.max(maxY,p.y+H)}
  return minX===Infinity?{x:0,y:0,width:COL*7,height:300}:{x:minX-PAD,y:minY-PAD-28,width:maxX-minX+PAD*2,height:maxY-minY+PAD*2+28}}
 function route(a,b){const sx=a.x+W,sy=a.y+H/2,tx=b.x,ty=b.y+H/2;
  if(tx>sx+10){const mid=(sx+tx)/2;return `M ${sx} ${sy} C ${mid} ${sy} ${mid} ${ty} ${tx} ${ty}`}
  const bend=Math.max(a.x,b.x)+W+40;return `M ${a.x+W} ${sy} C ${bend} ${sy} ${bend} ${ty} ${b.x+W} ${ty}`}
 function neighbours(graph,id){const ids=new Set([id]);for(const e of graph.edges){if(e.source===id)ids.add(e.target);if(e.target===id)ids.add(e.source)}return ids}
 function matches(node,query){if(!query)return true;query=query.toLowerCase();return [node.label,node.id,...Object.values(node.detail||{})].some(v=>String(v).toLowerCase().includes(query))}
 function mermaid(graph){
  const ids=new Map(graph.nodes.map((n,i)=>[n.id,'n'+i])),clean=s=>String(s).replace(/["<>`]/g,"'").replace(/[\r\n]+/g,' ');
  const lines=['flowchart LR','%% Evidence: --> observed · -.-> inferred · ==> explicit binding'];
  for(const n of graph.nodes)lines.push(`  ${ids.get(n.id)}["${clean(n.label)} (${n.state})"]`);
  for(const e of graph.edges){const arrow=e.evidence==='observed'?'-->':e.evidence==='binding'?'==>':'-.->';lines.push(`  ${ids.get(e.source)} ${arrow}|"${clean(e.relation)}"| ${ids.get(e.target)}`)}
  return lines.join('\n');
 }
 const NS='http://www.w3.org/2000/svg';
 const STATE_LABEL={active:'active',waiting:'waiting',error:'error',done:'finished',idle:'idle',unknown:'unknown',stale:'stale',linked:'linked'};
 /* Interactive view. Keyed reconciliation keeps nodes, focus and the viewport across heartbeats. */
 function createView(doc,host,options={}){
  const svg=(tag,attrs={})=>{const n=doc.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));return n};
  const root=svg('svg',{class:'trace-graph-svg',role:'group','aria-label':'Task relationship graph. Use Tab to reach nodes and arrow keys to move between them.'});
  const defs=svg('defs');for(const evidence of Object.keys(EVIDENCE)){const marker=svg('marker',{id:'trace-arrow-'+evidence,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:7,markerHeight:7,orient:'auto-start-reverse'});marker.append(svg('path',{d:'M0 0 L10 5 L0 10 z',class:'trace-arrow trace-arrow-'+evidence}));defs.append(marker)}
  const viewport=svg('g',{class:'trace-viewport'}),laneLayer=svg('g',{class:'trace-lanes'}),edgeLayer=svg('g',{class:'trace-edges'}),labelLayer=svg('g',{class:'trace-edge-labels'}),nodeLayer=svg('g',{class:'trace-nodes'});
  viewport.append(laneLayer,edgeLayer,labelLayer,nodeLayer);root.append(defs,viewport);host.append(root);
  LANES.forEach((name,i)=>{const t=svg('text',{x:LANE_X[i],y:PAD,class:'trace-lane-title'});t.textContent=name;laneLayer.append(t)});
  let graph={nodes:[],edges:[]},positions=null,selected=null,query='',focus=false,view={x:0,y:0,k:1},userMoved=false,taskKey=null;
  const nodeEls=new Map(),edgeEls=new Map();
  function applyView(){viewport.setAttribute('transform',`translate(${view.x} ${view.y}) scale(${view.k})`)}
  function size(){const box=root.getBoundingClientRect?.()||{width:900,height:520};return {width:box.width||900,height:box.height||520}}
  function fit(ids){const b=bounds(positions||{slots:new Map()},ids||graph.nodes.map(n=>n.id)),s=size(),k=Math.max(.1,Math.min(1.6,Math.min(s.width/b.width,s.height/b.height)));view={k,x:(s.width-b.width*k)/2-b.x*k,y:(s.height-b.height*k)/2-b.y*k};applyView()}
  function zoom(factor,cx,cy){const s=size();cx??=s.width/2;cy??=s.height/2;const k=Math.max(.1,Math.min(3,view.k*factor));view={k,x:cx-(cx-view.x)*k/view.k,y:cy-(cy-view.y)*k/view.k};userMoved=true;applyView()}
  function paint(){
   const visible=focus&&selected?neighbours(graph,selected):null;
   for(const n of graph.nodes){const g=nodeEls.get(n.id);if(!g)continue;const hit=matches(n,query);
    g.setAttribute('class',['trace-node','kind-'+n.kind,'state-'+n.state,n.id===selected?'selected':'',query&&hit?'match':'',(query&&!hit)||(visible&&!visible.has(n.id))?'dim':''].filter(Boolean).join(' '));
    g.setAttribute('aria-pressed',n.id===selected?'true':'false')}
   for(const e of graph.edges){const parts=edgeEls.get(e.id);if(!parts)continue;const related=selected&&(e.source===selected||e.target===selected);
    const hidden=visible&&!(visible.has(e.source)&&visible.has(e.target));
    parts.path.setAttribute('class','trace-edge evidence-'+e.evidence+(related?' related':'')+(hidden?' dim':''));
    parts.label.setAttribute('class','trace-edge-label'+(related?' shown':''))}
  }
  function select(id,announce=true){selected=id&&graph.nodes.some(n=>n.id===id)?id:null;paint();if(announce)options.onSelect?.(selected?graph.nodes.find(n=>n.id===selected):null,graph)}
  function move(direction){
   const current=selected&&point(positions,selected);if(!current){const first=graph.nodes[0];if(first)focusNode(first.id);return}
   let best=null,score=Infinity;
   // Move to the nearest drawn node in the pressed direction (sub-columns included).
   for(const n of graph.nodes){const p=point(positions,n.id);if(!p||n.id===selected)continue;
    const dx=p.x-current.x,dy=p.y-current.y,horizontal=direction==='ArrowRight'||direction==='ArrowLeft';
    const ok=direction==='ArrowRight'?dx>0:direction==='ArrowLeft'?dx<0:direction==='ArrowDown'?dy>0:dy<0;
    if(!ok)continue;const value=horizontal?Math.abs(dx)+Math.abs(dy)*3:Math.abs(dy)+Math.abs(dx)*3;if(value<score){score=value;best=n.id}}
   if(best)focusNode(best);
  }
  function focusNode(id){select(id);nodeEls.get(id)?.focus?.()}
  function update(next,meta={}){
   if(meta.taskKey!==undefined&&meta.taskKey!==taskKey){taskKey=meta.taskKey;positions=null;userMoved=false;for(const g of nodeEls.values())g.remove();nodeEls.clear();for(const p of edgeEls.values()){p.path.remove();p.label.remove()}edgeEls.clear()}
   graph=next;positions=layout(graph,positions);
   const ids=new Set(graph.nodes.map(n=>n.id));
   for(const [id,g] of nodeEls)if(!ids.has(id)){g.remove();nodeEls.delete(id)}
   for(const n of graph.nodes){let g=nodeEls.get(n.id);
    if(!g){g=svg('g',{tabindex:0,role:'button','data-node':n.id});const rect=svg('rect',{width:W,height:H,rx:8}),bar=svg('rect',{class:'trace-node-bar',width:5,height:H,rx:2}),label=svg('text',{x:14,y:19,class:'trace-node-label'}),sub=svg('text',{x:14,y:36,class:'trace-node-sub'}),title=svg('title');g.append(rect,bar,label,sub,title);
     g.addEventListener?.('click',event=>{event.stopPropagation();select(n.id)});
     g.addEventListener?.('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();select(n.id)}else if(event.key.startsWith('Arrow')){event.preventDefault();move(event.key)}else if(event.key==='Escape'){select(null)}});
     g.addEventListener?.('focus',()=>{if(selected!==n.id)select(n.id)});
     nodeEls.set(n.id,g);nodeLayer.append(g)}
    const p=point(positions,n.id);g.setAttribute('transform',`translate(${p.x} ${p.y})`);
    const [,, label, sub, title]=g.children;label.textContent=n.label;sub.textContent=n.kind+' · '+(STATE_LABEL[n.state]||n.state);title.textContent=n.label+' — '+n.kind+', '+(STATE_LABEL[n.state]||n.state);
    g.setAttribute('aria-label',n.label+', '+n.kind+', '+(STATE_LABEL[n.state]||n.state))}
   const edgeIds=new Set(graph.edges.map(e=>e.id));
   for(const [id,p] of edgeEls)if(!edgeIds.has(id)){p.path.remove();p.label.remove();edgeEls.delete(id)}
   for(const e of graph.edges){const a=point(positions,e.source),b=point(positions,e.target);if(!a||!b)continue;let parts=edgeEls.get(e.id);
    if(!parts){const path=svg('path',{'marker-end':`url(#trace-arrow-${e.evidence})`}),title=svg('title'),label=svg('text',{'text-anchor':'middle'});title.textContent=e.relation+' — '+EVIDENCE[e.evidence];path.append(title);label.textContent=short(e.relation,40);parts={path,label};edgeEls.set(e.id,parts);edgeLayer.append(path);labelLayer.append(label)}
    parts.path.setAttribute('d',route(a,b));if(DASH[e.evidence])parts.path.setAttribute('stroke-dasharray',DASH[e.evidence]);
    parts.label.setAttribute('x',(a.x+W+b.x)/2);parts.label.setAttribute('y',(a.y+b.y)/2+H/2-6)}
   if(selected&&!ids.has(selected))select(null);else paint();
   if(!userMoved)fit();
  }
  // Pointer panning on the background and wheel zoom around the cursor.
  let drag=null;
  root.addEventListener?.('pointerdown',event=>{if(event.target.closest?.('[data-node]'))return;drag={x:event.clientX,y:event.clientY,vx:view.x,vy:view.y};root.setPointerCapture?.(event.pointerId)});
  root.addEventListener?.('pointermove',event=>{if(!drag)return;view.x=drag.vx+event.clientX-drag.x;view.y=drag.vy+event.clientY-drag.y;userMoved=true;applyView()});
  root.addEventListener?.('pointerup',event=>{if(drag&&Math.abs(event.clientX-drag.x)+Math.abs(event.clientY-drag.y)<4)select(null);drag=null});
  root.addEventListener?.('wheel',event=>{event.preventDefault();const box=root.getBoundingClientRect();zoom(event.deltaY<0?1.12:1/1.12,event.clientX-box.left,event.clientY-box.top)},{passive:false});
  return {update,select,fit:()=>{userMoved=false;fit()},zoom,
   search(value){query=value.trim();paint();return graph.nodes.filter(n=>query&&matches(n,query))},
   setFocus(value){focus=value;paint();if(value&&selected){userMoved=true;fit([...neighbours(graph,selected)])}},
   tidy(){positions=null;update(graph)},
   selected:()=>selected,graph:()=>graph,element:root,
   svgMarkup(){const clone=root.cloneNode(true);clone.setAttribute('xmlns',NS);const b=bounds(positions,graph.nodes.map(n=>n.id));clone.setAttribute('viewBox',`${b.x} ${b.y} ${b.width} ${b.height}`);clone.setAttribute('width',b.width);clone.setAttribute('height',b.height);clone.querySelector('.trace-viewport')?.removeAttribute('transform');
    const style=doc.createElementNS(NS,'style');style.textContent=EXPORT_STYLE;clone.prepend(style);return new XMLSerializer().serializeToString(clone)}};
 }
 const EXPORT_STYLE='svg{background:#0f172a;font-family:Segoe UI,sans-serif}.trace-lane-title{fill:#94a3b8;font-size:12px;font-weight:600}.trace-node rect{fill:#1b2336;stroke:#3a4762}.trace-node-label{fill:#f1f5f9;font-size:12px}.trace-node-sub{fill:#94a3b8;font-size:10px}.trace-edge{fill:none;stroke:#64748b;stroke-width:1.3}.trace-edge.evidence-observed{stroke:#4ade80}.trace-edge.evidence-binding{stroke:#60a5fa}.trace-edge-label{display:none}.trace-arrow{fill:#94a3b8}.state-active .trace-node-bar{fill:#22c55e}.state-waiting .trace-node-bar{fill:#fbbf24}.state-error .trace-node-bar{fill:#f87171}.state-stale .trace-node-bar{fill:#c084fc}.trace-node-bar{fill:#475569}';
 return {project,layout,mermaid,createView,fileIdentity,neighbours,matches,LANES,EVIDENCE};
})();
if(typeof module!=='undefined')module.exports=SmelterTraceGraph;
