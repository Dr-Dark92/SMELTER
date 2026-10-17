#!/usr/bin/env python3
"""SMELTER local-only web console MVP. Standard library; no external dependencies.

Read-only endpoints. Never accepts shell commands, git URLs, or installs skills.
"""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import base64
import re
import socket
from pathlib import Path
import subprocess
import urllib.parse
import urllib.request

HOST="127.0.0.1"
PORT=8765
OPENCODE_PORT=4096
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
 else if(page==='GitHub'){const [x,r]=await Promise.all([data('/api/github'),data('/api/repos')]);content.innerHTML=panel('Current repository','<pre>'+safe(JSON.stringify(x,null,2))+'</pre>')+panel('Available GitHub repositories (read-only)','<p class="muted">Showing up to 30 repositories visible through your existing gh login. Nothing is cloned or connected automatically.</p>'+(r.error?'<pre>'+safe(r.error)+'</pre>':(r.repositories||[]).map(v=>'<div class="panel"><strong>'+safe(v.nameWithOwner)+'</strong> · '+safe(v.isPrivate?'Private':'Public')+'<p class="muted">'+safe(v.description||'No description')+'</p></div>').join('')||'<p>No repositories returned.</p>'))}
 else if(page==='Skills & Tools'){const [x,c]=await Promise.all([data('/api/skills'),data('/api/catalog')]);content.innerHTML=panel('Local skills and tools (discovery only)','<pre>'+safe(JSON.stringify(x,null,2))+'</pre>')+panel('Recommended capabilities','<p class="muted">Built-in suggestions only; no remote code is downloaded or executed.</p><input id="skill-filter" type="search" placeholder="Search Python, testing, web..." style="width:100%;padding:12px;background:#0c111b;color:white;border:1px solid #465b76;border-radius:8px;box-sizing:border-box">'+
 '<div id="skill-results"></div>')+panel('Inspect GitHub SKILL.md','<p class="muted">Enter a GitHub repository or a blob URL to SKILL.md. Preview only; no installation or execution.</p><input id="skill-url" type="url" placeholder="https://github.com/owner/repo/blob/main/skills/example/SKILL.md" style="width:100%;padding:12px;background:#0c111b;color:white;border:1px solid #465b76;border-radius:8px;box-sizing:border-box"><p><button id="inspect-skill">Inspect skill</button></p><pre id="inspection-result"></pre>');const draw=()=>{const q=document.querySelector('#skill-filter').value.toLowerCase();document.querySelector('#skill-results').innerHTML=(c.capabilities||[]).filter(v=>JSON.stringify(v).toLowerCase().includes(q)).map(v=>'<div class="panel"><strong>'+safe(v.name)+'</strong> <small>('+safe(v.kind)+')</small><p>'+safe(v.description)+'</p><small>'+safe(v.installation)+'</small></div>').join('')||'<p>No matching capabilities.</p>'};document.querySelector('#skill-filter').addEventListener('input',draw);draw();document.querySelector('#inspect-skill').addEventListener('click',async()=>{const u=document.querySelector('#skill-url').value;const el=document.querySelector('#inspection-result');el.textContent='Inspecting...';const result=await data('/api/inspect-skill?url='+encodeURIComponent(u));el.textContent=JSON.stringify(result,null,2)})}
 else if(page==='OpenCode'){const x=await data('/api/opencode');content.innerHTML=panel('OpenCode workspace',
 '<p><strong>CLI installed:</strong> '+safe(x.cli?.available?'Yes':'No')+'</p>'+
 '<p><strong>Local port '+safe(x.port)+':</strong> '+safe(x.listener?'Listening (service not verified)':'Not listening')+'</p>'+
 '<p><a href="'+safe(x.url)+'" target="_blank" rel="noopener noreferrer">Open local OpenCode interface ↗</a></p>'+
 '<p>Start OpenCode separately in another PowerShell window:</p><pre>'+safe(x.start_command)+'</pre>'+
 '<p class="muted">Set a strong OpenCode password. SMELTER never starts OpenCode or exposes it to LAN.</p>');}
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
def opencode_status():
    try:
        with socket.create_connection((HOST,OPENCODE_PORT),timeout=0.5):
            listening=True
    except OSError:
        listening=False
    return {"cli":run(["opencode","--version"]),"listener":listening,"port":OPENCODE_PORT,
            "url":f"http://{HOST}:{OPENCODE_PORT}",
            "start_command":"$env:OPENCODE_SERVER_PASSWORD = Read-Host 'Set OpenCode password'; opencode web --hostname 127.0.0.1 --port 4096"}

