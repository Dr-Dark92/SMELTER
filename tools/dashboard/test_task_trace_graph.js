const {test}=require('node:test'),assert=require('node:assert/strict');
const G=require('./task_trace_graph.js'),W=require('./task_trace_workbench.js');
const now='2026-10-27T12:00:10.000Z';
const snapshot=()=>({available:true,binding:{session_id:'ses_root',workspace_id:'ws1',directory:'C:/Project'},task_id:'msg_turn',task_id_source:'Native OpenCode turn (Melty ID not supplied)',native_turn_id:'msg_turn',
 workspace_root:'C:\\Work\\Copy',observed_at:now,index_revision:'f'.repeat(64),index_updated_at:'2026-10-27T12:00:00.000Z',
 status:{phase:'using_tool',task_outcome:'in_progress',quiet_seconds:4},
 sessions:[{session_id:'ses_root',state:'waiting_child',model:'qwen-fixture',provider:'ollama'},{session_id:'ses_a',parent_id:'ses_root',state:'using_tool',model:'qwen-fixture'},{session_id:'ses_b',parent_id:'ses_root',state:'using_tool'}],
 tools:[{session_id:'ses_a',call_id:'c1',tool:'smelter_read_coding_file',phase:'running',started_at:'2026-10-27T12:00:00.000Z',updated_at:'2026-10-27T12:00:01.000Z',file:'C:\\Work\\Copy\\Mods\\Controller.lua',indexed_sha256:'a'.repeat(64),index_updated_at:'2026-10-27T12:00:00.000Z'},
  {session_id:'ses_b',call_id:'c2',tool:'edit',phase:'completed',updated_at:'2026-10-27T12:00:05.000Z',file:'c:/work/copy/mods/controller.lua'},
  {session_id:'ses_b',call_id:'c3',tool:'edit',phase:'running',updated_at:'2026-10-27T12:00:06.000Z',file:'C:/Work/Copy/other/controller.lua'},
  {session_id:'ses_root',call_id:'c4',tool:'task',phase:'running',updated_at:'2026-10-27T12:00:00.000Z'},
  {session_id:'ses_root',call_id:'c5',tool:'skill',phase:'completed',updated_at:'2026-10-27T11:59:00.000Z'}],
 skills:['smelter-debugging'],permissions:[{id:'per_1',session_id:'ses_b',kind:'external_directory',paths:['C:/Elsewhere']}],questions:[],permission_source:'ACP live requests',
 ollama:{connection:'connected',loaded_models:[{name:'qwen-fixture',context_length:131072}],scope:'host-wide'},
 validation:[{profile:'lua',stage:'RED',current:true,workspace_tests_stage:'GREEN',acceptance_stage:'RED'}]});
const byId=(g,id)=>g.nodes.find(n=>n.id===id),edge=(g,s,t)=>g.edges.filter(e=>e.source===s&&e.target===t);

test('projects the requested component path with evidence-labelled edges',()=>{const g=G.project(snapshot(),{now});
 for(const id of ['melty','opencode','ollama','model:qwen-fixture','smelter','skill:smelter-debugging','workspace','test:lua'])assert.ok(byId(g,id),id);
 assert.equal(edge(g,'melty','opencode')[0].evidence,'binding');assert.equal(edge(g,'opencode','ollama')[0].evidence,'observed');
 assert.equal(edge(g,'ollama','model:qwen-fixture')[0].evidence,'observed');assert.equal(edge(g,'opencode','smelter')[0].evidence,'inferred');
 assert.match(byId(g,'melty').detail['Melty task ID'],/not integrated/)});
test('concurrent child sessions stay parallel branches and waits attach to the blocked session',()=>{const g=G.project(snapshot(),{now});
 assert.equal(edge(g,'session:ses_root','session:ses_a')[0].relation,'delegated child session');assert.ok(edge(g,'session:ses_root','session:ses_b').length);
 assert.equal(edge(g,'session:ses_a','session:ses_b').length,0);assert.equal(byId(g,'tool:ses_a:smelter_read_coding_file').state,'active');
 assert.equal(byId(g,'session:ses_b').state,'waiting');assert.equal(edge(g,'wait:access:per_1','session:ses_b')[0].evidence,'observed')});
