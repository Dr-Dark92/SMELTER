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

STATE = ROOT / ".smelter" / "extensions.json"
STATE_LOCK = threading.Lock()
REPORTS = ROOT / ".smelter" / "reports"
HTML = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SMELTER · Dashboard</title><style>
body{margin:0;background:#0b111d;color:#e7edfa;font:15px system-ui}main{max-width:980px;margin:35px auto;padding:20px}
h1{font-size:32px}p{color:#aabbd4}.panel{background:#151f31;border:1px solid #30445e;border-radius:14px;padding:22px;margin:16px 0}
button{background:#346de0;color:white;border:0;border-radius:7px;padding:10px 15px;cursor:pointer}button:disabled{opacity:.4}
.ext{display:flex;justify-content:space-between;align-items:center;gap:15px;border-top:1px solid #30445e;padding:17px 0}
small{color:#aabbd4}#error{color:#ff9e9e}
</style><main><h1>⚒ SMELTER</h1><p>Vanilla V1.4.1 · Workflow inputs &amp; saved reports · no AI required</p>
<section class="panel"><h2>Extensions</h2><p>Extensions are disabled by default. Activation only records configuration; execution permissions remain ungranted.</p>
<button id="refresh">Rescan tools</button><p id="error"></p><div id="items">Loading…</div></section>
<section class="panel"><h2>Workflow planner</h2><p>Preview ordered steps and dependency checks. Dry run only — no tools execute.</p>
<select id="workflow" style="padding:10px;background:#0b111d;color:#e7edfa;border:1px solid #30445e;border-radius:7px"></select>
<p><label for="inputs">Optional absolute input paths (one per line; maximum 16)</label></p>
<textarea id="inputs" rows="3" style="width:100%;box-sizing:border-box;background:#0b111d;color:#e7edfa;border:1px solid #30445e;border-radius:7px;padding:10px" placeholder="C:\\path\\to\\asset"></textarea>
<p><button id="plan">Preview and save dry run</button> <button id="history">Refresh report history</button></p>
<pre id="historyout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre><pre id="planout" style="white-space:pre-wrap;overflow-wrap:anywhere"></pre></section>
<script>
const token=new URLSearchParams(location.hash.slice(1)).get('token');
const el=id=>document.getElementById(id);
async function api(path,method='GET',data){const r=await fetch(path,{method,headers:{'X-Smelter-Token':token||'','Content-Type':'application/json'},body:data?JSON.stringify(data):undefined,cache:'no-store'});const v=await r.json();if(!r.ok)throw Error(v.error||r.status);return v}
async function refresh(){try{el('error').textContent='';const data=await api('/api/extensions');const list=el('items');list.replaceChildren();for(const x of data.extensions){const row=document.createElement('div');row.className='ext';const info=document.createElement('div');const title=document.createElement('strong');title.textContent=x.label;const meta=document.createElement('p');meta.textContent=x.description+' · '+x.status+' · Permissions: '+x.permissions.join(', ');title.textContent=x.label+' · '+x.health;meta.textContent=x.description+' · Tool: '+x.status+' · Declared permissions: '+x.permissions.join(', ')+' · Granted: no';info.append(title,meta);const b=document.createElement('button');b.textContent=x.enabled?'Disable':'Enable';b.disabled=!x.enabled&&x.status!=='installed';b.onclick=async()=>{try{await api('/api/extensions','POST',{id:x.id,enabled:!x.enabled});await refresh()}catch(e){el('error').textContent=e.message}};row.append(info,b);list.append(row)}}catch(e){el('error').textContent=e.message}}
async function loadWorkflows(){try{const data=await api('/api/workflows');for(const w of data.workflows){const opt=document.createElement('option');opt.value=w.id;opt.textContent=w.label+' — '+w.description;el('workflow').append(opt)}}catch(e){el('error').textContent=e.message}}
async function history(){try{const data=await api('/api/workflows/reports');el('historyout').textContent='Recent reports:\\n'+data.reports.map(r=>r.timestamp_utc+' | '+r.workflow_id+' | '+r.status+' | '+r.run_id).join('\\n')}catch(e){el('historyout').textContent=e.message}}
el('plan').onclick=async()=>{try{const paths=el('inputs').value.split(/\\r?\\n/).map(x=>x.trim()).filter(Boolean);const data=await api('/api/workflows/plan','POST',{workflow_id:el('workflow').value,inputs:paths});el('planout').textContent='Status: '+data.status+' | Mode: '+data.mode+' | Executed: '+data.executed+'\\n'+data.steps.map(s=>s.label+': '+s.status+(s.reason?' ('+s.reason+')':'')).join('\\n')+'\\nInputs: '+data.inputs.map(x=>x.path+' ('+x.status+')').join(', ')+'\\nOutput validation: '+data.output_validation.status;await history()}catch(e){el('planout').textContent=e.message}};
el('history').onclick=history;history();
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
            if route not in ("/api/extensions", "/api/workflows/plan"):
                return self.reply(404, {"error": "Not found"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 2048:
                    raise ValueError("Invalid request size")
                data = json.loads(self.rfile.read(length))
                if not isinstance(data, dict):
                    raise ValueError("Invalid request")
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
