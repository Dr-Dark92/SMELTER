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

STATE = ROOT / ".smelter" / "extensions.json"
STATE_LOCK = threading.Lock()
REPORTS = ROOT / ".smelter" / "reports"
MODEL_PREFS = ROOT / ".smelter" / "model_preferences.json"
HTML = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SMELTER · Dashboard</title><style>
body{margin:0;background:#0b111d;color:#e7edfa;font:15px system-ui}main{max-width:980px;margin:35px auto;padding:20px}
h1{font-size:32px}p{color:#aabbd4}.panel{background:#151f31;border:1px solid #30445e;border-radius:14px;padding:22px;margin:16px 0}
button{background:#346de0;color:white;border:0;border-radius:7px;padding:10px 15px;cursor:pointer}button:disabled{opacity:.4}
.ext{display:flex;justify-content:space-between;align-items:center;gap:15px;border-top:1px solid #30445e;padding:17px 0}
small{color:#aabbd4}#error{color:#ff9e9e}
</style><main><h1>⚒ SMELTER</h1><p>Vanilla V1.5.2 · OpenCode detection · no AI required</p>
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
<button id="opencodecheck">Check OpenCode</button><pre id="opencodeout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
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
el('refresh').onclick=refresh;refresh();loadWorkflows();
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
            if route not in ("/api/extensions", "/api/workflows/plan", "/api/archive/inspect", "/api/media/inspect", "/api/blender/inspect", "/api/ollama/preferences"):
                return self.reply(404, {"error": "Not found"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 2048:
                    raise ValueError("Invalid request size")
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("Invalid request")
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
