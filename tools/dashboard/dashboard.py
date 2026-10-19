#!/usr/bin/env python3
"""SMELTER V1.3 local dashboard: extension control, no tool execution."""
import argparse
import json
import secrets
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "setup"))
from check_requirements import scan
from extensions import catalog, load_state, save_state, set_enabled
from workflows import definitions, plan
from reports import attach_inputs, list_reports, save_report
from execution import inspect_archive
from media import inspect_media
from blender import inspect_blender
from ollama import list_models
from model_preferences import load_preferences, configure_model, configured_status
from opencode import inspect_opencode
from opencode_provider import provider_preview
from opencode_deploy import deploy_isolated_config
from opencode_validate import validate_staged_config
from database import inspect_database, select_database
from config_store import load_config, save_config
from startup import startup_report
from system_status import system_status
from chats import list_chats, create_chat, read_chat, add_note, rename_chat, delete_chat
from chat_inference import ask
from skills_catalog import catalog_skills
from skill_manager import add_skill, remove_skill, set_skill_enabled
from github_skill_discovery import discover_github_skill, discover_github_repository, install_discovered_skill
from aero_classifier import classify_task

STATE = ROOT / ".smelter" / "extensions.json"
STATE_LOCK = threading.Lock()
REPORTS = ROOT / ".smelter" / "reports"
MODEL_PREFS = ROOT / ".smelter" / "model_preferences.json"
HTML = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SMELTER · Dashboard</title><style>
[hidden]{display:none!important}body{margin:0;background:#0b111d;color:#e7edfa;font:15px system-ui}main{max-width:none;margin:0;padding:0;min-height:100vh;display:flex;flex-direction:column}#shell{display:grid;grid-template-columns:245px minmax(0,1fr) 315px;gap:12px;flex:1;padding:12px;min-height:0}#leftbar,#workspace,#rightbar{background:#111b2b;border:1px solid #30445e;border-radius:12px;padding:15px;min-width:0}#workspace{display:flex;flex-direction:column}#rightbar{max-height:calc(100vh - 125px);overflow:auto}#rightbar .panel{padding:12px}#leftbar button,#rightbar .navbtn{width:100%;margin:4px 0;text-align:left}#chatlog{flex:1;min-height:180px;color:#aabbd4;overflow:auto}#composer{display:flex;gap:8px}#chatinput{flex:1;min-width:0;padding:12px;background:#0b111d;color:#e7edfa;border:1px solid #30445e;border-radius:8px}#bootstrap{margin:24px auto;max-width:640px;width:calc(100% - 48px)}#bootstrap input{width:100%;box-sizing:border-box;background:#0b111d;color:#e7edfa;border:1px solid #30445e;border-radius:8px;padding:12px}#sysfooter{padding:12px 20px;border-top:1px solid #30445e;color:#aabbd4;display:flex;gap:24px;flex-wrap:wrap;font-size:12px}#rightbar .panel{display:none}#rightbar .panel.active{display:block}.navbtn.active{background:#244578}#shell h2{font-size:17px}@media(max-width:850px){#shell{grid-template-columns:1fr}#leftbar,#rightbar{max-height:none}#workspace{min-height:360px}}
h1{font-size:32px}p{color:#aabbd4}.panel{background:#151f31;border:1px solid #30445e;border-radius:14px;padding:22px;margin:16px 0}
button{background:#346de0;color:white;border:0;border-radius:7px;padding:10px 15px;cursor:pointer}button:disabled{opacity:.4}
.ext{display:flex;justify-content:space-between;align-items:center;gap:15px;border-top:1px solid #30445e;padding:17px 0}
small{color:#aabbd4}#error{color:#ff9e9e}
/* V1.6.5: independent floating scroll regions. Wheel scroll is local to hovered pane. */
html,body{height:100%;overflow:hidden}
main{height:100dvh;min-height:0;overflow:hidden}
main>h1,main>p{flex-shrink:0;margin:8px 16px}
#shell{flex:1 1 auto;min-height:0;overflow:hidden;align-items:stretch}
#leftbar,#workspace,#rightbar{height:100%;max-height:none;min-height:0;box-sizing:border-box;overflow-y:auto;overflow-x:hidden;overscroll-behavior:contain;scrollbar-width:thin;scrollbar-color:#30445e transparent}
#workspace{overflow:hidden}
#chatlog{min-height:0;overflow-y:auto;overscroll-behavior:contain;scrollbar-width:thin}
#chatHistory{min-height:0}
#sysfooter{flex:0 0 auto;box-sizing:border-box;max-height:76px;overflow:auto;overscroll-behavior:contain;flex-wrap:nowrap;white-space:nowrap;scrollbar-width:thin;background:#0b111d;position:relative;z-index:2}
#bootstrap{overflow-y:auto;min-height:0}
@media(max-width:850px){html,body{overflow:auto;height:auto}main{height:auto;min-height:100dvh;overflow:visible}#shell{display:flex;flex-direction:column;overflow:visible}#leftbar,#workspace,#rightbar{height:auto;max-height:45dvh;min-height:180px;overflow-y:auto}#workspace{min-height:360px;max-height:65dvh}#sysfooter{max-height:76px}}
.config-folder{border:1px solid #30445e;border-radius:9px;margin:9px 0;background:#111b2b}.config-folder>summary{cursor:pointer;padding:12px;font-weight:650;user-select:none;list-style-position:inside}.config-folder[open]>summary{border-bottom:1px solid #30445e}.config-folder-items{padding:7px}.config-folder-items .navbtn{font-size:13px;padding:9px 11px}.config-folder-items .panel{margin:8px 0}.config-folder-items .navbtn:disabled{opacity:.5;cursor:not-allowed}</style><main><h1>⚒ SMELTER</h1><p>V1.6.8 · Qwen vision · Local multimodal chat</p>
<section class="panel"><h2>Extensions</h2><p>Extensions are disabled by default. Activation only records configuration; execution permissions remain ungranted.</p>
<button id="refresh">Rescan tools</button><p id="error"></p><div id="items">Loading…</div></section>
<section class="panel"><h2>Workflow planner</h2><p>Preview ordered steps and dependency checks. Dry run only — no tools execute.</p>
<select id="workflow" style="padding:10px;background:#0b111d;color:#e7edfa;border:1px solid #30445e;border-radius:7px"></select>
<p><label for="inputs">Optional absolute input paths (one per line; maximum 16)</label></p>
<textarea id="inputs" rows="3" style="width:100%;box-sizing:border-box;background:#0b111d;color:#e7edfa;border:1px solid #30445e;border-radius:7px;padding:10px" placeholder="C:\\path\\to\\asset"></textarea>
<p><button id="plan">Preview and save dry run</button> <button id="history">Refresh report history</button></p>
<pre id="historyout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre><pre id="planout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
<section class="panel"><h2>Controlled execution: archive inspection</h2><p>Read-only 7-Zip listing. Select an existing archive and explicitly approve each run. No extraction or file changes.</p>
<input id="archivepath" style="width:100%;box-sizing:border-box;padding:10px;background:#0b111d;color:#e7edfa;border:1px solid #30445e" placeholder="C:\\archives\\example.zip">
<p><label><input id="approve" type="checkbox"> I approve running 7-Zip to list this archive only.</label></p>
<button id="inspect">Inspect archive (read only)</button><pre id="inspectout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
<section class="panel"><h2>Controlled execution: media inspection</h2><p>Read-only FFprobe metadata inspection. Approve each run; no transcoding or generated files.</p>
<input id="mediapath" style="width:100%;box-sizing:border-box;padding:10px;background:#0b111d;color:#e7edfa;border:1px solid #30445e" placeholder="C:\\media\\sample.mp4">
<p><label><input id="mediaapprove" type="checkbox"> I approve FFprobe reading this media file's metadata only.</label></p>
<button id="mediainspect">Inspect media (read only)</button><pre id="mediaout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
<section class="panel"><h2>Controlled execution: Blender capability</h2><p>Check the Blender executable and version only. No project loading, Python scripts, or asset modification.</p>
<p><label><input id="blenderapprove" type="checkbox"> I approve launching Blender with --version only.</label></p>
<button id="blenderinspect">Check Blender version</button><pre id="blenderout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
<section class="panel"><h2>Local AI: Ollama / Qwen</h2><p>Discover models already installed in your local Ollama service. No downloads, prompts, or model execution.</p>
<button id="ollamascan">Discover local models</button>
<p><label>Role <select id="modelrole"><option value="reasoning">Reasoning</option><option value="lightweight">Lightweight</option></select></label>
<label> Installed model <select id="modelchoice"></select></label></p>
<button id="modelsave">Save model preference</button><pre id="modelout"></pre><pre id="ollamaout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
<section class="panel"><h2>OpenCode agent readiness</h2><p>Detect the installed CLI and report version verification. No agent sessions, commands, or project access.</p>
<button id="opencodecheck">Check OpenCode</button> <button id="providerpreview">Preview Ollama provider config</button>
<p><label><input id="deployapprove" type="checkbox"> I approve creating an isolated OpenCode configuration in .smelter only.</label></p>
<button id="providerdeploy">Deploy isolated config (create only)</button> <button id="providervalidate">Validate staged config</button>
<pre id="validateout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre>
<pre id="deployout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre><pre id="providerout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre><pre id="opencodeout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
<section id="bootstrap" class="panel" hidden><h2>SMELTER startup</h2><p>Choose an absolute directory for persistent SQLite storage. Existing JSON configuration files remain untouched.</p><input id="dbdirectory" placeholder="D:\\SMELTER-Data"><button id="dbselect">Initialize database</button><button id="dbretry">Retry checks</button><pre id="dbstatus" style="white-space:pre-wrap"></pre></section>
<script>
let activeChat=null;
let selectedSkills=[];
let autoSkills=false;
function initShell(){
 const main=document.querySelector('main'), sections=[...main.querySelectorAll(':scope > section.panel:not(#bootstrap)')];
 const shell=document.createElement('div');shell.id='shell';
 const left=document.createElement('aside');left.id='leftbar';
 const center=document.createElement('section');center.id='workspace';
 const right=document.createElement('aside');right.id='rightbar';
 left.innerHTML='<h2>Chat history</h2>';
 const newChat=document.createElement('button');newChat.textContent='+ New chat';newChat.onclick=async()=>{try{const chat=await api('/api/chats','POST',{action:'create'});activeChat=chat.id;await refreshChats();await openChat(chat.id)}catch(e){alert(e.message)}};
 const history=document.createElement('div');history.id='chatHistory';left.append(newChat,history);
 const title=document.createElement('h2');title.textContent='SMELTER · Conversation notes';
 const log=document.createElement('div');log.id='chatlog';log.textContent='Select New chat. Notes are stored in SQLite; AI responses are not enabled yet.';
 const composer=document.createElement('div');composer.id='composer';
 const input=document.createElement('input');input.id='chatinput';input.placeholder='Message local Qwen 3.5 9B';
 const send=document.createElement('button');send.textContent='Send to Qwen';
 send.onclick=async()=>{if(!activeChat){alert('Create or select a conversation first');return}try{let attachment=null;const file=imageInput.files[0];
 if(file){if(file.size>2097152)throw Error('Image exceeds 2 MiB');const b64=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(Error('Could not read image'));reader.readAsDataURL(file)});attachment={mime:file.type,base64:b64}}
 await api('/api/chats','POST',{action:'ask',id:activeChat,content:input.value,image:attachment,skills:selectedSkills,auto_skills:autoSkills});input.value='';imageInput.value='';await openChat(activeChat)}catch(e){alert(e.message)}};
 const imageInput=document.createElement('input');imageInput.type='file';imageInput.accept='image/png,image/jpeg,image/webp';imageInput.title='Attach PNG, JPEG, or WebP (up to 2 MiB)';imageInput.style.maxWidth='180px';
 composer.append(input,imageInput,send);center.append(title,log,composer);
 right.innerHTML='<h2>Configuration</h2>';
 const folders=[
  {name:'AI & Models',items:[[5,'Ollama / Qwen'],[6,'OpenCode']]},
  {name:'Tools & Integrations',items:[[0,'Installed tools'],[2,'Archive / 7-Zip'],[3,'Media / FFprobe'],[4,'Blender']],planned:['GitHub connector','Tool path overrides']},
  {name:'Automation & Workflows',items:[[1,'Workflow planner']]},
  {name:'System & Storage',items:[],planned:['Database management','Startup services','Live hardware statistics']}
 ];
 const nav=[];
 for(const folder of folders){
  const group=document.createElement('details');group.className='config-folder';
  const heading=document.createElement('summary');heading.textContent='📁 '+folder.name;group.append(heading);
  const contents=document.createElement('div');contents.className='config-folder-items';
  for(const [i,label] of folder.items){
   const b=document.createElement('button');b.className='navbtn';b.textContent=label;
   b.onclick=()=>{right.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));nav.forEach(x=>x.classList.remove('active'));sectionFocus(section=i,button=b)};
   const section=sections[i];
   contents.append(b,section);nav.push(b);
  }
  for(const label of folder.planned||[]){const b=document.createElement('button');b.className='navbtn';b.textContent=label+' · planned';b.disabled=true;contents.append(b)}
  group.append(contents);right.append(group);
 }
 function sectionFocus(section,button){section.classList.add('active');button.classList.add('active')}
 folders[0] && (right.querySelector('details').open=true);
 if(nav.length)nav[0].click();
 shell.append(left,center,right);
 const footer=document.createElement('footer');footer.id='sysfooter';footer.textContent='CPU: pending · RAM: pending · GPU: pending · Disk: pending · AI: not started';
 main.append(shell,footer);
 const aeroPanel=document.createElement('div');aeroPanel.className='panel';aeroPanel.id='aeroPanel';
 const aeroInput=document.createElement('textarea');aeroInput.rows=3;aeroInput.placeholder='Describe an engineering task for read-only classification';aeroInput.style.width='100%';aeroInput.style.boxSizing='border-box';
 const aeroButton=document.createElement('button');aeroButton.textContent='Preview AERO classification';
 const aeroResult=document.createElement('pre');aeroResult.style.whiteSpace='pre-wrap';aeroResult.style.overflowWrap='anywhere';
 aeroButton.onclick=async()=>{try{const result=await api('/api/aero/classify','POST',{task:aeroInput.value});aeroResult.textContent=JSON.stringify(result,null,2)}catch(e){aeroResult.textContent=e.message}};
 aeroPanel.append(aeroInput,aeroButton,aeroResult);
 const automationFolder=[...right.querySelectorAll('details')].find(x=>x.querySelector('summary')?.textContent.includes('Automation & Workflows'));
 if(automationFolder){const btn=document.createElement('button');btn.className='navbtn';btn.textContent='AERO task preview';btn.onclick=()=>{automationFolder.open=true;right.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));right.querySelectorAll('.navbtn').forEach(x=>x.classList.remove('active'));aeroPanel.classList.add('active');btn.classList.add('active')};automationFolder.querySelector('.config-folder-items').append(btn,aeroPanel)}
 const skillsPanel=document.createElement('div');skillsPanel.className='panel';skillsPanel.id='skillsPanel';skillsPanel.textContent='Open Skills Manager to inspect installed skills.';
 const toolsFolder=[...right.querySelectorAll('details')].find(x=>x.querySelector('summary')?.textContent.includes('Tools & Integrations'));
 if(toolsFolder){
  const btn=document.createElement('button');btn.className='navbtn';btn.textContent='Skills Manager';
  btn.onclick=async()=>{
   toolsFolder.open=true;
   right.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));
   right.querySelectorAll('.navbtn').forEach(x=>x.classList.remove('active'));
   skillsPanel.classList.add('active');btn.classList.add('active');
   try{
    const data=await api('/api/skills');
    skillsPanel.replaceChildren();
    const heading=document.createElement('h2');heading.textContent='Skills Manager';
    const summary=document.createElement('p');
    const updateSummary=()=>{
     const mode=selectedSkills.length?'Manual override ('+selectedSkills.join(', ')+')':(autoSkills?'Automatic routing':'No skills selected');
     summary.textContent='Next Qwen message: '+mode+'. Installed: '+data.count+'. Context only; no execution permission.';
    };
    skillsPanel.append(heading,summary);
    const autoLabel=document.createElement('label');autoLabel.style.display='block';autoLabel.style.margin='12px 0';
    const autoBox=document.createElement('input');autoBox.type='checkbox';autoBox.checked=autoSkills;
    autoBox.onchange=()=>{autoSkills=autoBox.checked;updateSummary()};
    autoLabel.append(autoBox,document.createTextNode(' Enable automatic skill routing when no manual skills are selected'));
    skillsPanel.append(autoLabel);
    const clear=document.createElement('button');clear.textContent='Clear manual selections';
    clear.onclick=()=>{selectedSkills=[];skillsPanel.querySelectorAll('input[data-skill-id]').forEach(x=>x.checked=false);updateSummary()};
    skillsPanel.append(clear);
    for(const s of data.skills){
     const item=document.createElement('div');item.style.margin='12px 0';item.style.padding='10px';item.style.border='1px solid #7775';item.style.borderRadius='8px';
     const label=document.createElement('label');label.style.display='block';
     const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.dataset.skillId=s.id;
     checkbox.disabled=s.status!=='ready'||!s.enabled;checkbox.checked=s.enabled&&selectedSkills.includes(s.id);
     checkbox.onchange=()=>{
      if(checkbox.checked){if(selectedSkills.length>=3){checkbox.checked=false;alert('Maximum three manually selected skills');return}selectedSkills.push(s.id)}
      else selectedSkills=selectedSkills.filter(x=>x!==s.id);
      updateSummary();
     };
     label.append(checkbox,document.createTextNode(' '+(s.name||s.id)));
     const status=document.createElement('p');status.textContent='Status: '+s.status+' · '+(s.enabled?'Enabled':'Disabled')+' · '+s.source+' · '+(s.bytes||0)+' bytes · No execution rights';
     const toggle=document.createElement('button');toggle.textContent=s.enabled?'Disable':'Enable';toggle.disabled=!s.enabled&&s.status!=='ready';
     toggle.onclick=async()=>{if(!confirm((s.enabled?'Disable ':'Enable ')+s.id+'?'))return;try{await api('/api/skills/manage','POST',{action:'enable',id:s.id,enabled:!s.enabled,approval:true});if(s.enabled)selectedSkills=selectedSkills.filter(x=>x!==s.id);await btn.onclick()}catch(e){alert(e.message)}};
     const remove=document.createElement('button');remove.textContent='Remove';remove.disabled=!s.removable;remove.title=s.removable?'Delete user-added skill':'Bundled skills cannot be deleted';
     remove.onclick=async()=>{if(!confirm('Permanently remove skill '+s.id+'?'))return;try{await api('/api/skills/manage','POST',{action:'remove',id:s.id,approval:true});selectedSkills=selectedSkills.filter(x=>x!==s.id);await btn.onclick()}catch(e){alert(e.message)}};
     const description=document.createElement('p');description.textContent=s.description||'No purpose available.';
     item.append(label,status,description,toggle,remove);skillsPanel.append(item);
    }
    const addHeading=document.createElement('h3');addHeading.textContent='Discover skill from GitHub';
    const urlInput=document.createElement('input');urlInput.placeholder='https://github.com/owner/repo/blob/main/SKILL.md';urlInput.style.width='100%';
    const repoButton=document.createElement('button');repoButton.textContent='Discover repository skills';
    const candidates=document.createElement('div');candidates.style.maxHeight='250px';candidates.style.overflowY='auto';
    const discoveredSelect=document.createElement('select');discoveredSelect.style.width='100%';discoveredSelect.hidden=true;
    const inspectSelected=document.createElement('button');inspectSelected.textContent='Inspect selected skill';inspectSelected.hidden=true;
    let repositoryResults=[];
    repoButton.onclick=async()=>{candidates.replaceChildren();discoveredSelect.hidden=true;inspectSelected.hidden=true;repositoryResults=[];try{
      const result=await api('/api/skills/discover-repository','POST',{url:urlInput.value});
      repositoryResults=result.skills;
      const info=document.createElement('p');info.textContent=result.count+' skill(s) found in '+result.owner+'/'+result.repository+' @ '+result.ref;
      candidates.append(info);discoveredSelect.replaceChildren();
      for(const skill of result.skills){const option=document.createElement('option');option.value=skill.url;option.textContent=skill.path;discoveredSelect.append(option)}
      discoveredSelect.hidden=!result.skills.length;inspectSelected.hidden=!result.skills.length;
    }catch(e){const error=document.createElement('p');error.textContent=e.message;candidates.append(error)}};
    const discoverButton=document.createElement('button');discoverButton.textContent='Discover & inspect URL';
    inspectSelected.onclick=()=>{if(!discoveredSelect.value)return;urlInput.value=discoveredSelect.value;urlInput.dispatchEvent(new Event('input'));discoverButton.click()};
    const preview=document.createElement('pre');preview.style.whiteSpace='pre-wrap';preview.style.overflowWrap='anywhere';preview.style.maxHeight='260px';preview.style.overflow='auto';
    const idInput=document.createElement('input');idInput.placeholder='Local skill ID';idInput.style.width='100%';idInput.hidden=true;
    const installButton=document.createElement('button');installButton.textContent='Approve & install';installButton.hidden=true;
    let discovery=null;
    urlInput.oninput=()=>{discovery=null;preview.textContent='';installButton.hidden=true;idInput.hidden=true};
    discoverButton.onclick=async()=>{discovery=null;installButton.hidden=true;idInput.hidden=true;preview.textContent='Discovering...';try{
      const result=await api('/api/skills/discover','POST',{url:urlInput.value});
      discovery=result;
      preview.textContent='Source: '+result.owner+'/'+result.repository+' @ '+result.ref+'\\nPath: '+result.path+'\\nSHA256: '+result.sha256+'\\nWarnings: '+(result.warnings.join(', ')||'none detected (not a security guarantee)')+'\\n\\n--- SKILL.md ---\\n'+result.content;
      idInput.value=result.path.split('/').slice(-2,-1)[0]||result.repository.toLowerCase().replace(/[^a-z0-9_-]/g,'-');
      idInput.hidden=false;installButton.hidden=false;
    }catch(e){preview.textContent=e.message}};
    installButton.onclick=async()=>{if(!discovery)return;if(!confirm('Install reviewed GitHub skill '+idInput.value+'? Instructions only; no execution permissions.'))return;try{
      await api('/api/skills/manage','POST',{action:'install_github',id:idInput.value,url:discovery.url,sha256:discovery.sha256,approval:true});await btn.onclick()
    }catch(e){alert(e.message)}};
    skillsPanel.append(addHeading,urlInput,repoButton,candidates,discoveredSelect,inspectSelected,discoverButton,preview,idInput,installButton);
    updateSummary();
   }catch(e){skillsPanel.textContent='Skills Manager error: '+e.message}
  };
  toolsFolder.querySelector('.config-folder-items').prepend(btn,skillsPanel);
 }
 const statusPanel=document.createElement('div');statusPanel.className='panel';statusPanel.id='systemStatusPanel';statusPanel.textContent='Loading system status…';
 const systemFolder=[...right.querySelectorAll('details')].find(x=>x.querySelector('summary')?.textContent.includes('System & Storage'));
 if(systemFolder){const btn=document.createElement('button');btn.className='navbtn';btn.textContent='System status';btn.onclick=async()=>{systemFolder.open=true;right.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));right.querySelectorAll('.navbtn').forEach(x=>x.classList.remove('active'));statusPanel.classList.add('active');btn.classList.add('active');await refreshSystem()};systemFolder.querySelector('.config-folder-items').prepend(btn,statusPanel)}
}
async function refreshSystem(){
 try{const s=await api('/api/system/status');const gb=n=>(n/1073741824).toFixed(1)+' GiB';
  document.getElementById('sysfooter').textContent='CPU: pending · RAM: pending · GPU: pending · Disk free: '+gb(s.storage.free_bytes)+' / '+gb(s.storage.total_bytes)+' · DB: '+s.database.status;
  document.getElementById('systemStatusPanel').textContent='Database: '+s.database.status+'\\nLocation: '+(s.database.path||'not selected')+'\\nDisk: '+gb(s.storage.free_bytes)+' free / '+gb(s.storage.total_bytes)+' total\\nDashboard: running\\nOllama: inspect via AI & Models\\nOpenCode: not started\\nCPU/RAM/GPU: instrumentation pending';
 }catch(e){document.getElementById('sysfooter').textContent='System status unavailable: '+e.message}
}
async function refreshChats(){
 const data=await api('/api/chats');const history=document.getElementById('chatHistory');history.replaceChildren();
 for(const chat of data.conversations){
  const row=document.createElement('div');row.className='ext';
  const open=document.createElement('button');open.textContent=chat.title;open.onclick=()=>openChat(chat.id);
  const rename=document.createElement('button');rename.textContent='✎';rename.title='Rename';rename.onclick=async()=>{const title=prompt('Rename conversation',chat.title);if(title===null)return;try{await api('/api/chats','POST',{action:'rename',id:chat.id,title});await refreshChats()}catch(e){alert(e.message)}};
  const del=document.createElement('button');del.textContent='×';del.title='Delete';del.onclick=async()=>{if(!confirm('Delete this conversation and its notes?'))return;try{await api('/api/chats','POST',{action:'delete',id:chat.id});if(activeChat===chat.id){activeChat=null;document.getElementById('chatlog').textContent='Conversation deleted'}await refreshChats()}catch(e){alert(e.message)}};
  row.append(open,rename,del);history.append(row);
 }
}
async function openChat(id){
 try{const chat=await api('/api/chats/'+encodeURIComponent(id));activeChat=id;const log=document.getElementById('chatlog');log.replaceChildren();for(const msg of chat.messages){const p=document.createElement('p');p.textContent=msg.content;log.append(p)}if(!chat.messages.length)log.textContent='No notes yet.'}catch(e){alert(e.message)}
}
initShell();
const token=new URLSearchParams(location.hash.slice(1)).get('token');
const el=id=>document.getElementById(id);
async function api(path,method='GET',data){const r=await fetch(path,{method,headers:{'X-Smelter-Token':token||'','Content-Type':'application/json'},body:data?JSON.stringify(data):undefined,cache:'no-store'});const v=await r.json();if(!r.ok)throw Error(v.error||r.status);return v}
async function refresh(){try{el('error').textContent='';const data=await api('/api/extensions');const list=el('items');list.replaceChildren();for(const x of data.extensions){const row=document.createElement('div');row.className='ext';const info=document.createElement('div');const title=document.createElement('strong');title.textContent=x.label;const meta=document.createElement('p');meta.textContent=x.description+' · '+x.status+' · Permissions: '+x.permissions.join(', ');title.textContent=x.label+' · '+x.health;meta.textContent=x.description+' · Tool: '+x.status+' · Declared permissions: '+x.permissions.join(', ')+' · Granted: no';info.append(title,meta);const b=document.createElement('button');b.textContent=x.enabled?'Disable':'Enable';b.disabled=!x.enabled&&x.status!=='installed'&&!(x.id==='opencode'&&x.status==='detected_unverified');b.onclick=async()=>{try{await api('/api/extensions','POST',{id:x.id,enabled:!x.enabled});await refresh()}catch(e){el('error').textContent=e.message}};row.append(info,b);list.append(row)}}catch(e){el('error').textContent=e.message}}
async function loadWorkflows(){try{const data=await api('/api/workflows');for(const w of data.workflows){const opt=document.createElement('option');opt.value=w.id;opt.textContent=w.label+' — '+w.description;el('workflow').append(opt)}}catch(e){el('error').textContent=e.message}}
async function history(){try{const data=await api('/api/workflows/reports');el('historyout').textContent='Recent reports:\\n'+data.reports.map(r=>r.timestamp_utc+' | '+r.workflow_id+' | '+r.status+' | '+r.run_id).join('\\n')}catch(e){el('historyout').textContent=e.message}}
el('plan').onclick=async()=>{try{const paths=el('inputs').value.split(/\\r?\\n/).map(x=>x.trim()).filter(Boolean);const data=await api('/api/workflows/plan','POST',{workflow_id:el('workflow').value,inputs:paths});el('planout').textContent='Status: '+data.status+' | Mode: '+data.mode+' | Executed: '+data.executed+'\\n'+data.steps.map(s=>s.label+': '+s.status+(s.reason?' ('+s.reason+')':'')).join('\\n')+'\\nInputs: '+data.inputs.map(x=>x.path+' ('+x.status+')').join(', ')+'\\nOutput validation: '+data.output_validation.status;await history()}catch(e){el('planout').textContent=e.message}};
el('history').onclick=history;history();
el('inspect').onclick=async()=>{const out=el('inspectout');if(!el('approve').checked){out.textContent='Approval required';return}try{const data=await api('/api/archive/inspect','POST',{path:el('archivepath').value,approval:'LIST ARCHIVE'});out.textContent='Status: '+data.status+' | Exit: '+data.exit_code+'\\n'+data.stdout+'\\n'+data.stderr;el('approve').checked=false}catch(e){out.textContent=e.message}};
el('mediainspect').onclick=async()=>{const out=el('mediaout');if(!el('mediaapprove').checked){out.textContent='Approval required';return}el('mediaapprove').checked=false;try{const data=await api('/api/media/inspect','POST',{path:el('mediapath').value,approval:'PROBE MEDIA'});out.textContent='Status: '+data.status+' | Exit: '+data.exit_code+'\\n'+(data.metadata?JSON.stringify(data.metadata,null,2):data.stderr);await history()}catch(e){out.textContent=e.message}};
el('blenderinspect').onclick=async()=>{const out=el('blenderout');if(!el('blenderapprove').checked){out.textContent='Approval required';return}el('blenderapprove').checked=false;try{const data=await api('/api/blender/inspect','POST',{approval:'CHECK BLENDER'});out.textContent='Status: '+data.status+' | Exit: '+data.exit_code+'\\n'+data.stdout+'\\n'+data.stderr;await history()}catch(e){out.textContent=e.message}};
async function loadModels(){try{const data=await api('/api/ollama/models');el('ollamaout').textContent='Ollama: '+data.status+'\\n'+(data.error||'')+'\\n'+data.models.map(m=>m.name+' ('+(m.size===null?'size unknown':(m.size/1073741824).toFixed(2)+' GiB')+')').join('\\n');const choices=el('modelchoice');choices.replaceChildren();for(const m of data.models){const option=document.createElement('option');option.value=m.name;option.textContent=m.name;choices.append(option)}const pref=await api('/api/ollama/preferences');el('modelout').textContent='Saved preferences: '+JSON.stringify(pref.preferences.models)+'\\nAvailability: '+JSON.stringify(pref.availability)}catch(e){el('ollamaout').textContent=e.message}}
el('ollamascan').onclick=loadModels;
el('modelsave').onclick=async()=>{try{const result=await api('/api/ollama/preferences','POST',{role:el('modelrole').value,model:el('modelchoice').value});el('modelout').textContent='Saved: '+JSON.stringify(result.preferences.models)+'\\nAvailability: '+JSON.stringify(result.availability)}catch(e){el('modelout').textContent=e.message}};
el('opencodecheck').onclick=async()=>{try{const data=await api('/api/opencode/status');el('opencodeout').textContent='Status: '+data.status+'\\nDetected: '+data.detected+'\\nEntry type: '+data.entry_type+'\\nVersion: '+(data.version||'unverified')+'\\nAgent execution: disabled\\n'+data.notes}catch(e){el('opencodeout').textContent=e.message}};
el('providerpreview').onclick=async()=>{try{const data=await api('/api/opencode/provider-preview');el('providerout').textContent='Preview only (not written or executed)\\n'+JSON.stringify(data,null,2)}catch(e){el('providerout').textContent=e.message}};
el('providerdeploy').onclick=async()=>{const out=el('deployout');if(!el('deployapprove').checked){out.textContent='Approval required';return}el('deployapprove').checked=false;try{const data=await api('/api/opencode/deploy','POST',{approval:'DEPLOY ISOLATED CONFIG'});out.textContent=JSON.stringify(data,null,2)}catch(e){out.textContent=e.message}};
el('providervalidate').onclick=async()=>{try{const data=await api('/api/opencode/validate');el('validateout').textContent=JSON.stringify(data,null,2)}catch(e){el('validateout').textContent=e.message}};
async function startup(){
 const boot=el('bootstrap'),shell=el('shell'),footer=el('sysfooter');
 boot.hidden=false;shell.hidden=true;footer.hidden=true;
 try{
  const db=await api('/api/startup');
  el('dbstatus').textContent=JSON.stringify(db,null,2);
  if(db.ready){boot.hidden=true;shell.hidden=false;footer.hidden=false;refresh();loadWorkflows();refreshChats();refreshSystem()}
 }catch(e){el('dbstatus').textContent=e.message}
}
el('dbselect').onclick=async()=>{
 try{el('dbstatus').textContent='Initializing database...';await api('/api/database/select','POST',{directory:el('dbdirectory').value});await startup()}
 catch(e){el('dbstatus').textContent=e.message}
};
el('dbretry').onclick=startup;
el('refresh').onclick=refresh;startup();
</script></main></html>"""

def handler(token: str):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, data, content_type="application/json"):
            body = data.encode() if isinstance(data, str) else json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        def authorized(self):
            origin = self.headers.get("Origin")
            expected = "http://127.0.0.1:" + str(self.server.server_port)
            return secrets.compare_digest(self.headers.get("X-Smelter-Token", ""), token) and (not origin or origin == expected)
        def do_GET(self):
            route = urlsplit(self.path).path
            if route == "/":
                return self.reply(200, HTML, "text/html")
            if not self.authorized():
                return self.reply(403, {"error": "Unauthorized"})
            if route == "/api/skills":
                try:
                    return self.reply(200, catalog_skills(ROOT))
                except (OSError, ValueError) as e:
                    return self.reply(400, {"error": str(e)})
            if route == "/api/system/status":
                try:
                    return self.reply(200, system_status(ROOT))
                except (ValueError, OSError) as e:
                    return self.reply(400, {"error": str(e)})
            if route == "/api/chats":
                try:
                    return self.reply(200, list_chats(ROOT))
                except (ValueError, OSError) as e:
                    return self.reply(400, {"error": str(e)})
            if route.startswith("/api/chats/"):
                try:
                    return self.reply(200, read_chat(ROOT, route.removeprefix("/api/chats/")))
                except (ValueError, OSError) as e:
                    return self.reply(400, {"error": str(e)})
            if route == "/api/startup":
                try:
                    return self.reply(200, startup_report(ROOT, scan, list_models))
                except (ValueError, OSError, json.JSONDecodeError) as e:
                    return self.reply(400, {"error": str(e)})
            if route == "/api/opencode/validate":
                try:
                    with STATE_LOCK:
                        current_state = load_config(ROOT, 'extensions.json')
                        preferences = load_config(ROOT, 'model_preferences.json')
                    status = {item["name"]: item for item in scan()["tools"]}
                    inspect_opencode(current_state, status)
                    discovery = list_models(current_state, {name: item["status"] for name, item in status.items()})
                    return self.reply(200, validate_staged_config(ROOT / ".smelter" / "opencode-isolated", preferences, discovery))
                except (ValueError, OSError, json.JSONDecodeError, AttributeError) as e:
                    return self.reply(400, {"error": str(e)})
            if route == "/api/opencode/provider-preview":
                try:
                    with STATE_LOCK:
                        current_state = load_state(STATE)
                        preferences = load_preferences(MODEL_PREFS)
                    status = {item["name"]: item for item in scan()["tools"]}
                    discovery = list_models(current_state, {name: item["status"] for name, item in status.items()})
                    agent = inspect_opencode(current_state, status)
                    return self.reply(200, provider_preview(preferences, discovery, agent))
                except (ValueError, OSError, json.JSONDecodeError) as e:
                    return self.reply(400, {"error": str(e)})
            if route == "/api/opencode/status":
                try:
                    with STATE_LOCK:
                        current_state = load_state(STATE)
                    status = {item["name"]: item for item in scan()["tools"]}
                    return self.reply(200, inspect_opencode(current_state, status))
                except (ValueError, OSError, json.JSONDecodeError) as e:
                    return self.reply(400, {"error": str(e)})
            if route == "/api/ollama/preferences":
                try:
                    with STATE_LOCK:
                        preferences = load_preferences(MODEL_PREFS)
                        current_state = load_state(STATE)
                    status = {item["name"]: item["status"] for item in scan()["tools"]}
                    return self.reply(200, configured_status(preferences, list_models(current_state, status)))
                except (ValueError, OSError, json.JSONDecodeError) as e:
                    return self.reply(400, {"error": str(e)})
            if route == "/api/ollama/models":
                try:
                    with STATE_LOCK:
                        current_state = load_state(STATE)
                    status = {item["name"]: item["status"] for item in scan()["tools"]}
                    return self.reply(200, list_models(current_state, status))
                except (ValueError, OSError, json.JSONDecodeError) as e:
                    return self.reply(400, {"error": str(e)})
            if route == "/api/workflows/reports":
                return self.reply(200, {"reports": list_reports(REPORTS)})
            if route == "/api/workflows":
                return self.reply(200, {"workflows": definitions()})
            if route == "/api/extensions":
                try:
                    return self.reply(200, {"extensions": catalog(scan(), load_state(STATE))})
                except (ValueError, OSError, json.JSONDecodeError) as e:
                    return self.reply(500, {"error": str(e)})
            return self.reply(404, {"error": "Not found"})
        def do_POST(self):
            if not self.authorized():
                return self.reply(403, {"error": "Unauthorized"})
            route = urlsplit(self.path).path
            if route not in ("/api/extensions", "/api/workflows/plan", "/api/archive/inspect", "/api/media/inspect", "/api/blender/inspect", "/api/ollama/preferences", "/api/opencode/deploy", "/api/database/select", "/api/chats", "/api/aero/classify", "/api/skills/manage", "/api/skills/discover", "/api/skills/discover-repository"):
                return self.reply(404, {"error": "Not found"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= (3 * 1024 * 1024 if route == "/api/chats" else 2048):
                    raise ValueError("Invalid request size")
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("Invalid request")
                if route == "/api/skills/discover-repository":
                    return self.reply(200, discover_github_repository(data.get("url")))
                if route == "/api/skills/discover":
                    return self.reply(200, discover_github_skill(data.get("url")))
                if route == "/api/skills/manage":
                    with STATE_LOCK:
                        action = data.get("action")
                        if action == "add":
                            raise ValueError("Use GitHub discovery before installation")
                        elif action == "install_github":
                            result = install_discovered_skill(ROOT, data.get("id"), data.get("url"), data.get("sha256"), data.get("approval"))
                        elif action == "enable":
                            result = set_skill_enabled(ROOT, data.get("id"), data.get("enabled"), data.get("approval"))
                        elif action == "remove":
                            result = remove_skill(ROOT, data.get("id"), data.get("approval"))
                        else:
                            raise ValueError("Unknown skill action")
                    return self.reply(200, result)
                if route == "/api/aero/classify":
                    return self.reply(200, classify_task(data.get("task")))
                if route == "/api/chats":
                    with STATE_LOCK:
                        action = data.get("action")
                        if action == "ask":
                            result = ask(ROOT, data.get("id"), data.get("content"), image=data.get("image"), skills=data.get("skills"), auto_skills=data.get("auto_skills", False))
                        elif action == "create":
                            result = create_chat(ROOT, data.get("title", "New chat"))
                        elif action == "note":
                            result = add_note(ROOT, data.get("id"), data.get("content"))
                        elif action == "rename":
                            result = rename_chat(ROOT, data.get("id"), data.get("title"))
                        elif action == "delete":
                            result = delete_chat(ROOT, data.get("id"))
                        else:
                            raise ValueError("Unknown chat action")
                    return self.reply(200, result)
                if route == "/api/database/select":
                    with STATE_LOCK:
                        return self.reply(200, select_database(ROOT, data.get("directory")))
                if route == "/api/opencode/deploy":
                    with STATE_LOCK:
                        current_state = load_state(STATE)
                        preferences = load_preferences(MODEL_PREFS)
                    status = {item["name"]: item for item in scan()["tools"]}
                    discovery = list_models(current_state, {name: item["status"] for name, item in status.items()})
                    agent = inspect_opencode(current_state, status)
                    preview = provider_preview(preferences, discovery, agent)
                    with STATE_LOCK:
                        result = deploy_isolated_config(ROOT / ".smelter" / "opencode-isolated", preview, data.get("approval"))
                    return self.reply(200, result)
                if route == "/api/ollama/preferences":
                    with STATE_LOCK:
                        current_state = load_state(STATE)
                    status = {item["name"]: item["status"] for item in scan()["tools"]}
                    discovery = list_models(current_state, status)
                    with STATE_LOCK:
                        role, model = data.get("role"), data.get("model")
                        if role not in ("reasoning", "lightweight") or not isinstance(model, str) or model not in {item["name"] for item in discovery.get("models", [])} or discovery.get("status") != "connected":
                            raise ValueError("Model must be installed in connected Ollama and role must be valid")
                        preferences = load_config(ROOT, "model_preferences.json")
                        preferences["models"][role] = model
                        save_config(ROOT, "model_preferences.json", preferences)
                    return self.reply(200, configured_status(preferences, discovery))
                if route == "/api/blender/inspect":
                    with STATE_LOCK:
                        current_state = load_state(STATE)
                    status = {item["name"]: item["status"] for item in scan()["tools"]}
                    report = inspect_blender(data.get("approval"), current_state, status)
                    with STATE_LOCK:
                        save_report(REPORTS, report)
                    return self.reply(200, report)
                if route == "/api/media/inspect":
                    with STATE_LOCK:
                        current_state = load_state(STATE)
                    status = {item["name"]: item["status"] for item in scan()["tools"]}
                    report = inspect_media(data.get("path"), data.get("approval"), current_state, status)
                    with STATE_LOCK:
                        save_report(REPORTS, report)
                    return self.reply(200, report)
                if route == "/api/archive/inspect":
                    with STATE_LOCK:
                        current_state = load_state(STATE)
                    status = {item["name"]: item["status"] for item in scan()["tools"]}
                    report = inspect_archive(data.get("path"), data.get("approval"), current_state, status)
                    with STATE_LOCK:
                        save_report(REPORTS, report)
                    return self.reply(200, report)
                if route == "/api/workflows/plan":
                    report = attach_inputs(plan(data.get("workflow_id"), scan(), load_state(STATE)), data.get("inputs"))
                    with STATE_LOCK:
                        save_report(REPORTS, report)
                    return self.reply(200, report)
                with STATE_LOCK:
                    state = set_enabled(load_state(STATE), data.get("id"), data.get("enabled"), scan())
                    save_config(ROOT, 'extensions.json', state)
                return self.reply(200, {"enabled": state["enabled"]})
            except (ValueError, OSError, json.JSONDecodeError) as e:
                return self.reply(400, {"error": str(e)})
    return Handler

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8768)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    token = secrets.token_urlsafe(32)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler(token))
    url = f"http://127.0.0.1:{server.server_port}/#token={token}"
    print("SMELTER dashboard:", url)
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