test('file identity folds Windows case and separators but keeps distinct folders apart',()=>{const g=G.project(snapshot(),{now});const files=g.nodes.filter(n=>n.kind==='file');
 assert.equal(files.length,2);assert.ok(byId(g,'file:ws1:mods/controller.lua'));assert.ok(byId(g,'file:ws1:other/controller.lua'));
 const merged=byId(g,'file:ws1:mods/controller.lua');assert.equal(merged.detail.Operations,'2')});
test('a write after the index observation marks the hash as stale',()=>{const g=G.project(snapshot(),{now});const file=byId(g,'file:ws1:mods/controller.lua');
 assert.equal(file.state,'active');const done=snapshot();done.status.phase='completed';done.tools[0].phase='completed';const after=byId(G.project(done,{now}),'file:ws1:mods/controller.lua');
 assert.equal(after.state,'stale');assert.match(after.detail['Hash freshness'],/may be stale/)});
test('loaded skills are evidence of loading only and frozen RED stays an error',()=>{const g=G.project(snapshot(),{now});
 assert.match(byId(g,'skill:smelter-debugging').detail.Evidence,/not proof/);assert.equal(byId(g,'test:lua').state,'error');assert.equal(byId(g,'test:lua').detail['Editable tests'],'GREEN')});
test('ended responses stop showing active work and unavailable data stays visible',()=>{const done=snapshot();done.status={phase:'completed',task_outcome:'changes_needed'};
 const g=G.project(done,{now});assert.ok(!g.nodes.some(n=>n.state==='active'));assert.equal(byId(g,'task').detail['Task outcome'],'changes_needed');
 const empty=G.project({available:false,reason:'Bind a session'});assert.deepEqual(empty.nodes,[]);assert.deepEqual(empty.notes,['Bind a session']);
 const quiet=snapshot();quiet.sessions=[{session_id:'ses_root',state:'awaiting_model'}];assert.equal(edge(G.project(quiet,{now}),'opencode','ollama')[0].evidence,'inferred')});
// A Qwen-sized turn: a root and `children` delegated sessions, each with tools touching shared and own files.
const qwenRun=(children,toolsPer=3)=>{const data=snapshot();data.sessions=[{session_id:'ses_root',state:'waiting_child',model:'qwen-fixture',provider:'ollama'}];data.tools=[{session_id:'ses_root',call_id:'t0',tool:'task',phase:'running',updated_at:now},{session_id:'ses_root',call_id:'s0',tool:'skill',phase:'completed',updated_at:now}];
 const verbs=['read','edit','grep','smelter_read_coding_file','write','glob'];
 for(let c=0;c<children;c++){const id='ses_c'+c;data.sessions.push({session_id:id,parent_id:'ses_root',state:'using_tool',model:c%2?'qwen-fixture':'qwen-small'});
  for(let t=0;t<toolsPer;t++)data.tools.push({session_id:id,call_id:id+'_'+t,tool:verbs[(c+t)%verbs.length],phase:t%2?'completed':'running',updated_at:now,file:'C:/Work/Copy/Mods/'+(t===0?'shared':id)+'_'+t%2+'.lua'})}
 data.permissions=[{id:'per_1',session_id:'ses_c0',kind:'external_directory',paths:['C:/Elsewhere']}];return data};
