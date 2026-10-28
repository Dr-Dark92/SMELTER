/* Explicit task-artifact registration and previews inside the trace workbench.
   Images use one owned blob URL; GLBs reuse SmelterModels (one owned viewer). */
const SmelterTraceArtifacts=(()=>{
 const PREVIEWABLE=/\.(png|jpe?g|webp|glb)$/i;
 const el=(doc,tag,text)=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;return n};
 let api=null,changed=()=>{},artifacts=[],error='',loading=null,image=null;
 function configure(fetcher,onChange){api=fetcher;changed=onChange||changed}
 async function refresh(){
  if(!api||loading)return loading;
  loading=(async()=>{try{const result=await api('/api/task-trace/artifacts');const next=result.artifacts||[];const differs=JSON.stringify(next)!==JSON.stringify(artifacts);artifacts=next;error='';if(differs)changed()}catch(e){error=e.message}finally{loading=null}})();
  return loading;
 }
 // Releases the single image preview; SmelterModels.clear releases the GLB viewer.
 function release(){if(image){URL.revokeObjectURL(image.url);image.node.remove();image=null}if(typeof SmelterModels!=='undefined')SmelterModels.clear()}
 function relativeOf(node){const value=node.detail?.['Workspace-relative'];return value&&!value.startsWith('outside')?value:null}
 async function preview(artifact,host,doc,status){
  release();
  if(artifact.state!=='current'){status.textContent='Preview unavailable: artifact is '+artifact.state+'. Register the current file again.';return}
  if(artifact.kind==='model'){
   if(typeof SmelterModels==='undefined'){status.textContent='GLB viewer is not loaded on this page.';return}
   // The shared viewer fetches only same-origin artifact URLs and keeps its own lifecycle.
   SmelterModels.mount({id:artifact.id,filename:artifact.relative_path.split('/').at(-1),bytes:artifact.bytes,meshes:artifact.details?.meshes??0,materials:artifact.details?.materials??0,images:artifact.details?.images??0,animation_clips:artifact.details?.animation_clips||[],source_url:artifact.source_url,labels_read_only:true},host);
   status.textContent='Use Load 3D preview. A successful preview does not prove game integration.';return}
  status.textContent='Loading image…';
  try{
   const response=await fetch(artifact.source_url,{headers:{'X-Smelter-Token':SmelterAuth.token()},cache:'no-store'});
   if(!response.ok){const body=await response.json().catch(()=>({}));throw Error(body.error||('HTTP '+response.status))}
   const url=URL.createObjectURL(await response.blob()),node=el(doc,'img');
   release();node.src=url;node.alt=artifact.relative_path;Object.assign(node.style,{maxWidth:'100%',maxHeight:'320px',display:'block',background:'#fff2',borderRadius:'6px'});
   image={url,node};host.append(node);status.textContent='Image preview · SHA-256 verified on read.';
  }catch(e){status.textContent='Preview failed: '+e.message}
 }
 function describe(artifact){return artifact.kind+' · '+artifact.state+' · '+artifact.bytes+' bytes · '+artifact.sha256.slice(0,16)+'… · '+(artifact.producer?.tool?artifact.producer.tool+' ('+artifact.producer.source+')':artifact.producer?.source||'')}
 function inspect(node,host,doc,trace,readOnly){
  const box=el(doc,'section');box.append(el(doc,'h3','Task artifact'));const status=el(doc,'p');status.setAttribute('role','status');const stage=el(doc,'div');
  const artifact=node.kind==='artifact'?node.artifact:null,relative=node.kind==='file'?relativeOf(node):artifact?.relative_path;
  const registered=artifact?[artifact]:artifacts.filter(a=>a.relative_path.toLowerCase()===String(relative).toLowerCase()&&a.workspace_id===trace?.binding?.workspace_id);
  for(const item of registered){const row=el(doc,'div');row.append(el(doc,'p',describe(item)));if(item.derived_from?.length)row.append(el(doc,'small','Derived from: '+item.derived_from.join(', ')));const show=el(doc,'button','Preview');show.onclick=()=>preview(item,stage,doc,status);row.append(show);box.append(row)}
  if(node.kind==='file'){
   if(!relative||!PREVIEWABLE.test(relative))box.append(el(doc,'p','Only PNG, JPEG, WebP and GLB files inside the bound workspace can be registered.'));
   else if(readOnly)box.append(el(doc,'p','Saved charts are read-only; return to the live trace to register.'));
   else{
    const names=t=>t.file&&t.file.replaceAll('\\','/').toLowerCase().endsWith('/'+relative.toLowerCase());
    const calls=(trace?.tools||[]).filter(t=>names(t)&&(['write','edit'].includes(t.tool)||t.tool.startsWith('smelter_')));
    const choose=el(doc,'select');choose.setAttribute('aria-label','Producing call');const none=el(doc,'option','No observed producer (declare only)');none.value='';choose.append(none);
    for(const c of calls){const o=el(doc,'option',c.tool+' · '+c.phase+' · '+c.call_id);o.value=c.call_id;choose.append(o)}
    const lineage=el(doc,'select');lineage.setAttribute('aria-label','Converted from registered artifact');const direct=el(doc,'option','Not a conversion');direct.value='';lineage.append(direct);
    for(const a of artifacts.filter(a=>a.workspace_id===trace?.binding?.workspace_id&&a.relative_path!==relative).slice(0,30)){const o=el(doc,'option','Converted from '+a.relative_path+' ('+a.sha256.slice(0,8)+')');o.value=a.id;lineage.append(o)}
    const add=el(doc,'button','Register as task artifact');
    add.onclick=async()=>{add.disabled=true;status.textContent='Registering…';try{const result=await api('/api/task-trace/artifacts','POST',{action:'register',relative_path:relative,...(choose.value?{producer_call_id:choose.value}:{}),...(lineage.value?{derived_from:[lineage.value]}:{})});status.textContent='Registered · SHA-256 '+result.sha256.slice(0,16)+'…';await refresh();changed()}catch(e){status.textContent=e.message}finally{add.disabled=false}};
    box.append(el(doc,'small','Registration records path, kind, size, SHA-256, source revision and the producer you select. It does not convert, copy or publish the file.'),choose,lineage,add);
   }
  }
  box.append(status,stage);host.append(box);
 }
 function render(panel,doc){
  const box=el(doc,'section');box.append(el(doc,'h4','Registered task artifacts ('+artifacts.length+')'));
  if(error)box.append(el(doc,'p',error));
  if(!artifacts.length)box.append(el(doc,'p','None registered. Select an image or GLB file node to register it explicitly.'));
  const list=el(doc,'ul');for(const a of artifacts.slice(0,50))list.append(el(doc,'li',a.relative_path+' · '+describe(a)+' · task '+(a.task?.task_id||'—')));box.append(list);panel.append(box);
 }
 return {configure,refresh,release,inspect,render,list:()=>artifacts};
})();
if(typeof module!=='undefined')module.exports=SmelterTraceArtifacts;
