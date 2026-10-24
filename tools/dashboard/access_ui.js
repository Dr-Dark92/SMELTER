/* One settings surface. Location policy and per-turn tool selection remain distinct. */
const SmelterAccess = (() => {
  function mount(api, doc=document) {
    const surface=SmelterSettings.current,right=surface.content,summary=surface.summary;
    const access=doc.createElement('section');
    const nav=surface.addPanel('accessPolicyPanel','Workspaces & Access',access);
    const permissions=doc.getElementById('pythonTools');permissions.open=true;
    const taskPanel=surface.task;
    const taskNote=doc.createElement('p');taskNote.textContent='Select a subset of registered access for the next Send. Skills cannot expand permissions. OpenCode uses a managed container and local-model relay; arbitrary external MCP remains blocked.';
    const effectiveContext=doc.createElement('p');effectiveContext.className='effective-task-context';taskPanel.prepend(taskNote,effectiveContext);
    const agentAccess=doc.createElement('div');agentAccess.id='openCodeTaskAccess';
    const agentHeading=doc.createElement('h4');agentHeading.textContent='OpenCode · selected skills + MCP tools';agentAccess.append(agentHeading);
    const check=doc.getElementById('opencodeServerCheck'),connection=doc.getElementById('opencodeServerStatus');
    const model=doc.getElementById('opencodeAgentModel').closest('label'),approval=doc.getElementById('opencodeAgentApprove').closest('label'),keep=doc.getElementById('keepTaskAccess').closest('label');
    agentAccess.append(check,connection,model);taskPanel.append(agentAccess);
    // Per-send grants sit in a popover beside Send, opened from the Tools chip.
    const composer=doc.getElementById('composer'),chips=doc.getElementById('composerChips');
    const popover=doc.createElement('div');popover.id='accessPopover';popover.className='access-popover';popover.hidden=true;
    popover.setAttribute('role','dialog');popover.setAttribute('aria-label','Tools for the next message');
    const popTitle=doc.createElement('h3');popTitle.textContent='Tools for the next message';
    const agentSection=doc.createElement('div');agentSection.className='popover-section';agentSection.append(approval);
    const keepSection=doc.createElement('div');keepSection.className='popover-section';keepSection.append(keep);
    permissions.open=true;
    // Connection checks are diagnostics, not grants: keep them in Task diagnostics.
    const reaCheck=doc.getElementById('reaCheck'),reaStatus=doc.getElementById('reaStatus');
    if(reaCheck){const rea=doc.createElement('div');rea.id='reaDiagnostics';const h=doc.createElement('h4');h.textContent='REA connection';rea.append(h,reaCheck,reaStatus);taskPanel.append(rea)}
    popover.append(popTitle,permissions,agentSection,keepSection);composer.append(popover);
    const chip=(id,label)=>{const b=doc.createElement('button');b.type='button';b.id=id;b.className='composer-chip';const t=doc.createElement('span');t.textContent=label;b.append(t);chips.append(b);return b};
    const modelChip=chip('composerModel','Model');modelChip.onclick=()=>surface.open('runtimePanel');
    const toolsChip=chip('composerTools','Tools');toolsChip.setAttribute('aria-controls','accessPopover');toolsChip.setAttribute('aria-expanded','false');
    const setPopover=open=>{popover.hidden=!open;toolsChip.setAttribute('aria-expanded',String(open));if(open)popover.querySelector('input,select,button')?.focus()};
    toolsChip.onclick=()=>setPopover(popover.hidden);window.openAccessPopover=()=>setPopover(true);
    doc.addEventListener('keydown',event=>{if(event.key==='Escape'&&!popover.hidden){setPopover(false);toolsChip.focus()}});
    doc.addEventListener('pointerdown',event=>{if(!popover.hidden&&!popover.contains(event.target)&&!toolsChip.contains(event.target))setPopover(false)});
    let policy=null;
    function updateSummary() {
      const engine=doc.getElementById('chatEngine').value;
      const direct=engine==='ollama';permissions.hidden=false;agentAccess.hidden=direct;agentSection.hidden=direct;
      const names=[];
      if(doc.getElementById('approveInventory').checked)names.push('folder inventory');
      if(doc.getElementById('approveDiagnostics').checked)names.push('new reports');
      if(doc.getElementById('approveRea').checked)names.push('REA');
      if(doc.getElementById('approveFrontendWorkspace').checked)names.push('V2 CSS/tests/preview');
      if(doc.getElementById('approveCodingWorkspace').checked)names.push('isolated code proposals/tests');
      if(doc.querySelector('#modelInspectionGrants input:checked'))names.push('selected GLB metadata');
      const detailedSummary=(direct?'Ollama':'OpenCode → Ollama')+' · '+(policy?.model||'loading model…')+' · ctx '+(policy?.configuration?.runtime.context_tokens||'?')+' / output '+(policy?.configuration?.runtime.max_output_tokens||'?')+' / '+(policy?.configuration?.runtime.timeout_seconds||'?')+'s · '+(names.join(', ')||'no host file tools selected');
      summary.textContent=(direct?'Direct chat':'OpenCode')+' · '+(names.join(', ')||'No host tools approved');summary.title=detailedSummary;effectiveContext.textContent=detailedSummary;
      const runtime=policy?.configuration?.runtime;
      modelChip.firstChild.textContent=(policy?.model||'Model')+(runtime?' · '+Math.round(runtime.context_tokens/1024)+'K':'');
      modelChip.title='Model and runtime for new tasks: '+detailedSummary+'. Opens Runtime & profiles.';
      const kept=doc.getElementById('keepTaskAccess').checked,approved=doc.getElementById('opencodeAgentApprove').checked;
      const needsApproval=!direct&&!approved;
      toolsChip.firstChild.textContent=needsApproval?'Approve OpenCode':names.length?'Tools · '+names.length+(kept?' · kept':''):'Tools';
      toolsChip.dataset.state=needsApproval?'warning':names.length?'granted':'';
      toolsChip.title=(names.join(', ')||'No host tools for the next message')+(kept?' · kept for following sends':'');
      toolsChip.setAttribute('aria-label','Tools for the next message: '+(needsApproval?'OpenCode not approved':names.join(', ')||'none'));
      modelChip.setAttribute('aria-label','Model and runtime: '+modelChip.firstChild.textContent);
      doc.getElementById('chatinput').placeholder=direct?'Message the selected local model':'Describe a task using selected skills and approved tools';
    }
    function applyContext(report){
      policy=report;window.smelterTaskConfiguration=policy.configuration;window.smelterTaskPolicyRevision=policy.revision;SmelterWorkbench.context(policy.configuration,doc);
      const folder=doc.getElementById('inventoryRoot'),previous=folder.value;folder.replaceChildren();
      const empty=doc.createElement('option');empty.value='';empty.textContent='Choose an applied read location';folder.append(empty);
      for(const row of policy.locations.filter(x=>x.enabled&&x.read)){const option=doc.createElement('option');option.value=row.path;option.textContent=row.name+' · '+row.path;folder.append(option)}
      folder.value=previous;updateSummary();
    }
    const locations=SmelterLocations.mount(access,api,{onApplied:applyContext,doc});
    nav.onclick=()=>{surface.activate(access.id);locations.refresh()};
    right.addEventListener('change',updateSummary);popover.addEventListener('change',updateSummary);doc.getElementById('chatEngine').addEventListener('change',updateSummary);
    window.refreshAccessSummary=updateSummary;window.reloadTaskContext=()=>locations.refresh();
    // Installation/staging tools stay available under Settings, away from chat.
    locations.refresh();
  }
  return {mount};
})();
