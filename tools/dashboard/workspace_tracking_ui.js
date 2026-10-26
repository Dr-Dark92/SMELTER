/* Canonical file locations and observed relations; no source is executed. */
const SmelterWorkspace = (() => {
 let chartSerial=0;
 function element(doc, tag, text) {const node=doc.createElement(tag);if(text!==undefined)node.textContent=text;return node}
 function renderGraph(value, host, doc=document) {
  const graph=value.graph;if(!graph)return;
  const box=element(doc,'details');box.className='workspace-relations';box.open=true;
  box.append(element(doc,'summary','File relations · '+(value.revision||'').slice(0,12)));
  box.append(element(doc,'p',graph.scope+(graph.truncated?' Graph limited to changed files and their references.':'')));
  box.append(element(doc,'small','Solid arrows: observed · dashed: static import · dotted: inferred candidate. Hover an edge for its relation.'));
  const wrap=element(doc,'div');wrap.style.overflow='auto';wrap.style.maxHeight='560px';
  const svg=(tag,attrs,text)=>{const n=doc.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs||{}))n.setAttribute(k,String(v));if(text!==undefined)n.textContent=text;return n};
  const columns=[[],[],[]];for(const node of graph.nodes)columns[node.kind==='workspace'||node.kind==='receipt'?0:node.kind==='test'?1:2].push(node);
  const height=Math.max(150,...columns.map(c=>c.length*54+20)),width=1500,positions=new Map();
  columns.forEach((c,i)=>c.forEach((n,j)=>positions.set(n.id,{x:10+i*460,y:20+j*54})));
  const canvas=svg('svg',{viewBox:`0 0 ${width} ${height}`,width,height,role:'img','aria-label':'Workspace file and test relations'});
  const serial=++chartSerial,defs=svg('defs');for(const confidence of ['observed','static','inferred']){const marker=svg('marker',{id:`rel-${serial}-${confidence}`,viewBox:'0 0 10 10',refX:9,refY:5,markerWidth:7,markerHeight:7,orient:'auto-start-reverse'});marker.append(svg('path',{d:'M 0 0 L 10 5 L 0 10 z',fill:confidence==='observed'?'#6aa88e':'#8c91ba'}));defs.append(marker)}canvas.append(defs);
  for(const edge of graph.edges){const a=positions.get(edge.source),b=positions.get(edge.target);if(!a||!b)continue;const sx=a.x+(b.x>=a.x?430:0),tx=b.x+(b.x>a.x?0:430),cx=a.x===b.x?a.x+510:(sx+tx)/2;const line=svg('path',{d:`M ${sx} ${a.y+18} Q ${cx} ${Math.min(a.y,b.y)-12} ${tx} ${b.y+18}`,fill:'none',stroke:edge.confidence==='observed'?'#6aa88e':'#8c91ba','stroke-width':1.3,'stroke-dasharray':edge.confidence==='observed'?'':edge.confidence==='static'?'5 4':'2 5','marker-end':`url(#rel-${serial}-${edge.confidence})`});line.append(svg('title',{},edge.kind+' / '+edge.confidence));canvas.append(line)}
  for(const node of graph.nodes){const p=positions.get(node.id),group=svg('g');group.append(svg('rect',{x:p.x,y:p.y,width:430,height:38,rx:6,fill:node.kind==='receipt'?'#333d49':'#242c35',stroke:'#667180'}));const label=node.label.length>56?'…'+node.label.slice(-55):node.label;group.append(svg('text',{x:p.x+8,y:p.y+24,fill:'#edf1f7','font-size':12,'font-family':'monospace'},label));group.append(svg('title',{},node.label+(node.sha256?'\nSHA-256 '+node.sha256:'')+(node.status?'\n'+node.status:'')));canvas.append(group)}
  wrap.append(canvas);box.append(wrap);
  const source=element(doc,'details');source.append(element(doc,'summary','Mermaid source · editable'));
  const text=element(doc,'textarea');text.readOnly=true;text.value=value.mermaid||'';text.rows=8;text.style.width='100%';text.setAttribute('aria-label','Mermaid relation chart source');source.append(text);box.append(source);host.append(box);return box;
 }
 function render(value, host, doc=document) {
  host.replaceChildren();
  if(value.indexed===false){host.append(element(doc,'p','No index yet. Refresh index to scan this managed copy.'));return}
  const info=element(doc,'pre','Coding copy: '+value.workspace_root+'\nOriginal checkout: '+value.source_root+'\nStorage: '+value.storage+'\n'+value.tests_use+'\nObserved: '+value.updated_at+' · '+value.operation+'\nTree SHA-256: '+value.revision);info.style.whiteSpace='pre-wrap';info.style.overflowWrap='anywhere';host.append(info);
  host.append(element(doc,'p',value.matching_files+' matching files · '+value.total_files+' indexed'+(value.has_more?' · more pages available':'')));
  const table=element(doc,'table');table.style.width='100%';const heading=element(doc,'tr');for(const text of ['File / physical location','Status','SHA-256'])heading.append(element(doc,'th',text));table.append(heading);
  for(const file of value.files){const row=element(doc,'tr');const path=element(doc,'td',file.relative_path);path.style.overflowWrap='anywhere';const physical=element(doc,'small',file.physical_path);physical.style.display='block';path.append(physical);const hash=element(doc,'td',file.sha256||'Missing');hash.style.overflowWrap='anywhere';row.append(path,element(doc,'td',file.status),hash);table.append(row)}host.append(table);
  host.append(element(doc,'p','Test receipts: '+(value.tests.map(t=>t.profile+' '+t.stage+' ('+(t.current?'current tree':'stale tree')+')').join(', ')||'none')));
  const history=element(doc,'details');history.append(element(doc,'summary','Recent observations'));const list=element(doc,'ul');for(const event of value.history)list.append(element(doc,'li',event.time+' · '+(event.path?event.status+' '+event.path+' · '+(event.sha256||'missing'):event.operation)));history.append(list);host.append(history);renderGraph(value,host,doc);
 }
 function mount(api,doc=document) {
  const settings=SmelterSettings.current;if(!settings)return;
  const panel=element(doc,'section');panel.append(element(doc,'h3','Workspace files & relations'));
  panel.append(element(doc,'p','Use the workspace belonging to your task. This panel reads a cached index; Refresh index scans the actual host copy. Changes made through SMELTER update it automatically.'));
  const select=element(doc,'select');select.setAttribute('aria-label','Coding workspace');
  const query=element(doc,'input');query.type='search';query.placeholder='Find filename or path';query.setAttribute('aria-label','Find indexed file');
  const refresh=element(doc,'button','Refresh index'),reload=element(doc,'button','Reload workspaces'),prev=element(doc,'button','Previous files'),next=element(doc,'button','Next files'),status=element(doc,'p'),body=element(doc,'div');status.setAttribute('role','status');
  panel.append(select,query,refresh,reload,prev,next,status,body);const button=settings.addPanel('workspaceTrackingPanel','Workspace files & relations',panel,'Debugging');let busy=false,offset=0,key='';
  async function load(scan=false){if(busy||!select.value)return;busy=true;refresh.disabled=true;const id=select.value,filter=query.value,page=offset;try{if(scan)await api('/api/workspace-tracking','POST',{action:'refresh',workspace_id:id});const result=await api('/api/workspace-tracking?'+new URLSearchParams({workspace_id:id,query:filter,offset:page,limit:30}));if(id!==select.value||filter!==query.value||page!==offset)return;const updated=JSON.stringify(result);if(updated!==key){key=updated;render(result,body,doc)}prev.disabled=offset===0;next.disabled=!result.has_more;status.textContent='Index observed '+(result.updated_at||'never')}catch(error){status.textContent=error.message}finally{busy=false;refresh.disabled=false}}
  async function discover(){try{const result=await api('/api/workspace-tracking');const selected=select.value;select.replaceChildren(element(doc,'option','Select task workspace'));select.children[0].value='';for(const row of result.workspaces){const option=element(doc,'option',row.workspace_id+' · '+row.workspace_root);option.value=row.workspace_id;select.append(option)}select.value=selected;status.textContent=result.selection;if(selected)await load()}catch(error){status.textContent=error.message}}
  button.onclick=()=>{settings.activate('workspaceTrackingPanel');discover()};reload.onclick=discover;refresh.onclick=()=>load(true);select.onchange=()=>{offset=0;key='';body.replaceChildren();load()};query.oninput=()=>{offset=0;load()};prev.onclick=()=>{offset=Math.max(0,offset-30);load()};next.onclick=()=>{offset+=30;load()};
  const timer=setInterval(()=>{if(doc.getElementById('settingsDialog')?.open&&panel.classList.contains('active'))load()},2000);return {panel,load,discover,dispose:()=>clearInterval(timer)};
 }
 return {mount,render,renderGraph};
})();
if(typeof module!=='undefined')module.exports=SmelterWorkspace;
