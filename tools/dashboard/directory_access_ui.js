/* Inline, human-only directory decisions. Render paths/reasons as plain text. */
const SmelterDirectoryAccess=(()=>{
 function mount(parent,api,doc=document){
  const box=doc.createElement('section');box.hidden=true;box.className='directory-access-card';
  box.setAttribute('role','region');box.setAttribute('aria-label','Directory access request');
  Object.assign(box.style,{border:'1px solid var(--accent, #888)',borderRadius:'10px',padding:'14px',margin:'12px 0'});
  const heading=doc.createElement('h3');heading.textContent='Grant folder access';
  const path=doc.createElement('pre');path.style.whiteSpace='pre-wrap';path.style.overflowWrap='anywhere';
  const reason=doc.createElement('p');const detail=doc.createElement('p');
  detail.textContent='Read only. Allowing resumes this task and keeps completed work.';
  const status=doc.createElement('p');status.setAttribute('role','status');
  const controls=doc.createElement('div');controls.style.display='flex';controls.style.flexWrap='wrap';controls.style.gap='8px';
  let active=null,busy=false;
  const buttons=[];
  for(const [label,decision] of [['Allow for this task','allow_task'],['Remember for this project','allow_project'],['Deny','deny']]){
   const button=doc.createElement('button');button.type='button';button.textContent=label;
   button.onclick=async()=>{
    if(!active||busy)return;
    const request={...active};busy=true;buttons.forEach(b=>b.disabled=true);status.textContent='Applying your decision…';
    try{
     const result=await api('/api/access-requests','POST',{job_id:request.job_id,request_id:request.id,decision,expected_revision:request.policy_revision});
     if(active?.id===request.id){status.textContent=result.status==='access_granted'?'Access granted. Continuing the same task.':'Access declined. The task can continue other work.';active=null;box.hidden=true}
     globalThis.reloadTaskContext?.();
    }catch(error){if(active?.id===request.id)status.textContent=error.message}
    finally{busy=false;if(active?.id===request.id)buttons.forEach(b=>b.disabled=false)}
   };
   buttons.push(button);controls.append(button);
  }
  box.append(heading,path,reason,detail,controls,status);parent.append(box);
  return {render(job){
   const request=job?.state==='running'?job.pending_access:null;
   if(!request){active=null;box.hidden=true;return}
   box.hidden=false;path.textContent=request.directory;reason.textContent=request.reason;
   if(active?.id!==request.id){active={...request};busy=false;buttons.forEach(b=>b.disabled=false);status.textContent='Waiting for your decision. No folder access has been granted.'}
  }};
 }
 return {mount,permissions:supported=>supported===true?{access_requests:true}:{}};
})();
if(typeof module!=='undefined')module.exports=SmelterDirectoryAccess;
if(typeof window!=='undefined')window.SmelterDirectoryAccess=SmelterDirectoryAccess;
