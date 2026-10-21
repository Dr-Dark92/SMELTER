/* One settings surface. Location policy and per-turn tool selection remain distinct. */
const SmelterAccess = (() => {
  function mount(api, doc=document) {
    const surface=SmelterSettings.current,right=surface.content,summary=surface.summary;
    const access=doc.createElement('section');
    const title=doc.createElement('h3');title.textContent='Registered locations';
    const note=doc.createElement('p');note.textContent='Unregistered paths are denied. Most-specific enabled location and its exclusions apply. Execute permits registered operations only; it grants no shell. Confined tests/previews require configured local container images.';
    const list=doc.createElement('div');list.className='access-location-list';
    const status=doc.createElement('p');status.setAttribute('role','status');
    const add=doc.createElement('button');add.textContent='Add location';const save=doc.createElement('button');save.textContent='Save access policy';
    access.append(title,note,list,add,save,status);
    const nav=surface.addPanel('accessPolicyPanel','Workspaces & Access',access);
    const permissions=doc.getElementById('pythonTools');permissions.open=true;
    const taskPanel=surface.task;
    const taskNote=doc.createElement('p');taskNote.textContent='Select a subset of registered access for the next Send. Skills cannot expand permissions. OpenCode uses a managed container and local-model relay; arbitrary external MCP remains blocked.';
    taskPanel.prepend(taskNote);
    const agentAccess=doc.createElement('div');agentAccess.id='openCodeTaskAccess';
    const agentHeading=doc.createElement('h4');agentHeading.textContent='Confined OpenCode · read-only';agentAccess.append(agentHeading);
    const check=doc.getElementById('opencodeServerCheck'),connection=doc.getElementById('opencodeServerStatus');
    const model=doc.getElementById('opencodeAgentModel').closest('label'),approval=doc.getElementById('opencodeAgentApprove').closest('label');
    agentAccess.append(check,connection,model,approval);taskPanel.append(agentAccess);
    let rows=[],operations=[],policy=null;
    function render() {
      list.replaceChildren();
      for(const row of rows) {
        const card=doc.createElement('fieldset');card.className='access-location';
        const legend=doc.createElement('legend');legend.textContent=row.name||'New location';card.append(legend);
        for(const [key,labelText] of [['name','Name'],['path','Absolute local path']]) {
          const label=doc.createElement('label');label.textContent=labelText;
          const input=doc.createElement('input');input.value=row[key];input.oninput=()=>{row[key]=input.value};label.append(input);card.append(label);
        }
        const flags=doc.createElement('div');flags.className='access-flags';
        for(const key of ['enabled','read','write','execute']) {
          const label=doc.createElement('label'),input=doc.createElement('input');input.type='checkbox';input.checked=row[key];
          input.onchange=()=>{row[key]=input.checked;if(key==='execute'){if(!input.checked)row.operations=[];render()}};
          label.append(input,doc.createTextNode(' '+key));flags.append(label);
        }card.append(flags);
        const choices=doc.createElement('div');choices.className='access-flags';
        for(const operation of operations) {
          const label=doc.createElement('label'),input=doc.createElement('input');input.type='checkbox';input.checked=row.operations.includes(operation);input.disabled=!row.execute;
          input.onchange=()=>{row.operations=input.checked?[...row.operations,operation]:row.operations.filter(x=>x!==operation)};
          label.append(input,doc.createTextNode(' '+operation));choices.append(label);
        }card.append(choices);
        const label=doc.createElement('label');label.textContent='Excluded relative patterns (one per line)';
        const exclude=doc.createElement('textarea');exclude.rows=2;exclude.value=row.exclusions.join('\n');exclude.oninput=()=>{row.exclusions=exclude.value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean)};label.append(exclude);card.append(label);
        const remove=doc.createElement('button');remove.textContent='Remove location';remove.onclick=()=>{rows=rows.filter(x=>x!==row);render()};card.append(remove);list.append(card);
      }
    }
    function updateSummary() {
      const engine=doc.getElementById('chatEngine').value;
      const direct=engine==='ollama';permissions.hidden=!direct;agentAccess.hidden=direct;
      const names=[];
      if(doc.getElementById('approveInventory').checked)names.push('folder inventory');
      if(doc.getElementById('approveDiagnostics').checked)names.push('new reports');
      if(doc.getElementById('approveRea').checked)names.push('REA');
      if(doc.getElementById('approveFrontendWorkspace').checked)names.push('V2 CSS/tests/preview');
      if(doc.querySelector('#modelInspectionGrants input:checked'))names.push('selected GLB metadata');
      summary.textContent=direct?'Ollama · '+(policy?.model||'loading model…')+' · ctx '+(policy?.configuration?.runtime.context_tokens||'?')+' / output '+(policy?.configuration?.runtime.max_output_tokens||'?')+' / '+(policy?.configuration?.runtime.timeout_seconds||'?')+'s · '+(names.join(', ')||'no file tools selected'):'OpenCode · confined read-only workspace';
      doc.getElementById('chatinput').placeholder=direct?'Message the selected local model':'Request a read-only source inspection';
    }
    async function load() {
      try {
        policy=await api('/api/access-policy');window.smelterTaskConfiguration=policy.configuration;window.smelterTaskPolicyRevision=policy.revision;rows=structuredClone(policy.locations);operations=policy.operations;render();
        const folder=doc.getElementById('inventoryRoot'),previous=folder.value;folder.replaceChildren();
        const empty=doc.createElement('option');empty.value='';empty.textContent='Choose a registered read location';folder.append(empty);
        for(const row of rows.filter(x=>x.enabled&&x.read)){const option=doc.createElement('option');option.value=row.path;option.textContent=row.name+' · '+row.path;folder.append(option)}
        folder.value=previous;status.textContent='Policy revision '+policy.revision.slice(0,12)+'. Changes apply to new tasks.';updateSummary();
      }catch(error){status.textContent=error.message;summary.textContent='Task access unavailable: '+error.message}
    }
    nav.onclick=()=>{surface.activate(access.id);load()};add.onclick=()=>{rows.push({id:'location-'+crypto.randomUUID().slice(0,8),name:'',path:'',read:false,write:false,execute:false,operations:[],exclusions:[],enabled:true});render()};
    save.onclick=async()=>{save.disabled=true;try{await api('/api/access-policy','POST',{policy:{schema_version:1,locations:rows}});await load()}catch(error){status.textContent=error.message}finally{save.disabled=false}};
    right.addEventListener('change',updateSummary);doc.getElementById('chatEngine').addEventListener('change',updateSummary);
    window.refreshAccessSummary=updateSummary;window.reloadTaskContext=load;
    // Installation/staging tools stay available under Settings, away from chat.
    load();
  }
  return {mount};
})();
