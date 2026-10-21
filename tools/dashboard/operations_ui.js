/* Operator-only maintenance and confinement; these controls expose no model tools. */
const SmelterOperations=(()=>{
 function mount(api,doc=document){
  const settings=SmelterSettings.current;
  function panel(id,label){const section=doc.createElement('section');const heading=doc.createElement('h3');heading.textContent=label;section.append(heading);const button=settings.addPanel(id,label,section,'System');return {section,button}}
  function button(label,action,enabled=()=>true){const b=doc.createElement('button');b.textContent=label;b.onclick=async()=>{b.disabled=true;try{await action()}finally{b.disabled=!enabled()}};return b}
  function output(parent){const pre=doc.createElement('pre');pre.style.whiteSpace='pre-wrap';pre.style.overflowWrap='anywhere';pre.setAttribute('role','status');parent.append(pre);return pre}
  const sandbox=panel('sandboxPanel','Confined execution');
  const info=doc.createElement('p');info.textContent='Frontend tests and previews require a local Docker Engine 28+ in Linux-container mode and preloaded Python/Node images. No images are downloaded by SMELTER. There is no host-execution fallback. OpenCode requires its separate reviewed image; arbitrary external MCP remains blocked.';sandbox.section.append(info);
  const help=doc.createElement('pre');help.textContent='Operator setup (review image publishers first):\ndocker pull python:3.12-alpine\ndocker pull node:22-alpine\ndocker image inspect --format "{{.Id}}" python:3.12-alpine\ndocker image inspect --format "{{.Id}}" node:22-alpine\ndocker build -f tools/dashboard/Dockerfile.opencode -t smelter-opencode:1.19.3 .\ndocker image inspect --format "{{.Id}}" smelter-opencode:1.19.3';sandbox.section.append(help);
  const images={};for(const [key,labelText] of [['python_image','Python immutable image ID'],['node_image','Node immutable image ID'],['opencode_image','OpenCode immutable image ID (optional)']]){const label=doc.createElement('label');label.style.display='block';label.textContent=labelText;const input=doc.createElement('input');input.placeholder='sha256:…';input.style.width='100%';input.setAttribute('aria-label',labelText);images[key]=input;label.append(input);sandbox.section.append(label)}
  const sandboxOut=output(sandbox.section);
  const loadSandbox=async()=>{try{const result=await api('/api/sandbox');for(const key in images)images[key].value=result.configured[key]||'';sandboxOut.textContent=result.reason+'\n'+result.boundary}catch(error){sandboxOut.textContent=error.message}};
  sandbox.section.append(button('Save confined runner configuration',async()=>{try{await api('/api/sandbox','POST',{action:'save',configuration:{schema_version:1,...Object.fromEntries(Object.entries(images).map(([key,input])=>[key,input.value.trim()||null]))}});sandboxOut.textContent='Saved. No container started.'}catch(error){sandboxOut.textContent=error.message}}),button('Check confined runner',loadSandbox),button('Stop confined preview',async()=>{try{const result=await api('/api/sandbox','POST',{action:'stop_preview'});sandboxOut.textContent=result.cleanup_pending?.length?'Container cleanup was not confirmed: '+result.cleanup_pending.join(', '):result.stopped?'Preview stopped.':'No owned preview is running.'}catch(error){sandboxOut.textContent=error.message}}));
  sandbox.button.onclick=()=>{settings.activate('sandboxPanel');loadSandbox()};
  const maintenance=panel('maintenancePanel','Storage, recovery & backup');
  const note=doc.createElement('p');note.textContent='Review durable task records, artifact quotas and retention before deleting anything. Backups include a consistent SQLite snapshot and verified application state. Restore is offline and refuses existing destinations.';maintenance.section.append(note);
  const stateOut=output(maintenance.section);let retention=null;
  const loadMaintenance=async()=>{retention=null;apply.disabled=true;try{const result=await api('/api/maintenance');stateOut.textContent=JSON.stringify(result,null,2)}catch(error){stateOut.textContent=error.message}};
  const directory=doc.createElement('input');directory.placeholder='New absolute backup directory outside checkout/database';directory.style.width='100%';directory.setAttribute('aria-label','New backup directory');maintenance.section.append(directory);
  const age=doc.createElement('input');age.type='number';age.min='1';age.max='3650';age.value='30';age.setAttribute('aria-label','Retention age in days');maintenance.section.append(age);
  const canApply=()=>Boolean(retention&&retention.files>0&&Date.now()<retention.expiresAt);
  const apply=button('Apply reviewed retention plan',async()=>{
   if(!canApply()){retention=null;stateOut.textContent='Retention plan expired or unavailable. Preview a new plan.';return}
   if(!confirm('Delete the '+retention.files+' unchanged files in this reviewed plan?'))return;
   const reviewed=retention;retention=null;
   try{stateOut.textContent=JSON.stringify(await api('/api/maintenance','POST',{action:'prune',plan_id:reviewed.plan_id,approval:true}),null,2)}catch(error){stateOut.textContent=error.message+' Preview a new plan before retrying.'}
  },canApply);apply.disabled=true;
  age.oninput=()=>{retention=null;apply.disabled=true};
  const preview=async()=>{
   retention=null;apply.disabled=true;
   if(!Number.isInteger(age.valueAsNumber)||age.valueAsNumber<1||age.valueAsNumber>3650){stateOut.textContent='Choose a whole retention age from 1 to 3650 days.';return}
   try{
    const plan=await api('/api/maintenance','POST',{action:'plan',days:age.valueAsNumber});
    retention={...plan,expiresAt:Date.now()+plan.expires_in_seconds*1000};stateOut.textContent=JSON.stringify(plan,null,2);apply.disabled=!canApply();
    setTimeout(()=>{if(retention?.plan_id===plan.plan_id){retention=null;apply.disabled=true;stateOut.textContent='Retention plan expired. Preview a new plan.'}},plan.expires_in_seconds*1000);
   }catch(error){stateOut.textContent=error.message}
  };
  maintenance.section.append(button('Refresh storage and task records',loadMaintenance),button('Reconcile interrupted containers',async()=>{if(!confirm('Clean up owned containers whose task/process has ended?'))return;try{stateOut.textContent=JSON.stringify(await api('/api/maintenance','POST',{action:'reconcile_containers',approval:true}),null,2)}catch(error){stateOut.textContent=error.message}}),button('Check database integrity',async()=>{try{stateOut.textContent=JSON.stringify(await api('/api/maintenance','POST',{action:'integrity'}),null,2)}catch(error){stateOut.textContent=error.message}}),button('Preview retention plan',preview),apply,button('Create verified backup',async()=>{if(!confirm('Create a new backup at '+directory.value+'?'))return;try{stateOut.textContent=JSON.stringify(await api('/api/maintenance','POST',{action:'backup',directory:directory.value,approval:true}),null,2)}catch(error){stateOut.textContent=error.message}}));
  maintenance.button.onclick=()=>{settings.activate('maintenancePanel');loadMaintenance()};
  const capabilities=panel('capabilitiesPanel','Capabilities & project checks');const capOut=output(capabilities.section);
  capabilities.button.onclick=async()=>{settings.activate('capabilitiesPanel');try{capOut.textContent=JSON.stringify(await api('/api/capabilities'),null,2)}catch(error){capOut.textContent=error.message}};
  const project=doc.createElement('input');project.placeholder='Registered readable project directory';project.style.width='100%';project.setAttribute('aria-label','Project contract directory');capabilities.section.append(project,button('Inspect project documentation contract',async()=>{try{capOut.textContent=JSON.stringify(await api('/api/project-contract','POST',{path:project.value}),null,2)}catch(error){capOut.textContent=error.message}}));
 }
 return {mount};
})();
