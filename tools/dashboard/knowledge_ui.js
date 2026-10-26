/* Project internet/memory controls and plain-text source cards. */
const SmelterKnowledge=(()=>{
 let web=null,memory=null;
 function collect(){return {...(web&&web.mode!=='off'?{web_read:true}:{}),...(memory?.enabled?{project_memory:true}:{})}}
 function sources(parent,events,doc=document){
  for(const event of events||[]){
   const result=event.result;if(result?.status!=='web_completed'||!Array.isArray(result.sources))continue;
   const box=doc.createElement('section');box.className='web-source-cards';
   const heading=doc.createElement('h4');heading.textContent='Web sources · '+result.action+' · '+(result.cached?'cached':'live');box.append(heading);
   if(result.provider_errors){const partial=doc.createElement('small');partial.textContent=result.provider_errors+' search engine(s) unavailable; results may be incomplete.';box.append(partial)}
   for(const source of result.sources.slice(0,8)){
    let url;try{url=new URL(source.url);if(url.protocol!=='https:'||url.username||url.password)continue}catch{continue}
    const card=doc.createElement('div');card.style.marginBottom='8px';
    const link=doc.createElement('a');link.href=url.href;link.target='_blank';link.rel='noopener noreferrer';link.referrerPolicy='no-referrer';link.textContent=String(source.title||url.hostname).slice(0,200);card.append(link);
    const detail=doc.createElement('small');detail.style.display='block';detail.textContent=url.hostname+(result.fetched_at?' · '+result.fetched_at:'');card.append(detail);
    if(source.snippet){const excerpt=doc.createElement('p');excerpt.textContent=String(source.snippet).slice(0,800);card.append(excerpt)}
    box.append(card);
   }
   parent.append(box);
  }
 }
 function mount(api,doc=document){
  const surface=SmelterSettings.current,section=doc.createElement('section');
  const nav=surface.addPanel('knowledgePanel','Internet & memory',section,'Model & runtime');
  function heading(text){const h=doc.createElement('h3');h.textContent=text;section.append(h)}
  function label(text,input){const l=doc.createElement('label');l.style.display='block';input.setAttribute('aria-label',text);l.append(doc.createTextNode(text+' '),input);section.append(l);return input}
  function select(text,values){const input=doc.createElement('select');for(const [value,name] of values){const option=doc.createElement('option');option.value=value;option.textContent=name;input.append(option)}return label(text,input)}
  function button(text,action){const b=doc.createElement('button');b.type='button';b.textContent=text;b.onclick=async()=>{b.disabled=true;try{await action()}catch(e){status.textContent=e.message}finally{b.disabled=false}};section.append(b);return b}
  const status=doc.createElement('p');status.setAttribute('role','status');
  heading('Internet');const mode=select('Project access',[['off','Off'],['docs','Documentation domains'],['public','Public web']]);
  const domains=label('Documentation domains (one per line)',doc.createElement('textarea'));domains.rows=4;domains.style.width='100%';
  const provider=doc.createElement('p');section.append(provider);
  const webNote=doc.createElement('p');webNote.textContent='Search queries go to public search engines. Documentation mode filters results and fetched pages to your domains.';section.append(webNote);
  let webRevision=null,memoryRevision=null,currentNote=null;
  async function loadWeb(){const result=await api('/api/web-access');web=result.settings;webRevision=result.revision;mode.value=web.mode;domains.value=web.domains.join('\n');provider.textContent='Search: '+result.provider.status+(result.provider.reason?' · '+result.provider.reason:' · SearXNG '+result.provider.version)}
  button('Save internet settings',async()=>{const result=await api('/api/web-access','POST',{action:'save',settings:{...web,mode:mode.value,domains:domains.value.split(/\r?\n/).map(x=>x.trim().toLowerCase()).filter(Boolean)},expected_revision:webRevision});web=result.settings;webRevision=result.revision;status.textContent='Project internet settings saved.'});
  button('Refresh search status',loadWeb);
  heading('Project memory');const enabled=label('Use project memory',doc.createElement('input'));enabled.type='checkbox';
  const automatic=label('Save completed tool checkpoints',doc.createElement('input'));automatic.type='checkbox';
  const ram=select('RAM cache',[['0','Off'],['16','16 MiB'],['32','32 MiB'],['64','64 MiB']]);
  const counts=doc.createElement('p');section.append(counts);
  const query=label('Search memory',doc.createElement('input'));query.type='text';
  const list=doc.createElement('div');section.append(list);
  const title=label('Note title',doc.createElement('input'));title.type='text';title.style.width='100%';
  const body=label('Note',doc.createElement('textarea'));body.rows=7;body.style.width='100%';
  const refs=label('Source references (one per line)',doc.createElement('textarea'));refs.rows=2;refs.style.width='100%';
  const confidence=doc.createElement('p');section.append(confidence);
  function edit(note){currentNote=note;title.value=note?.title||'';body.value=note?.text||'';refs.value=(note?.sources||[]).join('\n');confidence.textContent=note?'Origin: '+note.origin+' · '+note.confidence+' · '+note.sha256.slice(0,12):'New human note. Model notes remain unverified.'}
  function showNotes(notes){list.replaceChildren();for(const note of notes){const b=doc.createElement('button');b.type='button';b.textContent=note.title+' · '+note.confidence;b.onclick=async()=>{try{edit(await api('/api/project-memory','POST',{action:'read',id:note.id}))}catch(e){status.textContent=e.message}};list.append(b)}}
  async function loadMemory(){const result=await api('/api/project-memory');memory=result.settings;memoryRevision=result.revision;enabled.checked=memory.enabled;automatic.checked=memory.auto_capture;ram.value=String(memory.ram_mib);counts.textContent=result.notes+' notes · '+result.file_bytes+' bytes in files · '+result.ram_bytes_estimate+' estimated bytes cached in RAM';showNotes(result.recent||[])}
  button('Save memory settings',async()=>{await api('/api/project-memory','POST',{action:'save_settings',settings:{...memory,enabled:enabled.checked,auto_capture:automatic.checked,ram_mib:Number(ram.value)},expected_revision:memoryRevision});await loadMemory();status.textContent='Memory settings saved; model context remains unchanged.'});
  button('Search memory',async()=>{const result=await api('/api/project-memory','POST',{action:'search',query:query.value});showNotes(result.notes||[])});
  button('New note',async()=>edit(null));
  button('Save note',async()=>{const payload={action:'remember',title:title.value,text:body.value,sources:refs.value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean),kind:currentNote?.kind||'note',tags:currentNote?.tags||[]};if(currentNote){payload.id=currentNote.id;payload.expected_sha256=currentNote.sha256}const result=await api('/api/project-memory','POST',payload);edit(result.note);await loadMemory();status.textContent='Note saved as user-supplied project memory.'});
  button('Forget note',async()=>{if(!currentNote)throw Error('Select a note first');await api('/api/project-memory','POST',{action:'forget',id:currentNote.id,expected_sha256:currentNote.sha256});edit(null);await loadMemory();status.textContent='Note forgotten; its cached search result was cleared.'});
  button('Clear RAM cache',async()=>{await api('/api/project-memory','POST',{action:'clear_ram'});await loadMemory();status.textContent='RAM cache cleared. Durable memory files remain.'});
  button('Rebuild memory index',async()=>{await api('/api/project-memory','POST',{action:'reindex'});await loadMemory();status.textContent='Search index rebuilt from memory files.'});
  section.append(status);edit(null);
  async function refresh(){const results=await Promise.allSettled([loadWeb(),loadMemory()]);for(const result of results)if(result.status==='rejected')status.textContent=result.reason.message}
  nav.onclick=()=>{surface.activate('knowledgePanel');refresh()};refresh();return {refresh};
 }
 return {mount,collect,sources};
})();
if(typeof window!=='undefined')window.SmelterKnowledge=SmelterKnowledge;
if(typeof module!=='undefined')module.exports=SmelterKnowledge;
