/* One settings surface. Location policy and per-turn tool selection remain distinct. */
const SmelterAccess = (() => {
  function mount(api, doc=document) {
    const right=doc.getElementById('rightbar'), center=doc.getElementById('workspace');
    const dialog=doc.createElement('dialog');dialog.id='settingsDialog';dialog.className='settings-screen';
    const header=doc.createElement('header');header.className='settings-header';
    const heading=doc.createElement('h2');heading.textContent='SMELTER settings';
    const close=doc.createElement('button');close.textContent='Close settings';close.onclick=()=>dialog.close();header.append(heading,close);
    dialog.append(header,right);doc.body.append(dialog);
    const toolbar=doc.createElement('div');toolbar.className='workspace-toolbar';
    const settings=doc.createElement('button');settings.textContent='Settings';settings.onclick=()=>dialog.showModal();
    const summary=doc.createElement('span');summary.id='taskAccessSummary';summary.setAttribute('role','status');
    const review=doc.createElement('button');review.textContent='Review task access';toolbar.append(summary,review,settings);center.prepend(toolbar);
    function activate(panel,button) {
      right.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));
      right.querySelectorAll('.navbtn').forEach(x=>x.classList.remove('active'));
      panel.classList.add('active');button.classList.add('active');
    }
    const access=doc.createElement('section');access.className='panel';access.id='accessPolicyPanel';
    const nav=doc.createElement('button');nav.className='navbtn';nav.textContent='Workspaces & Access';
    const title=doc.createElement('h3');title.textContent='Registered locations';
    const note=doc.createElement('p');note.textContent='Unregistered paths are denied. The most specific enabled location applies; its exclusions override its flags. Execute permits only selected registered operations. Delete is not granted. These are application checks, not an OS sandbox. External MCP execution is blocked until a confined runner exists.';
    const list=doc.createElement('div');list.className='access-location-list';
    const status=doc.createElement('p');status.setAttribute('role','status');
    const add=doc.createElement('button');add.textContent='Add location';
    const save=doc.createElement('button');save.textContent='Save access policy';
    access.append(title,note,list,add,save,status);right.prepend(nav,access);
    const permissions=doc.getElementById('pythonTools');
    const taskPanel=doc.createElement('section');taskPanel.className='panel';taskPanel.id='taskAccessPanel';
    const taskTitle=doc.createElement('h3');taskTitle.textContent='Access for the next task';
    const taskNote=doc.createElement('p');taskNote.textContent='Select a subset of registered access. Skills cannot expand it. Selections are consumed on Send. OpenCode currently supports read-only source inspection; built-in selections below apply to direct Ollama only.';
    const agentAccess=doc.createElement('div');agentAccess.id='openCodeTaskAccess';
    const agentHeading=doc.createElement('h4');agentHeading.textContent='OpenCode read-only task';agentAccess.append(agentHeading);
    const check=doc.getElementById('opencodeServerCheck'),connection=doc.getElementById('opencodeServerStatus');
    const model=doc.getElementById('opencodeAgentModel').closest('label'),approval=doc.getElementById('opencodeAgentApprove').closest('label');
    agentAccess.append(check,connection,model,approval);
    taskPanel.append(taskTitle,taskNote,permissions,agentAccess);permissions.open=true;
    const taskButton=doc.createElement('button');taskButton.className='navbtn';taskButton.textContent='Next-task tool access';right.prepend(taskButton,taskPanel);
    const openTask=()=>{if(!dialog.open)dialog.showModal();activate(taskPanel,taskButton)};
    review.onclick=taskButton.onclick=openTask;
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
      summary.textContent=direct?'Ollama · '+(policy?.model||'loading model…')+' · '+(names.join(', ')||'no file tools selected'):'OpenCode · read-only V2 · no edits or commands';
      doc.getElementById('chatinput').placeholder=direct?'Message the selected local model':'Request a read-only source inspection';
    }
    async function load() {
      try {
        policy=await api('/api/access-policy');rows=structuredClone(policy.locations);operations=policy.operations;render();
        const folder=doc.getElementById('inventoryRoot'),previous=folder.value;folder.replaceChildren();
        const empty=doc.createElement('option');empty.value='';empty.textContent='Choose a registered read location';folder.append(empty);
        for(const row of rows.filter(x=>x.enabled&&x.read)){const option=doc.createElement('option');option.value=row.path;option.textContent=row.name+' · '+row.path;folder.append(option)}
        folder.value=previous;status.textContent='Policy revision '+policy.revision.slice(0,12)+'. Changes apply to new tasks.';updateSummary();
      }catch(error){status.textContent=error.message;summary.textContent='Task access unavailable: '+error.message}
    }
    nav.onclick=()=>{activate(access,nav);load()};add.onclick=()=>{rows.push({id:'location-'+crypto.randomUUID().slice(0,8),name:'',path:'',read:false,write:false,execute:false,operations:[],exclusions:[],enabled:true});render()};
    save.onclick=async()=>{save.disabled=true;try{await api('/api/access-policy','POST',{policy:{schema_version:1,locations:rows}});await load()}catch(error){status.textContent=error.message}finally{save.disabled=false}};
    right.addEventListener('change',updateSummary);doc.getElementById('chatEngine').addEventListener('change',updateSummary);
    window.refreshAccessSummary=updateSummary;window.reloadTaskContext=load;
    // Installation/staging tools stay available under Settings, away from chat.
    load();
  }
  return {mount};
})();
