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
test('layout keeps existing positions stable as nodes arrive and frees slots after removal',()=>{const first=G.project(snapshot(),{now}),positions=G.layout(first);
 const before=new Map([...positions.slots].map(([k,v])=>[k,{...v}]));const next=snapshot();next.tools.push({session_id:'ses_a',call_id:'c9',tool:'grep',phase:'running',updated_at:now});
 G.layout(G.project(next,{now}),positions);for(const [id,place] of before)assert.deepEqual(positions.slots.get(id),place,id);assert.ok(positions.slots.has('tool:ses_a:grep'));
 const smaller=snapshot();smaller.tools=[];G.layout(G.project(smaller,{now}),positions);G.layout(G.project(smaller,{now}),positions);assert.ok(!positions.slots.has('tool:ses_a:grep'))});
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