const rect=(n,pad=0)=>({x0:n.x-pad,y0:n.y-pad,x1:n.x+n.w+pad,y1:n.y+n.h+pad});
const segments=placed=>placed.points.slice(1).map((b,i)=>[placed.points[i],b]);
// Property checks shared by every fixture size.
function assertClean(g,positions){const boxes=[...positions.nodes].map(([id,n])=>[id,rect(n)]);
 for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){const a=boxes[i][1],b=rect(positions.nodes.get(boxes[j][0]),-0);
  assert.ok(a.x1+8<=b.x0||b.x1+8<=a.x0||a.y1+8<=b.y0||b.y1+8<=a.y0,'nodes overlap: '+boxes[i][0]+' / '+boxes[j][0])}
 const runs=[];
 for(const e of g.edges){const placed=positions.edges.get(e.id);assert.ok(placed,'edge routed: '+e.id);
  const [first,last]=[placed.points[0],placed.points.at(-1)],src=rect(positions.nodes.get(e.source)),dst=rect(positions.nodes.get(e.target));
  const onBorder=(p,r)=>p[0]>=r.x0&&p[0]<=r.x1&&(p[1]===r.y0||p[1]===r.y1);assert.ok(onBorder(first,src),'starts on source box: '+e.id);assert.ok(onBorder(last,dst),'ends on target box: '+e.id);
  for(const [a,b] of segments(placed)){assert.ok(a[0]===b[0]||a[1]===b[1],'orthogonal: '+e.id);
   for(const [id,r] of boxes){const lo=[Math.min(a[0],b[0]),Math.min(a[1],b[1])],hi=[Math.max(a[0],b[0]),Math.max(a[1],b[1])];
    assert.ok(!(lo[0]<r.x1&&hi[0]>r.x0&&lo[1]<r.y1&&hi[1]>r.y0)&&!(a[0]===b[0]&&a[0]>r.x0&&a[0]<r.x1&&lo[1]<r.y1&&hi[1]>r.y0)&&!(a[1]===b[1]&&a[1]>r.y0&&a[1]<r.y1&&lo[0]<r.x1&&hi[0]>r.x0),'edge '+e.id+' crosses node '+id)}
   runs.push({id:e.id,bundle:e.source+'|'+e.evidence,a,b})}}
 // No two connectors share a stretch of line (crossing at a point is allowed); only a same-source,
 // same-evidence bus may share its trunk.
 for(let i=0;i<runs.length;i++)for(let j=i+1;j<runs.length;j++){const p=runs[i],q=runs[j];if(p.id===q.id||p.bundle===q.bundle)continue;
  const vertical=s=>s.a[0]===s.b[0],span=(s,k)=>[Math.min(s.a[k],s.b[k]),Math.max(s.a[k],s.b[k])];
  if(vertical(p)!==vertical(q))continue;const axis=vertical(p)?0:1,along=1-axis;if(Math.abs(p.a[axis]-q.a[axis])>=1)continue;
  const [p0,p1]=span(p,along),[q0,q1]=span(q,along);assert.ok(Math.min(p1,q1)-Math.max(p0,q0)<=0.5,'connectors overlap: '+p.id+' / '+q.id)}}
test('layered layout keeps nodes apart and routes every edge orthogonally around node boxes',()=>{
 for(const [children,tools] of [[0,1],[2,3],[4,3],[6,3],[7,3]]){const g=G.project(qwenRun(children,tools),{now});assert.ok(g.nodes.length>=10&&g.nodes.length<=64,'fixture size '+children+'x'+tools+'='+g.nodes.length);
  assertClean(g,G.layout(g))}
 const g=G.project(snapshot(),{now});assertClean(g,G.layout(g))});
test('layers flow top-down from the task, waits hang below the session they block and wide layers wrap',()=>{const g=G.project(qwenRun(14,3),{now}),p=G.layout(g);
 const y=id=>p.nodes.get(id).y;assert.ok(y('task')<y('opencode'));assert.ok(y('opencode')<y('session:ses_root'));assert.ok(y('session:ses_root')<y('session:ses_c3'));
 assert.ok(y('session:ses_c0')<y('wait:access:per_1'));const access=p.edges.get(edge(g,'wait:access:per_1','session:ses_c0')[0].id).points;assert.ok(access[0][1]>access.at(-1)[1],'wait arrow points up into its session');
 const perLayer=new Map();for(const n of p.nodes.values())perLayer.set(n.y,(perLayer.get(n.y)||0)+1);assert.ok(Math.max(...perLayer.values())<=10)});
test('layout is deterministic and keeps crossings low on a tree-shaped run',()=>{const g=G.project(qwenRun(6,2),{now}),a=G.layout(g),b=G.layout(G.project(qwenRun(6,2),{now}));
 assert.deepEqual([...a.nodes],[...b.nodes]);assert.deepEqual([...a.edges].map(([k,v])=>[k,v.points]),[...b.edges].map(([k,v])=>[k,v.points]));
 const tree={...snapshot(),tools:[],permissions:[],validation:[],skills:[]};assert.equal(G.layout(G.project(tree,{now})).crossings,0)});
