#!/usr/bin/env python3
"""SMELTER local-only web console MVP. Standard library; no external dependencies.

Read-only endpoints. Never accepts shell commands, git URLs, or installs skills.
"""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import urllib.parse
import urllib.request

HOST="127.0.0.1"
PORT=8765
ROOT=Path(__file__).resolve().parents[2]
HTML=r"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>SMELTER Console</title>
<style>body{background:#0c111b;color:#e8eef8;font:15px system-ui;margin:0}header{padding:22px 32px;background:#151d2a;border-bottom:1px solid #303b4b}main{max-width:1100px;margin:30px auto;padding:0 18px}h1{margin:0}small{color:#9baec6}nav{display:flex;gap:10px;flex-wrap:wrap;margin:22px 0}button{background:#24334a;color:#fff;border:1px solid #465b76;border-radius:8px;padding:11px 16px;cursor:pointer}button.active{background:#315da0}.panel{background:#151e2c;border:1px solid #303f55;border-radius:12px;padding:22px;margin:12px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}.value{font-weight:650;font-size:20px}pre{white-space:pre-wrap;overflow-wrap:anywhere;color:#b6d6fb}a{color:#93c5fd}.muted{color:#a2b3c8}</style>
<header><h1>⚒ SMELTER <small>Local Development Console · MVP</small></h1><small>Windows localhost only · Read-only prototype</small></header>
<main><nav id="nav"></nav><div id="content" aria-live="polite"></div></main>
<script>
const pages=['Overview','GitHub','Skills & Tools','OpenCode','Research'];
const nav=document.querySelector('#nav'),content=document.querySelector('#content');
function safe(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
async function data(url){try{const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error(r.status);return await r.json()}catch(e){return {error:String(e)}}}
function panel(title,body){return '<section class="panel"><h2>'+safe(title)+'</h2>'+body+'</section>'}
async function render(page){
 nav.innerHTML=pages.map(x=>'<button class="'+(x===page?'active':'')+'" data-page="'+safe(x)+'">'+safe(x)+'</button>').join('');
 content.innerHTML=panel(page,'<p class="muted">Loading local status…</p>');
 if(page==='Overview'){const x=await data('/api/status');content.innerHTML=panel('System status','<div class="grid">'+Object.entries(x).map(([k,v])=>'<div class="panel"><small>'+safe(k)+'</small><div class="value">'+safe(typeof v==='object'?JSON.stringify(v):v)+'</div></div>').join('')+'</div>')}
 else if(page==='GitHub'){const x=await data('/api/github');content.innerHTML=panel('GitHub repository (read-only)','<pre>'+safe(JSON.stringify(x,null,2))+'</pre><p class="muted">Repository connection, review, and approval controls will be added later.</p>')}
 else if(page==='Skills & Tools'){const x=await data('/api/skills');content.innerHTML=panel('Local skills and tools (discovery only)','<pre>'+safe(JSON.stringify(x,null,2))+'</pre><p class="muted">Remote skill installation is disabled in this MVP.</p>')}
 else if(page==='OpenCode')content.innerHTML=panel('OpenCode workspace','<p>Planned: connect to a separately launched local OpenCode web session.</p><p class="muted">No OpenCode process is started or exposed by this prototype.</p>');
 else content.innerHTML=panel('Internet research','<p>Planned: configured search provider, citations, and approved documentation retrieval.</p><p class="muted">No unrestricted web requests from the console.</p>');
}
nav.addEventListener('click',e=>{const b=e.target.closest('button[data-page]');if(b)render(b.dataset.page)});
render('Overview');
</script></html>"""
def run(args,timeout=5):
    try:
        p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=timeout,check=False,
                         creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        return {"available":p.returncode==0,"detail":(p.stdout if p.returncode==0 else p.stderr).strip()[:250]}
    except (OSError,subprocess.TimeoutExpired):return {"available":False,"detail":"Not detected"}
def ollama():
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags",timeout=2) as r:
            d=json.load(r)
        return {"available":True,"models":[m.get("name","") for m in d.get("models",[])][:20]}
    except (OSError,ValueError):return {"available":False}
def skills():
    locations=[ROOT/"skills",ROOT/".opencode"/"skills",ROOT/"tools"/"skills"]
    names=[]
    for folder in locations:
        if folder.is_dir():
            for path in folder.glob("*/SKILL.md"):
                names.append(str(path.relative_to(ROOT)).replace("\\","/"))
    return {"count":len(names),"skills":sorted(names)[:100],"remote_installation":"disabled"}
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path=urllib.parse.urlsplit(self.path).path
        if path=="/":
            body=HTML.encode("utf-8")
            kind="text/html; charset=utf-8"
        elif path in ("/api/status","/api/github","/api/skills"):
            if path=="/api/status":
                obj={"mode":"localhost only","root":str(ROOT),"ollama":ollama(),"docker":run(["docker","info","--format","{{.ServerVersion}}"]),"opencode":run(["opencode","--version"])}
            elif path=="/api/github":
                obj={"repository":"Dr-Dark92/SMELTER","branch":run(["git","branch","--show-current"]),"remote":run(["git","remote","get-url","origin"]),"auth":run(["gh","auth","status"])}
                # Do not expose gh auth status details, which may include account identifiers.
                obj["auth"]={"available":obj["auth"]["available"]}
            else:obj=skills()
            body=json.dumps(obj).encode("utf-8")
            kind="application/json; charset=utf-8"
        else:
            self.send_error(404);return
        self.send_response(200)
        self.send_header("Content-Type",kind)
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Content-Security-Policy","default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_POST(self):self.send_error(405)
    def do_PUT(self):self.send_error(405)
    def do_DELETE(self):self.send_error(405)
def main():
    server=ThreadingHTTPServer((HOST,PORT),Handler)
    print(f"SMELTER console: http://{HOST}:{PORT} (Ctrl+C to stop)",flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=="__main__":main()
