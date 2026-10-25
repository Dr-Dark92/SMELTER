/* OpenCode: a persistent confined session plus an optional connection check (diagnostics). */
const SmelterOpenCode = (() => {
  function mount(api, doc=document) {
    const button=doc.getElementById('opencodeServerCheck');
    const output=doc.getElementById('opencodeServerStatus');
    const models=doc.getElementById('opencodeAgentModel');
    // The connection check is diagnostics only; it no longer gates the session approval.
    button.onclick=async()=>{
      button.disabled=true;models.replaceChildren();
      output.textContent='Starting an owned inspection container and checking its API…';
      try{
        const result=await api('/api/opencode/agent');
        output.textContent='Server: '+result.endpoint+'\nVersion: '+result.version+'\nDirectory: '+result.directory+'\nExpected: '+result.expected_directory+'\n'+result.reason;
        for(const model of result.models||[]){const option=doc.createElement('option');option.value=model.key;option.textContent=model.key;models.append(option)}
      }catch(error){output.textContent=error.message}
      finally{button.disabled=false}
    };
  }
  // Keep one confined container running while OpenCode is the selected engine.
  function session(api, {engine, chip, approval, ready=()=>true}, doc=document) {
    let timer=null,pending=null;
    const label={stopped:'OpenCode · off',starting:'OpenCode · starting…',ready:'OpenCode · ready',busy:'OpenCode · working',failed:'OpenCode · failed'};
    const state={starting:'busy',busy:'busy',ready:'granted',failed:'warning',stopped:''};
    function show(s){
      chip.hidden=engine.value!=='opencode';chip.firstChild.textContent=label[s.status]||'OpenCode';
      chip.dataset.state=state[s.status]||'';chip.title=s.error?'OpenCode session failed: '+s.error+'. Click to retry.':'Persistent confined OpenCode session'+(s.tasks?' · '+s.tasks+' task(s)':'')+'. Click to restart if it failed.';
      chip.setAttribute('aria-label',chip.firstChild.textContent+(s.error?' · '+s.error:''));
      clearTimeout(timer);if(engine.value==='opencode'&&(s.status==='starting'||s.status==='busy'))timer=setTimeout(poll,2500);
    }
    async function poll(){try{show(await api('/api/opencode/session'))}catch(e){show({status:'failed',error:e.message})}}
    async function start(){
      const selected=engine.value==='opencode';
      if(approval){approval.checked=selected;approval.dispatchEvent?.(new Event('change',{bubbles:true}))}
      if(!selected){clearTimeout(timer);chip.hidden=true;return}
      if(!ready())return;
      if(pending)return pending;
      show({status:'starting'});
      pending=(async()=>{try{show(await api('/api/opencode/session','POST',{action:'start'}))}catch(e){show({status:'failed',error:e.message})}finally{pending=null}})();
      return pending;
    }
    chip.onclick=start;engine.addEventListener('change',start);chip.hidden=true;start();
    return {poll,start};
  }
  function defaultModel(models, configuration){
    // Without a connection check, use the configured model's OpenCode key.
    return models.value||(configuration?.model?'local/'+configuration.model:'');
  }
  return {mount,session,defaultModel};
})();
if(typeof module!=='undefined')module.exports=SmelterOpenCode;