test('a heartbeat with one more node keeps the existing left-to-right order in each layer',()=>{const first=G.project(qwenRun(5,3),{now}),before=G.layout(first);
 const next=qwenRun(5,3);next.tools.push({session_id:'ses_c2',call_id:'late',tool:'webfetch',phase:'running',updated_at:now});const g=G.project(next,{now}),after=G.layout(g,before);
 const order=p=>{const rows=new Map();for(const [id,n] of p.nodes){if(!rows.has(n.y))rows.set(n.y,[]);rows.get(n.y).push([n.x,id])}return [...rows.values()].map(r=>r.sort((a,b)=>a[0]-b[0]).map(x=>x[1]))};
 const rank=new Map();for(const row of order(after))row.forEach((id,i)=>rank.set(id,i));
 for(const row of order(before)){const kept=row.filter(id=>rank.has(id));assert.deepEqual([...kept].sort((a,b)=>rank.get(a)-rank.get(b)),kept)}
 assert.ok(after.nodes.has('tool:ses_c2:webfetch'));assertClean(g,after)});
test('connector paths are orthogonal with rounded corners',()=>{const d=G.route([[0,0],[0,20],[40,20],[40,50]]);assert.match(d,/^M 0 0 L 0 14 Q 0 20 6 20 L 34 20 Q 40 20 40 26 L 40 50$/)});
test('graph size is bounded for large turns',()=>{const big=snapshot();big.tools=Array.from({length:96},(_,i)=>({session_id:'ses_root',call_id:'c'+i,tool:'t'+i,phase:'completed',updated_at:now,file:'C:/Work/Copy/f'+i+'.lua'}));
 const g=G.project(big,{now});assert.ok(g.nodes.filter(n=>n.kind==='file').length<=40);assert.ok(g.nodes.filter(n=>n.kind==='tool').length<=40);assert.ok(g.truncated);assert.ok(g.notes.length)});
