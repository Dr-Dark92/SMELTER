/* Connection checks do not create sessions or submit prompts. */
const SmelterOpenCode = (() => {
  function mount(api, doc=document) {
    const button=doc.getElementById('opencodeServerCheck');
    const output=doc.getElementById('opencodeServerStatus');
    const models=doc.getElementById('opencodeAgentModel');
    const approval=doc.getElementById('opencodeAgentApprove');
    approval.disabled=true;
    button.onclick=async()=>{
      button.disabled=true;approval.checked=false;approval.disabled=true;models.replaceChildren();
      output.textContent='Checking existing local server…';
      try{
        const result=await api('/api/opencode/agent');
        output.textContent='Server: '+result.endpoint+'\nVersion: '+result.version+'\nDirectory: '+result.directory+'\nExpected: '+result.expected_directory+'\n'+result.reason;
        for(const model of result.models||[]){const option=doc.createElement('option');option.value=model.key;option.textContent=model.key;models.append(option)}
        approval.disabled=!result.read_only_ready;
      }catch(error){output.textContent=error.message}
      finally{button.disabled=false}
    };
  }
  return {mount};
})();
if(typeof module!=='undefined')module.exports=SmelterOpenCode;
