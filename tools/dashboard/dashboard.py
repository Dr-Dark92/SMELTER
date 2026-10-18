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

STATE = ROOT / ".smelter" / "extensions.json"
STATE_LOCK = threading.Lock()
REPORTS = ROOT / ".smelter" / "reports"
MODEL_PREFS = ROOT / ".smelter" / "model_preferences.json"
HTML = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SMELTER · Dashboard</title><style>
body{margin:0;background:#0b111d;color:#e7edfa;font:15px system-ui}main{max-width:none;margin:0;padding:0;min-height:100vh;display:flex;flex-direction:column}#shell{display:grid;grid-template-columns:245px minmax(0,1fr) 315px;gap:12px;flex:1;padding:12px;min-height:0}#leftbar,#workspace,#rightbar{background:#111b2b;border:1px solid #30445e;border-radius:12px;padding:15px;min-width:0}#workspace{display:flex;flex-direction:column}#rightbar{max-height:calc(100vh - 125px);overflow:auto}#rightbar .panel{padding:12px}#leftbar button,#rightbar .navbtn{width:100%;margin:4px 0;text-align:left}#chatlog{flex:1;min-height:180px;color:#aabbd4;overflow:auto}#composer{display:flex;gap:8px}#chatinput{flex:1;min-width:0;padding:12px;background:#0b111d;color:#e7edfa;border:1px solid #30445e;border-radius:8px}#bootstrap{margin:24px auto;max-width:640px;width:calc(100% - 48px)}#bootstrap input{width:100%;box-sizing:border-box;background:#0b111d;color:#e7edfa;border:1px solid #30445e;border-radius:8px;padding:12px}#sysfooter{padding:12px 20px;border-top:1px solid #30445e;color:#aabbd4;display:flex;gap:24px;flex-wrap:wrap;font-size:12px}#rightbar .panel{display:none}#rightbar .panel.active{display:block}.navbtn.active{background:#244578}#shell h2{font-size:17px}@media(max-width:850px){#shell{grid-template-columns:1fr}#leftbar,#rightbar{max-height:none}#workspace{min-height:360px}}
h1{font-size:32px}p{color:#aabbd4}.panel{background:#151f31;border:1px solid #30445e;border-radius:14px;padding:22px;margin:16px 0}
button{background:#346de0;color:white;border:0;border-radius:7px;padding:10px 15px;cursor:pointer}button:disabled{opacity:.4}
.ext{display:flex;justify-content:space-between;align-items:center;gap:15px;border-top:1px solid #30445e;padding:17px 0}
small{color:#aabbd4}#error{color:#ff9e9e}
</style><main><h1>⚒ SMELTER</h1><p>V1.6.0 · Workspace shell · AI chat and statistics pending</p>
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
<script>
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
  if(db.ready){boot.hidden=true;shell.hidden=false;footer.hidden=false;refresh();loadWorkflows()}
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
            if route == "/api/startup":
                try:
                    db = inspect_database(ROOT)
                    return self.reply(200, {**db, "inspection": "SQLite schema and integrity checked", "services": {"dashboard": "running", "ollama": "not_required_for_database_startup", "opencode": "not_started"}})
                except (ValueError, OSError, json.JSONDecodeError) as e:
                    return self.reply(400, {"error": str(e)})
            if route == "/api/opencode/validate":
                try:
                    with STATE_LOCK:
                        current_state = load_state(STATE)
                        preferences = load_preferences(MODEL_PREFS)
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
            if route not in ("/api/extensions", "/api/workflows/plan", "/api/archive/inspect", "/api/media/inspect", "/api/blender/inspect", "/api/ollama/preferences", "/api/opencode/deploy", "/api/database/select"):
                return self.reply(404, {"error": "Not found"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 2048:
                    raise ValueError("Invalid request size")
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("Invalid request")
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
                        preferences = configure_model(MODEL_PREFS, data.get("role"), data.get("model"), discovery)
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
                    save_state(STATE, state)
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
