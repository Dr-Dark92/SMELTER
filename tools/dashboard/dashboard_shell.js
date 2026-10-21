
let activeChat=null;
let selectedSkills=[];
let autoSkills=false;
function initShell(){
 const main=document.querySelector('main'), sections=[...main.querySelectorAll(':scope > section.panel:not(#bootstrap)')];
 const shell=document.createElement('div');shell.id='shell';
 const left=document.createElement('aside');left.id='leftbar';
 const center=document.createElement('section');center.id='workspace';
 const settings=SmelterSettings.create(document);const right=settings.content;center.prepend(settings.toolbar);
 left.innerHTML='<h2>Chat history</h2>';
 const newChat=document.createElement('button');newChat.textContent='+ New chat';newChat.onclick=()=>editConversationTitle();
 const historySearch=document.createElement('input');historySearch.id='chatSearch';historySearch.type='search';historySearch.placeholder='Search conversations';historySearch.setAttribute('aria-label','Search conversation titles');historySearch.oninput=renderChatHistory;
 const historyCount=document.createElement('p');historyCount.id='historyCount';historyCount.className='history-count';
 const history=document.createElement('div');history.id='chatHistory';left.append(newChat,historySearch,historyCount,history);
 const title=document.createElement('h2');title.id='chatTitle';title.textContent='SMELTER · Local chat';
 const log=document.createElement('div');log.id='chatlog';log.setAttribute('role','log');log.setAttribute('aria-label','Conversation messages');log.textContent='Select New chat. Python tools require permission for each message.';
 const permissionsBox=document.createElement('details');permissionsBox.id='pythonTools';
 const permissionsTitle=document.createElement('summary');permissionsTitle.textContent='Tool permissions for the next message';
 const readFolder=document.createElement('select');readFolder.id='inventoryRoot';readFolder.placeholder='Absolute folder to inventory';readFolder.style.width='95%';
 const readGrant=document.createElement('input');readGrant.type='checkbox';readGrant.id='approveInventory';
 const readLabel=document.createElement('label');readLabel.append(readGrant,document.createTextNode(' Allow read-only inventory of this folder'));
 const writeGrant=document.createElement('input');writeGrant.type='checkbox';writeGrant.id='approveDiagnostics';
 const writeLabel=document.createElement('label');writeLabel.append(writeGrant,document.createTextNode(' Allow new Markdown reports in diagnostics/ (no overwrite)'));
 const reaGrant=document.createElement('input');reaGrant.type='checkbox';reaGrant.id='approveRea';
 const reaLabel=document.createElement('label');reaLabel.append(reaGrant,document.createTextNode(' Allow REA CLI for this message (runs Node; static PE inspection in the folder above)'));
 const reaCheck=document.createElement('button');reaCheck.type='button';reaCheck.textContent='Check REA connection';
 const reaStatus=document.createElement('p');reaStatus.id='reaStatus';
 reaCheck.onclick=async()=>{try{const s=await api('/api/rea/status');reaStatus.textContent='REA: '+s.status+' | version: '+(s.installed_version||'not installed')+' | '+s.reason}catch(e){reaStatus.textContent=e.message}};
 const workspaceGrant=document.createElement('input');workspaceGrant.type='checkbox';workspaceGrant.id='approveFrontendWorkspace';
 const workspaceLabel=document.createElement('label');workspaceLabel.style.display='block';workspaceLabel.append(workspaceGrant,document.createTextNode(' Allow isolated frontend workspace: read source, edit destination CSS, run fixed tests and launch port 8770 (24 calls, up to 15 minutes)'));
 const modelGrants=document.createElement('div');modelGrants.id='modelInspectionGrants';
 const selectedModelIds=()=>[...modelGrants.querySelectorAll('input:checked')].map(x=>x.dataset.assetId);
 window.setChatModelGrants=assets=>{modelGrants.replaceChildren();for(const asset of assets){const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.dataset.assetId=asset.id;const label=document.createElement('label');label.style.display='block';label.append(checkbox,document.createTextNode(' Allow read-only GLB inspection: '+asset.filename));modelGrants.append(label)}permissionsBox.dispatchEvent(new Event('change',{bubbles:true}))};
 const toolsNote=document.createElement('p');toolsNote.textContent='Applies only to the next Send. Built-in scopes do not sandbox external MCP servers. Tool results are logged locally.';
 permissionsBox.append(permissionsTitle,readFolder,document.createElement('br'),readLabel,document.createElement('br'),writeLabel,document.createElement('br'),reaLabel,document.createElement('br'),reaCheck,reaStatus,modelGrants,workspaceLabel,toolsNote);
 const composer=document.createElement('div');composer.id='composer';
 const input=document.createElement('textarea');input.rows=3;input.maxLength=1800;input.setAttribute('aria-label','Message');input.id='chatinput';input.placeholder='Message local Qwen 3.5 9B';
 const send=document.createElement('button');send.textContent='Send';
 const requestStatus=document.createElement('p');requestStatus.id='requestStatus';requestStatus.setAttribute('role','status');requestStatus.setAttribute('aria-live','polite');requestStatus.textContent='Ready · local workspace';
 const stop=document.createElement('button');stop.textContent='Stop';stop.type='button';stop.disabled=true;
 const reconnect=document.createElement('button');reconnect.type='button';reconnect.textContent='Reconnect task';reconnect.hidden=true;reconnect.onclick=()=>resumeJob();
 const jobMessage=job=>{const text=job.state==='done'?'Completed · '+job.elapsed_seconds+'s':job.state==='cancelled'?'Stopped · completed tool actions remain recorded':job.state==='partial'?'Partially completed · '+job.error:job.state==='interrupted'?'Interrupted · '+job.error:job.state==='running'?job.phase+' · '+job.elapsed_seconds+'s':'Request failed: '+job.error;return text+(job.persistence_pending?' · '+job.persistence_error+' Polling or the next admission retries metadata only.':'')};
 const engineLabel=document.createElement('label');engineLabel.textContent='Execution engine ';
 const engineChoice=document.createElement('select');engineChoice.id='chatEngine';engineChoice.setAttribute('aria-label','Execution engine');
 for(const [value,text] of [['opencode','OpenCode · skills + approved tools'],['ollama','Ollama · direct chat']]){const option=document.createElement('option');option.value=value;option.textContent=text;engineChoice.append(option)}engineLabel.append(engineChoice);
 engineChoice.onchange=()=>{send.textContent=engineChoice.value==='opencode'?'Send via OpenCode':'Send'};engineChoice.onchange();
 let currentJob=null;
 let fileActivityView=null,fileActivityJob=null,fileActivityHost=null;
 const showFileActivity=job=>{if(!job.files?.length)return;if(fileActivityJob!==job.id||!fileActivityHost?.isConnected){fileActivityHost=document.createElement('section');log.append(fileActivityHost);fileActivityView=SmelterFiles.mount(fileActivityHost);fileActivityJob=job.id}fileActivityView.update(job.files)};
 let agentHost=null,agentJob=null;
 const showAgentActivity=job=>{if(!job.output_text&&!job.tool_activity?.length)return;if(agentJob!==job.id||!agentHost?.isConnected){agentHost=document.createElement('article');agentHost.className='message message-assistant';agentJob=job.id;log.append(agentHost)}agentHost.replaceChildren();const heading=document.createElement('header');heading.className='message-label';heading.textContent=job.engine?.startsWith('opencode')?'OpenCode · scoped agent session':'Ollama · generating';const body=document.createElement('div');SmelterChat.render(job.output_text||'Waiting for OpenCode…',body);const activity=document.createElement('pre');activity.style.fontSize='11px';activity.style.whiteSpace='pre-wrap';activity.textContent=(job.tool_activity||[]).map(e=>e.tool+' · '+e.result.status+(e.result.path?' · '+e.result.path:'')).join('\n');agentHost.append(heading,body,activity)};
 const renderPending=(content)=>{const bubble=document.createElement('article');bubble.className='message message-user';const header=document.createElement('header');header.className='message-label';header.textContent='You · submitting';const body=document.createElement('div');body.className='message-content';body.textContent=content;bubble.append(header,body);log.append(bubble);log.scrollTop=log.scrollHeight;return header};
 stop.onclick=async()=>{if(!currentJob)return;stop.disabled=true;try{const job=await api('/api/chats','POST',{action:'stop',job_id:currentJob});requestStatus.textContent=job.phase}catch(e){requestStatus.textContent='Could not stop: '+e.message;stop.disabled=false}};
 input.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();if(!send.disabled)send.click()}});
 send.onclick=async()=>{if(!activeChat){requestStatus.textContent='Name this conversation, then send your message.';newChat.click();return}if(send.disabled)return;const content=input.value.trim();if(!content){requestStatus.textContent='Enter a message before sending';return}if(engineChoice.value==='opencode'&&!document.getElementById('opencodeAgentApprove').checked){requestStatus.textContent='Check managed OpenCode and approve this session in Task access';return}send.disabled=true;newChat.disabled=true;input.disabled=true;imageInput.disabled=true;
 const executionEngine=engineChoice.value;engineChoice.disabled=true;
 const conversation=activeChat;const started=Date.now();const pending=renderPending(content);
 const toolPermissions={...mcpControls.collect(),frontend_workspace:workspaceGrant.checked,model_ids:selectedModelIds(),inventory_root:readGrant.checked?readFolder.value.trim():null,write_diagnostics:writeGrant.checked,rea_analysis:reaGrant.checked,rea_root:reaGrant.checked&&readFolder.value.trim()?readFolder.value.trim():null};
 readGrant.checked=false;writeGrant.checked=false;reaGrant.checked=false;workspaceGrant.checked=false;modelGrants.querySelectorAll('input').forEach(x=>x.checked=false);mcpControls.refreshApprovals();window.refreshAccessSummary?.();
 requestStatus.textContent='Submitting request…';
 try{let attachment=null;const file=imageInput.files[0];
 if(file){if(file.size>2097152)throw Error('Image exceeds 2 MiB');const b64=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(Error('Could not read image'));reader.readAsDataURL(file)});attachment={mime:file.type,base64:b64}}
 const agentApproval=document.getElementById('opencodeAgentApprove');const approved=agentApproval.checked;agentApproval.checked=false;
 if(executionEngine==='opencode'&&attachment)throw Error('OpenCode accepts text tasks; images are not forwarded');
 if(executionEngine==='opencode'&&!approved)throw Error('Check managed OpenCode and approve this session in Task access');
 let job=await api('/api/chats','POST',{action:'start',id:conversation,content,configuration_revision:window.smelterTaskConfiguration?.revision,policy_revision:window.smelterTaskPolicyRevision,engine:executionEngine,opencode_approval:approved,opencode_model:document.getElementById('opencodeAgentModel').value,image:attachment,skills:selectedSkills,auto_skills:autoSkills,tool_permissions:toolPermissions});currentJob=job.id;stop.disabled=false;reconnect.hidden=true;pending.textContent='You · sent';input.value='';imageInput.value='';
 try{sessionStorage.setItem('smelterActiveJob',JSON.stringify({id:job.id,conversation}))}catch(e){}
 while(job.state==='running'){showFileActivity(job);showAgentActivity(job);requestStatus.textContent=job.phase+' · '+Math.floor((Date.now()-started)/1000)+'s';await new Promise(resolve=>setTimeout(resolve,1000));job=await api('/api/chat-jobs/'+encodeURIComponent(currentJob))}showFileActivity(job);showAgentActivity(job);
 currentJob=null;try{sessionStorage.removeItem('smelterActiveJob')}catch(e){}
 requestStatus.textContent=jobMessage(job);
 if(activeChat===conversation)await openChat(conversation);await refreshChats();
 }catch(e){pending.textContent='You · submission/status error';requestStatus.textContent=e.message+(currentJob?' · Task status is unknown. Reconnect or use Stop.':'');reconnect.hidden=!currentJob;}
 finally{if(!currentJob){stop.disabled=true;send.disabled=false;newChat.disabled=false;input.disabled=false;imageInput.disabled=false;engineChoice.disabled=false;input.focus()}}};
 const resumeJob=async()=>{
  let saved;try{saved=JSON.parse(sessionStorage.getItem('smelterActiveJob')||'null')}catch(e){return}if(!saved)return;
  currentJob=saved.id;send.disabled=true;newChat.disabled=true;input.disabled=true;imageInput.disabled=true;engineChoice.disabled=true;stop.disabled=false;reconnect.hidden=true;
  let terminal=false;
  try{
   let job;do{job=await api('/api/chat-jobs/'+encodeURIComponent(currentJob));showFileActivity(job);showAgentActivity(job);requestStatus.textContent=jobMessage(job);if(job.state==='running')await new Promise(resolve=>setTimeout(resolve,1000))}while(job.state==='running');
   terminal=true;await openChat(saved.conversation);await refreshChats();
  }catch(e){requestStatus.textContent=e.message+(terminal?'':' · Task status is unknown. Reconnect or use Stop.');reconnect.hidden=terminal}
  finally{
   if(terminal){currentJob=null;try{sessionStorage.removeItem('smelterActiveJob')}catch(e){}stop.disabled=true;send.disabled=false;newChat.disabled=false;input.disabled=false;imageInput.disabled=false;engineChoice.disabled=false;reconnect.hidden=true}
  }
 };
 window.resumeChatJob=resumeJob;
 const imageInput=document.createElement('input');imageInput.type='file';imageInput.accept='image/png,image/jpeg,image/webp';imageInput.title='Attach PNG, JPEG, or WebP (up to 2 MiB)';imageInput.style.maxWidth='180px';
 const modelFile=document.createElement('input');modelFile.type='file';modelFile.accept='.glb';modelFile.hidden=true;modelFile.id='modelFile';
 const attachments=SmelterAttachments.mount(composer,{imageInput,modelInput:modelFile,canAttach:()=>!send.disabled,onError:message=>requestStatus.textContent=message});const attachModel=attachments.button;
 modelFile.onchange=async()=>{const file=modelFile.files[0];if(!file)return;if(!activeChat){requestStatus.textContent='Create a titled conversation before attaching a model.';modelFile.value='';return}if(send.disabled){modelFile.value='';return}if(file.size>25*1024*1024){requestStatus.textContent='GLB exceeds 25 MiB';modelFile.value='';return}const conversation=activeChat;send.disabled=true;newChat.disabled=true;input.disabled=true;imageInput.disabled=true;attachModel.disabled=true;requestStatus.textContent='Uploading GLB for local preview…';try{const base64=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(Error('Could not read GLB'));reader.readAsDataURL(file)});await api('/api/models','POST',{conversation_id:conversation,filename:file.name,base64});await openChat(conversation);await refreshChats();requestStatus.textContent='GLB saved. Click Load 3D preview; Qwen was not called.'}catch(e){requestStatus.textContent=e.message}finally{send.disabled=false;newChat.disabled=false;input.disabled=false;imageInput.disabled=false;attachModel.disabled=false;modelFile.value=''}};
 composer.append(input,imageInput,modelFile,engineLabel,send,stop,reconnect);center.append(title,log,requestStatus,composer);settings.task.append(permissionsBox);

 const entries=[['toolsPanel','Installed tools',0,'Tools'],['workflowPanel','Workflow planner',1,'Tools'],['archivePanel','Archive inspection',2,'Tools'],['mediaPanel','Media inspection',3,'Tools'],['blenderPanel','Blender',4,'Tools'],['ollamaPanel','Ollama models',5,'AI & runtime'],['opencodePanel','OpenCode',6,'AI & runtime']];
 for(const [id,label,index,category] of entries)settings.addPanel(id,label,sections[index],category);
 settings.activate('taskAccessPanel');
 shell.append(left,center);
 const skillNotice=document.createElement('div');skillNotice.id='skillNotice';skillNotice.hidden=true;skillNotice.setAttribute('role','status');
 const skillNoticeText=document.createElement('span');skillNoticeText.id='skillNoticeText';const skillReview=document.createElement('button');skillReview.textContent='Review skills';const dismissNotice=document.createElement('button');dismissNotice.textContent='Dismiss';skillNotice.append(skillNoticeText,skillReview,dismissNotice);main.prepend(skillNotice);
 const chatElements=[title,log,engineLabel,requestStatus,composer];
 window.showChatWorkspace=()=>chatElements.forEach(x=>x.hidden=false);
 const showSkills=()=>{settings.open();document.getElementById('skillsManagerButton')?.click()};
 const integrations=null;
 const mcpControls=SmelterMcp.mount(right,integrations,permissionsBox,api,()=>({frontend_workspace:workspaceGrant.checked,model_ids:selectedModelIds(),inventory_root:readGrant.checked?readFolder.value.trim():null,write_diagnostics:writeGrant.checked,rea_analysis:reaGrant.checked,rea_root:reaGrant.checked&&readFolder.value.trim()?readFolder.value.trim():null}));
 skillReview.onclick=showSkills;
 let dismissedRevision=null,lastSkillsData=null,skillsPolling=false;
 dismissNotice.onclick=()=>{dismissedRevision=lastSkillsData?.revision;skillNotice.hidden=true};
 const refreshSkillNotice=async()=>{if(skillsPolling||document.hidden)return;skillsPolling=true;try{const data=await api('/api/skills/status');lastSkillsData=data;skillNoticeText.textContent=data.changes.length+' skill '+(data.changes.length===1?'change':'changes')+' · review before restart. ';skillNotice.hidden=!data.changes.length||dismissedRevision===data.revision;}catch(e){skillNoticeText.title='Skill discovery unavailable: '+e.message}finally{skillsPolling=false}};
 setInterval(refreshSkillNotice,15000);refreshSkillNotice();
 const runtimePanel=document.createElement('section');runtimePanel.className='panel';runtimePanel.id='runtimePanel';
 const runtimeNav=settings.addPanel('runtimePanel','Chat runtime',runtimePanel,'AI & runtime');
 runtimeNav.onclick=async()=>{settings.activate('runtimePanel');runtimePanel.textContent='Loading runtime settings…';
 try{const data=await api('/api/runtime');runtimePanel.replaceChildren();const heading=document.createElement('h3');heading.textContent='Chat runtime';const description=document.createElement('p');description.textContent='Applies to new direct and managed OpenCode tasks. Active tasks keep their admitted settings. Saving starts no model.';const presets=document.createElement('select');presets.setAttribute('aria-label','Runtime preset');for(const [key,label] of [['office','Office · 16K · direct'],['home','Home · 32K']]){const option=document.createElement('option');option.value=key;option.textContent=label;presets.append(option)}const apply=document.createElement('button');apply.textContent='Use preset';
 const inputs={};const definitions=[['context_tokens','Context tokens',2048,131072],['max_output_tokens','Maximum response tokens',128,8192],['timeout_seconds','Request timeout (seconds)',30,1800]];
 runtimePanel.append(heading,description,presets,apply);
 for(const [key,label,min,max] of definitions){const row=document.createElement('label');row.className='runtime-field';const input=document.createElement('input');input.type='number';input.min=min;input.max=max;input.step=1;input.value=data.settings[key];inputs[key]=input;row.append(document.createTextNode(label+' '),input);runtimePanel.append(row)}
 const thinking=document.createElement('input');thinking.type='checkbox';thinking.checked=data.settings.thinking;const thinkingLabel=document.createElement('label');thinkingLabel.className='runtime-field';thinkingLabel.append(thinking,document.createTextNode(' Allow thinking in plain text chats'));runtimePanel.append(thinkingLabel);
 const note=document.createElement('p');note.textContent='Tool/image requests use direct responses. Larger context increases memory use. The timeout covers the whole model turn; active tool operations have their own bounds.';runtimePanel.append(note);
 const result=document.createElement('p');result.setAttribute('role','status');result.textContent='Sources: '+Object.entries(data.sources).map(([key,value])=>key+'='+value).join(', ');
 apply.onclick=()=>{const preset=data.profiles[presets.value];for(const key of Object.keys(inputs))inputs[key].value=preset[key];thinking.checked=preset.thinking;result.textContent='Preset selected. Click Save to apply.'};
 const save=document.createElement('button');save.textContent='Save runtime settings';save.onclick=async()=>{const settings={thinking:thinking.checked};for(const [key,input] of Object.entries(inputs)){if(!input.checkValidity()||!input.value){result.textContent='Enter a valid value for '+key;return}settings[key]=input.valueAsNumber}save.disabled=true;try{await api('/api/chats','POST',{action:'runtime_settings',settings});result.textContent='Saved locally. Applies to the next request; active generation is unchanged.';window.reloadTaskContext?.()}catch(e){result.textContent=e.message}finally{save.disabled=false}};runtimePanel.append(save,result);
 }catch(e){runtimePanel.textContent='Runtime settings unavailable: '+e.message}};

 const footer=document.createElement('footer');footer.id='sysfooter';footer.textContent='Host observations · CPU: pending · RAM: pending · GPU: pending · Disk: pending · AI: not started';
 main.append(shell,footer);
 const aeroPanel=document.createElement('div');aeroPanel.className='panel';aeroPanel.id='aeroPanel';
 const aeroInput=document.createElement('textarea');aeroInput.id='aeroInput';aeroInput.rows=3;aeroInput.placeholder='Describe an engineering task for read-only classification';aeroInput.style.width='100%';aeroInput.style.boxSizing='border-box';
 const aeroButton=document.createElement('button');aeroButton.textContent='Preview AERO classification';
 const aeroResult=document.createElement('pre');aeroResult.style.whiteSpace='pre-wrap';aeroResult.style.overflowWrap='anywhere';
 aeroButton.onclick=async()=>{try{const result=await api('/api/aero/classify','POST',{task:aeroInput.value});aeroResult.textContent=JSON.stringify(result,null,2)}catch(e){aeroResult.textContent=e.message}};
 aeroPanel.append(aeroInput,aeroButton,aeroResult);
 const aeroNav=settings.addPanel('aeroPanel','AERO classification',aeroPanel,'Tools');
 aeroNav.onclick=()=>settings.activate('aeroPanel');
 const skillsPanel=document.createElement('section');const skillsNav=settings.addPanel('skillsPanel','Skills',skillsPanel,'Skills & integrations');skillsNav.id='skillsManagerButton';
 const skillsView=SmelterSkills.mount(skillsPanel,api,{get:()=>({selected:selectedSkills,automatic:autoSkills}),set:value=>{selectedSkills=value.selected;autoSkills=value.automatic}},document);
 skillsNav.onclick=()=>{settings.activate('skillsPanel');skillsView.load()};
 const statusPanel=document.createElement('div');statusPanel.className='panel';statusPanel.id='systemStatusPanel';statusPanel.textContent='Loading system status…';
 const statusNav=settings.addPanel('systemStatusPanel','System status',statusPanel,'System');statusNav.onclick=async()=>{settings.activate('systemStatusPanel');await refreshSystem()};
 const showEmpty=()=>SmelterWorkbench.empty(log,{hasConversation:!!activeChat,onNew:()=>newChat.click(),onSettings:id=>settings.open(id),onAttach:()=>activeChat?modelFile.click():newChat.click()});
 SmelterWorkbench.mount({main,shell,left,workspace:center,log,input,newChat,settings,engineLabel,status:requestStatus,onAttach:()=>modelFile.click(),onEmpty:showEmpty});
}
let systemStatusBusy=false;
async function refreshSystem(){
 if(systemStatusBusy||document.hidden)return;systemStatusBusy=true;
 try{const s=await api('/api/system/status');const gb=n=>(n/1073741824).toFixed(1)+' GiB';
  const cpu=s.cpu.status==='ready'?s.cpu.percent+'%':s.cpu.status;
  const ram=s.memory.status==='ready'?gb(s.memory.used_bytes)+' / '+gb(s.memory.total_bytes)+' ('+gb(s.memory.available_bytes)+' available)':s.memory.status;
  const gpu=s.gpu.status==='ready'?gb(s.gpu.allocated_bytes)+' model allocation':'unavailable';
  const models=s.models.status==='ready'?(s.models.models.map(m=>m.name).join(', ')||'no model loaded'):'Ollama unavailable';
  const summary='Host CPU: '+cpu+' · Host RAM: '+ram+' · Ollama GPU allocation: '+gpu+' · AI: '+models+' · Disk free: '+gb(s.storage.free_bytes)+' · DB: '+s.database.status;
  const footer=document.getElementById('sysfooter');SmelterWorkbench.resources(s,SmelterSettings.current);footer.title='Live host metrics. GPU means Ollama-reported model allocation, not utilization; iGPU memory is shared with RAM. Updated '+new Date(s.timestamp*1000).toLocaleTimeString();
  document.getElementById('systemStatusPanel').textContent=summary+' · Database: '+(s.database.path||'not selected');
 }catch(e){document.getElementById('sysfooter').textContent='System status unavailable: '+e.message}
 finally{systemStatusBusy=false}
}
setInterval(()=>{if(document.getElementById('sysfooter')&&!document.getElementById('sysfooter').hidden)refreshSystem()},5000);
let conversationHistory=[];
function localTimestamp(value){const raw=String(value||'');const date=new Date(raw.includes('T')?raw:raw.replace(' ','T')+'Z');return Number.isNaN(date.getTime())?raw:date.toLocaleString()}
function highlightChat(){for(const row of document.querySelectorAll('.history-row')){const selected=row.dataset.chatId===activeChat;row.classList.toggle('selected',selected);row.querySelector('.chat-open')?.setAttribute('aria-current',selected?'true':'false')}}
async function editConversationTitle(chat=null){
 if(document.getElementById('chatinput').disabled)return;
 const dialog=document.createElement('dialog');dialog.className='chat-dialog';const form=document.createElement('form');const heading=document.createElement('h2');heading.textContent=chat?'Rename conversation':'New conversation';heading.id='chatDialogTitle';dialog.setAttribute('aria-labelledby',heading.id);
 const label=document.createElement('label');label.textContent='Conversation title';const field=document.createElement('input');field.type='text';field.required=true;field.maxLength=120;field.value=chat?.title||'';field.placeholder='Give this conversation a name';label.append(field);
 const error=document.createElement('p');error.className='dialog-error';error.setAttribute('role','alert');const actions=document.createElement('div');actions.className='dialog-actions';const cancel=document.createElement('button');cancel.type='button';cancel.textContent='Cancel';const save=document.createElement('button');save.type='submit';save.textContent=chat?'Save title':'Create conversation';actions.append(cancel,save);form.append(heading,label,error,actions);dialog.append(form);document.body.append(dialog);
 let pending=false;cancel.onclick=()=>dialog.close();dialog.addEventListener('cancel',event=>{if(pending)event.preventDefault()});dialog.addEventListener('close',()=>dialog.remove());
 form.onsubmit=async event=>{event.preventDefault();if(pending)return;const title=field.value.trim();if(!title){error.textContent='A conversation title is required.';field.focus();return}if(document.getElementById('chatinput').disabled){error.textContent='Finish or stop the active request first.';return}pending=true;save.disabled=cancel.disabled=true;field.disabled=true;error.textContent='';
 try{const result=await api('/api/chats','POST',chat?{action:'rename',id:chat.id,title}:{action:'create',title});if(!chat||activeChat===chat.id)await openChat(result.id);await refreshChats();dialog.close();}
 catch(e){error.textContent=e.message;pending=false;save.disabled=cancel.disabled=false;field.disabled=false;field.focus()}};
 dialog.showModal();field.focus();field.select();
}
function renderChatHistory(){
 const history=document.getElementById('chatHistory');if(!history)return;history.replaceChildren();const query=(document.getElementById('chatSearch')?.value||'').trim().toLocaleLowerCase();const matches=conversationHistory.filter(chat=>chat.title.toLocaleLowerCase().includes(query));document.getElementById('historyCount').textContent=matches.length+' of '+conversationHistory.length+' recent conversations';
 if(!matches.length){const empty=document.createElement('p');empty.textContent=query?'No matching titles.':'Create your first conversation.';history.append(empty)}
 for(const chat of matches){const row=document.createElement('div');row.className='history-row';row.dataset.chatId=chat.id;
 const open=document.createElement('button');open.className='chat-open';open.title=chat.title;const title=document.createElement('span');title.className='history-title';title.textContent=chat.title;const date=document.createElement('small');date.textContent=localTimestamp(chat.created_at);open.append(title,date);open.onclick=()=>{if(document.getElementById('chatinput').disabled)return;openChat(chat.id)};
 const rename=document.createElement('button');rename.className='chat-action';rename.textContent='✎';rename.title='Rename';rename.setAttribute('aria-label','Rename '+chat.title);rename.onclick=()=>editConversationTitle(chat);
 const del=document.createElement('button');del.className='chat-action';del.textContent='×';del.title='Delete';del.setAttribute('aria-label','Delete '+chat.title);del.onclick=async()=>{if(document.getElementById('chatinput').disabled){SmelterWorkbench.notify('Finish or stop the active request first');return}if(!confirm('Delete conversation “'+chat.title+'”, its messages and attached 3D files? Diagnostic reports and audit logs remain.'))return;try{await api('/api/chats','POST',{action:'delete',id:chat.id});if(activeChat===chat.id){activeChat=null;document.getElementById('chatTitle').textContent='SMELTER · Local chat';document.getElementById('chatlog').textContent='Conversation deleted. Create or select another conversation.'}await refreshChats()}catch(e){SmelterWorkbench.notify(e.message)}};
 row.append(open,rename,del);history.append(row)}highlightChat();
}
async function refreshChats(){const data=await api('/api/chats');conversationHistory=data.conversations;renderChatHistory()}
function executionCards(execution){
 const section=document.createElement('section');section.className='execution-cards';section.setAttribute('aria-label','Backend tool execution');
 const heading=document.createElement('h3');heading.textContent='Tool execution · Controller record';section.append(heading);
 const events=execution.events||[];
 if(execution.verification_scope){const scope=document.createElement('p');scope.textContent=execution.verification_scope;section.append(scope)}
 if(execution.skill_snapshots?.length){const skills=document.createElement('p');skills.className='execution-path';skills.textContent='Loaded skills: '+execution.skill_snapshots.map(s=>s.id+' · '+s.sha256.slice(0,12)).join(', ');skills.title=execution.skill_snapshots.map(s=>s.id+' SHA-256 '+s.sha256).join('\n');section.append(skills)}
 if(execution.files?.length){const host=document.createElement('section');section.append(host);SmelterFiles.mount(host).update(execution.files)}
 if(!events.length){const note=document.createElement('p');const grants=execution.permissions||{};note.textContent=execution.engine==='opencode'?'No tool activity was reported by OpenCode for this session.':execution.cancelled?'Request stopped; no tool result recorded.':grants.inventory_root||grants.write_diagnostics||grants.rea_analysis||grants.mcp_tools?.length||grants.model_ids?.length||grants.frontend_workspace?'Tools were approved, but no tool calls were received.':'No tools were approved for this message.';section.append(note)}
 for(const event of events){const result=event.result||{};const failed=result.status==='error'||result.status==='rea_failed'||result.status==='mcp_failed'||result.status==='workspace_validation_failed';const card=document.createElement('article');card.className='execution-card '+(failed?'execution-error':'execution-success');
 const title=document.createElement('strong');title.textContent=(event.tool||'Unknown tool')+(event.transport==='mcp'?' [MCP]':event.transport==='opencode'?' [OpenCode]':event.process_owner==='dashboard'?' [dashboard]':'')+' · '+(event.reused?'Reused previous result':failed?(event.executed?'Failed':'Rejected'):result.status||'Unknown');card.append(title);
 if(event.transport==='opencode'){const provenance=document.createElement('small');provenance.textContent='Reported by OpenCode; execution is not independently verified by this record.';card.append(provenance)}
 const details=document.createElement('p');details.textContent=failed?(result.error||result.stderr||'Operation returned failure'):result.status==='written'?'Saved: '+result.path+' · '+result.bytes+' bytes':result.status==='inventoried'?result.files_observed+' files observed · Scan complete: '+result.scan_complete+' · Listed '+result.returned_entries+'/'+result.observed_entries:result.operation?'Operation: '+result.operation+' · Exit: '+result.exit_code:result.status==='model_inspected'?result.filename+' · '+result.meshes+' meshes · '+result.animations+' animation clips':result.server?'MCP server: '+result.server+' · Tool: '+result.tool:'Result recorded';card.append(details);
 const hash=result.sha256||result.evidence_sha256;if(hash){const checksum=document.createElement('p');checksum.className='execution-path';checksum.textContent='SHA-256: '+hash;card.append(checksum)}
 if(result.evidence_path){const path=document.createElement('p');path.className='execution-path';path.textContent='Evidence: '+result.evidence_path;card.append(path)}
 const disclosure=document.createElement('details');const summary=document.createElement('summary');summary.textContent='Recorded result';const raw=document.createElement('pre');raw.textContent=JSON.stringify(event,null,2);disclosure.append(summary,raw);card.append(disclosure);section.append(card)}
 if(execution.audit_path){const audit=document.createElement('p');audit.className='execution-path';audit.textContent='Audit: '+execution.audit_path;section.append(audit)}
 const scope=document.createElement('small');scope.textContent='Controller records establish tool results and saved bytes. AI explanations are not fact-checked.';section.append(scope);return section;
}
async function openChat(id,before=null){
 try{const chat=await api('/api/chats/'+encodeURIComponent(id)+(before?'?before='+encodeURIComponent(before):''));SmelterModels.clear();if(window.showChatWorkspace)window.showChatWorkspace();activeChat=id;window.setChatModelGrants?.(chat.messages.filter(m=>m.model_attachment).map(m=>m.model_attachment));highlightChat();const log=document.getElementById('chatlog');log.replaceChildren();document.getElementById('chatTitle').textContent=chat.title;
 if(chat.has_older){const older=document.createElement('button');older.textContent='Load older messages';older.onclick=()=>openChat(id,chat.older_cursor);log.append(older)}if(before){const latest=document.createElement('button');latest.textContent='Return to latest messages';latest.onclick=()=>openChat(id);log.append(latest)}
 for(const msg of chat.messages){const bubble=document.createElement('article');bubble.className='message '+(msg.role==='user'?'message-user':'message-assistant');const label=document.createElement('header');label.className='message-label';const speaker=msg.role==='user'?'You':msg.role==='assistant'?(msg.execution?.engine==='opencode'?'SMELTER · OpenCode response':'SMELTER · AI response'):'System';label.textContent=speaker+' · '+localTimestamp(msg.created_at);const body=document.createElement('div');body.className='message-content';const text=msg.execution?.source==='controller'?msg.execution.model_text:msg.content;if(msg.role==='assistant'){SmelterChat.render(text,body);label.append(SmelterChat.copyButton(text,'Copy response'))}else body.textContent=text;bubble.append(label,body);if(msg.model_attachment)SmelterModels.mount(msg.model_attachment,bubble);log.append(bubble);
 if(msg.role==='assistant'){if(msg.execution?.source==='controller')log.append(executionCards(msg.execution));else{const legacy=document.createElement('small');legacy.textContent='Historical transcript: structured tool execution records are unavailable for this message.';log.append(legacy)}}}
 if(!chat.messages.length){window.showEmptyConversation?.();log.scrollTop=0}else log.scrollTop=log.scrollHeight;
 }catch(e){SmelterWorkbench.notify(e.message)}
}
initShell();
const el=id=>document.getElementById(id);
SmelterAccess.mount(api);
SmelterOpenCode.mount(api);
SmelterOperations.mount(api);
async function api(path,method='GET',data){const r=await fetch(path,{method,headers:{'X-Smelter-Token':SmelterAuth.token(),'Content-Type':'application/json'},body:data?JSON.stringify(data):undefined,cache:'no-store'});const v=await r.json();if(!r.ok){const error=Error(v.error||r.status);error.status=r.status;throw error}return v}
async function refresh(force=false){try{el('error').textContent='';const data=await api('/api/extensions'+(force?'?refresh=1':''));const list=el('items');list.replaceChildren();for(const x of data.extensions){const row=document.createElement('div');row.className='ext';const info=document.createElement('div');const title=document.createElement('strong');title.textContent=x.label;const meta=document.createElement('p');meta.textContent=x.description+' · '+x.status+' · Permissions: '+x.permissions.join(', ');title.textContent=x.label+' · '+x.health;meta.textContent=x.description+' · Tool: '+x.status+' · Declared permissions: '+x.permissions.join(', ')+' · Granted: no';info.append(title,meta);const b=document.createElement('button');b.textContent=x.enabled?'Disable':'Enable';b.disabled=!x.enabled&&x.status!=='installed'&&!(x.id==='opencode'&&x.status==='detected_unverified');b.onclick=async()=>{try{await api('/api/extensions','POST',{id:x.id,enabled:!x.enabled});await refresh()}catch(e){el('error').textContent=e.message}};row.append(info,b);list.append(row)}}catch(e){el('error').textContent=e.message}}
async function loadWorkflows(){try{const data=await api('/api/workflows');for(const w of data.workflows){const opt=document.createElement('option');opt.value=w.id;opt.textContent=w.label+' — '+w.description;el('workflow').append(opt)}}catch(e){el('error').textContent=e.message}}
async function history(){try{const data=await api('/api/workflows/reports');el('historyout').textContent='Recent reports:\n'+data.reports.map(r=>r.timestamp_utc+' | '+r.workflow_id+' | '+r.status+' | '+r.run_id).join('\n')}catch(e){el('historyout').textContent=e.message}}
el('plan').onclick=async()=>{try{const paths=el('inputs').value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean);const data=await api('/api/workflows/plan','POST',{workflow_id:el('workflow').value,inputs:paths});el('planout').textContent='Status: '+data.status+' | Mode: '+data.mode+' | Executed: '+data.executed+'\n'+data.steps.map(s=>s.label+': '+s.status+(s.reason?' ('+s.reason+')':'')).join('\n')+'\nInputs: '+data.inputs.map(x=>x.path+' ('+x.status+')').join(', ')+'\nOutput validation: '+data.output_validation.status;await history()}catch(e){el('planout').textContent=e.message}};
el('history').onclick=history;history();
el('inspect').onclick=async()=>{const out=el('inspectout');if(!el('approve').checked){out.textContent='Approval required';return}try{const data=await api('/api/archive/inspect','POST',{path:el('archivepath').value,approval:'LIST ARCHIVE'});out.textContent='Status: '+data.status+' | Exit: '+data.exit_code+'\n'+data.stdout+'\n'+data.stderr;el('approve').checked=false}catch(e){out.textContent=e.message}};
el('mediainspect').onclick=async()=>{const out=el('mediaout');if(!el('mediaapprove').checked){out.textContent='Approval required';return}el('mediaapprove').checked=false;try{const data=await api('/api/media/inspect','POST',{path:el('mediapath').value,approval:'PROBE MEDIA'});out.textContent='Status: '+data.status+' | Exit: '+data.exit_code+'\n'+(data.metadata?JSON.stringify(data.metadata,null,2):data.stderr);await history()}catch(e){out.textContent=e.message}};
el('blenderinspect').onclick=async()=>{const out=el('blenderout');if(!el('blenderapprove').checked){out.textContent='Approval required';return}el('blenderapprove').checked=false;try{const data=await api('/api/blender/inspect','POST',{approval:'CHECK BLENDER'});out.textContent='Status: '+data.status+' | Exit: '+data.exit_code+'\n'+data.stdout+'\n'+data.stderr;await history()}catch(e){out.textContent=e.message}};
async function loadModels(){try{const data=await api('/api/ollama/models');el('ollamaout').textContent='Ollama: '+data.status+'\n'+(data.error||'')+'\n'+data.models.map(m=>m.name+' ('+(m.size===null?'size unknown':(m.size/1073741824).toFixed(2)+' GiB')+')').join('\n');const choices=el('modelchoice');choices.replaceChildren();for(const m of data.models){const option=document.createElement('option');option.value=m.name;option.textContent=m.name;choices.append(option)}const pref=await api('/api/ollama/preferences');el('modelout').textContent='Saved preferences: '+JSON.stringify(pref.preferences.models)+'\nAvailability: '+JSON.stringify(pref.availability)}catch(e){el('ollamaout').textContent=e.message}}
el('ollamascan').onclick=loadModels;
el('modelsave').onclick=async()=>{try{const result=await api('/api/ollama/preferences','POST',{role:el('modelrole').value,model:el('modelchoice').value});el('modelout').textContent='Saved: '+JSON.stringify(result.preferences.models)+'\nAvailability: '+JSON.stringify(result.availability);window.reloadTaskContext?.()}catch(e){el('modelout').textContent=e.message}};
el('opencodecheck').onclick=async()=>{try{const data=await api('/api/opencode/status');el('opencodeout').textContent='Status: '+data.status+'\nDetected: '+data.detected+'\nEntry type: '+data.entry_type+'\nVersion: '+(data.version||'unverified')+'\nAgent execution: disabled\n'+data.notes}catch(e){el('opencodeout').textContent=e.message}};
el('providerpreview').onclick=async()=>{try{const data=await api('/api/opencode/provider-preview');el('providerout').textContent='Preview only (not written or executed)\n'+JSON.stringify(data,null,2)}catch(e){el('providerout').textContent=e.message}};
el('providerdeploy').onclick=async()=>{const out=el('deployout');if(!el('deployapprove').checked){out.textContent='Approval required';return}el('deployapprove').checked=false;try{const data=await api('/api/opencode/deploy','POST',{approval:'DEPLOY ISOLATED CONFIG'});out.textContent=JSON.stringify(data,null,2)}catch(e){out.textContent=e.message}};
el('providervalidate').onclick=async()=>{try{const data=await api('/api/opencode/validate');el('validateout').textContent=JSON.stringify(data,null,2)}catch(e){el('validateout').textContent=e.message}};
async function startup(){
 const boot=el('bootstrap'),shell=el('shell'),footer=el('sysfooter');
 boot.hidden=false;shell.hidden=true;footer.hidden=true;el('databaseSetup').hidden=true;el('authRecovery').hidden=true;el('startupHeading').textContent='SMELTER startup';el('dbstatus').textContent='Checking session and database…';
 try{
  const db=await api('/api/startup');
  el('databaseSetup').hidden=db.ready;el('dbstatus').textContent=JSON.stringify(db,null,2);
  if(db.ready){boot.hidden=true;shell.hidden=false;footer.hidden=false;refresh();loadWorkflows();refreshChats();refreshSystem();window.reloadTaskContext?.();if(window.resumeChatJob)window.resumeChatJob()}
 }catch(e){const unauthorized=e.status===401||e.status===403;el('authRecovery').hidden=!unauthorized;el('startupHeading').textContent=unauthorized?'Session authorization required':'SMELTER startup check failed';el('dbstatus').textContent=unauthorized?'The session token is missing, expired, or rejected. Existing database files have not been reinitialized.':e.message}
}
el('sessionReconnect').onclick=()=>{try{const previous=location.hash;SmelterAuth.apply(el('sessionToken').value);el('sessionToken').value='';if(previous===location.hash)startup()}catch(error){el('dbstatus').textContent=error.message}};
window.addEventListener('hashchange',()=>startup());
el('dbselect').onclick=async()=>{
 try{el('dbstatus').textContent='Initializing database...';await api('/api/database/select','POST',{directory:el('dbdirectory').value});await startup()}
 catch(e){el('dbstatus').textContent=e.message}
};
el('dbretry').onclick=startup;
el('refresh').onclick=()=>refresh(true);startup();
