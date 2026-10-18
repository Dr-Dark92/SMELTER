#!/usr/bin/env python3
"""SMELTER V1 CLI-launched localhost web setup; stdlib only."""
import argparse
import json
import secrets
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from profiles import catalog, resolve
from install_actions import build_actions

ROOT = Path(__file__).resolve().parents[2]
REQ = ROOT / "requirements.txt"
SCANNER = ROOT / "tools/setup/check_requirements.py"
TESTS = ROOT / "tools/setup"
HTML = r'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SMELTER V1 Setup</title><style>
body{font:15px system-ui;background:#0b101a;color:#e8effb;margin:0}main{max-width:850px;margin:35px auto;padding:20px}h1{font-size:30px}.panel{background:#151e2e;border:1px solid #35445c;border-radius:12px;padding:22px;margin:18px 0}button{background:#356fe0;color:white;border:0;border-radius:8px;padding:11px 17px;cursor:pointer}button:disabled{opacity:.4}pre{background:#080d16;border:1px solid #35445c;border-radius:8px;padding:14px;white-space:pre-wrap;overflow-wrap:anywhere;max-height:360px;overflow:auto}.muted{color:#a4b5cd}label{display:block;margin:10px 0}
</style><main><h1>⚒ SMELTER Vanilla V1</h1><p class="muted">Local setup wizard · no optional tool installs</p>
<section class="panel"><h2>1 · Check requirements</h2><button id="scan">Scan system</button><pre id="scanout">Not scanned</pre></section>
<section class="panel"><h2>2 · Review installation plan</h2><label>☑ Vanilla core (required)</label><label>☐ Blender (deferred)</label><label>☐ FFmpeg (deferred)</label><label>☐ 7-Zip (deferred)</label><button id="plan">Review plan</button><pre id="planout">Not reviewed</pre></section>
<section class="panel"><h2>3 · Optional profile dependency preview</h2><p class="muted">Preview only; no additional software will be installed.</p><div id="profiles"></div><button id="preview">Preview selected dependencies</button><pre id="previewout">Select profiles to inspect requirements</pre></section>
<section class="panel"><h2>4 · Optional dependency installation</h2><p class="muted">Windows winget only. Review exact package IDs and approve separately. May request elevation or interactive terms.</p><div id="installchoices"></div><button id="queue">Review install queue</button><pre id="queueout">No install queue</pre><label><input id="installapprove" type="checkbox"> I approve these exact packages and their installation</label><button id="install" disabled>Install approved packages</button><pre id="installlog">No dependency installation run</pre></section>
<section class="panel"><h2>5 · Approve Vanilla setup</h2><label><input id="approve" type="checkbox"> I approve the displayed plan</label><button id="apply" disabled>Run setup</button><p id="status" class="muted">Idle</p><pre id="log">No installation run</pre></section>
<script>
const token=new URLSearchParams(location.hash.slice(1)).get('token');const el=id=>document.getElementById(id);let planId=null,installId=null,preview=null;
async function api(path,method='GET',body){const r=await fetch(path,{method,headers:{'X-Smelter-Token':token||'','Content-Type':'application/json'},body:body?JSON.stringify(body):undefined,cache:'no-store'});const d=await r.json();if(!r.ok)throw Error(d.error||r.status);return d}
function error(e){el('status').textContent='Error: '+e.message}
async function loadProfiles(){try{const p=await api('/api/profiles');el('profiles').innerHTML=p.profiles.filter(x=>x.id!=='vanilla').map(x=>'<label><input type="checkbox" class="profile" value="'+x.id+'"> '+x.label+' — '+x.description+'</label>').join('')}catch(e){error(e)}}loadProfiles();
el('preview').onclick=async()=>{try{const selected=[...document.querySelectorAll('.profile:checked')].map(x=>x.value);const p=await api('/api/preview','POST',{profiles:selected});preview=p;installId=null;el('install').disabled=true;el('installapprove').checked=false;el('previewout').textContent=JSON.stringify(p,null,2);el('installchoices').innerHTML=p.dependencies.filter(x=>x.status!=='installed').map(x=>'<label><input type="checkbox" class="dependency" value="'+x.name+'"> '+x.name+' ('+x.status+')</label>').join('')||'No missing dependencies'}catch(e){error(e)}};
el('queue').onclick=async()=>{try{if(!preview)throw Error('Preview profiles first');const names=[...document.querySelectorAll('.dependency:checked')].map(x=>x.value);const p=await api('/api/install-plan','POST',{profiles:preview.profiles,names});installId=p.install_id;el('queueout').textContent=JSON.stringify(p,null,2);el('installapprove').checked=false;el('install').disabled=true}catch(e){error(e)}};
el('installapprove').onchange=()=>el('install').disabled=!el('installapprove').checked||!installId;
el('install').onclick=async()=>{try{el('install').disabled=true;await api('/api/install-apply','POST',{install_id:installId,approved:true});installPoll()}catch(e){error(e)}};
async function installPoll(){try{const p=await api('/api/install-progress');el('installlog').textContent=p.status+'\n'+p.lines.join('\n');if(p.status==='running')setTimeout(installPoll,750);else{installId=null;el('installapprove').checked=false}}catch(e){error(e)}}
el('scan').onclick=async()=>{try{el('scanout').textContent=JSON.stringify(await api('/api/scan'),null,2)}catch(e){error(e)}};
el('plan').onclick=async()=>{try{const p=await api('/api/plan');planId=p.plan_id;el('planout').textContent=JSON.stringify(p,null,2);el('approve').checked=false;el('apply').disabled=true}catch(e){error(e)}};
el('approve').onchange=()=>el('apply').disabled=!el('approve').checked||!planId;
el('apply').onclick=async()=>{try{el('apply').disabled=true;await api('/api/apply','POST',{plan_id:planId,approved:true});poll()}catch(e){error(e)}};
async function poll(){try{const p=await api('/api/progress');el('status').textContent=p.status;el('log').textContent=p.lines.join('\n');if(p.status==='running')setTimeout(poll,750);else{planId=null;el('approve').checked=false}}catch(e){error(e)}}
</script></main></html>'''

def validate_plan():
    if sys.version_info < (3, 12):
        raise ValueError("Python 3.12+ required")
    if not REQ.is_file() or not SCANNER.is_file():
        raise ValueError("SMELTER requirements or scanner missing")
    if any(line.strip() and not line.lstrip().startswith("#") for line in REQ.read_text(encoding="utf-8").splitlines()):
        raise ValueError("Vanilla setup refuses third-party Python requirements until reviewed")
    return {"profile": "vanilla", "steps": ["Create local .venv if absent", "Run system scanner", "Run setup unit tests"],
            "optional_installations": [], "downloads": False, "system_package_changes": False}

class DependencyInstaller:
    def __init__(self):
        self.lock = threading.Lock()
        self.status = "idle"
        self.lines = []
        self.install_id = None
        self.actions = []

    def plan(self, profiles, names):
        from check_requirements import scan
        preview = resolve(profiles, scan())
        plan = build_actions(preview, names)
        with self.lock:
            if self.status == "running":
                raise ValueError("Installation already running")
            self.install_id = secrets.token_urlsafe(24)
            self.actions = plan["actions"]
            return {"install_id": self.install_id, **plan}

    def apply(self, install_id, approved):
        with self.lock:
            if self.status == "running":
                raise ValueError("Installation already running")
            if not approved or not self.install_id or install_id != self.install_id:
                raise ValueError("Exact installation plan approval required")
            if not self.actions:
                raise ValueError("No packages selected")
            self.install_id = None
            actions = list(self.actions)
            self.actions = []
            self.lines = []
            self.status = "running"
        threading.Thread(target=self.run, args=(actions,), daemon=True).start()

    def run(self, actions):
        try:
            for action in actions:
                command = action["command"]
                self.log("Installing " + action["name"] + " (" + action["package_id"] + ")")
                proc = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                        text=True, errors="replace")
                for line in proc.stdout:
                    self.log(line.rstrip())
                if proc.wait() != 0:
                    raise RuntimeError("winget failed for " + action["name"])
                from check_requirements import scan
                observed = {t["name"]: t for t in scan()["tools"]}
                if observed.get(action["name"], {}).get("status") != "installed":
                    raise RuntimeError(action["name"] + " not verified; restart shell or check PATH")
                self.log("Verified: " + action["name"])
            status = "completed"
        except Exception as exc:
            self.log("ERROR: " + str(exc))
            status = "failed"
        with self.lock:
            self.status = status

    def log(self, message):
        with self.lock:
            self.lines.append(str(message)[:400])
            self.lines = self.lines[-400:]

    def progress(self):
        with self.lock:
            return {"status": self.status, "lines": list(self.lines)}


class Engine:
    def __init__(self):
        self.lock = threading.Lock()
        self.status = "idle"
        self.lines = []
        self.plan_id = None

    def plan(self):
        details = validate_plan()
        with self.lock:
            if self.status == "running":
                raise ValueError("Setup already running")
            self.plan_id = secrets.token_urlsafe(20)
            return {"plan_id": self.plan_id, **details}

    def apply(self, plan_id, approved):
        with self.lock:
            if self.status == "running":
                raise ValueError("Setup already running")
            if not approved or not self.plan_id or self.plan_id != plan_id:
                raise ValueError("Explicit approval of current plan required")
            validate_plan()
            self.plan_id = None
            self.status = "running"
            self.lines = []
        threading.Thread(target=self.run, daemon=True).start()

    def log(self, line):
        with self.lock:
            self.lines.append(line[:400])
            self.lines = self.lines[-400:]

    def execute(self, argv):
        self.log("Running: " + Path(argv[0]).name + " " + " ".join(Path(a).name if a.startswith(str(ROOT)) else a for a in argv[1:]))
        proc = subprocess.Popen(argv, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, errors="replace")
        for line in proc.stdout:
            self.log(line.rstrip())
        if proc.wait():
            raise RuntimeError("Step failed with exit code " + str(proc.returncode))

    def run(self):
        try:
            venv = ROOT / ".venv"
            python = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
            if not python.is_file():
                self.execute([sys.executable, "-m", "venv", str(venv)])
            if not python.is_file():
                raise RuntimeError("Virtual environment Python missing")
            self.execute([str(python), str(SCANNER)])
            self.execute([str(python), "-m", "unittest", "discover", "-s", str(TESTS), "-p", "test_*.py", "-v"])
            self.log("Vanilla setup verified; no optional tools installed.")
            status = "completed"
        except Exception as exc:
            self.log("ERROR: " + str(exc))
            status = "failed"
        with self.lock:
            self.status = status

    def progress(self):
        with self.lock:
            return {"status": self.status, "lines": list(self.lines)}

def handler_factory(engine, token, port, installer=None):
    installer = installer or DependencyInstaller()
    class Handler(BaseHTTPRequestHandler):
        def reply(self, code, obj):
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def auth(self):
            origin = self.headers.get("Origin")
            if origin and origin != "http://127.0.0.1:" + str(port):
                self.reply(403, {"error": "Origin mismatch"})
                return False
            if self.headers.get("X-Smelter-Token") != token:
                self.reply(403, {"error": "Invalid setup token"})
                return False
            return True

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/":
                data = HTML.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
            if not self.auth():
                return
            try:
                if path == "/api/profiles":
                    self.reply(200, {"profiles": catalog()})
                elif path == "/api/scan":
                    from check_requirements import scan
                    self.reply(200, scan())
                elif path == "/api/plan":
                    self.reply(200, engine.plan())
                elif path == "/api/install-progress":
                    self.reply(200, installer.progress())
                elif path == "/api/progress":
                    self.reply(200, engine.progress())
                else:
                    self.reply(404, {"error": "Not found"})
            except ValueError as exc:
                self.reply(400, {"error": str(exc)})

        def do_POST(self):
            if not self.auth():
                return
            if urlsplit(self.path).path not in ("/api/apply", "/api/preview", "/api/install-plan", "/api/install-apply"):
                self.reply(404, {"error": "Not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 2048:
                    raise ValueError("Invalid request size")
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ValueError("Expected JSON object")
                if urlsplit(self.path).path == "/api/install-plan":
                    self.reply(200, installer.plan(body.get("profiles"), body.get("names")))
                elif urlsplit(self.path).path == "/api/install-apply":
                    installer.apply(body.get("install_id"), body.get("approved") is True)
                    self.reply(202, {"status": "running"})
                elif urlsplit(self.path).path == "/api/preview":
                    from check_requirements import scan
                    self.reply(200, resolve(body.get("profiles", []), scan()))
                else:
                    engine.apply(body.get("plan_id"), body.get("approved") is True)
                    self.reply(202, {"status": "running"})
            except (ValueError, TypeError) as exc:
                self.reply(400, {"error": str(exc)})

        def log_message(self, *args):
            pass
    return Handler

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if sys.version_info < (3, 12):
        parser.error("Python 3.12+ required")
    if not 0 <= args.port <= 65535:
        parser.error("Invalid port")
    token = secrets.token_urlsafe(32)
    # The server is loopback-only; port zero is supported for test automation.
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_factory(Engine(), token, args.port))
    port = server.server_address[1]
    print("SMELTER setup: http://127.0.0.1:" + str(port) + "/ (Ctrl+C to stop)", flush=True)
    if not args.no_browser:
        webbrowser.open("http://127.0.0.1:" + str(port) + "/#token=" + token)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
