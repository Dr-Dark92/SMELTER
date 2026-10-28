/* Public native lifecycle metadata only. No inference or native control calls. */
const SmelterNativeProgress=(()=>{
 function el(doc,tag,text){const node=doc.createElement(tag);if(text!==undefined)node.textContent=text;return node}
 function stamp(value){if(!value)return 'waiting';const date=new Date(value);return Number.isNaN(date.getTime())?value:date.toLocaleString()}
 function render(value,host,doc=document,compact=false){
  host.replaceChildren();host.hidden=!value.binding;
  if(!value.binding)return;
  if(compact)Object.assign(host.style,{margin:'12px 18px',padding:'10px 14px',border:'1px solid var(--border)',borderRadius:'var(--radius)',background:'var(--surface)',maxHeight:'36vh',overflow:'auto',flexShrink:'0'});
  const title=el(doc,'h3','Melty / OpenCode · '+value.task_state);if(compact){title.style.margin='0 0 6px';title.style.fontSize='14px';title.title='Session '+value.binding.session_id+' · Workspace '+value.binding.workspace_id}host.append(title);
  const summary=el(doc,'p',(value.enabled?'Monitor: ':'Monitor paused · ')+value.connection+' · Last activity: '+stamp(value.last_observed_at));summary.setAttribute('role','status');host.append(summary);
  if(compact){summary.style.margin='4px 0';summary.style.fontSize='12px'}else host.append(el(doc,'small','Session '+value.binding.session_id+' · Workspace '+value.binding.workspace_id));
  if(value.connection_error)host.append(el(doc,'p',value.connection_error));
  if(value.finalizing_snapshot)host.append(el(doc,'p','Saving the final workspace index and relation chart…'));
  if(value.catching_up)host.append(el(doc,'p','Recovering recorded tool activity from the native session…'));
  if(!compact&&value.status_source)host.append(el(doc,'small','Activity source: '+value.status_source));
  if(value.gap)host.append(el(doc,compact?'small':'p',compact?'Reconnected · open progress for event-gap details.':'The connection had a gap. Session status was checked again; some tool events may be missing.'));
  if(!compact)host.append(el(doc,'small',value.scope));
  const events=compact?value.events.filter(e=>e.kind==='tool').slice(-1):value.events.slice(-60),list=el(doc,'ol');
  for(const event of events){const item=el(doc,'li',(event.kind==='tool'?event.tool+' · ':'Session · ')+event.phase+' · '+stamp(event.observed_at));list.append(item)}host.append(list);
  const final=value.completions.at(-1);
  if(final){const handoff=el(doc,'details');handoff.open=!compact;handoff.append(el(doc,'summary','Final workspace snapshot · '+final.phase+' · '+stamp(final.observed_at)));
   if(final.gap)handoff.append(el(doc,'p','This task included an event-stream gap.'));
   if(final.snapshot_error)handoff.append(el(doc,'p',final.snapshot_error));
   if(final.workspace_tracking){handoff.append(el(doc,'p','Tree SHA-256: '+final.tree_sha256));handoff.append(el(doc,'p','Tests: '+(final.workspace_tracking.tests.map(t=>t.profile+' '+t.stage+' ('+(t.current?'current tree':'stale')+')').join(', ')||'none')));SmelterWorkspace.renderGraph(final.workspace_tracking,handoff,doc)}
   host.append(handoff);
  }
 }
 function mount(api,doc=document,ready=()=>true){
  const settings=SmelterSettings.current;if(!settings)return;
  const panel=el(doc,'section');panel.append(el(doc,'h3','Native task progress'));
  panel.append(el(doc,'p','Watch an exact Melty / OpenCode session and link it to its coding workspace. Watching sends no prompts. Pause monitor affects only this view.'));
  function field(labelText,node){const label=el(doc,'label',labelText);label.style.display='block';node.setAttribute('aria-label',labelText);node.style.width='100%';label.append(node);panel.append(label);return node}
  const directory=field('Melty project directory',el(doc,'input')),session=field('Native session ID',el(doc,'input')),sessions=field('Sessions in that directory',el(doc,'select')),workspace=field('SMELTER coding workspace',el(doc,'select')),meltyTask=field('Melty task ID (optional, supplied by Melty)',el(doc,'input'));
  directory.placeholder='Absolute directory used by the native session';session.placeholder='ses_…';
  const noSessions=el(doc,'option','Use Find sessions to list this directory');noSessions.value='';sessions.append(noSessions);sessions.disabled=true;
  const discover=el(doc,'button','Find sessions'),bind=el(doc,'button','Bind and watch'),link=el(doc,'button','Link Melty task ID'),start=el(doc,'button','Resume monitor'),stop=el(doc,'button','Pause monitor'),reload=el(doc,'button','Refresh view'),status=el(doc,'p'),body=el(doc,'div');status.setAttribute('role','status');panel.append(discover,bind,link,start,stop,reload,status,body);
  const button=settings.addPanel('nativeProgressPanel','Native task progress',panel,'Debugging');
  const compact=el(doc,'section');compact.className='native-progress-card';compact.hidden=true;const log=doc.getElementById('chatlog');log?.parentNode.insertBefore(compact,log);
  let value=null,pending=false,key='',revision='';
  async function workspaces(){const result=await api('/api/workspace-tracking');workspace.replaceChildren();const placeholder=el(doc,'option','Select the task workspace');placeholder.value='';workspace.append(placeholder);for(const row of result.workspaces){const option=el(doc,'option',row.workspace_id+' · '+row.workspace_root);option.value=row.workspace_id;workspace.append(option)}if(value?.binding)workspace.value=value.binding.workspace_id}
  function show(result){value=result;start.disabled=result.enabled||!result.binding;stop.disabled=!result.enabled;bind.disabled=result.enabled||result.connection==='stopping';const next=JSON.stringify(result);if(next!==key){key=next;render(result,body,doc);if(typeof SmelterTaskTrace==='undefined')render(result,compact,doc,true);else compact.hidden=true;if(result.binding){const detail=el(doc,'button','Open native progress');detail.onclick=()=>settings.activate('nativeProgressPanel');compact.append(detail)}}if(revision!==result.configuration_revision){revision=result.configuration_revision;if(result.binding){directory.value=result.binding.directory;session.value=result.binding.session_id;workspace.value=result.binding.workspace_id;meltyTask.value=result.binding.melty_task_id||''}}}
  async function load(){if(pending||!ready())return;pending=true;try{show(await api('/api/native-progress'));status.textContent='Read-only monitor · '+value.connection}catch(error){status.textContent=error.message}finally{pending=false}}
  async function action(action,fields={}){if(pending||!value)return;pending=true;try{show(await api('/api/native-progress','POST',{action,expected_revision:value.configuration_revision,...fields}));status.textContent='Read-only monitor · '+value.connection}catch(error){status.textContent=error.message}finally{pending=false}}
  discover.onclick=async()=>{if(pending)return;pending=true;try{const result=await api('/api/native-progress','POST',{action:'sessions',directory:directory.value});sessions.replaceChildren();const placeholder=el(doc,'option','Select the exact task session');placeholder.value='';sessions.append(placeholder);for(const row of result.sessions){const option=el(doc,'option',row.session_id+(row.updated?' · '+new Date(row.updated).toLocaleString():''));option.value=row.session_id;sessions.append(option)}sessions.disabled=!result.sessions.length;status.textContent=result.selection}catch(error){status.textContent=error.message}finally{pending=false}};
  sessions.onchange=()=>{if(sessions.value)session.value=sessions.value};bind.onclick=()=>action('bind',{session_id:session.value,directory:directory.value,workspace_id:workspace.value,...(meltyTask.value.trim()?{melty_task_id:meltyTask.value.trim()}:{})});start.onclick=()=>action('start');stop.onclick=()=>action('stop');reload.onclick=load;
  link.onclick=()=>action('correlate',{melty_task_id:meltyTask.value.trim()});
  button.onclick=async()=>{settings.activate('nativeProgressPanel');try{await workspaces();await load()}catch(error){status.textContent=error.message}};
  const timer=setInterval(load,2500);load();return {load,dispose:()=>clearInterval(timer)};
 }
 return {render,mount};
})();
if(typeof module!=='undefined')module.exports=SmelterNativeProgress;
