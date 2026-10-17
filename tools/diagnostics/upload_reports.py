#!/usr/bin/env python3
"""Upload sanitized SMELTER JSON diagnostics to the configured private GitHub repo.

Uses GitHub CLI authentication; never reads or stores tokens itself.
Only JSON reports, no raw binaries, source assets, or game files.
"""
from __future__ import annotations
import argparse,base64,datetime,json,os,pathlib,re,subprocess,sys,uuid

DEFAULT_REPO="Dr-Dark92/SMELTER"
DENY_KEYS=re.compile(r"(?:token|secret|password|credential|api.?key|authorization|cookie|private.?key|access.?key)",re.I)
PATH_RE=re.compile(r"(?i)(?:[a-z]:\\(?:[^\\\s\"']+\\)*[^\\\s\"']*|/(?:home|Users|mnt|opt|var|etc)/[^\s\"']+)")
SECRET_RE=re.compile(r"(?i)\b(?:gh[pousr]_[A-Za-z0-9_]{15,}|github_pat_[A-Za-z0-9_]{15,}|sk-[A-Za-z0-9_-]{16,})\b")
URL_AUTH_RE=re.compile(r"(?i)(https?://)[^\s/@]+:[^\s/@]+@")
MAX_INPUT=2_000_000
MAX_OUTPUT=500_000
def sanitize(value,depth=0):
 if depth>24:return "[DEPTH_LIMIT]"
 if isinstance(value,dict):
  return {str(k):("[REDACTED]" if DENY_KEYS.search(str(k)) else sanitize(v,depth+1)) for k,v in value.items()}
 if isinstance(value,list):return [sanitize(x,depth+1) for x in value[:300]]
 if isinstance(value,str):
  value=SECRET_RE.sub("[REDACTED_SECRET]",value)
  value=URL_AUTH_RE.sub(r"\1[REDACTED]@",value)
  value=PATH_RE.sub("[LOCAL_PATH]",value)
  return value[:20000]
 return value
def gh(*args,input_data=None):
 try:
  p=subprocess.run(["gh",*args],input=input_data,text=True,capture_output=True,timeout=45,check=False)
 except FileNotFoundError:raise RuntimeError("GitHub CLI (gh) not installed or not on PATH")
 if p.returncode:
  raise RuntimeError("GitHub CLI command failed: "+(p.stderr or p.stdout)[-1200:])
 return p.stdout
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument("--root",default=r"C:\SMELTER")
 p.add_argument("--repo",default=DEFAULT_REPO)
 p.add_argument("--report",action="append",help="JSON report path; repeat for multiple files")
 p.add_argument("--latest",action="store_true",help="Find newest JSON in known SMELTER diagnostic folders")
 p.add_argument("--dry-run",action="store_true",help="Create sanitized local previews without uploading")
 args=p.parse_args()
 root=pathlib.Path(args.root).resolve()
 workspace=(root/"workspace").resolve()
 if not workspace.is_dir():raise SystemExit("SMELTER workspace missing")
 paths=[]
 if args.report:
  paths.extend(pathlib.Path(x).resolve() for x in args.report)
 if args.latest:
  patterns=["smelter-goal-agent.json","smelter-skill-diagnostic.json","smelter-skill-execution.json","smelter-core-tool-chain.json","smelter-core-tool-routing.json","smelter-local-ai-agent-test.json","smelter-unified-orchestrator.json","smelter-multiskill.json","smelter-blender.json","smelter-round9.json","smelter-round10.json","smelter-round11.json"]
  for pattern in patterns:
   found=[x for x in workspace.rglob(pattern) if x.is_file()]
   if found:paths.append(max(found,key=lambda x:x.stat().st_mtime))
 if not paths:raise SystemExit("Specify --latest or --report PATH")
 unique=list(dict.fromkeys(paths))
 stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
 batch=stamp+"-"+uuid.uuid4().hex[:8]
 local=(workspace/"diagnostic-upload-previews"/batch);local.mkdir(parents=True,exist_ok=True)
 prepared=[]
 for path in unique:
  if not path.is_relative_to(workspace):raise SystemExit("Refusing file outside workspace: "+str(path))
  if path.suffix.lower()!=".json" or not path.is_file() or path.stat().st_size>MAX_INPUT:
   raise SystemExit("Invalid or oversized JSON report: "+str(path))
  data=json.loads(path.read_text(encoding="utf-8-sig"))
  if not isinstance(data,dict):raise SystemExit("Expected JSON object report: "+str(path))
  sanitized=sanitize(data)
  payload=json.dumps(sanitized,ensure_ascii=False,indent=2)
  if len(payload.encode("utf-8"))>MAX_OUTPUT:raise SystemExit("Sanitized report too large: "+str(path))
  filename=re.sub(r"[^a-zA-Z0-9_.-]","_",path.name)
  remote="diagnostics/"+batch+"/"+filename
  (local/filename).write_text(payload+"\n",encoding="utf-8")
  prepared.append((remote,payload))
 print("Sanitized previews:",local)
 print("Reports:",len(prepared))
 if args.dry_run:
  print("DRY RUN: no network upload")
  return
 if args.repo!=DEFAULT_REPO:
  raise SystemExit("Repository override blocked; edit reviewed source to change destination")
 repo=json.loads(gh("api",f"repos/{args.repo}"))
 if not repo.get("private"):
  raise SystemExit("Refusing upload: GitHub repository is not private")
 for remote,payload in prepared:
  encoded=base64.b64encode((payload+"\n").encode("utf-8")).decode("ascii")
  body=json.dumps({"message":"Add sanitized SMELTER diagnostic "+batch,"content":encoded})
  # gh api reads JSON request body from stdin. No token is printed or persisted.
  gh("api","--method","PUT",f"repos/{args.repo}/contents/{remote}","--input","-",input_data=body)
  print("Uploaded:",f"https://github.com/{args.repo}/blob/HEAD/{remote}")
 print("UPLOAD COMPLETE")
if __name__=="__main__":
 try:main()
 except (RuntimeError,ValueError,json.JSONDecodeError) as exc:
  print("ERROR:",exc,file=sys.stderr);sys.exit(1)
