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
from urllib.parse import urlsplit, unquote, parse_qs

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "setup"))
from check_requirements import scan
from extensions import catalog, set_enabled
from workflows import definitions, plan
from reports import attach_inputs, list_reports, save_report
from execution import inspect_archive
from media import inspect_media
from blender import inspect_blender
from ollama import list_models
from model_preferences import configured_status
from opencode import inspect_opencode
from opencode_provider import provider_preview
from opencode_deploy import deploy_isolated_config
from opencode_validate import validate_staged_config
from database import select_database
from config_store import load_config, save_config
from startup import startup_report
from system_status import system_status
from chats import list_chats, create_chat, read_chat, add_note, rename_chat, delete_chat
from skill_manager import remove_skill, set_skill_enabled
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
STATE_LOCK = threading.RLock()
REPORTS = ROOT / ".smelter" / "reports"
MODEL_PREFS = ROOT / ".smelter" / "model_preferences.json"
HTML = r"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SMELTER · Dashboard</title><style>
:root{color-scheme:dark;--bg:#101114;--surface:#181a20;--raised:#20232b;--border:#30343e;--text:#edeef3;--muted:#9da4b3;--accent:#a0dfd0;--danger:#f0a3a3;font:14px/1.5 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
*{box-sizing:border-box}[hidden]{display:none!important}html,body{height:100%;margin:0;overflow:hidden}body{background:var(--bg);color:var(--text)}main{height:100dvh;display:flex;flex-direction:column;min-height:0}main>h1{font-size:21px;font-weight:650;letter-spacing:-.5px;margin:18px 24px 0}main>p{margin:2px 24px 12px;font-size:12px;color:var(--muted)}h2,h3,h4{letter-spacing:-.025em;line-height:1.25}h2{font-size:23px;margin:0 0 12px}h3{font-size:18px;margin:0 0 14px}p{color:var(--muted)}small,.muted{color:var(--muted)}button,input,select,textarea{font:inherit}button{border:1px solid var(--border);border-radius:9px;padding:8px 13px;background:var(--raised);color:var(--text);cursor:pointer;transition:background .15s,border-color .15s}button:hover:not(:disabled){background:#2a2e38;border-color:#51596b}button:disabled{opacity:.4;cursor:not-allowed}button:focus-visible,input:focus-visible,select:focus-visible,textarea:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:3px}input:not([type=checkbox]):not([type=range]),select,textarea{max-width:100%;padding:10px 12px;color:var(--text);background:#111318;border:1px solid var(--border);border-radius:9px}input[type=checkbox]{width:16px;height:16px;accent-color:var(--accent);vertical-align:middle}label{color:#c5cad5}summary{cursor:pointer}pre,code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}pre{font-size:12px;line-height:1.65;white-space:pre-wrap;overflow-wrap:anywhere;overflow:auto}a{color:var(--accent)}.panel{min-width:0}.quiet-button{background:transparent}
#shell{display:grid;grid-template-columns:230px minmax(0,1fr);gap:12px;padding:0 16px 12px;flex:1;min-height:0}#leftbar{padding:16px 10px;border:1px solid var(--border);border-radius:16px;background:#15171c;min-height:0;overflow:auto}#leftbar h2{font-size:12px;text-transform:uppercase;letter-spacing:.09em;margin:0 8px 14px;color:var(--muted)}#leftbar>button{width:100%;text-align:left;background:#262b34}#chatSearch{width:100%;margin:12px 0 0}.history-count{font-size:11px;margin:10px 6px}.history-row{display:grid;grid-template-columns:minmax(0,1fr) 25px 25px;gap:2px;align-items:center;border:1px solid transparent;border-radius:10px;padding:4px;margin:4px 0}.history-row.selected{background:#242932;border-color:#3a4656}.chat-open{min-width:0;background:transparent;border:0;text-align:left;padding:8px}.history-title{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.chat-open small{font-size:10px}.chat-action{padding:2px;border:0;background:transparent;font-size:16px}.history-title{font-weight:550}
#workspace{background:#15171c;border:1px solid var(--border);border-radius:16px;display:flex;flex-direction:column;padding:18px;min-width:0;min-height:0;overflow:hidden}.workspace-toolbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:18px;flex-shrink:0}.workspace-toolbar button{font-size:12px;background:transparent}#taskAccessSummary{flex:1;min-width:170px;color:var(--muted);font-size:11px}#chatTitle{font-size:18px}#chatlog{display:flex;flex-direction:column;gap:18px;flex:1;min-height:0;overflow:auto;overscroll-behavior:contain;padding:8px 6px 24px;scrollbar-width:thin}.message{min-width:0;max-width:94%;padding:14px 18px;border-radius:17px;flex-shrink:0;overflow-wrap:anywhere}.message-user{align-self:flex-end;background:#29313d;border:1px solid #3c485a}.message-assistant{align-self:flex-start;max-width:97%;background:transparent;border:0}.message-label{display:flex;justify-content:space-between;gap:16px;align-items:center;flex-wrap:wrap;font-size:11px;font-weight:650;color:#bfc7d5;margin-bottom:10px}.message-content{white-space:pre-wrap;line-height:1.7}.copy-button{font-size:10px;padding:3px 8px;background:transparent}.formatted-message p{color:inherit;white-space:pre-wrap;margin:9px 0}.formatted-message ul,.formatted-message ol{padding-left:24px}.formatted-message li{margin:6px 0}.formatted-message blockquote{border-left:2px solid #6a8b84;padding-left:12px;margin-left:0;color:var(--muted)}.formatted-message :not(pre)>code{background:#242832;border-radius:4px;padding:2px 5px;font-size:.9em}.code-block{border:1px solid var(--border);border-radius:10px;overflow:hidden;margin:12px 0;background:#101217}.code-toolbar{display:flex;justify-content:space-between;align-items:center;padding:7px 12px;background:#20232b;font-size:11px;color:var(--muted)}.code-block pre{white-space:pre;margin:0;padding:16px;overflow-x:auto}.message:has(.model-card){width:97%}
#composer{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:10px;background:#20232a;border:1px solid #3a3f49;border-radius:20px;flex-shrink:0;position:relative}#chatinput{order:-1;flex-basis:100%;width:100%;min-height:74px;max-height:170px;resize:vertical;background:transparent;border:0;padding:6px 8px;line-height:1.6}#composer>button{border-radius:10px}#composer>button:nth-last-of-type(3){margin-left:auto}#requestStatus{font-size:11px;min-height:17px;margin:8px 2px;flex-shrink:0}#workspace>label{font-size:12px;color:var(--muted)}#chatEngine{font-size:12px;padding:5px 10px;margin-left:5px;background:transparent;border-color:transparent}#sysfooter{flex-shrink:0;padding:9px 22px;border-top:1px solid #252831;font-size:10px;color:var(--muted);overflow:auto;white-space:nowrap;max-height:62px}
.attachment-control{position:relative;display:flex;gap:8px;align-items:center}.attachment-add{font-size:26px;width:36px;height:36px;line-height:1;padding:0;border-radius:50%;background:transparent;border-color:transparent}.attachment-menu{position:absolute;bottom:48px;left:0;width:310px;max-width:calc(100vw - 65px);padding:8px;border:1px solid #424650;border-radius:16px;background:#292b31;box-shadow:0 18px 60px #0009;z-index:20}.attachment-menu>p{font-size:10px;letter-spacing:.12em;padding:2px 10px;color:#a6adba}.attachment-menu button{display:flex;flex-direction:column;width:100%;text-align:left;gap:3px;padding:12px;border:0;background:transparent;border-radius:10px}.attachment-menu button:hover,.attachment-menu button:focus{background:#3b3e46}.attachment-menu strong{font-size:13px;font-weight:550}.attachment-menu small{font-size:11px}.attachment-chip{display:inline-flex;align-items:center;gap:6px;padding:3px 6px 3px 10px;border:1px solid #4a5363;border-radius:9px;font-size:11px;max-width:220px}.attachment-chip>span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.attachment-chip button{border:0;padding:1px 5px;background:transparent;font-size:18px}
.settings-screen{width:min(1220px,96vw);height:90dvh;max-width:none;max-height:none;padding:0;color:var(--text);background:var(--surface);border:1px solid #424650;border-radius:20px;box-shadow:0 40px 100px #0008;overflow:hidden}.settings-screen::backdrop,.import-dialog::backdrop,.chat-dialog::backdrop{background:#050608a8;backdrop-filter:blur(5px)}.settings-header{height:74px;display:flex;justify-content:space-between;align-items:center;padding:0 28px;border-bottom:1px solid var(--border)}.settings-header h2{font-size:21px;margin:0}.settings-header button{font-size:12px}#rightbar{display:grid;grid-template-columns:220px minmax(0,1fr);height:calc(100% - 74px);min-height:0}.settings-nav{background:#13151a;padding:14px 12px;overflow:auto;border-right:1px solid var(--border);scrollbar-width:thin}.settings-nav-group{margin-bottom:18px}.settings-nav-group h3{font-size:10px;text-transform:uppercase;letter-spacing:.12em;color:#7f899a;margin:10px 10px 7px}.settings-nav .navbtn{display:block;width:100%;border:0;background:transparent;border-radius:8px;text-align:left;font-size:12px;padding:9px 11px;margin:2px 0;color:#b3bbc9}.settings-nav .navbtn.active{background:#2b343a;color:#c2f1e6}.settings-content{overflow:auto;padding:28px;min-width:0;scrollbar-width:thin}.settings-content>.panel{display:none;margin:0;padding:0;border:0;background:transparent}.settings-content>.panel.active{display:block}.settings-content p{max-width:85ch;font-size:12px;line-height:1.65}.settings-content h2{font-size:25px}.settings-content h3{font-size:20px}.settings-content input:not([type=checkbox]),.settings-content textarea{max-width:100%}.settings-content button{margin:3px 5px 3px 0;font-size:12px}.settings-content pre{background:#111318;border:1px solid #282d36;border-radius:10px;padding:14px;max-height:400px}.settings-content .ext{padding:16px 0;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center;gap:15px}.settings-content .ext h3{font-size:14px;margin:0}.runtime-field{display:block;margin:18px 0;font-size:12px}.runtime-field input[type=number]{display:block;width:100%;margin-top:6px}.access-location-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,290px),1fr));gap:14px}.access-location{min-width:0;border:1px solid var(--border);border-radius:12px;padding:16px;margin:0}.access-location legend{padding:0 6px;font-size:12px}.access-location>label{display:block;margin:12px 0;font-size:11px}.access-location>label input,.access-location textarea{display:block;width:100%;margin-top:5px}.access-flags{display:flex;gap:10px;flex-wrap:wrap;font-size:11px;margin:12px 0}#taskAccessPanel #pythonTools{overflow:visible}#pythonTools>label{display:inline-block;margin:8px 0;font-size:12px}#pythonTools>summary{font-weight:600;margin:12px 0}#inventoryRoot{width:100%!important}#skillNotice{padding:10px 24px;background:#383222;color:#efdaa7;font-size:12px}#skillNotice button{font-size:11px;padding:4px 9px;margin-left:8px}
.section-heading p{margin:0 0 22px}.skills-toolbar{position:sticky;top:0;z-index:3;background:var(--surface);padding:8px 0;display:flex;align-items:center;gap:6px;flex-wrap:wrap}.skills-toolbar input{margin-left:auto;width:220px;font-size:12px}.skills-toolbar button:first-child{background:#a0dfd0;border-color:#a0dfd0;color:#122720;font-weight:650}.skills-notice{font-size:11px!important;min-height:18px}.skills-table-wrap{overflow:auto;border:1px solid var(--border);border-radius:12px}.skills-table{width:100%;border-collapse:collapse;text-align:left;min-width:650px}.skills-table th{font-size:10px;font-weight:600;color:#9fa8b8;letter-spacing:.07em;text-transform:uppercase;background:#20232a;padding:12px;white-space:nowrap}.skills-table td{padding:12px;border-top:1px solid #2b2f38;font-size:12px;vertical-align:middle}.skills-table th:first-child,.skills-table td:first-child{width:40px;padding-right:0}.skills-table tr:hover td{background:#20242c}.skills-table .skill-name{background:none;border:0;padding:0!important;margin:0!important;display:block;text-align:left;font-size:13px;font-weight:600}.skills-table td>small{display:block;font-size:10px;margin-top:3px}.skill-description{display:block;font-size:11px;color:#8994a5;max-width:350px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.status-badge{display:inline-flex;align-items:center;gap:5px;padding:3px 7px;border-radius:6px;font-size:10px;white-space:nowrap;background:#2a2e37;color:#aab1bf}.status-badge:before{content:'';width:5px;height:5px;border-radius:50%;background:currentColor}.status-badge.good{background:#19332b;color:#9cdebc}.status-badge.warn{background:#3c3220;color:#e9c984}.status-badge.bad{background:#3b252b;color:#f0a3a3}.status-badge.accent{background:#253548;color:#a8cbf2}.skill-group td{background:#20242b;font-weight:600}.collection-toggle{padding:0!important;border:0;background:transparent!important}.collection-count{margin-left:14px;color:var(--muted);font-size:10px;font-weight:400}.skills-taskbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:16px}.skills-taskbar label{font-size:11px;margin-left:auto}.skill-detail{margin-top:20px;border-top:1px solid var(--border);padding-top:20px}.skill-detail p{overflow-wrap:anywhere}.skill-detail pre{max-height:350px}
.import-dialog,.chat-dialog{width:min(720px,94vw);max-height:88dvh;border:1px solid #424650;border-radius:18px;background:var(--surface);color:var(--text);padding:28px;overflow:auto}.chat-dialog{width:min(440px,94vw)}.chat-dialog input,.import-dialog>input{width:100%;margin:8px 0 12px}.chat-dialog label{display:block;font-size:12px}.dialog-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:20px}.dialog-error{min-height:20px;color:var(--danger)}.import-dialog pre{max-height:270px;font-size:11px;padding:12px;background:#101217;border-radius:9px}.import-candidates{max-height:200px;overflow:auto;margin:12px 0}.import-candidates label{display:block;padding:6px;font-size:12px}.import-dialog p{font-size:12px}.import-dialog .dialog-actions button:last-child{background:var(--accent);color:#122720}
.execution-cards{align-self:stretch;border:1px solid #2b4943;background:#14231f;border-radius:12px;padding:14px;flex-shrink:0;min-width:0}.execution-cards h3{font-size:12px;color:#a0dfd0;margin:0 0 10px}.execution-cards p{font-size:11px;margin:7px 0;overflow-wrap:anywhere}.execution-card{border-left:2px solid #8bcab1;background:#1b302a;margin:10px 0;padding:12px;border-radius:6px;font-size:12px}.execution-error{border-left-color:var(--danger);background:#34232c}.execution-path{font-family:monospace;overflow-wrap:anywhere}.execution-card pre{max-height:250px;font-size:11px}.file-activity{align-self:stretch;min-width:0;padding:16px;border:1px solid var(--border);border-radius:12px;background:#12151b}.file-activity h3{font-size:15px;margin:0 0 8px}.file-activity-note{font-size:11px;color:var(--muted)}.file-activity-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:12px}.file-work-card{min-width:0;border:1px solid #37506c;border-radius:10px;padding:14px;background:#191e27}.file-work-card h4{font:11px/1.5 ui-monospace,monospace;overflow-wrap:anywhere;margin:0 0 8px}.file-work-status{display:block;font-size:10px;color:#b6c5d7;margin-bottom:12px}.file-work-card[data-state=saved]{border-color:#69c6a3}.file-work-card[data-state=error]{border-color:var(--danger)}.file-work-card summary{font-size:11px;padding:8px 0}.file-original-code,.file-work-card details pre{max-height:320px;white-space:pre;overflow:auto;font:11px/1.6 ui-monospace,monospace;background:#101217;padding:12px}.file-code-label{display:block;font-size:11px;margin-top:12px}.file-code-label span{display:block;margin-bottom:7px}.file-updated-code{width:100%;min-height:160px;max-height:500px;resize:vertical;white-space:pre;overflow:auto;font:11px/1.6 ui-monospace,monospace}.file-work-error{color:var(--danger);font-size:11px}.model-card{border:1px solid var(--border);border-radius:12px;padding:14px;margin-top:12px;min-width:0}.model-card h3{font-size:15px;margin:0 0 8px}.model-card p{font-size:11px;overflow-wrap:anywhere}.model-card button{font-size:11px;padding:7px;margin:4px}.model-card pre{max-height:200px;font-size:11px}.model-stage{width:100%;min-width:0}.animation-panel{margin-top:14px;padding-top:12px;border-top:1px solid var(--border)}.animation-panel select,.animation-panel input:not([type=range]){width:100%;margin:5px 0}.animation-panel input[type=range]{width:75%;vertical-align:middle}#bootstrap{margin:30px auto;padding:24px;max-width:640px;width:calc(100% - 40px);overflow:auto}#bootstrap input{width:100%}#error{color:var(--danger)}
@media(max-width:850px){html,body{height:auto;overflow:auto}main{height:auto;min-height:100dvh}main>h1{margin:14px 16px 0}main>p{margin-left:16px}#shell{display:flex;flex-direction:column;padding:0 8px 8px}#leftbar{max-height:170px;flex-shrink:0}#workspace{height:76dvh;min-height:500px;padding:12px}#chatlog{min-height:120px}.message{max-width:98%;padding:12px}#sysfooter{font-size:9px}.settings-screen{width:98vw;height:96dvh;border-radius:14px}.settings-header{height:62px;padding:0 16px}#rightbar{height:calc(100% - 62px);grid-template-columns:155px minmax(0,1fr)}.settings-nav{padding:8px 6px}.settings-nav .navbtn{font-size:11px;padding:8px}.settings-content{padding:18px 14px}.settings-nav-group h3{font-size:9px;margin-left:8px}.skills-toolbar input{width:100%;margin-left:0}.skills-taskbar label{margin-left:0}}
@media(max-width:520px){#rightbar{display:flex;flex-direction:column}.settings-nav{display:flex;gap:8px;overflow-x:auto;max-height:122px;flex-shrink:0;border-right:0;border-bottom:1px solid var(--border)}.settings-nav-group{min-width:155px;margin:0}.settings-nav-group h3{margin-top:3px}.settings-nav .navbtn{padding:5px 8px;margin:0}.settings-content{flex:1;min-height:0}.settings-header h2{font-size:19px}.attachment-chip{max-width:160px}}
.settings-section-picker{display:none}@media(max-width:520px){.settings-nav{display:none}.settings-section-picker{display:block;margin:12px 14px 0;width:calc(100% - 28px);flex-shrink:0}}
</style><main><h1>⚒ SMELTER</h1><p>V1.7 · Scoped local workbench</p>
<section class="panel"><h2>Extensions</h2><p>Extensions are disabled by default. Activation only records configuration; execution permissions remain ungranted.</p>
<button id="refresh">Rescan tools</button><p id="error"></p><div id="items">Loading…</div></section>
<section class="panel"><h2>Workflow planner</h2><p>Preview ordered steps and dependency checks. Dry run only — no tools execute.</p>
<select id="workflow" style="padding:10px;background:#0b111d;color:#e7edfa;border:1px solid #30445e;border-radius:7px"></select>
<p><label for="inputs">Optional absolute input paths (one per line; maximum 16)</label></p>
<textarea id="inputs" rows="3" style="width:100%;box-sizing:border-box;background:#0b111d;color:#e7edfa;border:1px solid #30445e;border-radius:7px;padding:10px" placeholder="C:\path\to\asset"></textarea>
<p><button id="plan">Preview and save dry run</button> <button id="history">Refresh report history</button></p>
<pre id="historyout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre><pre id="planout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
<section class="panel"><h2>Controlled execution: archive inspection</h2><p>Read-only 7-Zip listing. Select an existing archive and explicitly approve each run. No extraction or file changes.</p>
<input id="archivepath" style="width:100%;box-sizing:border-box;padding:10px;background:#0b111d;color:#e7edfa;border:1px solid #30445e" placeholder="C:\archives\example.zip">
<p><label><input id="approve" type="checkbox"> I approve running 7-Zip to list this archive only.</label></p>
<button id="inspect">Inspect archive (read only)</button><pre id="inspectout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
<section class="panel"><h2>Controlled execution: media inspection</h2><p>Read-only FFprobe metadata inspection. Approve each run; no transcoding or generated files.</p>
<input id="mediapath" style="width:100%;box-sizing:border-box;padding:10px;background:#0b111d;color:#e7edfa;border:1px solid #30445e" placeholder="C:\media\sample.mp4">
<p><label><input id="mediaapprove" type="checkbox"> I approve FFprobe reading this media file's metadata only.</label></p>
<button id="mediainspect">Inspect media (read only)</button><pre id="mediaout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
<section class="panel"><h2>Controlled execution: Blender capability</h2><p>Check the Blender executable and version only. No project loading, Python scripts, or asset modification.</p>
<p><label><input id="blenderapprove" type="checkbox"> I approve launching Blender with --version only.</label></p>
<button id="blenderinspect">Check Blender version</button><pre id="blenderout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
<section class="panel"><h2>Local AI: Ollama / Qwen</h2><p>Discover models already installed in your local Ollama service. No downloads, prompts, or model execution.</p>
<button id="ollamascan">Discover local models</button>
<p><label>Role <select id="modelrole"><option value="reasoning">Reasoning</option><option value="lightweight">Lightweight · configuration only</option></select></label>
<label> Installed model <select id="modelchoice"></select></label></p>
<button id="modelsave">Save model preference</button><pre id="modelout"></pre><pre id="ollamaout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
<section class="panel"><h2>OpenCode agent readiness</h2><p>Installation checks do not start an agent. The read-only pilot below connects to a separately running OpenCode server.</p>
<button id="opencodecheck">Check OpenCode</button> <button id="providerpreview">Preview Ollama provider config</button>
<p><label><input id="deployapprove" type="checkbox"> I approve creating an isolated OpenCode configuration in .smelter only.</label></p>
<button id="providerdeploy">Deploy isolated config (create only)</button> <button id="providervalidate">Validate staged config</button>
<pre id="validateout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre>
<h3>Local OpenCode server · read-only pilot</h3><p>Connects to an existing server on 127.0.0.1:4096. The expected workspace is the sibling V2 directory. This is an OpenCode session permission policy, not an OS sandbox.</p>
<button id="opencodeServerCheck">Check OpenCode server</button><pre id="opencodeServerStatus" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre>
<label>Verified local model <select id="opencodeAgentModel" aria-label="OpenCode local model"></select></label>
<label style="display:block"><input id="opencodeAgentApprove" type="checkbox"> Allow one read-only OpenCode session in the V2 workspace. Editing, shell commands, delegation and external tools are denied.</label>
<p>Configure a reviewed OpenCode image in Confined execution, check the managed server, then approve one read-only task. The existing unrestricted host server is not used. Skills, attachments and MCP grants are not forwarded.</p>
<pre id="deployout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre><pre id="providerout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre><pre id="opencodeout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
<section id="bootstrap" class="panel" hidden><h2 id="startupHeading">SMELTER startup</h2><div id="databaseSetup"><p>Choose an absolute directory for persistent SQLite storage. Existing JSON configuration files remain untouched.</p><input id="dbdirectory" placeholder="D:\SMELTER-Data"><button id="dbselect">Initialize database</button></div><div id="authRecovery" hidden><p>This page is not authorized for the running dashboard. Use the current launch URL printed in its terminal. Restarting the server changes the token; database initialization will not fix authorization.</p><label>Current launch URL or token<input id="sessionToken" type="password" autocomplete="off" spellcheck="false" aria-label="Current launch URL or token"></label><button id="sessionReconnect">Reconnect session</button></div><button id="dbretry">Retry checks</button><pre id="dbstatus" style="white-space:pre-wrap"></pre></section>
<script src="/assets/session-auth.js"></script><script src="/assets/mcp-ui.js"></script><script src="/assets/turntable.js"></script><script src="/assets/model-animations.js"></script><script src="/assets/model-preview.js"></script><script src="/assets/chat-renderer.js"></script><script src="/assets/file-activity.js"></script><script src="/assets/opencode-agent-ui.js"></script><script src="/assets/skills-ui.js"></script><script src="/assets/attachments-ui.js"></script><script src="/assets/settings-ui.js"></script><script src="/assets/access-ui.js"></script><script src="/assets/operations-ui.js"></script><script src="/assets/dashboard-shell.js"></script></main></html>"""

def handler(token: str):
    from dashboard_api import ApiRoutes,Context
    class Handler(ApiRoutes,BaseHTTPRequestHandler):
        app=Context(globals())
        def handle(self):
            try:
                super().handle()
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                self.close_connection = True
        def reply(self, status, data, content_type="application/json"):
            body = data if isinstance(data, bytes) else data.encode() if isinstance(data, str) else json.dumps(data).encode()
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'unsafe-inline'; connect-src 'self' blob: data:; img-src 'self' blob: data:; worker-src 'self' blob:")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                self.close_connection = True
        def authorized(self):
            origin = self.headers.get("Origin")
            expected = "http://127.0.0.1:" + str(self.server.server_port)
            supplied = self.headers.get("X-Smelter-Token", "")
            return supplied.isascii() and secrets.compare_digest(supplied, token) and (not origin or origin == expected)
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
