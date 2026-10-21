/* One settings surface. Location policy and per-turn tool selection remain distinct. */
const SmelterAccess = (() => {
  function mount(api, doc=document) {
    const surface=SmelterSettings.current,right=surface.content,summary=surface.summary;
    const access=doc.createElement('section');
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
    let policy=null;
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
    function applyContext(report){
      policy=report;window.smelterTaskConfiguration=policy.configuration;window.smelterTaskPolicyRevision=policy.revision;
      const folder=doc.getElementById('inventoryRoot'),previous=folder.value;folder.replaceChildren();
      const empty=doc.createElement('option');empty.value='';empty.textContent='Choose an applied read location';folder.append(empty);
      for(const row of policy.locations.filter(x=>x.enabled&&x.read)){const option=doc.createElement('option');option.value=row.path;option.textContent=row.name+' · '+row.path;folder.append(option)}
      folder.value=previous;updateSummary();
    }
    const locations=SmelterLocations.mount(access,api,{onApplied:applyContext,doc});
    nav.onclick=()=>{surface.activate(access.id);locations.refresh()};
    right.addEventListener('change',updateSummary);doc.getElementById('chatEngine').addEventListener('change',updateSummary);
    window.refreshAccessSummary=updateSummary;window.reloadTaskContext=()=>locations.refresh();
    // Installation/staging tools stay available under Settings, away from chat.
    locations.refresh();
  }
  return {mount};
})();
