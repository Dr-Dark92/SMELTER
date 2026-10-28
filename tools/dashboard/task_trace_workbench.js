/* Full-screen trace workbench: live relationship graph, inspector, waits, files,
   validation and saved final charts. Fed by the existing trace socket; read-only. */
const SmelterTraceWorkbench=(()=>{
 const G=typeof SmelterTraceGraph!=='undefined'?SmelterTraceGraph:require('./task_trace_graph.js');
 const PHASES={telemetry_delayed:'Telemetry delayed',waiting_access:'Waiting for access',waiting_answer:'Waiting for answer',tool_budget_exhausted:'Tool budget exhausted',waiting_child:'Waiting for delegated task',awaiting_model:'Waiting for model / provider',using_tool:'Using tools',completed:'Response ended',cancelled:'Cancelled',failed:'Failed',unknown:'Unknown'};
 const OUTCOMES={in_progress:'In progress',changes_needed:'Changes needed',not_verified:'Not verified',checks_passed:'Checks passed (recorded scope)'};
 const el=(doc,tag,text,cls)=>{const n=doc.createElement(tag);if(text!==undefined&&text!==null)n.textContent=text;if(cls)n.className=cls;return n};
 const age=s=>s==null||!Number.isFinite(s)?'unknown':s<60?Math.round(s)+'s':Math.floor(s/60)+'m '+Math.round(s%60)+'s';
 const time=v=>{if(!v)return 'unknown';const d=new Date(v);return Number.isNaN(d.getTime())?String(v):d.toLocaleTimeString()};
 const STYLE=`
.trace-workbench{width:min(1500px,98vw);height:min(940px,96dvh);max-width:none;max-height:none;padding:0;background:var(--surface);color:var(--text);border:1px solid var(--border-strong);border-radius:var(--radius-lg);overflow:hidden}
.trace-workbench[open]{display:flex;flex-direction:column}
.tw-header,.tw-chips,.tw-banner{flex-shrink:0}
.tw-header{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;padding:12px 16px;border-bottom:1px solid var(--border)}
.tw-header h2{margin:0;font-size:16px;flex:1 1 220px}
.tw-chips{display:flex;flex-wrap:wrap;gap:6px;padding:8px 16px;border-bottom:1px solid var(--border);font-size:12px}
.tw-chip{border:1px solid var(--border);border-radius:999px;padding:3px 10px;background:var(--raised);max-width:100%;overflow-wrap:anywhere}
.tw-chip b{color:var(--muted);font-weight:600;margin-right:4px}
.tw-chip.warn{border-color:var(--warning);color:var(--warning)}.tw-chip.bad{border-color:var(--danger);color:var(--danger)}.tw-chip.good{border-color:var(--accent-line)}
.tw-main{flex:1 1 auto;display:grid;grid-template-columns:minmax(0,1fr) 360px;grid-template-rows:minmax(0,1fr) minmax(170px,34%);min-height:0}
.tw-graph{display:grid;grid-template-rows:auto minmax(0,1fr) auto;min-height:0;border-right:1px solid var(--border);border-bottom:1px solid var(--border);background:var(--bg)}
.tw-toolbar{display:flex;flex-wrap:wrap;gap:6px;padding:8px;border-bottom:1px solid var(--border)}
.tw-toolbar input{min-width:160px;flex:1 1 180px;max-width:300px}
.tw-toolbar button,.tw-tabs button,.tw-actions button{font-size:12px}
.tw-toolbar button[aria-pressed=true]{background:var(--active);border-color:var(--accent-line)}
.tw-legend{padding:4px 10px 6px;font-size:11px;color:var(--muted);display:flex;gap:4px 14px;flex-wrap:wrap;border-top:1px solid var(--border)}
.tw-legend svg{vertical-align:middle;margin-right:4px}
.trace-graph-svg{width:100%;height:100%;display:block;cursor:grab;touch-action:none}
.trace-lane-title{fill:var(--muted);font-size:12px;font-weight:600;letter-spacing:.04em}
.trace-node{cursor:pointer}
.trace-node rect:first-child{fill:var(--card);stroke:var(--border-strong);stroke-width:1}
.trace-node-bar{fill:var(--subtle)}
.trace-node-label{fill:var(--text);font-size:12px;font-weight:600}
.trace-node-sub{fill:var(--muted);font-size:10.5px}
.trace-node.state-active .trace-node-bar{fill:var(--accent)}.trace-node.state-active rect:first-child{stroke:var(--accent-line)}
.trace-node.state-waiting .trace-node-bar{fill:var(--warning)}.trace-node.state-waiting rect:first-child{stroke:var(--warning);stroke-dasharray:4 3}
.trace-node.state-error .trace-node-bar{fill:var(--danger)}.trace-node.state-error rect:first-child{stroke:var(--danger)}
.trace-node.state-stale .trace-node-bar{fill:#c084fc}.trace-node.state-linked .trace-node-bar{fill:var(--info)}
.trace-node.selected rect:first-child{stroke:var(--focus);stroke-width:2.5}
.trace-node.match rect:first-child{stroke:var(--info);stroke-width:2}
.trace-node:focus{outline:none}.trace-node:focus-visible rect:first-child{stroke:var(--focus);stroke-width:3}
.trace-node.dim,.trace-edge.dim{opacity:.18}
.trace-edge{fill:none;stroke:var(--subtle);stroke-width:1.3}
.trace-edge.evidence-observed{stroke:#6aa88e}.trace-edge.evidence-binding{stroke:var(--info)}.trace-edge.evidence-inferred{stroke:#8c91ba}
.trace-edge.related{stroke-width:2.6}
.trace-arrow{fill:var(--muted)}
.trace-edge-label{display:none;fill:var(--text);font-size:10.5px;paint-order:stroke;stroke:var(--bg);stroke-width:4px}
.trace-edge-label.shown{display:block}
.tw-inspector{grid-row:1/3;grid-column:2;overflow:auto;padding:12px 14px;font-size:13px}
.tw-inspector h3{margin:0 0 6px;font-size:14px;overflow-wrap:anywhere}
.tw-inspector dl{display:grid;grid-template-columns:max-content minmax(0,1fr);gap:4px 10px;margin:8px 0}
.tw-inspector dt{color:var(--muted)}.tw-inspector dd{margin:0;overflow-wrap:anywhere}
.tw-inspector ul{padding-left:18px;margin:4px 0}.tw-inspector li{margin:3px 0;overflow-wrap:anywhere}
.tw-bottom{display:grid;grid-template-rows:auto 1fr;min-height:0;border-right:1px solid var(--border)}
.tw-tabs{display:flex;gap:4px;padding:6px 8px;border-bottom:1px solid var(--border);flex-wrap:wrap}
.tw-tabs button[aria-selected=true]{background:var(--active);border-color:var(--accent-line)}
.tw-tabpanel{overflow:auto;padding:8px 12px;font-size:12.5px}
.tw-tabpanel table{width:100%;border-collapse:collapse}.tw-tabpanel td,.tw-tabpanel th{text-align:left;padding:4px 6px;border-bottom:1px solid var(--border);vertical-align:top;overflow-wrap:anywhere}
.tw-tabpanel th{color:var(--muted);font-weight:600}
.tw-wait{padding:6px 8px;margin:4px 0;border-left:3px solid var(--border-strong);background:var(--raised);border-radius:4px}
.tw-wait.warn{border-left-color:var(--warning)}.tw-wait.bad{border-left-color:var(--danger)}
.tw-muted{color:var(--muted)}
.tw-banner{padding:6px 16px;background:var(--info-soft);font-size:12px;display:flex;gap:10px;align-items:center;flex-wrap:wrap}
@media (max-width:900px){.trace-workbench{width:100vw;height:100dvh;border:0;border-radius:0}
 .tw-header{padding:8px 12px}.tw-header h2{flex-basis:100%}.tw-actions button{min-height:30px;padding:3px 8px}
 .tw-chips{flex-wrap:nowrap;overflow-x:auto;padding:6px 12px}.tw-chip{white-space:nowrap;max-width:none}
 .tw-main{display:block;overflow:auto}.tw-graph{height:56dvh;border-right:0}.tw-inspector{border-bottom:1px solid var(--border);max-height:none}
 .tw-bottom{min-height:320px;border-right:0}.tw-toolbar input{max-width:none}}
@media (prefers-reduced-motion:no-preference){.trace-node rect:first-child{transition:stroke var(--fast) var(--ease)}}`;
 function definitions(doc,host,entries){const dl=el(doc,'dl');for(const [k,v] of entries){dl.append(el(doc,'dt',k),el(doc,'dd',v==null||v===''?'—':String(v)))}host.append(dl);return dl}
 /* Pure helpers used by the view and the tests. */
 function clocks(data,feed,lastFrameAt,now=Date.now()){
  const status=data?.status||{},frame=lastFrameAt?Math.round((now-lastFrameAt)/1000):null;
  const sinceObserved=data?.observed_at?Math.max(0,(now-Date.parse(data.observed_at))/1000):0;
  // The observer's age keeps growing between frames, so a dead socket cannot freeze it at '0s'.
  const observer=data?.observer_age_seconds==null?null:data.observer_age_seconds+(frame??0);
  return {native:status.quiet_seconds==null?null:status.quiet_seconds+Math.round(sinceObserved),observer,socket:frame,feed,
   possibleStall:!!status.possible_stall,observerDelayed:!!data?.observations_stale||observer>15,socketDown:!/^connected/.test(feed||'')}
 }
 function waits(data,native,clock){
  const out=[],status=data?.status||{};
  if(clock.socketDown)out.push({level:'bad',title:'Trace feed '+clock.feed,text:'Telemetry is disconnected; task state below may be outdated. Reconnecting does not resubmit work.'});
  if(clock.observerDelayed)out.push({level:'warn',title:'Observer delayed ('+age(clock.observer)+')',text:'The collector has not refreshed for more than fifteen seconds. Current task activity is unknown.'});
  for(const p of data?.permissions||[])out.push({level:'warn',title:'Access request · '+p.kind,text:'Session '+p.session_id+' · '+((p.paths||[]).join(', ')||'no paths reported')+'. Decide in the native client; the trace never approves access.'});
  for(const q of data?.questions||[])out.push({level:'warn',title:'Question pending',text:'Session '+q.session_id+' waits for an answer in the native client.'});
  if(status.phase==='awaiting_model')out.push({level:'info',title:'Waiting for model / provider',text:'No running tool. Quiet for '+age(clock.native)+'. This does not identify a rate limit, deadlock or GPU failure.'});
  // Retry evidence needs a bound, enabled, connected native monitor; otherwise it is unavailable, not absent.
  native=native&&native.binding&&native.enabled&&native.connection==='connected'?native:null;
  if(native?.task_state==='retry')out.push({level:'warn',title:'Provider retry observed',text:'Native session status reported retry ('+(native.status_source||'native lifecycle')+'). Attempt count and retry time are not recorded by the monitor.'});
  else out.push({level:'info',title:'Retry / rate limit',text:native?'None observed in native session status ('+(native.status_source||'native lifecycle')+').':'Native lifecycle status unavailable; retries cannot be observed. Silence alone is not a rate limit.'});
  if(status.possible_stall)out.push({level:'warn',title:'Possible stall',text:'No native activity for '+age(clock.native)+' (threshold '+(status.stall_threshold_seconds||120)+'s). This is a clue, not a diagnosis.'});
  if(status.phase==='tool_budget_exhausted')out.push({level:'bad',title:'Tool budget exhausted',text:'SMELTER reported its tool-call budget exhausted.'});
  if(status.recovery_redirect)out.push({level:'warn',title:'Recovery checkpoint',text:status.recovery_hint||''});
  if(data?.permission_source==='unavailable')out.push({level:'info',title:'Permission feed unavailable',text:'A quiet tool may be waiting for an access decision that the trace cannot see.'});
  const active=(data?.tools||[]).filter(t=>['pending','running'].includes(t.phase));
  if(!['completed','cancelled','failed'].includes(status.phase))for(const t of active.slice(0,8)){const s=(Date.now()-Date.parse(t.started_at||t.updated_at))/1000;out.push({level:s>=120?'warn':'info',title:'Active · '+t.tool+' ('+t.phase+')',text:'Running for '+age(s)+' · session '+t.session_id})}
  return out;
 }
 function create(doc=document,api=null){
  if(!doc.getElementById('trace-workbench-style')){const style=el(doc,'style',STYLE);style.id='trace-workbench-style';doc.head.append(style)}
  const dialog=el(doc,'dialog',null,'trace-workbench');dialog.setAttribute('aria-labelledby','traceWorkbenchTitle');
  const header=el(doc,'header',null,'tw-header'),title=el(doc,'h2','Trace workbench');title.id='traceWorkbenchTitle';
  const actions=el(doc,'div',null,'tw-actions'),exportJson=el(doc,'button','Export JSON'),exportMermaid=el(doc,'button','Export Mermaid'),exportSvg=el(doc,'button','Export SVG'),close=el(doc,'button','Close');close.className='quiet-button';
  actions.append(exportJson,exportMermaid,exportSvg,close);header.append(title,actions);
  const chips=el(doc,'div',null,'tw-chips');chips.setAttribute('role','status');chips.setAttribute('aria-live','polite');
  const banner=el(doc,'div',null,'tw-banner');banner.hidden=true;const bannerText=el(doc,'span'),live=el(doc,'button','Return to live trace');banner.append(bannerText,live);
  const main=el(doc,'div',null,'tw-main'),graphBox=el(doc,'div',null,'tw-graph'),toolbar=el(doc,'div',null,'tw-toolbar');
  const search=el(doc,'input');search.type='search';search.placeholder='Search nodes, IDs, paths, hashes…';search.setAttribute('aria-label','Search the trace graph');
  const fit=el(doc,'button','Fit'),zin=el(doc,'button','+'),zout=el(doc,'button','−'),tidy=el(doc,'button','Tidy layout'),focus=el(doc,'button','Focus neighbourhood');
  zin.setAttribute('aria-label','Zoom in');zout.setAttribute('aria-label','Zoom out');focus.setAttribute('aria-pressed','false');
  toolbar.append(search,fit,zin,zout,tidy,focus);
  const legend=el(doc,'div',null,'tw-legend');
  for(const [evidence,label] of Object.entries(G.EVIDENCE)){const item=el(doc,'span');const s=doc.createElementNS('http://www.w3.org/2000/svg','svg');s.setAttribute('width','30');s.setAttribute('height','8');const l=doc.createElementNS('http://www.w3.org/2000/svg','line');Object.entries({x1:0,y1:4,x2:30,y2:4,class:'trace-edge evidence-'+evidence,'stroke-dasharray':{observed:'',binding:'9 5',inferred:'2 5'}[evidence]}).forEach(([k,v])=>l.setAttribute(k,v));s.append(l);item.append(s,doc.createTextNode(label));legend.append(item)}
  legend.append(el(doc,'span','Bar: green active · amber waiting · red error · violet stale'));
  graphBox.append(toolbar,legend);
  const inspector=el(doc,'aside',null,'tw-inspector');inspector.setAttribute('aria-label','Selected node details');inspector.setAttribute('aria-live','polite');
  const bottom=el(doc,'section',null,'tw-bottom'),tabs=el(doc,'div',null,'tw-tabs'),panel=el(doc,'div',null,'tw-tabpanel');tabs.setAttribute('role','tablist');panel.setAttribute('role','tabpanel');panel.tabIndex=0;
  const TABS=[['waits','Waits & clocks'],['timeline','Timeline'],['files','Files'],['tests','Outcome & tests'],['charts','Saved charts']];let tab='waits';
  const tabButtons=TABS.map(([id,label])=>{const b=el(doc,'button',label);b.setAttribute('role','tab');b.dataset.tab=id;b.onclick=()=>{tab=id;renderTab()};b.onkeydown=e=>{const i=TABS.findIndex(t=>t[0]===tab);if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();tab=TABS[(i+(e.key==='ArrowRight'?1:TABS.length-1))%TABS.length][0];renderTab();tabButtons.find(x=>x.dataset.tab===tab).focus()}};return b});
  tabs.append(...tabButtons);bottom.append(tabs,panel);main.append(graphBox,inspector,bottom);dialog.append(header,chips,banner,main);doc.body.append(dialog);
  let data=null,feed='connecting',lastFrameAt=0,native=null,charts=null,chartsError='',viewing=null,graph={nodes:[],edges:[]},lastRendered='';
  const view=G.createView(doc,graphBox,{onSelect:node=>renderInspector(node)});
  if(typeof SmelterTraceArtifacts!=='undefined')SmelterTraceArtifacts.configure(api,()=>{lastRendered='';draw();const id=view.selected();renderInspector(id?graph.nodes.find(n=>n.id===id):null,true)});graphBox.insertBefore(view.element,legend);
  const current=()=>viewing?viewing.trace:data;
  function chip(label,value,level){const c=el(doc,'span',null,'tw-chip'+(level?' '+level:''));c.append(el(doc,'b',label),doc.createTextNode(value));chips.append(c)}
  function renderChips(){
   chips.replaceChildren();const d=current(),status=d?.status||{},clock=clocks(d,viewing?'saved chart':feed,viewing?null:lastFrameAt);
   if(!d?.available){chip('Trace',d?.reason||'Waiting for the first snapshot','warn');chip('Feed',feed,clock.socketDown?'bad':'');return}
   chip('Task',(d.task_id||'no submitted turn')+' · '+d.task_id_source);
   chip('Native turn',d.native_turn_id||'not observed');chip('Session',d.binding?.session_id||'—');chip('Workspace',d.binding?.workspace_id||'—');
   chip('Response',PHASES[status.phase]||status.phase||'unknown',status.phase==='failed'?'bad':['waiting_access','waiting_answer','telemetry_delayed','tool_budget_exhausted'].includes(status.phase)?'warn':'');
   chip('Task outcome',OUTCOMES[status.task_outcome]||status.task_outcome||'unknown',status.task_outcome==='changes_needed'?'bad':status.task_outcome==='checks_passed'?'good':status.task_outcome==='not_verified'?'warn':'');
   if(!viewing){chip('Native activity',age(clock.native)+' ago',clock.possibleStall?'warn':'');chip('Observer',clock.observer==null?'unknown':age(clock.observer)+' old',clock.observerDelayed?'warn':'');chip('Feed',feed+(clock.socket!=null?' · frame '+age(clock.socket)+' ago':''),clock.socketDown?'bad':'')}
   else chip('Saved',viewing.reason+' · '+time(viewing.saved_at));
  }
  function edgesOf(node){return graph.edges.filter(e=>e.source===node.id||e.target===node.id)}
  function label(id){return graph.nodes.find(n=>n.id===id)?.label||id}
  // Details refresh with each heartbeat; the artifact section (forms, previews) only when the selection or artifact list changes.
  const details=el(doc,'div'),extra=el(doc,'div');inspector.append(details,extra);let extraKey=null;
  function renderInspector(node,force=false){
   const target=details;target.replaceChildren();
   const key=node&&['file','artifact'].includes(node.kind)?node.id+':'+(viewing?.id||'live'):null;
   if(force||key!==extraKey){extraKey=key;extra.replaceChildren();if(typeof SmelterTraceArtifacts!=='undefined'){SmelterTraceArtifacts.release();if(key)SmelterTraceArtifacts.inspect(node,extra,doc,current(),!!viewing)}}
   if(!node){target.append(el(doc,'h3','Inspector'),el(doc,'p','Select a node (click, or Tab then Enter) to see its identities, evidence and relationships. Arrow keys move between nodes; Esc clears.','tw-muted'));
    if(graph.notes?.length){const ul=el(doc,'ul');for(const n of graph.notes)ul.append(el(doc,'li',n));target.append(el(doc,'h3','Graph limits'),ul)}
    target.append(el(doc,'h3','Reading this graph'),el(doc,'p','Nodes are components, sessions, tool groups, files, tests and waits observed in the current snapshot. Edges carry an evidence class; a registered tool or loaded skill is not proof of an operation, and branches may run concurrently.','tw-muted'));return}
   target.append(el(doc,'h3',node.label),el(doc,'p',node.kind+' · '+node.state,'tw-muted'));
   definitions(doc,target,Object.entries(node.detail||{}));
   if(node.calls?.length){target.append(el(doc,'h3','Calls ('+node.calls.length+')'));const ul=el(doc,'ul');for(const c of node.calls.slice(0,30))ul.append(el(doc,'li',c.phase+' · '+time(c.updated_at)+(c.error_code?' · '+c.error_code:'')+(c.file?' · '+c.file.split(/[\\/]/).at(-1):'')+' · '+c.call_id));target.append(ul)}
   const related=edgesOf(node);if(related.length){target.append(el(doc,'h3','Relationships'));const ul=el(doc,'ul');for(const e of related){const li=el(doc,'li',(e.source===node.id?'→ '+label(e.target):'← '+label(e.source))+' · '+e.relation+' ('+G.EVIDENCE[e.evidence]+')');ul.append(li)}target.append(ul)}
  }
  function table(headers,rows){const t=el(doc,'table'),h=el(doc,'tr');for(const x of headers)h.append(el(doc,'th',x));t.append(h);for(const r of rows){const tr=el(doc,'tr');for(const x of r)tr.append(el(doc,'td',x==null?'—':String(x)));t.append(tr)}return t}
  function renderTab(){
   for(const b of tabButtons){b.setAttribute('aria-selected',String(b.dataset.tab===tab));b.tabIndex=b.dataset.tab===tab?0:-1}
   panel.replaceChildren();const d=current();
   if(tab==='charts')return renderCharts();
   if(!d?.available){panel.append(el(doc,'p',d?.reason||'No snapshot.','tw-muted'));return}
   if(tab==='waits'){const clock=clocks(d,viewing?'saved chart':feed,viewing?null:lastFrameAt);
    panel.append(el(doc,'p','Three separate clocks: last native task activity '+age(clock.native)+' · observer refresh '+(clock.observer==null?'unknown':age(clock.observer))+' · last socket frame '+(clock.socket==null?'n/a':age(clock.socket))+'.','tw-muted'));
    for(const w of waits(d,viewing?null:native,clock)){const box=el(doc,'div',null,'tw-wait '+(w.level==='info'?'':w.level));box.append(el(doc,'strong',w.title),el(doc,'div',w.text));panel.append(box)}}
   else if(tab==='timeline'){panel.append(el(doc,'p','Sampled about every two seconds (latest 96 tool rows); not a lossless log.','tw-muted'));panel.append(table(['Updated','Tool','Phase','Session','File','Error'],(d.tools||[]).map(t=>[time(t.updated_at),t.tool,t.phase,t.session_id,t.file?t.file.split(/[\\/]/).at(-1):'',t.error_code||''])))}
   else if(tab==='files'){const files=graph.nodes.filter(n=>n.kind==='file');panel.append(el(doc,'p','Hashes are index observations with capture time, not proof of the bytes a tool read. Shell command contents are not inspected.','tw-muted'));
    if(!files.length)panel.append(el(doc,'p','No named file activity observed this turn.'));else panel.append(table(['File','Workspace-relative','State','Indexed SHA-256','Index captured','Last activity'],files.map(f=>[f.label,f.detail['Workspace-relative'],f.state,f.detail['Indexed SHA-256'],f.detail['Index captured'],f.detail['Last activity']])));
    if(typeof SmelterTraceArtifacts!=='undefined')SmelterTraceArtifacts.render(panel,doc)}
   else if(tab==='tests'){const status=d.status||{};
    panel.append(el(doc,'p','Response lifecycle: '+(PHASES[status.phase]||status.phase)+'. Task outcome: '+(OUTCOMES[status.task_outcome]||status.task_outcome||'unknown')+'.'));
    if(status.outcome_hint)panel.append(el(doc,'p',status.outcome_hint));
    panel.append(el(doc,'p','An ended response, a successful tool or passing editable tests do not establish task success or in-game behaviour. Frozen acceptance is authoritative.','tw-muted'));
    panel.append(table(['Profile','Overall','Editable tests','Frozen acceptance','Tree'],(d.validation||[]).map(v=>[v.profile,v.stage,v.workspace_tests_stage||'not reported',v.acceptance_stage||'not reported',v.current?'current':'stale'])));
    if(!(d.validation||[]).length)panel.append(el(doc,'p','No validation receipts observed.'))}
  }
  async function loadCharts(){if(!api)return;try{const r=await api('/api/task-trace/charts');charts=r.charts||[];chartsError=''}catch(e){chartsError=e.message}if(tab==='charts')renderTab()}
  function renderCharts(){
   panel.append(el(doc,'p','Final task charts are saved when a response ends, is cancelled or fails, and when a newer turn replaces an unfinished one. Paths are rechecked against current access before display.','tw-muted'));
   const refresh=el(doc,'button','Refresh saved charts');refresh.onclick=loadCharts;panel.append(refresh);
   if(chartsError)panel.append(el(doc,'p',chartsError));
   if(!charts){panel.append(el(doc,'p','Loading…'));if(api)loadCharts();return}
   if(!charts.length){panel.append(el(doc,'p','No saved charts yet.'));return}
   const t=table(['Saved','Reason','Task','Response','Outcome','Index revision',''],[]);
   for(const c of charts){const tr=el(doc,'tr');for(const x of [time(c.saved_at),c.reason,c.trace.task_id||'—',PHASES[c.trace.status?.phase]||c.trace.status?.phase,OUTCOMES[c.trace.status?.task_outcome]||c.trace.status?.task_outcome,(c.trace.index_revision||'—').slice(0,12)])tr.append(el(doc,'td',x));
    const td=el(doc,'td'),open=el(doc,'button','View chart');open.onclick=()=>{viewing=c;draw()};td.append(open);tr.append(td);t.append(tr)}
   panel.append(t);
  }
  function draw(){
   const d=current();graph=G.project(d,{artifacts:typeof SmelterTraceArtifacts!=='undefined'?SmelterTraceArtifacts.list():[]});
   const key=JSON.stringify([graph.nodes.map(n=>[n.id,n.state,n.label,n.detail]),graph.edges.map(e=>e.id),viewing?.id,feed]);
   banner.hidden=!viewing;if(viewing)bannerText.textContent='Viewing saved chart · '+viewing.reason+' · '+time(viewing.saved_at)+' · read-only evidence summary';
   renderChips();
   if(key===lastRendered){if(tab==='waits')renderTab();return}
   lastRendered=key;
   view.update(graph,{taskKey:(viewing?'saved:'+viewing.id:'live:')+(d?.binding?.session_id||'')+':'+(d?.native_turn_id||'')});
   const selected=view.selected();renderInspector(selected?graph.nodes.find(n=>n.id===selected):null);renderTab();
  }
  function download(name,type,text){const url=URL.createObjectURL(new Blob([text],{type}));const a=el(doc,'a');a.href=url;a.download=name;doc.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
  const stamp=()=>((current()?.task_id||'trace')+'').replace(/[^A-Za-z0-9_-]/g,'_').slice(0,60);
  exportJson.onclick=()=>download(stamp()+'.trace.json','application/json',JSON.stringify(exportable(current(),graph),null,2));
  exportMermaid.onclick=()=>download(stamp()+'.trace.mmd','text/plain',G.mermaid(graph));
  exportSvg.onclick=()=>download(stamp()+'.trace.svg','image/svg+xml',view.svgMarkup());
  search.oninput=()=>{const hits=view.search(search.value);search.setAttribute('aria-description',hits.length+' matching nodes')};
  search.onkeydown=e=>{if(e.key==='Enter'){const hits=view.search(search.value);if(hits[0])view.select(hits[0].id)}};
  fit.onclick=()=>view.fit();zin.onclick=()=>view.zoom(1.2);zout.onclick=()=>view.zoom(1/1.2);tidy.onclick=()=>view.tidy();
  focus.onclick=()=>{const on=focus.getAttribute('aria-pressed')!=='true';focus.setAttribute('aria-pressed',String(on));view.setFocus(on)};
  live.onclick=()=>{viewing=null;draw()};close.onclick=()=>dialog.close();
  dialog.addEventListener?.('close',()=>{clearInterval(nativeTimer);nativeTimer=null;if(typeof SmelterTraceArtifacts!=='undefined')SmelterTraceArtifacts.release()});
  let nativeTimer=null;
  async function pollNative(){if(!api||!dialog.open)return;try{native=await api('/api/native-progress')}catch{native=null}}
  return {
   open(){if(!dialog.open)dialog.showModal();draw();view.fit();pollNative();if(typeof SmelterTraceArtifacts!=='undefined')SmelterTraceArtifacts.refresh();nativeTimer??=setInterval(()=>{pollNative();if(typeof SmelterTraceArtifacts!=='undefined')SmelterTraceArtifacts.refresh()},5000);charts=null},
   update(next,nextFeed,frameAt){data=next;feed=nextFeed;lastFrameAt=frameAt;if(dialog.open)draw()},
   dialog,view,dispose(){clearInterval(nativeTimer);dialog.remove()}
  };
 }
 // Export allowlist: identities, states, paths and hashes only. No prompts, arguments or bodies exist in the snapshot.
 function exportable(data,graph){
  if(!data?.available)return {schema:'smelter.trace.chart.v1',available:false,reason:data?.reason||null};
  return {schema:'smelter.trace.chart.v1',exported_at:new Date().toISOString(),identity:graph.identity,
   status:data.status,observed_at:data.observed_at,index_revision:data.index_revision||null,validation:data.validation||[],
   nodes:graph.nodes.map(({id,kind,label,state,detail})=>({id,kind,label,state,detail})),edges:graph.edges,notes:graph.notes};
 }
 return {create,clocks,waits,exportable};
})();
if(typeof module!=='undefined')module.exports=SmelterTraceWorkbench;
