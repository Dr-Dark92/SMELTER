#!/usr/bin/env python3
"""SMELTER local dashboard with explicit per-message tool permissions."""
import argparse
import json
import secrets
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote

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
from skill_collections import install_collection
from aero_classifier import classify_task
from rea_connection import package_status as rea_package_status
from chat_jobs import JOBS
from skill_runtime import initialize as initialize_skills, monitor as skill_monitor, tools_status
from runtime_settings import load_runtime, save_runtime
from mcp_connections import status as mcp_status, save_config as save_mcp_config, exchange as mcp_exchange
from python_tools import permissions as validate_tool_permissions
from model_assets import rename_animation, attach_model, model_path, viewer_bundle, viewer_status

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
.config-folder{border:1px solid #30445e;border-radius:9px;margin:9px 0;background:#111b2b}.config-folder>summary{cursor:pointer;padding:12px;font-weight:650;user-select:none;list-style-position:inside}.config-folder[open]>summary{border-bottom:1px solid #30445e}.config-folder-items{padding:7px}.config-folder-items .navbtn{font-size:13px;padding:9px 11px}.config-folder-items .panel{margin:8px 0}.config-folder-items .navbtn:disabled{opacity:.5;cursor:not-allowed}
#chatlog{display:flex;flex-direction:column;gap:16px;padding:12px 6px;margin-bottom:12px;white-space:normal}
.message{box-sizing:border-box;max-width:90%;padding:14px 18px;border:1px solid #30445e;border-radius:16px;background:#18263b;flex-shrink:0;min-width:0;color:#e7edfa}
.message-user{align-self:flex-end;background:#173c65;border-color:#4075a5;border-bottom-right-radius:4px}
.message-assistant{align-self:flex-start;border-bottom-left-radius:4px}
.message-label{font-size:12px;font-weight:700;color:#adcaec;margin-bottom:9px}
.message-content{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.65}
#chatinput{resize:vertical;min-height:64px;max-height:180px;font:inherit;box-sizing:border-box}#requestStatus{flex-shrink:0;font-size:12px;margin:6px 0;min-height:18px}#composer{flex-shrink:0;align-items:flex-end;flex-wrap:wrap}#pythonTools{flex-shrink:0;max-height:35%;overflow:auto}
@media(max-width:850px){.message{max-width:97%}}

.execution-cards{align-self:stretch;border:1px solid #3d596b;background:#0d2029;border-radius:12px;padding:14px;flex-shrink:0;min-width:0}
.execution-cards h3{font-size:13px;color:#92d5c5;margin:0 0 10px}.execution-cards p{font-size:12px;margin:7px 0;overflow-wrap:anywhere}
.execution-card{border-left:3px solid #69c6a3;background:#132c34;margin:10px 0;padding:12px;border-radius:6px;font-size:13px}
.execution-error{border-left-color:#ee9b9b;background:#34232c}.execution-path{font-family:monospace;overflow-wrap:anywhere}
.execution-card pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:250px;overflow:auto;font-size:11px}.execution-card summary{cursor:pointer;color:#b6d5e0}

#skillsOverview{overflow-y:auto;min-height:0;flex:1;padding:4px 8px}#skillsOverview h2{font-size:24px}#skillNotice{background:#25364b;border-bottom:1px solid #708dae;padding:10px 18px;flex-shrink:0;font-size:13px}#skillNotice button{margin-left:8px;padding:6px 10px}
.skill-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;margin:14px 0}.skill-card{border:1px solid #37506c;background:#142237;border-radius:12px;padding:16px;min-width:0}.skill-card h3{margin-top:0;font-size:16px}.skill-card p{font-size:13px;overflow-wrap:anywhere}.skill-card small{overflow-wrap:anywhere}.skill-card button{margin:4px 6px 0 0;padding:8px 10px;font-size:12px}.skill-badge{color:#8fd8c2!important}.skill-search{padding:10px;width:min(100%,340px);box-sizing:border-box;background:#0b111d;color:#e7edfa;border:1px solid #49607d;border-radius:7px}.skill-restart{padding:12px;background:#223048;border-radius:8px}.skill-preview{border:1px solid #58718f;border-radius:10px;padding:16px;margin-top:16px}.skill-preview pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:400px;overflow:auto}
.runtime-field{display:block;margin:12px 0;font-size:13px}.runtime-field input[type=number]{box-sizing:border-box;width:100%;margin-top:5px;background:#0b111d;color:#e7edfa;border:1px solid #49607d;border-radius:5px;padding:8px}#runtimePanel p{font-size:12px;overflow-wrap:anywhere}#runtimePanel select{max-width:100%;margin-right:6px}
#chatSearch{box-sizing:border-box;width:100%;padding:10px;margin-top:10px;background:#0b111d;border:1px solid #49607d;border-radius:7px;color:#e7edfa}.history-count{font-size:11px;margin:10px 0}
.history-row{display:grid;grid-template-columns:minmax(0,1fr) 28px 28px;align-items:center;gap:3px;border:1px solid transparent;border-radius:9px;padding:4px;margin:5px 0}.history-row.selected{border-color:#5d8ec4;background:#1a3550}#leftbar .history-row .chat-open{min-width:0;width:100%;padding:9px 5px;background:transparent;margin:0}.history-title{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px}.chat-open small{display:block;font-size:10px;margin-top:5px;color:#aabbd4}#leftbar .history-row .chat-action{width:28px;height:30px;padding:3px;margin:0;text-align:center;background:#203249}
.chat-dialog{background:#132237;color:#e7edfa;border:1px solid #597a9d;border-radius:14px;width:min(420px,calc(100vw - 60px));padding:24px}.chat-dialog::backdrop{background:#030a14b8}.chat-dialog h2{font-size:20px;margin-top:0}.chat-dialog label{display:block;font-size:13px}.chat-dialog input{box-sizing:border-box;width:100%;margin-top:9px;padding:12px;border:1px solid #597a9d;background:#0b111d;color:#e7edfa;border-radius:7px;font:inherit}.dialog-actions{display:flex;justify-content:flex-end;gap:10px}.dialog-error{min-height:20px;color:#ffadad;font-size:13px}

.message-label{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.copy-button{background:#263f59;color:#cde3fa;padding:5px 9px;font-size:11px;border:1px solid #47617b;white-space:nowrap}.formatted-message{white-space:normal}.formatted-message p{color:inherit;white-space:pre-wrap;margin:9px 0}.formatted-message h3,.formatted-message h4,.formatted-message h5,.formatted-message h6{color:#eff6ff;margin:16px 0 8px}.formatted-message ul,.formatted-message ol{padding-left:24px;margin:9px 0}.formatted-message li{margin:5px 0;white-space:pre-wrap}.formatted-message blockquote{border-left:3px solid #638bac;padding-left:12px;margin:10px 0;color:#b6cce3}.formatted-message :not(pre)>code{background:#0b1624;border-radius:4px;padding:2px 5px;font-size:.9em;overflow-wrap:anywhere}.code-block{border:1px solid #3b526d;border-radius:8px;overflow:hidden;margin:12px 0;background:#09121f;min-width:0}.code-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;background:#1c2c40;padding:6px 10px;font:12px system-ui;color:#bcd2e7}.code-block pre{margin:0;padding:14px;overflow-x:auto;max-width:100%;white-space:pre;tab-size:4;font:12px/1.65 ui-monospace,monospace}.code-block pre code{background:none;padding:0;overflow-wrap:normal}.message-assistant{max-width:95%;width:fit-content}
.model-card{border:1px solid #526e8b;border-radius:10px;padding:14px;margin-top:12px;min-width:0}.model-card h3{margin:0 0 8px;font-size:16px}.model-card p{font-size:12px;overflow-wrap:anywhere}.model-card button{font-size:12px;padding:8px;margin:4px}.model-card pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:200px;overflow:auto;font-size:11px}.animation-panel{margin-top:14px;padding-top:12px;border-top:1px solid #526e8b}.animation-panel h4{margin:0 0 8px}.animation-panel select,.animation-panel input:not([type=range]){box-sizing:border-box;max-width:100%;width:100%;padding:9px;margin:5px 0;background:#0b111d;color:#e7edfa;border:1px solid #597a9d;border-radius:6px}.animation-panel input[type=range]{width:75%;vertical-align:middle}.model-stage{width:100%;min-width:0}.message:has(.model-card){width:95%;max-width:95%}
</style><main><h1>⚒ SMELTER</h1><p>V1.6.8 · Qwen vision · Local multimodal chat</p>
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
<script src="/assets/mcp-ui.js"></script><script src="/assets/turntable.js"></script><script src="/assets/model-animations.js"></script><script src="/assets/model-preview.js"></script><script src="/assets/chat-renderer.js"></script><script>
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
 const newChat=document.createElement('button');newChat.textContent='+ New chat';newChat.onclick=()=>editConversationTitle();
 const historySearch=document.createElement('input');historySearch.id='chatSearch';historySearch.type='search';historySearch.placeholder='Search conversations';historySearch.setAttribute('aria-label','Search conversation titles');historySearch.oninput=renderChatHistory;
 const historyCount=document.createElement('p');historyCount.id='historyCount';historyCount.className='history-count';
 const history=document.createElement('div');history.id='chatHistory';left.append(newChat,historySearch,historyCount,history);
 const title=document.createElement('h2');title.id='chatTitle';title.textContent='SMELTER · Local chat';
 const log=document.createElement('div');log.id='chatlog';log.setAttribute('role','log');log.setAttribute('aria-label','Conversation messages');log.textContent='Select New chat. Python tools require permission for each message.';
 const permissionsBox=document.createElement('details');permissionsBox.id='pythonTools';
 const permissionsTitle=document.createElement('summary');permissionsTitle.textContent='Tool permissions for the next message';
 const readFolder=document.createElement('input');readFolder.id='inventoryRoot';readFolder.placeholder='Absolute folder to inventory';readFolder.style.width='95%';
 const readGrant=document.createElement('input');readGrant.type='checkbox';readGrant.id='approveInventory';
 const readLabel=document.createElement('label');readLabel.append(readGrant,document.createTextNode(' Allow read-only inventory of this folder'));
 const writeGrant=document.createElement('input');writeGrant.type='checkbox';writeGrant.id='approveDiagnostics';
 const writeLabel=document.createElement('label');writeLabel.append(writeGrant,document.createTextNode(' Allow new Markdown reports in diagnostics/ (no overwrite)'));
 const reaGrant=document.createElement('input');reaGrant.type='checkbox';reaGrant.id='approveRea';
 const reaLabel=document.createElement('label');reaLabel.append(reaGrant,document.createTextNode(' Allow REA CLI for this message (runs Node; static PE inspection in the folder above)'));
 const reaCheck=document.createElement('button');reaCheck.type='button';reaCheck.textContent='Check REA connection';
 const reaStatus=document.createElement('p');reaStatus.id='reaStatus';
 reaCheck.onclick=async()=>{try{const s=await api('/api/rea/status');reaStatus.textContent='REA: '+s.status+' | version: '+(s.installed_version||'not installed')+' | '+s.reason}catch(e){reaStatus.textContent=e.message}};
 const modelGrants=document.createElement('div');modelGrants.id='modelInspectionGrants';
 const selectedModelIds=()=>[...modelGrants.querySelectorAll('input:checked')].map(x=>x.dataset.assetId);
 window.setChatModelGrants=assets=>{modelGrants.replaceChildren();for(const asset of assets){const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.dataset.assetId=asset.id;const label=document.createElement('label');label.style.display='block';label.append(checkbox,document.createTextNode(' Allow read-only GLB inspection: '+asset.filename));modelGrants.append(label)}permissionsBox.dispatchEvent(new Event('change',{bubbles:true}))};
 const toolsNote=document.createElement('p');toolsNote.textContent='Applies only to the next Send. Built-in scopes do not sandbox external MCP servers. Tool results are logged locally.';
 permissionsBox.append(permissionsTitle,readFolder,document.createElement('br'),readLabel,document.createElement('br'),writeLabel,document.createElement('br'),reaLabel,document.createElement('br'),reaCheck,reaStatus,modelGrants,toolsNote);
 const composer=document.createElement('div');composer.id='composer';
 const input=document.createElement('textarea');input.rows=3;input.maxLength=1800;input.setAttribute('aria-label','Message');input.id='chatinput';input.placeholder='Message local Qwen 3.5 9B';
 const send=document.createElement('button');send.textContent='Send to Qwen';
 const requestStatus=document.createElement('p');requestStatus.id='requestStatus';requestStatus.setAttribute('role','status');requestStatus.setAttribute('aria-live','polite');requestStatus.textContent='Ready · Enter to send · Shift+Enter for a new line';
 const stop=document.createElement('button');stop.textContent='Stop';stop.type='button';stop.disabled=true;
 let currentJob=null;
 const renderPending=(content)=>{const bubble=document.createElement('article');bubble.className='message message-user';const header=document.createElement('header');header.className='message-label';header.textContent='You · submitting';const body=document.createElement('div');body.className='message-content';body.textContent=content;bubble.append(header,body);log.append(bubble);log.scrollTop=log.scrollHeight;return header};
 stop.onclick=async()=>{if(!currentJob)return;stop.disabled=true;try{const job=await api('/api/chats','POST',{action:'stop',job_id:currentJob});requestStatus.textContent=job.phase}catch(e){requestStatus.textContent='Could not stop: '+e.message;stop.disabled=false}};
 input.addEventListener('keydown',event=>{if(event.key==='Enter'&&!event.shiftKey&&!event.isComposing){event.preventDefault();if(!send.disabled)send.click()}});
 send.onclick=async()=>{if(!activeChat){alert('Create a titled conversation first');return}if(send.disabled)return;const content=input.value.trim();if(!content){requestStatus.textContent='Enter a message before sending';return}send.disabled=true;newChat.disabled=true;input.disabled=true;imageInput.disabled=true;
 const conversation=activeChat;const started=Date.now();const pending=renderPending(content);
 const toolPermissions={...mcpControls.collect(),model_ids:selectedModelIds(),inventory_root:readGrant.checked?readFolder.value.trim():null,write_diagnostics:writeGrant.checked,rea_analysis:reaGrant.checked,rea_root:reaGrant.checked&&readFolder.value.trim()?readFolder.value.trim():null};
 readGrant.checked=false;writeGrant.checked=false;reaGrant.checked=false;modelGrants.querySelectorAll('input').forEach(x=>x.checked=false);mcpControls.refreshApprovals();
 requestStatus.textContent='Submitting request…';
 try{let attachment=null;const file=imageInput.files[0];
 if(file){if(file.size>2097152)throw Error('Image exceeds 2 MiB');const b64=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(Error('Could not read image'));reader.readAsDataURL(file)});attachment={mime:file.type,base64:b64}}
 let job=await api('/api/chats','POST',{action:'start',id:conversation,content,image:attachment,skills:selectedSkills,auto_skills:autoSkills,tool_permissions:toolPermissions});currentJob=job.id;stop.disabled=false;pending.textContent='You · sent';input.value='';imageInput.value='';
 try{sessionStorage.setItem('smelterActiveJob',JSON.stringify({id:job.id,conversation}))}catch(e){}
 while(job.state==='running'){requestStatus.textContent=job.phase+' · '+Math.floor((Date.now()-started)/1000)+'s';await new Promise(resolve=>setTimeout(resolve,1000));job=await api('/api/chat-jobs/'+encodeURIComponent(currentJob))}
 currentJob=null;try{sessionStorage.removeItem('smelterActiveJob')}catch(e){}
 requestStatus.textContent=job.state==='done'?'Completed · '+job.elapsed_seconds+'s':job.state==='cancelled'?'Stopped · completed tool actions remain recorded':'Request failed: '+job.error;
 if(activeChat===conversation)await openChat(conversation);await refreshChats();
 }catch(e){pending.textContent='You · submission/status error';requestStatus.textContent=e.message+(currentJob?' · Request may still be running. Use Stop or reload to reconnect.':'');}
 finally{if(!currentJob){stop.disabled=true;send.disabled=false;newChat.disabled=false;input.disabled=false;imageInput.disabled=false;input.focus()}}};
 const resumeJob=async()=>{let saved;try{saved=JSON.parse(sessionStorage.getItem('smelterActiveJob')||'null')}catch(e){return}if(!saved)return;currentJob=saved.id;send.disabled=true;newChat.disabled=true;input.disabled=true;imageInput.disabled=true;stop.disabled=false;
 try{let job;do{job=await api('/api/chat-jobs/'+encodeURIComponent(currentJob));requestStatus.textContent=job.state==='running'?job.phase+' · '+job.elapsed_seconds+'s':job.state==='error'?'Request failed: '+job.error:job.state;if(job.state==='running')await new Promise(resolve=>setTimeout(resolve,1000))}while(job.state==='running');await openChat(saved.conversation);await refreshChats();}
 catch(e){requestStatus.textContent=e.message}
 finally{currentJob=null;try{sessionStorage.removeItem('smelterActiveJob')}catch(e){}stop.disabled=true;send.disabled=false;newChat.disabled=false;input.disabled=false;imageInput.disabled=false}};
 window.resumeChatJob=resumeJob;
 const imageInput=document.createElement('input');imageInput.type='file';imageInput.accept='image/png,image/jpeg,image/webp';imageInput.title='Attach PNG, JPEG, or WebP (up to 2 MiB)';imageInput.style.maxWidth='180px';
 const modelFile=document.createElement('input');modelFile.type='file';modelFile.accept='.glb';modelFile.hidden=true;modelFile.id='modelFile';
 const attachModel=document.createElement('button');attachModel.type='button';attachModel.textContent='Attach GLB';attachModel.onclick=()=>{if(!activeChat){alert('Create a titled conversation first');return}if(send.disabled)return;modelFile.click()};
 modelFile.onchange=async()=>{const file=modelFile.files[0];if(!file)return;if(send.disabled){modelFile.value='';return}if(file.size>25*1024*1024){requestStatus.textContent='GLB exceeds 25 MiB';modelFile.value='';return}const conversation=activeChat;send.disabled=true;newChat.disabled=true;input.disabled=true;imageInput.disabled=true;attachModel.disabled=true;requestStatus.textContent='Uploading GLB for local preview…';try{const base64=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(Error('Could not read GLB'));reader.readAsDataURL(file)});await api('/api/models','POST',{conversation_id:conversation,filename:file.name,base64});await openChat(conversation);await refreshChats();requestStatus.textContent='GLB saved. Click Load 3D preview; Qwen was not called.'}catch(e){requestStatus.textContent=e.message}finally{send.disabled=false;newChat.disabled=false;input.disabled=false;imageInput.disabled=false;attachModel.disabled=false;modelFile.value=''}};
 composer.append(input,imageInput,modelFile,attachModel,send,stop);center.append(title,log,permissionsBox,requestStatus,composer);
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
   b.onclick=()=>{right.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));nav.forEach(x=>x.classList.remove('active'));sectionFocus(section,b)};
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
 const skillNotice=document.createElement('div');skillNotice.id='skillNotice';skillNotice.hidden=true;skillNotice.setAttribute('role','status');
 const skillNoticeText=document.createElement('span');const skillReview=document.createElement('button');skillReview.textContent='Review skills';const dismissNotice=document.createElement('button');dismissNotice.textContent='Dismiss';skillNotice.append(skillNoticeText,skillReview,dismissNotice);main.prepend(skillNotice);
 const skillView=document.createElement('section');skillView.id='skillsOverview';skillView.hidden=true;center.append(skillView);
 const chatElements=[title,log,permissionsBox,requestStatus,composer];
 window.showChatWorkspace=()=>{skillView.hidden=true;chatElements.forEach(x=>x.hidden=false)};
 const showSkills=()=>{if(send.disabled){alert('Finish or stop the current chat request first');return}SmelterModels.clear();chatElements.forEach(x=>x.hidden=true);skillView.hidden=false;loadSkillsOverview()};
 const overviewButton=document.createElement('button');overviewButton.textContent='Skills & Tools';overviewButton.className='navbtn';overviewButton.onclick=showSkills;
 const integrations=[...right.querySelectorAll('details')].find(x=>x.querySelector('summary')?.textContent.includes('Tools & Integrations'));if(integrations)integrations.querySelector('.config-folder-items').prepend(overviewButton);
 const mcpControls=SmelterMcp.mount(right,integrations,permissionsBox,api,()=>({model_ids:selectedModelIds(),inventory_root:readGrant.checked?readFolder.value.trim():null,write_diagnostics:writeGrant.checked,rea_analysis:reaGrant.checked,rea_root:reaGrant.checked&&readFolder.value.trim()?readFolder.value.trim():null}));
 skillReview.onclick=showSkills;
 let dismissedRevision=null,lastSkillsData=null,skillsPolling=false;
 dismissNotice.onclick=()=>{dismissedRevision=lastSkillsData?.revision;skillNotice.hidden=true};
 const refreshSkillNotice=async()=>{if(skillsPolling||document.hidden)return;skillsPolling=true;try{const data=await api('/api/skills/status');lastSkillsData=data;skillNoticeText.textContent=data.changes.length+' skill changes detected · review before restart. ';skillNotice.hidden=!data.changes.length||dismissedRevision===data.revision;}catch(e){overviewButton.title='Skill discovery unavailable: '+e.message}finally{skillsPolling=false}};
 const loadSkillsOverview=async()=>{skillView.replaceChildren();const heading=document.createElement('h2');heading.textContent='Skills & Tools';const back=document.createElement('button');back.textContent='Back to chat';back.onclick=window.showChatWorkspace;skillView.append(heading,back);
 try{const data=await api('/api/skills/status');lastSkillsData=data;
 const explanation=document.createElement('p');explanation.textContent='Drop skills into the watched folders. Review new or changed manifests, enable as needed, then restart the dashboard. Instructions never grant execution access.';
 const watched=document.createElement('p');watched.className='execution-path';watched.textContent='Watching: '+data.watched.join(' · ');
 const restart=document.createElement('p');restart.className='skill-restart';restart.textContent=data.restart_required?'Restart required: '+data.changes.map(c=>c.id+' ('+c.change+')').join(', ')+'. Stop the dashboard with Ctrl+C, then relaunch it.':'No manifest changes pending restart.';
 const search=document.createElement('input');search.placeholder='Search skill name, purpose or ID';search.setAttribute('aria-label','Search skills');search.className='skill-search';
 const filter=document.createElement('select');filter.setAttribute('aria-label','Filter activation');for(const [value,label] of [['','All skills'],['enabled','Enabled'],['disabled','Disabled'],['restart_required','Restart required'],['invalid','Invalid']]){const option=document.createElement('option');option.value=value;option.textContent=label;filter.append(option)}
 const count=document.createElement('p');const list=document.createElement('div');list.className='skill-grid';
 const preview=document.createElement('section');preview.className='skill-preview';preview.hidden=true;
 const render=()=>{list.replaceChildren();const query=search.value.toLowerCase();const matches=data.skills.filter(x=>(!filter.value||x.activation===filter.value)&&[x.name,x.id,x.description].join(' ').toLowerCase().includes(query));count.textContent=matches.length+' of '+data.count+' skills';
 for(const skill of matches){const card=document.createElement('article');card.className='skill-card';const name=document.createElement('h3');name.textContent=skill.name||skill.id;const identifier=document.createElement('small');identifier.textContent=skill.id;const status=document.createElement('p');status.className='skill-badge';status.textContent=skill.activation.replaceAll('_',' ')+' · '+skill.source;const description=document.createElement('p');description.textContent=skill.description||'No purpose declared.';
 const dependencies=document.createElement('p');dependencies.textContent=skill.dependencies===null?'Dependencies: unknown (no declaration)':skill.dependencies.length?'Dependencies: '+skill.dependencies.map(d=>d.name+' — '+d.status).join(', '):'Dependencies: none declared';
 const review=document.createElement('button');review.textContent='Review manifest';review.onclick=async()=>{preview.hidden=false;preview.replaceChildren();try{const result=await api('/api/skills/review/'+encodeURIComponent(skill.id));const label=document.createElement('h3');label.textContent=skill.id;const location=document.createElement('p');location.className='execution-path';location.textContent=result.manifest+' · Manifest/config fingerprint: '+result.fingerprint;const source=document.createElement('pre');source.textContent=result.text;const close=document.createElement('button');close.textContent='Close preview';close.onclick=()=>preview.hidden=true;preview.append(label,location,close,source);preview.scrollIntoView({block:'nearest'})}catch(e){preview.textContent=e.message}};
 const toggle=document.createElement('button');toggle.textContent=skill.enabled?'Disable':'Enable';toggle.disabled=skill.status!=='ready'||skill.activation==='invalid';toggle.onclick=async()=>{if(!confirm((skill.enabled?'Disable ':'Enable ')+skill.id+'? This grants no execution permission.'))return;try{await api('/api/skills/manage','POST',{action:'enable',id:skill.id,enabled:!skill.enabled,approval:true});await loadSkillsOverview();await refreshSkillNotice()}catch(e){alert(e.message)}};
 card.append(name,identifier,status,description,dependencies,review,toggle);if(skill.error){const error=document.createElement('p');error.textContent=skill.error;card.append(error)}list.append(card)}};
 search.oninput=filter.onchange=render;
 const refresh=document.createElement('button');refresh.textContent='Rescan folders';refresh.onclick=async()=>{await loadSkillsOverview();await refreshSkillNotice()};
 skillView.append(explanation,watched,restart,search,filter,refresh,count,list,preview);
 const toolHeading=document.createElement('h3');toolHeading.textContent='Connected tools';skillView.append(toolHeading);for(const tool of data.tools){const row=document.createElement('p');row.textContent=tool.name+' · '+tool.status+' · '+tool.detail;skillView.append(row)}
 const scope=document.createElement('small');scope.textContent=data.scope+'. Dependency presence is not runtime verification. Enablement does not load a skill into every message.';skillView.append(scope);render();
 }catch(e){const error=document.createElement('p');error.textContent='Could not inspect skills: '+e.message;skillView.append(error)}};
 setInterval(refreshSkillNotice,15000);refreshSkillNotice();
 const runtimePanel=document.createElement('section');runtimePanel.className='panel';runtimePanel.id='runtimePanel';
 const runtimeButton=document.createElement('button');runtimeButton.className='navbtn';runtimeButton.textContent='Chat runtime settings';
 const aiFolder=[...right.querySelectorAll('details')].find(x=>x.querySelector('summary')?.textContent.includes('AI & Models'));
 runtimeButton.onclick=async()=>{right.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));right.querySelectorAll('.navbtn').forEach(x=>x.classList.remove('active'));runtimePanel.classList.add('active');runtimeButton.classList.add('active');runtimePanel.textContent='Loading runtime settings…';
 try{const data=await api('/api/runtime');runtimePanel.replaceChildren();const heading=document.createElement('h3');heading.textContent='Chat runtime';const description=document.createElement('p');description.textContent='Applies to new SMELTER requests. Saving starts no model and does not change OpenCode.';const presets=document.createElement('select');presets.setAttribute('aria-label','Runtime preset');for(const [key,label] of [['office','Office · 16K · direct'],['home','Home · 32K']]){const option=document.createElement('option');option.value=key;option.textContent=label;presets.append(option)}const apply=document.createElement('button');apply.textContent='Use preset';
 const inputs={};const definitions=[['context_tokens','Context tokens',2048,131072],['max_output_tokens','Maximum response tokens',128,8192],['timeout_seconds','Request timeout (seconds)',30,1800]];
 runtimePanel.append(heading,description,presets,apply);
 for(const [key,label,min,max] of definitions){const row=document.createElement('label');row.className='runtime-field';const input=document.createElement('input');input.type='number';input.min=min;input.max=max;input.step=1;input.value=data.settings[key];inputs[key]=input;row.append(document.createTextNode(label+' '),input);runtimePanel.append(row)}
 const thinking=document.createElement('input');thinking.type='checkbox';thinking.checked=data.settings.thinking;const thinkingLabel=document.createElement('label');thinkingLabel.className='runtime-field';thinkingLabel.append(thinking,document.createTextNode(' Allow thinking in plain text chats'));runtimePanel.append(thinkingLabel);
 const note=document.createElement('p');note.textContent='Tool/image requests use direct responses. Larger context increases memory use. The timeout covers the whole model turn; active tool operations have their own bounds.';runtimePanel.append(note);
 const result=document.createElement('p');result.setAttribute('role','status');result.textContent='Sources: '+Object.entries(data.sources).map(([key,value])=>key+'='+value).join(', ');
 apply.onclick=()=>{const preset=data.profiles[presets.value];for(const key of Object.keys(inputs))inputs[key].value=preset[key];thinking.checked=preset.thinking;result.textContent='Preset selected. Click Save to apply.'};
 const save=document.createElement('button');save.textContent='Save runtime settings';save.onclick=async()=>{const settings={thinking:thinking.checked};for(const [key,input] of Object.entries(inputs)){if(!input.checkValidity()||!input.value){result.textContent='Enter a valid value for '+key;return}settings[key]=input.valueAsNumber}save.disabled=true;try{await api('/api/chats','POST',{action:'runtime_settings',settings});result.textContent='Saved locally. Applies to the next request; active generation is unchanged.'}catch(e){result.textContent=e.message}finally{save.disabled=false}};runtimePanel.append(save,result);
 }catch(e){runtimePanel.textContent='Runtime settings unavailable: '+e.message}};
 if(aiFolder)aiFolder.querySelector('.config-folder-items').prepend(runtimeButton,runtimePanel);
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
    const collectionFolders=new Map();
    for(const s of data.skills){
     const item=document.createElement('div');item.style.margin='12px 0';item.style.padding='10px';item.style.border='1px solid #7775';item.style.borderRadius='8px';
     const label=document.createElement('label');label.style.display='block';
     const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.dataset.skillId=s.id;
     checkbox.disabled=s.status!=='ready'||!s.enabled||!s.active_snapshot||s.activation==='invalid';checkbox.checked=s.enabled&&selectedSkills.includes(s.id);
     checkbox.onchange=()=>{
      if(checkbox.checked){if(selectedSkills.length>=3){checkbox.checked=false;alert('Maximum three manually selected skills');return}selectedSkills.push(s.id)}
      else selectedSkills=selectedSkills.filter(x=>x!==s.id);
      updateSummary();
     };
     label.append(checkbox,document.createTextNode(' '+(s.name||s.id)));
     const status=document.createElement('p');status.textContent='Status: '+s.activation.replaceAll('_',' ')+' · '+(s.enabled?'Enabled':'Disabled')+' · '+s.source+' · '+(s.bytes||0)+' bytes · No execution rights';
     const toggle=document.createElement('button');toggle.textContent=s.enabled?'Disable':'Enable';toggle.disabled=!s.enabled&&s.status!=='ready';
     toggle.onclick=async()=>{if(!confirm((s.enabled?'Disable ':'Enable ')+s.id+'?'))return;try{await api('/api/skills/manage','POST',{action:'enable',id:s.id,enabled:!s.enabled,approval:true});if(s.enabled)selectedSkills=selectedSkills.filter(x=>x!==s.id);await btn.onclick()}catch(e){alert(e.message)}};
     const remove=document.createElement('button');remove.textContent='Remove';remove.disabled=!s.removable;remove.title=s.removable?'Delete user-added skill':'Bundled skills cannot be deleted';
     remove.onclick=async()=>{if(!confirm('Permanently remove skill '+s.id+'?'))return;try{await api('/api/skills/manage','POST',{action:'remove',id:s.id,approval:true});selectedSkills=selectedSkills.filter(x=>x!==s.id);await btn.onclick()}catch(e){alert(e.message)}};
     const description=document.createElement('p');description.textContent=s.description||'No purpose available.';
     item.append(label,status,description,toggle,remove);
     if(s.collection){
       if(!collectionFolders.has(s.collection)){
         const folder=document.createElement('details');folder.style.margin='12px 0';
         const heading=document.createElement('summary');heading.textContent='📁 '+s.collection;folder.append(heading);
         collectionFolders.set(s.collection,folder);skillsPanel.append(folder);
       }
       collectionFolders.get(s.collection).append(item);
     }else skillsPanel.append(item);
    }
    const addHeading=document.createElement('h3');addHeading.textContent='Discover skill from GitHub';
    const urlInput=document.createElement('input');urlInput.placeholder='https://github.com/owner/repo/blob/main/SKILL.md';urlInput.style.width='100%';
    const repoButton=document.createElement('button');repoButton.textContent='Discover repository skills';
    const candidates=document.createElement('div');candidates.style.maxHeight='300px';candidates.style.overflowY='auto';
    const selectAll=document.createElement('button');selectAll.textContent='Select all';selectAll.hidden=true;
    const clearAll=document.createElement('button');clearAll.textContent='Clear';clearAll.hidden=true;
    const previewBatch=document.createElement('button');previewBatch.textContent='Review selected skills';previewBatch.hidden=true;
    const batchReview=document.createElement('pre');batchReview.style.whiteSpace='pre-wrap';batchReview.style.overflowWrap='anywhere';batchReview.style.maxHeight='320px';batchReview.style.overflow='auto';
    const installBatch=document.createElement('button');installBatch.textContent='Approve & install collection';installBatch.hidden=true;
    let repositoryUrl='', repositoryResults=[], reviewedBatch=[];
    const selectedUrls=()=>[...candidates.querySelectorAll('input[type=checkbox]:checked')].map(x=>x.value);
    const resetBatch=()=>{reviewedBatch=[];installBatch.hidden=true;batchReview.textContent=''};
    repoButton.onclick=async()=>{candidates.replaceChildren();selectAll.hidden=true;clearAll.hidden=true;previewBatch.hidden=true;resetBatch();try{
      repositoryUrl=urlInput.value;
      const result=await api('/api/skills/discover-repository','POST',{url:repositoryUrl});
      repositoryResults=result.skills;
      const info=document.createElement('p');info.textContent=result.count+' skills found in '+result.owner+'/'+result.repository+' @ '+result.ref;
      candidates.append(info);
      for(const skill of result.skills){
        const label=document.createElement('label');label.style.display='block';label.style.margin='6px 0';
        const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.value=skill.url;checkbox.onchange=resetBatch;
        label.append(checkbox,document.createTextNode(' '+skill.path.replace('skills/','').replace('/SKILL.md','')));
        candidates.append(label);
      }
      selectAll.hidden=clearAll.hidden=previewBatch.hidden=!result.skills.length;
    }catch(e){const error=document.createElement('p');error.textContent=e.message;candidates.append(error)}};
    selectAll.onclick=()=>{candidates.querySelectorAll('input[type=checkbox]').forEach(x=>x.checked=true);resetBatch()};
    clearAll.onclick=()=>{candidates.querySelectorAll('input[type=checkbox]').forEach(x=>x.checked=false);resetBatch()};
    previewBatch.onclick=async()=>{resetBatch();const urls=selectedUrls();if(!urls.length){batchReview.textContent='Select at least one skill';return}
      batchReview.textContent='Fetching selected manifests for review...';
      try{const result=await api('/api/skills/collection-preview','POST',{urls});
        reviewedBatch=result.skills.map(s=>({url:s.url,sha256:s.sha256,id:(s.path.split('/').slice(-2,-1)[0]||s.repository).toLowerCase().replace(/[^a-z0-9_-]/g,'-')}));
        batchReview.textContent=result.skills.map(s=>'--- '+s.path+' ---\\nWarnings: '+(s.warnings.join(', ')||'none detected')+'\\nSHA256: '+s.sha256+'\\n'+s.content).join('\\n\\n');
        installBatch.hidden=false;
      }catch(e){batchReview.textContent=e.message}};
    installBatch.onclick=async()=>{if(!reviewedBatch.length)return;
      if(!confirm('Install '+reviewedBatch.length+' reviewed skills as a disabled collection?'))return;
      try{await api('/api/skills/manage','POST',{action:'install_collection',repository_url:repositoryUrl,selected:reviewedBatch,approval:true});await btn.onclick()}
      catch(e){alert(e.message)}};
    const discoverButton=document.createElement('button');discoverButton.textContent='Discover & inspect URL';

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
    skillsPanel.append(addHeading,urlInput,repoButton,candidates,selectAll,clearAll,previewBatch,batchReview,installBatch,discoverButton,preview,idInput,installButton);
    updateSummary();
   }catch(e){skillsPanel.textContent='Skills Manager error: '+e.message}
  };
  toolsFolder.querySelector('.config-folder-items').prepend(btn,skillsPanel);
 }
 const statusPanel=document.createElement('div');statusPanel.className='panel';statusPanel.id='systemStatusPanel';statusPanel.textContent='Loading system status…';
 const systemFolder=[...right.querySelectorAll('details')].find(x=>x.querySelector('summary')?.textContent.includes('System & Storage'));
 if(systemFolder){const btn=document.createElement('button');btn.className='navbtn';btn.textContent='System status';btn.onclick=async()=>{systemFolder.open=true;right.querySelectorAll('.panel').forEach(x=>x.classList.remove('active'));right.querySelectorAll('.navbtn').forEach(x=>x.classList.remove('active'));statusPanel.classList.add('active');btn.classList.add('active');await refreshSystem()};systemFolder.querySelector('.config-folder-items').prepend(btn,statusPanel)}
}
let systemStatusBusy=false;
async function refreshSystem(){
 if(systemStatusBusy||document.hidden)return;systemStatusBusy=true;
 try{const s=await api('/api/system/status');const gb=n=>(n/1073741824).toFixed(1)+' GiB';
  const cpu=s.cpu.status==='ready'?s.cpu.percent+'%':s.cpu.status;
  const ram=s.memory.status==='ready'?gb(s.memory.used_bytes)+' / '+gb(s.memory.total_bytes)+' ('+gb(s.memory.available_bytes)+' available)':s.memory.status;
  const gpu=s.gpu.status==='ready'?gb(s.gpu.allocated_bytes)+' model allocation':'unavailable';
  const models=s.models.status==='ready'?(s.models.models.map(m=>m.name).join(', ')||'no model loaded'):'Ollama unavailable';
  const summary='CPU: '+cpu+' · RAM: '+ram+' · GPU: '+gpu+' · AI: '+models+' · Disk free: '+gb(s.storage.free_bytes)+' · DB: '+s.database.status;
  const footer=document.getElementById('sysfooter');footer.textContent=summary;footer.title='Live host metrics. GPU means Ollama-reported model allocation, not utilization; iGPU memory is shared with RAM. Updated '+new Date(s.timestamp*1000).toLocaleTimeString();
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
 const del=document.createElement('button');del.className='chat-action';del.textContent='×';del.title='Delete';del.setAttribute('aria-label','Delete '+chat.title);del.onclick=async()=>{if(document.getElementById('chatinput').disabled){alert('Finish or stop the active request first');return}if(!confirm('Delete conversation “'+chat.title+'” and its messages? Diagnostic files, 3D uploads and audit logs remain on disk.'))return;try{await api('/api/chats','POST',{action:'delete',id:chat.id});if(activeChat===chat.id){activeChat=null;document.getElementById('chatTitle').textContent='SMELTER · Local chat';document.getElementById('chatlog').textContent='Conversation deleted. Create or select another conversation.'}await refreshChats()}catch(e){alert(e.message)}};
 row.append(open,rename,del);history.append(row)}highlightChat();
}
async function refreshChats(){const data=await api('/api/chats');conversationHistory=data.conversations;renderChatHistory()}
function executionCards(execution){
 const section=document.createElement('section');section.className='execution-cards';section.setAttribute('aria-label','Backend tool execution');
 const heading=document.createElement('h3');heading.textContent='Tool execution · Controller record';section.append(heading);
 const events=execution.events||[];
 if(!events.length){const note=document.createElement('p');const grants=execution.permissions||{};note.textContent=execution.cancelled?'Request stopped; no tool result recorded.':grants.inventory_root||grants.write_diagnostics||grants.rea_analysis||grants.mcp_tools?.length||grants.model_ids?.length?'Tools were approved, but no tool calls were received.':'No tools were approved for this message.';section.append(note)}
 for(const event of events){const result=event.result||{};const failed=result.status==='error'||result.status==='rea_failed'||result.status==='mcp_failed';const card=document.createElement('article');card.className='execution-card '+(failed?'execution-error':'execution-success');
 const title=document.createElement('strong');title.textContent=(event.tool||'Unknown tool')+(event.transport==='mcp'?' [MCP]':'')+' · '+(event.reused?'Reused previous result':failed?(event.executed?'Failed':'Rejected'):result.status||'Unknown');card.append(title);
 const details=document.createElement('p');details.textContent=failed?(result.error||result.stderr||'Operation returned failure'):result.status==='written'?'Saved: '+result.path+' · '+result.bytes+' bytes':result.status==='inventoried'?result.files_observed+' files observed · Scan complete: '+result.scan_complete+' · Listed '+result.returned_entries+'/'+result.observed_entries:result.operation?'Operation: '+result.operation+' · Exit: '+result.exit_code:result.status==='model_inspected'?result.filename+' · '+result.meshes+' meshes · '+result.animations+' animation clips':result.server?'MCP server: '+result.server+' · Tool: '+result.tool:'Result recorded';card.append(details);
 const hash=result.sha256||result.evidence_sha256;if(hash){const checksum=document.createElement('p');checksum.className='execution-path';checksum.textContent='SHA-256: '+hash;card.append(checksum)}
 if(result.evidence_path){const path=document.createElement('p');path.className='execution-path';path.textContent='Evidence: '+result.evidence_path;card.append(path)}
 const disclosure=document.createElement('details');const summary=document.createElement('summary');summary.textContent='Recorded result';const raw=document.createElement('pre');raw.textContent=JSON.stringify(event,null,2);disclosure.append(summary,raw);card.append(disclosure);section.append(card)}
 if(execution.audit_path){const audit=document.createElement('p');audit.className='execution-path';audit.textContent='Audit: '+execution.audit_path;section.append(audit)}
 const scope=document.createElement('small');scope.textContent='Controller records establish tool results and saved bytes. AI explanations are not fact-checked.';section.append(scope);return section;
}
async function openChat(id){
 try{const chat=await api('/api/chats/'+encodeURIComponent(id));SmelterModels.clear();if(window.showChatWorkspace)window.showChatWorkspace();activeChat=id;window.setChatModelGrants?.(chat.messages.filter(m=>m.model_attachment).map(m=>m.model_attachment));highlightChat();const log=document.getElementById('chatlog');log.replaceChildren();document.getElementById('chatTitle').textContent=chat.title;
 for(const msg of chat.messages){const bubble=document.createElement('article');bubble.className='message '+(msg.role==='user'?'message-user':'message-assistant');const label=document.createElement('header');label.className='message-label';const speaker=msg.role==='user'?'You':msg.role==='assistant'?'SMELTER · AI response':'System';label.textContent=speaker+' · '+localTimestamp(msg.created_at);const body=document.createElement('div');body.className='message-content';const text=msg.execution?.source==='controller'?msg.execution.model_text:msg.content;if(msg.role==='assistant'){SmelterChat.render(text,body);label.append(SmelterChat.copyButton(text,'Copy response'))}else body.textContent=text;bubble.append(label,body);if(msg.model_attachment)SmelterModels.mount(msg.model_attachment,bubble);log.append(bubble);
 if(msg.role==='assistant'){if(msg.execution?.source==='controller')log.append(executionCards(msg.execution));else{const legacy=document.createElement('small');legacy.textContent='Historical transcript: structured tool execution records are unavailable for this message.';log.append(legacy)}}}
 if(!chat.messages.length)log.textContent='Start the conversation below.';log.scrollTop=log.scrollHeight;
 }catch(e){alert(e.message)}
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
  if(db.ready){boot.hidden=true;shell.hidden=false;footer.hidden=false;refresh();loadWorkflows();refreshChats();refreshSystem();if(window.resumeChatJob)window.resumeChatJob()}
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
            body = data if isinstance(data, bytes) else data.encode() if isinstance(data, str) else json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'unsafe-inline'; connect-src 'self' blob: data:; img-src 'self' blob: data:; worker-src 'self' blob:")
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
            if route == '/assets/mcp-ui.js':
                return self.reply(200, Path(__file__).with_name('mcp_ui.js').read_text(encoding='utf-8'), 'application/javascript')
            if route == '/assets/chat-renderer.js':
                return self.reply(200, Path(__file__).with_name('chat_renderer.js').read_text(encoding='utf-8'), 'application/javascript')
            if route == '/assets/model-animations.js':
                return self.reply(200, Path(__file__).with_name('model_animations.js').read_text(encoding='utf-8'), 'application/javascript')
            if route == '/assets/model-preview.js':
                return self.reply(200, Path(__file__).with_name('model_preview.js').read_text(encoding='utf-8'), 'application/javascript')
            if route == '/assets/turntable.js':
                return self.reply(200, Path(__file__).with_name('turntable.js').read_text(encoding='utf-8'), 'application/javascript')
            if route == '/assets/model-viewer.min.js':
                try:
                    return self.reply(200, viewer_bundle(ROOT).read_bytes(), 'application/javascript')
                except (OSError, ValueError) as e:
                    return self.reply(404, {'error': str(e)})
            if not self.authorized():
                return self.reply(403, {"error": "Unauthorized"})
            if route == '/api/mcp/status':
                try:
                    return self.reply(200, mcp_status(ROOT))
                except (OSError, ValueError) as e:
                    return self.reply(400, {'error': str(e)})
            if route == '/api/models/status':
                return self.reply(200, viewer_status(ROOT))
            if route.startswith('/api/models/'):
                try:
                    return self.reply(200, model_path(ROOT, route.removeprefix('/api/models/')).read_bytes(), 'model/gltf-binary')
                except (OSError, ValueError) as e:
                    return self.reply(400, {'error': str(e)})
            if route.startswith("/api/chat-jobs/"):
                try:
                    return self.reply(200, JOBS.status(route.removeprefix("/api/chat-jobs/")))
                except ValueError as e:
                    return self.reply(400, {"error": str(e)})
            if route == "/api/skills":
                try:
                    return self.reply(200, skill_monitor(ROOT).status())
                except (OSError, ValueError) as e:
                    return self.reply(400, {"error": str(e)})
            if route == "/api/skills/status":
                try:
                    return self.reply(200, {**skill_monitor(ROOT).status(), 'tools': tools_status(ROOT)})
                except (OSError, ValueError) as e:
                    return self.reply(400, {"error": str(e)})
            if route.startswith('/api/skills/review/'):
                try:
                    return self.reply(200, skill_monitor(ROOT).review(unquote(route.removeprefix('/api/skills/review/'))))
                except (OSError, ValueError) as e:
                    return self.reply(400, {'error': str(e)})
            if route == "/api/rea/status":
                return self.reply(200, rea_package_status(ROOT))
            if route == '/api/runtime':
                try:
                    return self.reply(200, load_runtime(ROOT))
                except (OSError, ValueError) as e:
                    return self.reply(400, {'error': str(e)})
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
            if route not in ("/api/mcp", "/api/models", "/api/extensions", "/api/workflows/plan", "/api/archive/inspect", "/api/media/inspect", "/api/blender/inspect", "/api/ollama/preferences", "/api/opencode/deploy", "/api/database/select", "/api/chats", "/api/aero/classify", "/api/skills/manage", "/api/skills/discover", "/api/skills/discover-repository", "/api/skills/collection-preview"):
                return self.reply(404, {"error": "Not found"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= (36 * 1024 * 1024 if route == "/api/models" else 65536 if route == "/api/mcp" else 3 * 1024 * 1024 if route == "/api/chats" else 16384):
                    raise ValueError("Invalid request size")
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("Invalid request")
                if route == '/api/mcp':
                    if data.get('action') == 'save':
                        with STATE_LOCK:
                            return self.reply(200, save_mcp_config(ROOT, data.get('config')))
                    if data.get('action') == 'probe':
                        sid = data.get('server')
                        if not isinstance(sid, str):
                            raise ValueError('Choose an MCP server')
                        grants = validate_tool_permissions(ROOT, data.get('permissions')) if sid == 'smelter' else {}
                        return self.reply(200, mcp_exchange(ROOT, sid, grants, timeout=20))
                    raise ValueError('Unknown MCP action')
                if route == "/api/models":
                    return self.reply(200, rename_animation(ROOT, data) if data.get('action') == 'rename_animation' else attach_model(ROOT, data))
                if route == "/api/skills/collection-preview":
                    urls = data.get("urls")
                    if not isinstance(urls, list) or not 1 <= len(urls) <= 40:
                        raise ValueError("Select 1-40 skills")
                    results = [discover_github_skill(url) for url in urls]
                    return self.reply(200, {"skills": results})
                if route == "/api/skills/discover-repository":
                    return self.reply(200, discover_github_repository(data.get("url")))
                if route == "/api/skills/discover":
                    return self.reply(200, discover_github_skill(data.get("url")))
                if route == "/api/skills/manage":
                    with STATE_LOCK:
                        action = data.get("action")
                        if action == "add":
                            raise ValueError("Use GitHub discovery before installation")
                        elif action == "install_collection":
                            result = install_collection(ROOT, data.get("repository_url"), data.get("selected"), data.get("approval"))
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
                if route == '/api/chats' and data.get('action') == 'runtime_settings':
                    return self.reply(200, save_runtime(ROOT, data.get('settings')))
                if route == "/api/chats":
                    if data.get("action") == "start":
                        return self.reply(202, JOBS.start(ROOT, data))
                    if data.get("action") == "stop":
                        return self.reply(200, JOBS.cancel(data.get("job_id")))
                    with STATE_LOCK:
                        action = data.get("action")
                        if action == "ask":
                            result = ask(ROOT, data.get("id"), data.get("content"), image=data.get("image"), skills=data.get("skills"), auto_skills=data.get("auto_skills", False), tool_permissions=data.get("tool_permissions"))
                        elif action == "create":
                            result = create_chat(ROOT, data.get("title"))
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
    initialize_skills(ROOT)
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