def repositories():
    try:
        p=subprocess.run(["gh","repo","list","--limit","30","--json",
                          "nameWithOwner,isPrivate,description,url"],
                         cwd=ROOT,capture_output=True,text=True,timeout=12,check=False,
                         creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if p.returncode:
            return {"repositories":[],"error":"GitHub CLI not authenticated or repository listing unavailable"}
        data=json.loads(p.stdout)
        return {"repositories":[{"nameWithOwner":v.get("nameWithOwner",""),
                                 "isPrivate":bool(v.get("isPrivate")),
                                 "description":str(v.get("description") or "")[:200]}
                                for v in data[:30]]}
    except (OSError,subprocess.TimeoutExpired,ValueError,TypeError):
        return {"repositories":[],"error":"GitHub repository listing unavailable"}

CATALOG=[
    {"name":"Python unit testing","kind":"programming","description":"pytest and unittest acceptance tests","installation":"Review dependencies before enabling"},
    {"name":"Python linting","kind":"programming","description":"Ruff linting and formatting","installation":"Review dependencies before enabling"},
    {"name":"Python typing","kind":"programming","description":"mypy static type analysis","installation":"Review dependencies before enabling"},
    {"name":"Python security review","kind":"security","description":"Bandit checks and dependency audit","installation":"Review dependencies before enabling"},
    {"name":"GitHub development","kind":"tool","description":"Git and GitHub CLI repository inspection","installation":"Use existing authenticated gh CLI"},
    {"name":"Documentation research","kind":"research","description":"Search engine and cited documentation retrieval","installation":"Requires approved search provider"},
    {"name":"Blender automation","kind":"modding","description":"Headless Blender asset pipeline validation","installation":"Use SMELTER existing adapters"},
]
def inspect_skill(url):
    """Inspect only a GitHub SKILL.md via authenticated gh API. Never execute content."""
    try:
        parsed=urllib.parse.urlsplit(url)
        if parsed.scheme!="https" or parsed.hostname!="github.com" or parsed.username or parsed.password or parsed.port:
            return {"error":"Only HTTPS github.com skill links are accepted"}
        parts=[urllib.parse.unquote(x) for x in parsed.path.strip("/").split("/")]
        if len(parts)<2 or any(not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}",x) for x in parts[:2]):
            return {"error":"Expected github.com/owner/repository"}
        owner,repo=parts[:2]
        if owner in (".","..") or repo in (".",".."):
            return {"error":"Invalid repository"}
        if len(parts)==2:
            location="SKILL.md"
            ref=None
        elif len(parts)>=5 and parts[2]=="blob":
            ref=parts[3]
            location="/".join(parts[4:])
        else:
            return {"error":"Expected a repository root or a blob URL ending in SKILL.md"}
        if not re.fullmatch(r"[A-Za-z0-9_./-]{1,250}",location) or ".." in location.split("/") or not location.endswith("/SKILL.md") and location!="SKILL.md":
            return {"error":"Only SKILL.md paths are supported"}
        if ref is not None and (not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}",ref) or ref in (".","..")):
            return {"error":"Invalid ref; branch names containing slashes are not supported"}
        endpoint=f"repos/{owner}/{repo}/contents/{location}"
        if ref: endpoint+="?ref="+urllib.parse.quote(ref,safe="")
        p=subprocess.run(["gh","api",endpoint],cwd=ROOT,capture_output=True,text=True,
                         timeout=12,check=False,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if p.returncode:
            return {"error":"Unable to retrieve SKILL.md through authenticated GitHub CLI"}
        if len(p.stdout)>150000:
            return {"error":"GitHub response too large"}
        item=json.loads(p.stdout)
        if item.get("type")!="file" or item.get("encoding")!="base64" or item.get("size",0)>32768:
            return {"error":"SKILL.md missing, too large, or unsupported"}
        content=base64.b64decode(item["content"],validate=False).decode("utf-8")
        if len(content)>32768:return {"error":"SKILL.md too large"}
        flags=[name for name,pattern in (
            ("shell execution",r"\b(?:curl|wget|powershell|bash|Invoke-Expression|subprocess)\b"),
            ("credentials",r"\b(?:token|password|secret|credential|API_KEY)\b"),
            ("network access",r"https?://"),
            ("filesystem changes",r"\b(?:rm -rf|Remove-Item|git clone|pip install)\b"),
        ) if re.search(pattern,content,re.I)]
        return {"repository":owner+"/"+repo,"path":location,"ref":ref or "default",
                "sha":item.get("sha"),"size":len(content.encode("utf-8")),
                "preview":content[:6000],"review_flags":flags,
                "status":"Inspection only. Flags are heuristic; absence does not imply safety. Installation disabled."}
    except (OSError,subprocess.TimeoutExpired,ValueError,TypeError,KeyError,UnicodeError,base64.binascii.Error):
        return {"error":"Skill inspection unavailable"}

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
        if self.client_address[0] not in ("127.0.0.1","::1") or self.headers.get("Host","") not in (f"{HOST}:{PORT}",HOST):
            self.send_error(403,"Invalid host");return
        path=urllib.parse.urlsplit(self.path).path
        if path=="/":
            body=HTML.encode("utf-8")
            kind="text/html; charset=utf-8"
        elif path in ("/api/status","/api/github","/api/skills","/api/opencode","/api/repos","/api/catalog","/api/inspect-skill"):
            if path=="/api/status":
                obj={"mode":"localhost only","root":str(ROOT),"ollama":ollama(),"docker":run(["docker","info","--format","{{.ServerVersion}}"]),"opencode":run(["opencode","--version"])}
            elif path=="/api/github":
                obj={"repository":"Dr-Dark92/SMELTER","branch":run(["git","branch","--show-current"]),"remote":run(["git","remote","get-url","origin"]),"auth":run(["gh","auth","status"])}
                # Do not expose gh auth status details, which may include account identifiers.
                obj["auth"]={"available":obj["auth"]["available"]}
            elif path=="/api/opencode":obj=opencode_status()
            elif path=="/api/repos":obj=repositories()
            elif path=="/api/catalog":obj={"capabilities":CATALOG,"remote_installation":"disabled"}
            elif path=="/api/inspect-skill":
                query=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                url=query.get("url",[""])[0]
                obj=inspect_skill(url) if len(url)<=600 else {"error":"URL too long"}
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
