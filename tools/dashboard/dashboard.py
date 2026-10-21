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
.file-activity{align-self:stretch;min-width:0;padding:16px;border:1px solid #37506c;border-radius:12px;background:#0d1623}.file-activity h3{margin:0 0 8px;font-size:16px}.file-activity-note{font-size:12px;color:#aabbd4}.file-activity-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:12px}.file-work-card{min-width:0;border:1px solid #37506c;border-radius:10px;padding:14px;background:#121e2e}.file-work-card h4{font:12px/1.5 ui-monospace,monospace;overflow-wrap:anywhere;margin:0 0 8px}.file-work-status{display:block;font-size:11px;color:#b6d5e0;margin-bottom:12px}.file-work-card[data-state=saved]{border-color:#69c6a3}.file-work-card[data-state=error]{border-color:#ee9b9b}.file-work-card summary{cursor:pointer;font-size:12px;padding:8px 0;color:#bdd2eb}.file-original-code,.file-work-card details pre{max-height:320px;overflow:auto;white-space:pre;font:11px/1.6 ui-monospace,monospace;background:#09121f;padding:12px;tab-size:4}.file-code-label{display:block;font-size:12px;margin-top:12px}.file-code-label span{display:block;margin-bottom:7px}.file-updated-code{box-sizing:border-box;width:100%;min-height:160px;max-height:500px;resize:vertical;overflow:auto;background:#09121f;color:#d8e8fa;border:1px solid #49607d;border-radius:6px;padding:12px;font:11px/1.6 ui-monospace,monospace;tab-size:4}.file-updated-code:focus-visible,.file-work-card summary:focus-visible{outline:2px solid #9bc7ff;outline-offset:3px}.file-work-error{color:#ffadad;font-size:12px;overflow-wrap:anywhere}

#skillsOverview{overflow-y:auto;min-height:0;flex:1;padding:4px 8px}#skillsOverview h2{font-size:24px}#skillNotice{background:#25364b;border-bottom:1px solid #708dae;padding:10px 18px;flex-shrink:0;font-size:13px}#skillNotice button{margin-left:8px;padding:6px 10px}
.skill-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;margin:14px 0}.skill-card{border:1px solid #37506c;background:#142237;border-radius:12px;padding:16px;min-width:0}.skill-card h3{margin-top:0;font-size:16px}.skill-card p{font-size:13px;overflow-wrap:anywhere}.skill-card small{overflow-wrap:anywhere}.skill-card button{margin:4px 6px 0 0;padding:8px 10px;font-size:12px}.skill-badge{color:#8fd8c2!important}.skill-search{padding:10px;width:min(100%,340px);box-sizing:border-box;background:#0b111d;color:#e7edfa;border:1px solid #49607d;border-radius:7px}.skill-restart{padding:12px;background:#223048;border-radius:8px}.skill-preview{border:1px solid #58718f;border-radius:10px;padding:16px;margin-top:16px}.skill-preview pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:400px;overflow:auto}
.runtime-field{display:block;margin:12px 0;font-size:13px}.runtime-field input[type=number]{box-sizing:border-box;width:100%;margin-top:5px;background:#0b111d;color:#e7edfa;border:1px solid #49607d;border-radius:5px;padding:8px}#runtimePanel p{font-size:12px;overflow-wrap:anywhere}#runtimePanel select{max-width:100%;margin-right:6px}
#chatSearch{box-sizing:border-box;width:100%;padding:10px;margin-top:10px;background:#0b111d;border:1px solid #49607d;border-radius:7px;color:#e7edfa}.history-count{font-size:11px;margin:10px 0}
.history-row{display:grid;grid-template-columns:minmax(0,1fr) 28px 28px;align-items:center;gap:3px;border:1px solid transparent;border-radius:9px;padding:4px;margin:5px 0}.history-row.selected{border-color:#5d8ec4;background:#1a3550}#leftbar .history-row .chat-open{min-width:0;width:100%;padding:9px 5px;background:transparent;margin:0}.history-title{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px}.chat-open small{display:block;font-size:10px;margin-top:5px;color:#aabbd4}#leftbar .history-row .chat-action{width:28px;height:30px;padding:3px;margin:0;text-align:center;background:#203249}
.chat-dialog{background:#132237;color:#e7edfa;border:1px solid #597a9d;border-radius:14px;width:min(420px,calc(100vw - 60px));padding:24px}.chat-dialog::backdrop{background:#030a14b8}.chat-dialog h2{font-size:20px;margin-top:0}.chat-dialog label{display:block;font-size:13px}.chat-dialog input{box-sizing:border-box;width:100%;margin-top:9px;padding:12px;border:1px solid #597a9d;background:#0b111d;color:#e7edfa;border-radius:7px;font:inherit}.dialog-actions{display:flex;justify-content:flex-end;gap:10px}.dialog-error{min-height:20px;color:#ffadad;font-size:13px}

.message-label{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}.copy-button{background:#263f59;color:#cde3fa;padding:5px 9px;font-size:11px;border:1px solid #47617b;white-space:nowrap}.formatted-message{white-space:normal}.formatted-message p{color:inherit;white-space:pre-wrap;margin:9px 0}.formatted-message h3,.formatted-message h4,.formatted-message h5,.formatted-message h6{color:#eff6ff;margin:16px 0 8px}.formatted-message ul,.formatted-message ol{padding-left:24px;margin:9px 0}.formatted-message li{margin:5px 0;white-space:pre-wrap}.formatted-message blockquote{border-left:3px solid #638bac;padding-left:12px;margin:10px 0;color:#b6cce3}.formatted-message :not(pre)>code{background:#0b1624;border-radius:4px;padding:2px 5px;font-size:.9em;overflow-wrap:anywhere}.code-block{border:1px solid #3b526d;border-radius:8px;overflow:hidden;margin:12px 0;background:#09121f;min-width:0}.code-toolbar{display:flex;align-items:center;justify-content:space-between;gap:12px;background:#1c2c40;padding:6px 10px;font:12px system-ui;color:#bcd2e7}.code-block pre{margin:0;padding:14px;overflow-x:auto;max-width:100%;white-space:pre;tab-size:4;font:12px/1.65 ui-monospace,monospace}.code-block pre code{background:none;padding:0;overflow-wrap:normal}.message-assistant{max-width:95%;width:fit-content}
.model-card{border:1px solid #526e8b;border-radius:10px;padding:14px;margin-top:12px;min-width:0}.model-card h3{margin:0 0 8px;font-size:16px}.model-card p{font-size:12px;overflow-wrap:anywhere}.model-card button{font-size:12px;padding:8px;margin:4px}.model-card pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:200px;overflow:auto;font-size:11px}.animation-panel{margin-top:14px;padding-top:12px;border-top:1px solid #526e8b}.animation-panel h4{margin:0 0 8px}.animation-panel select,.animation-panel input:not([type=range]){box-sizing:border-box;max-width:100%;width:100%;padding:9px;margin:5px 0;background:#0b111d;color:#e7edfa;border:1px solid #597a9d;border-radius:6px}.animation-panel input[type=range]{width:75%;vertical-align:middle}.model-stage{width:100%;min-width:0}.message:has(.model-card){width:95%;max-width:95%}

/* Unified settings surface and stable full-width composer. */
#shell{grid-template-columns:245px minmax(0,1fr)}
.workspace-toolbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;flex-shrink:0;margin-bottom:12px}
#taskAccessSummary{flex:1;font-size:12px;color:#b8cbe3;min-width:180px}
#composer{align-items:center;gap:8px}#chatinput{flex-basis:100%;width:100%;min-width:100%;min-height:88px}
.settings-screen{box-sizing:border-box;width:min(1100px,96vw);height:92dvh;max-width:none;max-height:none;padding:18px;border:1px solid #49607d;border-radius:12px;background:#0b111d;color:#e7edfa}
.settings-screen::backdrop{background:#000a}.settings-header{display:flex;justify-content:space-between;align-items:center;gap:12px}.settings-header h2{margin:0;font-size:21px}
.settings-screen #rightbar{height:auto;max-height:none;overflow:visible;border:0;padding:8px 0;background:transparent}.settings-screen .panel{max-width:none}
.settings-screen input:not([type=checkbox]),.settings-screen select,.settings-screen textarea{box-sizing:border-box;max-width:100%;padding:9px;border:1px solid #49607d;border-radius:6px;background:#0b111d;color:#e7edfa;font:inherit}
.access-location-list{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,340px),1fr));gap:12px}.access-location{min-width:0;border:1px solid #49607d;border-radius:8px;padding:14px}.access-location>label{display:block;margin:8px 0}.access-location>label input,.access-location textarea{display:block;width:100%;margin-top:5px}.access-flags{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0}
#taskAccessPanel #pythonTools{max-height:none;overflow:visible}#taskAccessPanel>p{max-width:85ch}
@media(max-width:850px){#leftbar{max-height:180px;min-height:0}#workspace{height:76dvh;min-height:460px;max-height:none;overflow:hidden}#chatlog{flex:1;min-height:0}#composer input[type=file]{max-width:150px}.settings-screen{padding:12px;width:98vw;height:96dvh}.workspace-toolbar button{font-size:12px;padding:8px}}
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
<script src="/assets/session-auth.js"></script><script src="/assets/mcp-ui.js"></script><script src="/assets/turntable.js"></script><script src="/assets/model-animations.js"></script><script src="/assets/model-preview.js"></script><script src="/assets/chat-renderer.js"></script><script src="/assets/file-activity.js"></script><script src="/assets/opencode-agent-ui.js"></script><script src="/assets/settings-ui.js"></script><script src="/assets/access-ui.js"></script><script src="/assets/operations-ui.js"></script><script src="/assets/dashboard-shell.js"></script></main></html>"""

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
