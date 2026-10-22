/* Operator controls only; model tool schemas never expose this API. */
const SmelterSystem=(()=>{
 function mount(host,api,doc=document){
  const make=(tag,text)=>{const node=doc.createElement(tag);if(text)node.textContent=text;return node};
  const title=make('h3','System status');
  const description=make('p','Check installation and runtime separately. Model Start/Stop loads or unloads memory. OpenCode and MCP run on demand; their Start/Stop controls enable or disable new work.');
  const toolbar=make('div');toolbar.className='component-toolbar';
  const refresh=make('button','Refresh all statuses');refresh.type='button';
  const updated=make('small','Not checked yet');toolbar.append(refresh,updated);
  const notice=make('p');notice.setAttribute('role','status');notice.setAttribute('aria-live','polite');
  const wrap=make('div');wrap.className='component-table-wrap';wrap.tabIndex=0;wrap.setAttribute('aria-label','System component statuses and controls');
  const table=make('table');table.className='component-table';
  const caption=make('caption','Critical components and supporting dependencies');
  const head=make('thead'),header=make('tr');
  for(const text of ['Component','Installation','Runtime','Controls']){const th=make('th',text);th.scope='col';header.append(th)}
  head.append(header);const body=make('tbody');table.append(caption,head,body);wrap.append(table);
  const resources=make('p');resources.id='systemResourceSummary';resources.className='muted';
  host.append(title,description,toolbar,notice,wrap,resources);
  let pending=false,last=null;
  function render(snapshot){
   last=snapshot;body.replaceChildren();updated.textContent='Checked '+new Date(snapshot.checked_at).toLocaleTimeString();
   for(const row of snapshot.components){
    const tr=make('tr');tr.dataset.component=row.id;
    const name=make('th');name.scope='row';name.append(make('strong',row.name),make('small',row.kind));
    const installation=make('td');installation.append(make('span',row.installation.replaceAll('_',' ')));
    if(row.version)installation.append(make('small','Version '+row.version));
    const runtime=make('td'),badge=make('span',row.state.replaceAll('_',' '));badge.className='component-state component-state-'+row.state;
    runtime.append(badge,make('small',row.detail));
    const controls=make('td'),buttons=make('div');buttons.className='component-actions';
    for(const action of ['status','start','stop','reload','restart']){
     const option=row.actions[action],button=make('button',action[0].toUpperCase()+action.slice(1));
     button.type='button';button.setAttribute('aria-label',action[0].toUpperCase()+action.slice(1)+' '+row.name);
     button.disabled=pending||!option.enabled;button.title=option.reason||action+' '+row.name;
     button.onclick=()=>perform(row.id,action);buttons.append(button);
    }
    controls.append(buttons);
    const unavailable=Object.entries(row.actions).filter(([action,option])=>action!=='status'&&!option.enabled).map(([,option])=>option.reason).filter(Boolean);
    if(unavailable.length)controls.append(make('small',[...new Set(unavailable)].join('. ')));
    tr.append(name,installation,runtime,controls);body.append(tr);
   }
   refresh.disabled=pending;wrap.setAttribute('aria-busy',String(pending));
  }
  async function perform(component,action){
   if(pending)return;pending=true;if(last)render(last);refresh.disabled=true;
   notice.textContent=(action==='status'?'Checking statuses':action[0].toUpperCase()+action.slice(1)+' '+component)+'…';
   try{const result=await api('/api/system/components','POST',{component,action,...(component==='qwen'?{expected_model:last.model}:{})});notice.textContent=result.message||'Status check completed.';render(result.snapshot);window.reloadTaskContext?.()}
   catch(error){notice.textContent='Component operation failed: '+error.message;try{render(await api('/api/system/components'))}catch{}}
   finally{pending=false;if(last)render(last);refresh.disabled=false}
  }
  async function load(){
   if(pending)return;pending=true;refresh.disabled=true;notice.textContent='Checking installed components and local services…';
   try{render(await api('/api/system/components'));notice.textContent='Controls apply to this dashboard’s managed components. Finish active chat work before changing runtime state.'}
   catch(error){notice.textContent='Component status unavailable: '+error.message}
   finally{pending=false;if(last)render(last);refresh.disabled=false}
  }
  refresh.onclick=()=>perform('all','status');
  return {load};
 }
 return {mount};
})();
