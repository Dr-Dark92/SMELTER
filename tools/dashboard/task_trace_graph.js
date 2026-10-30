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
 // Layer geometry: node box, placeholder width for long edges, gaps, channel tracks and the layer-label gutter.
 const W=184,H=46,DUMMY=12,GAP=28,DGAP=10,TRACK=9,MIN_CHANNEL=46,PAD=36,LABEL=150,CAP=7,SWEEPS=16;
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
   if(file.identity.inside)edge('workspace',id,'inside bound workspace','binding',{containment:true});
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
 const mean=values=>values.reduce((a,b)=>a+b,0)/values.length;
 /* Layered top-down layout, deterministic for a given graph and previous layout:
    1. edges point down: a wait hangs below the session it blocks and DFS back edges are reversed;
    2. longest-path layers, and a layer wider than CAP pushes its leaves (then their successors) down;
    3. a placeholder on every layer a long edge crosses, so edges only pass through free columns;
    4. barycentre sweeps seeded from the previous order, kept only when crossings strictly drop;
    5. order-preserving placement, then orthogonal connectors whose horizontal runs use separate
       tracks in the channel between two layers. Connectors never enter a node box. */
 function layout(graph,previous){
  const ids=graph.nodes.map(n=>n.id),index=new Map(ids.map((id,i)=>[id,i])),kind=new Map(graph.nodes.map(n=>[n.id,n.kind]));
  const links=[],adjacent=new Map(ids.map(id=>[id,[]]));
  for(const e of graph.edges){if(!index.has(e.source)||!index.has(e.target)||e.source===e.target)continue;
   const flip=kind.get(e.source)==='wait',link={edge:e,from:flip?e.target:e.source,to:flip?e.source:e.target,flip};links.push(link);adjacent.get(link.from).push(link)}
  const seen=new Map(),visit=id=>{seen.set(id,1);for(const link of adjacent.get(id)){const state=seen.get(link.to);if(state===1)link.back=true;else if(!state)visit(link.to)}seen.set(id,2)};
  for(const id of ids)if(!seen.has(id))visit(id);
  for(const link of links)if(link.back){[link.from,link.to]=[link.to,link.from];link.flip=!link.flip}
  const preds=new Map(ids.map(id=>[id,[]])),succs=new Map(ids.map(id=>[id,[]]));
  for(const link of links){succs.get(link.from).push(link.to);preds.get(link.to).push(link.from)}
  const rank=new Map(),waiting=new Map(ids.map(id=>[id,preds.get(id).length])),queue=ids.filter(id=>!waiting.get(id));
  for(let i=0;i<queue.length;i++){const id=queue[i];rank.set(id,Math.max(0,...preds.get(id).map(p=>rank.get(p)+1)));
   for(const s of succs.get(id)){waiting.set(s,waiting.get(s)-1);if(!waiting.get(s))queue.push(s)}}
  const push=(id,r)=>{if(rank.get(id)>=r)return;rank.set(id,r);for(const s of succs.get(id))push(s,r+1)};
  // Wrapping prefers nodes that sat lower last time, then new nodes, then leaves, so heartbeats do not reshuffle rows.
  const was=id=>previous?.nodes.get(id)?.layer,lower=(id,r)=>was(id)===undefined?1:was(id)>r?2:0;
  for(let r=0;r<=Math.max(0,...rank.values());r++){const members=ids.filter(id=>rank.get(id)===r);if(members.length<=CAP)continue;
   members.sort((a,b)=>lower(b,r)-lower(a,r)||succs.get(a).length-succs.get(b).length||index.get(b)-index.get(a));for(const id of members.slice(0,members.length-CAP))push(id,r+1)}
  const used=[...new Set(rank.values())].sort((a,b)=>a-b),compact=new Map(used.map((r,i)=>[r,i]));
  const layers=used.map(()=>[]);let seq=0;
  const add=(id,layer,real)=>{const v={id,layer,real,w:real?W:DUMMY,up:[],down:[],seq:seq++};layers[layer].push(v);return v};
  const vertex=new Map(ids.map(id=>[id,add(id,compact.get(rank.get(id)),true)]));
  // Long edges from one source with one evidence class share a trunk (a bus) and branch at their target's layer.
  const dummies=new Map(),trunks=new Map();
  const chains=links.map(link=>{const path=[vertex.get(link.from)],end=vertex.get(link.to),bundle=link.flip?link.edge.id:link.from+'|'+link.edge.evidence;
   for(let r=path[0].layer+1;r<end.layer;r++){const id=bundle+'#'+r;if(!dummies.has(id))dummies.set(id,add(id,r,false));path.push(dummies.get(id))}path.push(end);
   const segments=path.slice(1).map((bottom,i)=>{const top=path[i],key=top.id+'>'+bottom.id;if(!bottom.real&&trunks.has(key))return trunks.get(key);
    const s={top,bottom,id:link.edge.id};top.down.push(s);bottom.up.push(s);if(!bottom.real)trunks.set(key,s);return s});return {link,segments}});
  // Seed each layer from the previous centres; new vertices start under their parents.
  const before=previous?.centres||new Map(),byKey=(a,b)=>(a.key===b.key?0:a.key<b.key?-1:1)||a.seq-b.seq;
  for(const row of layers){for(const v of row){const ups=v.up.map(s=>s.top.key);v.key=before.get(v.id)??(ups.length?mean(ups):Infinity)}
   row.sort(byKey);let last=0;for(const v of row){if(!Number.isFinite(v.key))v.key=last+W+GAP;last=v.key}row.forEach((v,i)=>v.order=i)}
  const crossings=()=>{let total=0;for(const row of layers){const segs=row.flatMap(v=>v.down.map(s=>[v.order,s.bottom.order]));
   for(let i=0;i<segs.length;i++)for(let j=i+1;j<segs.length;j++)if((segs[i][0]-segs[j][0])*(segs[i][1]-segs[j][1])<0)total++}return total};
  const save=()=>layers.map(row=>[...row]);let best=crossings(),bestOrder=save();
  for(let sweep=0;sweep<SWEEPS&&best>0;sweep++){const down=sweep%2===0,range=[...layers.keys()];if(!down)range.reverse();
   for(const r of range.slice(1)){const row=layers[r];for(const v of row){const near=(down?v.up.map(s=>s.top):v.down.map(s=>s.bottom)).map(n=>n.order);v.bary=near.length?mean(near):v.order}
    row.sort((a,b)=>a.bary-b.bary||a.order-b.order);
    // On a heartbeat only new vertices and placeholders move; nodes already shown keep their relative order.
    const kept=row.map((v,i)=>[v,i]).filter(([v])=>v.real&&before.has(v.id)),fixed=[...kept].sort((a,b)=>a[0].order-b[0].order);kept.forEach(([,i],k)=>row[i]=fixed[k][0]);
    row.forEach((v,i)=>v.order=i)}
   const count=crossings();if(count<best){best=count;bestOrder=save()}}
  bestOrder.forEach((row,r)=>{layers[r]=row;row.forEach((v,i)=>v.order=i)});
  // Transpose: swap neighbours while that removes crossings with the layers above and below.
  const pairs=(u,v,side,end)=>{let n=0;for(const a of u[side])for(const b of v[side])if(a[end].order>b[end].order)n++;return n};
  const cost=(u,v)=>pairs(u,v,'up','top')+pairs(u,v,'down','bottom');
  for(let round=0,changed=true;changed&&round<8;round++){changed=false;
   for(const row of layers)for(let i=0;i+1<row.length;i++){const u=row[i],v=row[i+1];if(u.real&&v.real&&before.has(u.id)&&before.has(v.id))continue;
    if(cost(v,u)<cost(u,v)){row[i]=v;row[i+1]=u;u.order=i+1;v.order=i;changed=true}}}
  best=crossings();
  // Placement keeps the order; averaging a left-packed and a right-packed solution keeps every gap.
  const sep=(a,b)=>(a.w+b.w)/2+(a.real||b.real?GAP:DGAP);
  const place=(row,want)=>{const n=row.length,L=[],R=[];for(let i=0;i<n;i++)L[i]=i?Math.max(want[i],L[i-1]+sep(row[i-1],row[i])):want[i];
   for(let i=n-1;i>=0;i--)R[i]=i<n-1?Math.min(want[i],R[i+1]-sep(row[i],row[i+1])):want[i];row.forEach((v,i)=>v.cx=(L[i]+R[i])/2)};
  for(const row of layers){let x=0;row.forEach((v,i)=>{x+=i?sep(row[i-1],v):0;v.cx=x});row.forEach(v=>v.cx-=x/2)}
  for(let pass=0;pass<8;pass++){const down=pass%2===0,last=pass===7,range=[...layers.keys()];if(!down)range.reverse();
   for(const r of range)place(layers[r],layers[r].map(v=>{const near=[...(down||last?v.up.map(s=>s.top):[]),...(!down||last?v.down.map(s=>s.bottom):[])];return near.length?mean(near.map(n=>n.cx)):v.cx}))}
  const all=layers.flat(),left=Math.min(...all.map(v=>v.cx-v.w/2));for(const v of all)v.cx+=PAD+LABEL-left;
  // Ports spread along box edges in the order of the other end; a port is nudged off any other connector's column.
  const spread=(v,list,other,key)=>list.sort((a,b)=>other(a)-other(b)||(a.id<b.id?-1:a.id>b.id?1:0)).forEach((s,i)=>s[key]=v.cx-v.w/2+v.w*(i+1)/(list.length+1));
  const tracks=[];
  layers.forEach((row,r)=>{for(const v of row)if(v.real)spread(v,v.down,s=>s.bottom.cx,'x1');else for(const s of v.down)s.x1=v.port??v.cx;
   if(r+1===layers.length)return;const segs=row.flatMap(v=>v.down);
   for(const v of layers[r+1])if(v.real)spread(v,v.up,s=>s.x1,'x2');else for(const s of v.up)s.x2=v.cx;
   for(const s of segs){const clash=x=>segs.some(o=>o!==s&&((o.top!==s.top||s.top.real)&&Math.abs(o.x1-x)<3||Math.abs(o.x2-x)<3)),v=s.bottom,room=v.real?v.w/2-4:v.w/2;
    if(Math.abs(s.x2-s.x1)<1.5&&!clash(s.x1)&&Math.abs(s.x1-v.cx)<=room)s.x2=s.x1;
    else if(clash(s.x2))for(const d of [4,-4,6,-6,9,-9,12,-12])if(Math.abs(s.x2+d-v.cx)<=room&&!clash(s.x2+d)){s.x2+=d;break}
    if(!v.real)v.port=s.x2}
   const runs=segs.filter(s=>s.x1!==s.x2).sort((a,b)=>Math.min(a.x1,a.x2)-Math.min(b.x1,b.x2)||(a.id<b.id?-1:1)),ends=[];
   for(const s of runs){const lo=Math.min(s.x1,s.x2),hi=Math.max(s.x1,s.x2);let t=ends.findIndex(end=>end+TRACK<lo);if(t<0){t=ends.length;ends.push(hi)}else ends[t]=hi;s.track=t}
   tracks[r]=ends.length});
  const tops=[],channels=[];let y=PAD;
  layers.forEach((_,r)=>{tops[r]=y;channels[r]=Math.max(MIN_CHANNEL,((tracks[r]||0)+1)*TRACK+12);y+=H+channels[r]});
  const trackY=(r,t)=>tops[r]+H+(channels[r]-((tracks[r]||1)-1)*TRACK)/2+t*TRACK;
  const edges=new Map();
  for(const {link,segments} of chains){let points=[];
   for(const s of segments){const r=s.top.layer;points.push([s.x1,tops[r]+H]);if(s.track!==undefined)points.push([s.x1,trackY(r,s.track)],[s.x2,trackY(r,s.track)]);points.push([s.x2,tops[r+1]])}
   points=points.filter((p,i)=>!i||p[0]!==points[i-1][0]||p[1]!==points[i-1][1]);
   points=points.filter((p,i)=>i===0||i===points.length-1||!((p[0]===points[i-1][0]&&p[0]===points[i+1][0])||(p[1]===points[i-1][1]&&p[1]===points[i+1][1])));
   edges.set(link.edge.id,{points:link.flip?points.reverse():points,source:link.edge.source,target:link.edge.target})}
  const nodes=new Map(),centres=new Map();
  for(const v of all){centres.set(v.id,v.cx);if(v.real)nodes.set(v.id,{x:v.cx-W/2,y:tops[v.layer],w:W,h:H,layer:v.layer})}
  return {nodes,edges,centres,crossings:best,layers:layers.map((row,r)=>({y:tops[r],kinds:[...new Set(row.filter(v=>v.real).map(v=>kind.get(v.id)))]})),
   width:Math.max(PAD+LABEL,...all.map(v=>v.cx+v.w/2))+PAD,height:layers.length?tops.at(-1)+H+PAD:PAD*2};
 }
 function point(positions,id){return positions?.nodes.get(id)||null}
 function bounds(positions,ids){if(!positions||!positions.nodes.size)return {x:0,y:0,width:900,height:300};
  if(!ids)return {x:0,y:0,width:positions.width,height:positions.height};
  let maxX=-Infinity,maxY=-Infinity,minX=Infinity,minY=Infinity;for(const id of ids){const p=point(positions,id);if(!p)continue;minX=Math.min(minX,p.x);minY=Math.min(minY,p.y);maxX=Math.max(maxX,p.x+W);maxY=Math.max(maxY,p.y+H)}
  return minX===Infinity?bounds(positions):{x:minX-PAD,y:minY-PAD,width:maxX-minX+PAD*2,height:maxY-minY+PAD*2}}
 // Orthogonal polyline with small rounded corners.
 function route(points,radius=6){const f=n=>Math.round(n*10)/10;let d=`M ${f(points[0][0])} ${f(points[0][1])}`;
  for(let i=1;i<points.length;i++){const [x,y]=points[i],next=points[i+1];if(!next){d+=` L ${f(x)} ${f(y)}`;break}
   const [px,py]=points[i-1],a=Math.min(radius,Math.hypot(x-px,y-py)/2,Math.hypot(next[0]-x,next[1]-y)/2);
   d+=` L ${f(x-Math.sign(x-px)*a)} ${f(y-Math.sign(y-py)*a)} Q ${f(x)} ${f(y)} ${f(x+Math.sign(next[0]-x)*a)} ${f(y+Math.sign(next[1]-y)*a)}`}return d}
 // Edge labels sit on the middle of the longest straight run.
 function labelPoint(points){let best=[points[0],points[1]],size=-1;for(let i=1;i<points.length;i++){const a=points[i-1],b=points[i],l=Math.abs(b[0]-a[0])+Math.abs(b[1]-a[1]);if(l>size){size=l;best=[a,b]}}
  return {x:(best[0][0]+best[1][0])/2,y:(best[0][1]+best[1][1])/2}}
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
 const KIND_LABEL={task:'Task',component:'Components',session:'Sessions',service:'Services',workspace:'Workspace',model:'Models',tool:'Tools',skill:'Skills',file:'Files',test:'Tests',artifact:'Artifacts',wait:'Waits'};
 // Layer colours cycle by row; mid-tone hues read on dark and light backgrounds and stay clear of the state and evidence colours.
 const LAYER_COLOURS=['#5b8def','#a77bf3','#e0a43a','#2fb5a8','#e46f9b','#8aa63a'];
 const layerColour=r=>LAYER_COLOURS[r%LAYER_COLOURS.length];
 const STATE_LABEL={active:'active',waiting:'waiting',error:'error',done:'finished',idle:'idle',unknown:'unknown',stale:'stale',linked:'linked'};
 /* Interactive view. Keyed reconciliation keeps nodes, focus and the viewport across heartbeats. */
 function createView(doc,host,options={}){
  const svg=(tag,attrs={})=>{const n=doc.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,String(v));return n};
  const root=svg('svg',{class:'trace-graph-svg',role:'group','aria-label':'Task relationship graph. Use Tab to reach nodes and arrow keys to move between them.'});
  const defs=svg('defs');for(const evidence of Object.keys(EVIDENCE)){const marker=svg('marker',{id:'trace-arrow-'+evidence,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:7,markerHeight:7,orient:'auto-start-reverse'});marker.append(svg('path',{d:'M0 0 L10 5 L0 10 z',class:'trace-arrow trace-arrow-'+evidence}));defs.append(marker)}
  const viewport=svg('g',{class:'trace-viewport'}),laneLayer=svg('g',{class:'trace-lanes'}),edgeLayer=svg('g',{class:'trace-edges'}),labelLayer=svg('g',{class:'trace-edge-labels'}),nodeLayer=svg('g',{class:'trace-nodes'});
  viewport.append(laneLayer,edgeLayer,labelLayer,nodeLayer);root.append(defs,viewport);host.append(root);
  let graph={nodes:[],edges:[]},containment=false,positions=null,selected=null,query='',focus=false,view={x:0,y:0,k:1},userMoved=false,taskKey=null;
  const nodeEls=new Map(),edgeEls=new Map();
  function applyView(){viewport.setAttribute('transform',`translate(${view.x} ${view.y}) scale(${view.k})`)}
  function size(){const box=root.getBoundingClientRect?.()||{width:900,height:520};return {width:box.width||900,height:box.height||520}}
  function fit(ids){const b=bounds(positions,ids),s=size(),k=Math.max(.1,Math.min(1.6,Math.min(s.width/b.width,s.height/b.height)));view={k,x:(s.width-b.width*k)/2-b.x*k,y:(s.height-b.height*k)/2-b.y*k};applyView()}
  function zoom(factor,cx,cy){const s=size();cx??=s.width/2;cy??=s.height/2;const k=Math.max(.1,Math.min(3,view.k*factor));view={k,x:cx-(cx-view.x)*k/view.k,y:cy-(cy-view.y)*k/view.k};userMoved=true;applyView()}
  function paint(){
   const visible=focus&&selected?neighbours(graph,selected):null;
   for(const n of graph.nodes){const g=nodeEls.get(n.id);if(!g)continue;const hit=matches(n,query);
    g.setAttribute('class',['trace-node','kind-'+n.kind,'state-'+n.state,n.id===selected?'selected':'',query&&hit?'match':'',(query&&!hit)||(visible&&!visible.has(n.id))?'dim':''].filter(Boolean).join(' '));
    g.setAttribute('aria-pressed',n.id===selected?'true':'false')}
   for(const e of graph.edges){const parts=edgeEls.get(e.id);if(!parts)continue;const related=selected&&(e.source===selected||e.target===selected);
    const hidden=visible&&!(visible.has(e.source)&&visible.has(e.target));
    parts.path.setAttribute('class','trace-edge evidence-'+e.evidence+(related?' related':'')+(hidden?' dim':''));parts.casing.setAttribute('class','trace-edge-casing'+(hidden?' dim':''));
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
   if(meta.taskKey!==undefined&&meta.taskKey!==taskKey){taskKey=meta.taskKey;positions=null;userMoved=false;for(const g of nodeEls.values())g.remove();nodeEls.clear();for(const p of edgeEls.values()){p.group.remove();p.label.remove()}edgeEls.clear()}
   graph=next;
   // Workspace containment (one binding edge per file) is drawn only on request; the node carries the count instead.
   const hidden=containment?0:graph.edges.filter(e=>e.containment).length;positions=layout(hidden?{nodes:graph.nodes,edges:graph.edges.filter(e=>!e.containment)}:graph,positions);
   // Each layer is a tinted band with a colour stripe; its label lists the kinds on that row, one per line (at most three).
   laneLayer.replaceChildren();positions.layers.forEach((layer,r)=>{const names=layer.kinds.map(k=>KIND_LABEL[k]||k),lines=names.length>3?[...names.slice(0,2),'+'+(names.length-2)+' more']:names,colour=layerColour(r);
    const band=svg('rect',{class:'trace-layer-band','data-layer':r,x:PAD/2,y:layer.y-10,width:positions.width-PAD,height:H+20,rx:10,fill:colour}),stripe=svg('rect',{class:'trace-layer-stripe',x:PAD/2,y:layer.y-10,width:4,height:H+20,rx:2,fill:colour});
    const t=svg('text',{x:PAD,y:layer.y+H/2+4-(lines.length-1)*6.5,class:'trace-lane-title'});lines.forEach((line,i)=>{const span=svg('tspan',{x:PAD,dy:i?13:0});span.textContent=line;t.append(span)});laneLayer.append(band,stripe,t)});
   const ids=new Set(graph.nodes.map(n=>n.id));
   for(const [id,g] of nodeEls)if(!ids.has(id)){g.remove();nodeEls.delete(id)}
   for(const n of graph.nodes){let g=nodeEls.get(n.id);
    if(!g){g=svg('g',{tabindex:0,role:'button','data-node':n.id});const rect=svg('rect',{width:W,height:H,rx:8}),bar=svg('rect',{class:'trace-node-bar',width:5,height:H,rx:2}),label=svg('text',{x:14,y:19,class:'trace-node-label'}),sub=svg('text',{x:14,y:36,class:'trace-node-sub'}),title=svg('title');g.append(rect,bar,label,sub,title);
     g.addEventListener?.('click',event=>{event.stopPropagation();select(n.id)});
     g.addEventListener?.('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();select(n.id)}else if(event.key.startsWith('Arrow')){event.preventDefault();move(event.key)}else if(event.key==='Escape'){select(null)}});
     g.addEventListener?.('focus',()=>{if(selected!==n.id)select(n.id)});
     nodeEls.set(n.id,g);nodeLayer.append(g)}
    const p=point(positions,n.id),r=positions.nodes.get(n.id)?.layer??0;g.setAttribute('transform',`translate(${p.x} ${p.y})`);g.setAttribute('data-layer',r);g.setAttribute('style','--layer-colour:'+layerColour(r));
    const [,, label, sub, title]=g.children;label.textContent=n.label;sub.textContent=n.kind+' · '+(STATE_LABEL[n.state]||n.state)+(n.id==='workspace'&&hidden?' · contains '+hidden+(hidden===1?' file':' files'):'');title.textContent=n.label+' — '+n.kind+', '+(STATE_LABEL[n.state]||n.state);
    g.setAttribute('aria-label',n.label+', '+n.kind+', '+(STATE_LABEL[n.state]||n.state))}
   const edgeIds=new Set(graph.edges.map(e=>e.id));
   for(const [id,p] of edgeEls)if(!edgeIds.has(id)||!positions.edges.has(id)){p.group.remove();p.label.remove();edgeEls.delete(id)}
   // Each connector sits on a background-coloured casing so a crossing reads as one line passing over another.
   for(const e of graph.edges){const placed=positions.edges.get(e.id);if(!placed)continue;let parts=edgeEls.get(e.id);
    if(!parts){const group=svg('g'),casing=svg('path'),path=svg('path',{'marker-end':`url(#trace-arrow-${e.evidence})`}),title=svg('title'),label=svg('text',{'text-anchor':'middle'});title.textContent=e.relation+' — '+EVIDENCE[e.evidence];path.append(title);label.textContent=short(e.relation,40);group.append(casing,path);parts={group,casing,path,label};edgeEls.set(e.id,parts);edgeLayer.append(group);labelLayer.append(label)}
    const d=route(placed.points);parts.casing.setAttribute('d',d);parts.path.setAttribute('d',d);if(DASH[e.evidence])parts.path.setAttribute('stroke-dasharray',DASH[e.evidence]);
    const at=labelPoint(placed.points);parts.label.setAttribute('x',at.x);parts.label.setAttribute('y',at.y-5)}
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
   setContainment(value){containment=value;update(graph)},
   selected:()=>selected,graph:()=>graph,element:root,
   svgMarkup(){const clone=root.cloneNode(true);clone.setAttribute('xmlns',NS);const b=bounds(positions);clone.setAttribute('viewBox',`${b.x} ${b.y} ${b.width} ${b.height}`);clone.setAttribute('width',b.width);clone.setAttribute('height',b.height);clone.querySelector('.trace-viewport')?.removeAttribute('transform');
    const style=doc.createElementNS(NS,'style');style.textContent=EXPORT_STYLE;clone.prepend(style);return new XMLSerializer().serializeToString(clone)}};
 }
 const EXPORT_STYLE='svg{background:#0f172a;font-family:Segoe UI,sans-serif}.trace-lane-title{fill:#94a3b8;font-size:12px;font-weight:600}.trace-layer-band{fill-opacity:.12}.trace-layer-stripe{fill-opacity:.85}.trace-node rect{fill:#1b2336;stroke:#3a4762;stroke:var(--layer-colour,#3a4762);stroke-opacity:.75}.trace-node-label{fill:#f1f5f9;font-size:12px}.trace-node-sub{fill:#94a3b8;font-size:10px}.trace-edge-casing{fill:none;stroke:#0f172a;stroke-width:5}.trace-edge{fill:none;stroke:#94a3b8;stroke-width:1.4}.trace-edge.evidence-observed{stroke:#4ade80}.trace-edge.evidence-binding{stroke:#60a5fa}.trace-edge-label{display:none}.trace-arrow{fill:#94a3b8}.trace-arrow-observed{fill:#4ade80}.trace-arrow-binding{fill:#60a5fa}.state-active .trace-node-bar{fill:#22c55e}.state-waiting .trace-node-bar{fill:#fbbf24}.state-error .trace-node-bar{fill:#f87171}.state-stale .trace-node-bar{fill:#c084fc}.trace-node-bar{fill:#475569}';
 return {project,layout,route,mermaid,createView,fileIdentity,neighbours,matches,LANES,EVIDENCE,LAYER_COLOURS,SIZE:{W,H}};
})();
if(typeof module!=='undefined')module.exports=SmelterTraceGraph;