test('labels stay plain data and Mermaid export neutralises markup',()=>{const bad=snapshot();bad.tools[0].file='C:/Work/Copy/<img src=x onerror=alert(1)>"].lua';bad.skills=['x"]-->evil'];
 const g=G.project(bad,{now}),text=G.mermaid(g);assert.doesNotMatch(text,/<img/);assert.doesNotMatch(text,/"\]-->evil/);assert.match(text,/^flowchart LR/)});
test('search and neighbourhood use identities, paths and hashes',()=>{const g=G.project(snapshot(),{now});
 assert.ok(G.matches(byId(g,'file:ws1:mods/controller.lua'),'aaaaaaaa'));const near=G.neighbours(g,'session:ses_b');assert.ok(near.has('wait:access:per_1'));assert.ok(near.has('session:ses_root'))});
test('three clocks stay separate and waits never invent a retry or rate limit',()=>{const data=snapshot();data.observer_age_seconds=20;data.observations_stale=true;data.status.possible_stall=true;data.status.quiet_seconds=130;
 const clock=W.clocks(data,'disconnected; reconnecting',Date.parse(now)-14000,Date.parse(now));assert.equal(clock.socket,14);assert.equal(clock.observer,34);assert.equal(clock.native,130);assert.ok(clock.socketDown);
 const text=W.waits(data,null,clock).map(w=>w.title+' '+w.text).join('\n');assert.match(text,/Trace feed disconnected/);assert.match(text,/Observer delayed/);assert.match(text,/Possible stall/);assert.match(text,/Access request/);
 assert.match(text,/retries cannot be observed/);assert.doesNotMatch(text,/Provider retry observed/);
 assert.match(W.waits(data,{binding:{},enabled:true,connection:'connected',task_state:'retry',status_source:'native'},clock).map(w=>w.title).join(),/Provider retry observed/)});
test('exports contain only allowlisted identities and evidence',()=>{const data={...snapshot(),prompt:'private-prompt',reasoning:'private-thought'};const out=JSON.stringify(W.exportable(data,G.project(data,{now})));
 assert.doesNotMatch(out,/private-/);assert.match(out,/smelter\.trace\.chart\.v1/);assert.match(out,/msg_turn/)});
test('registered artifacts join only their own task and keep observed versus declared producers apart',()=>{const art=(id,extra)=>({id,task:{session_id:'ses_root',native_turn_id:'msg_turn'},workspace_id:'ws1',relative_path:'Mods/Controller.lua',kind:'image',mime:'image/png',bytes:10,sha256:'c'.repeat(64),state:'current',producer:{source:'declared in dashboard (no observed producing call)'},derived_from:[],...extra});
 const artifacts=[art('a1',{producer:{source:'observed tool call naming this path',tool:'edit',session_id:'ses_b',call_id:'c2'}}),art('a2',{state:'changed',derived_from:['a1']}),art('a3',{task:{session_id:'ses_root',native_turn_id:'msg_other'}})];
 const g=G.project(snapshot(),{now,artifacts});assert.ok(byId(g,'artifact:a1'));assert.ok(!byId(g,'artifact:a3'));assert.equal(byId(g,'artifact:a2').state,'stale');
 assert.equal(edge(g,'tool:ses_b:edit','artifact:a1')[0].evidence,'observed');assert.equal(edge(g,'file:ws1:mods/controller.lua','artifact:a1')[0].evidence,'binding');assert.equal(edge(g,'artifact:a1','artifact:a2')[0].relation,'converted into (declared lineage)')});
test('an unbound or stopped native monitor reports retries as unobservable, not absent',()=>{const clock=W.clocks(snapshot(),'connected',Date.parse(now),Date.parse(now));
 for(const native of [{task_state:'retry'},{binding:{},enabled:false,connection:'stopped',task_state:'retry'}]){const text=W.waits(snapshot(),native,clock).map(w=>w.title+' '+w.text).join();assert.match(text,/cannot be observed/);assert.doesNotMatch(text,/None observed|Provider retry observed/)}});
test('observer age grows while no frames arrive',()=>{const data=snapshot();data.observer_age_seconds=0;const clock=W.clocks(data,'disconnected; reconnecting',Date.parse(now)-20000,Date.parse(now));assert.equal(clock.observer,20);assert.ok(clock.observerDelayed)});
test('workspace containment edges are flagged so the view can collapse them and the rest still routes cleanly',()=>{const g=G.project(qwenRun(6,3),{now});
 const contained=g.edges.filter(e=>e.containment);assert.ok(contained.length>=5);assert.ok(contained.every(e=>e.source==='workspace'&&e.relation==='inside bound workspace'&&e.evidence==='binding'));
 const drawn={nodes:g.nodes,edges:g.edges.filter(e=>!e.containment)},p=G.layout(drawn);assertClean(drawn,p);assert.ok(!contained.some(e=>p.edges.has(e.id)))});
test('each layer gets a tinted band and its nodes carry the same layer colour',()=>{
 class El{constructor(tag){this.tag=tag;this.attrs={};this.children=[];this.textContent=''}setAttribute(k,v){this.attrs[k]=String(v)}removeAttribute(k){delete this.attrs[k]}append(...c){for(const n of c){n.parent=this;this.children.push(n)}}
  replaceChildren(...c){this.children=[];this.append(...c)}remove(){if(this.parent)this.parent.children=this.parent.children.filter(n=>n!==this)}}
 const doc={createElementNS:(_ns,tag)=>new El(tag)},host=new El('div'),view=G.createView(doc,host),g=G.project(qwenRun(3,2),{now});view.update(g);
 const all=n=>[n,...n.children.flatMap(all)],els=all(host),bands=els.filter(e=>e.attrs.class==='trace-layer-band'),p=G.layout({nodes:g.nodes,edges:g.edges.filter(e=>!e.containment)});
 assert.equal(bands.length,p.layers.length);bands.forEach((b,r)=>assert.equal(b.attrs.fill,G.LAYER_COLOURS[r%G.LAYER_COLOURS.length]));
 for(const n of els.filter(e=>e.attrs['data-node'])){const r=Number(n.attrs['data-layer']);assert.equal(n.attrs.style,'--layer-colour:'+G.LAYER_COLOURS[r%G.LAYER_COLOURS.length]);assert.equal(r,p.nodes.get(n.attrs['data-node']).layer)}});
