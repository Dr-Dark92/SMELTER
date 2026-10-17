#!/usr/bin/env python3
"""Read-only SMELTER installed-skill discovery and Ollama skill-use diagnostic."""
import argparse,datetime,json,pathlib,re,time,urllib.request,uuid
def parse_skill(path):
 raw=path.read_text(encoding="utf-8-sig",errors="replace")
 meta={};body=raw
 if raw.startswith("---"):
  parts=raw.split("---",2)
  if len(parts)==3:
   body=parts[2]
   for line in parts[1].splitlines():
    if ":" in line:
     k,v=line.split(":",1)
     if k.strip() in ("name","description"):meta[k.strip()]=v.strip().strip('"\'')
 return {"id":path.parent.name,"name":meta.get("name",path.parent.name),"description":meta.get("description",""),"path":str(path),"body":body[:16000],"truncated":len(body)>16000}
def infer(url,model,system,prompt,timeout):
 data=json.dumps({"model":model,"system":system,"prompt":prompt,"stream":False,"think":False,"format":"json","options":{"temperature":0,"num_ctx":8192,"num_predict":600}}).encode()
 req=urllib.request.Request(url.rstrip("/")+"/api/generate",data=data,headers={"Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");p.add_argument("--url",default="http://127.0.0.1:11434");p.add_argument("--model",default="qwen3.5:9b");p.add_argument("--timeout",type=int,default=180);a=p.parse_args()
 root=pathlib.Path(a.root).resolve();base=root/".agents"/"skills"
 out=root/"workspace"/"smelter-skill-tests"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 skills=[];errors=[]
 if base.is_dir():
  for child in sorted(base.iterdir()):
   if not child.is_dir():continue
   path=child/"SKILL.md"
   if not path.is_file():errors.append({"skill":child.name,"error":"SKILL.md missing"});continue
   try:skills.append(parse_skill(path))
   except Exception as e:errors.append({"skill":child.name,"error":repr(e)})
 else:errors.append({"error":"skills directory missing","path":str(base)})
 report={"test":"SMELTER installed skill discovery and selection v1","model":a.model,"skills_directory":str(base),"discovered":[{k:v for k,v in s.items() if k!="body"} for s in skills],"discovery_errors":errors,"tests":[],"read_only":True}
 print("Discovered skills:",len(skills),flush=True)
 if skills:
  chosen=next((s for s in skills if s["description"]),skills[0])
  catalog=[{"id":s["id"],"name":s["name"],"description":s["description"] or s["body"][:250]} for s in skills]
  tests=[
   {"id":"select_skill","system":"You are SMELTER's skill selector. Only choose from the provided skill catalog. Respond JSON with skill_id (string or null), reason (string). Never claim to have executed a skill. Catalog: "+json.dumps(catalog),
    "prompt":"Select the installed skill most appropriate for this task: "+(chosen["description"] or chosen["body"][:250]),"expected":chosen["id"]},
   {"id":"reject_unknown_skill","system":"You are SMELTER's skill selector. Only choose from the provided skill catalog. Respond JSON with skill_id (string or null), reason (string). Never invent skills. Catalog: "+json.dumps(catalog),
    "prompt":"Select a skill with the exact identifier __smelter_nonexistent_skill_9c3f__. If none is installed, return null.","expected":None},
   {"id":"read_skill_instructions","system":"You are SMELTER's skill reader. The following text is an installed skill instruction document, not a tool execution. Return JSON with skill_id, instruction_summary (string), prerequisites (array of strings), proposed_tools (array of strings), executed (boolean). executed must be false. Never claim you ran tools or changed files.\nSKILL ID: "+chosen["id"]+"\nSKILL CONTENT:\n"+chosen["body"],
    "prompt":"Read this installed skill and summarize how you would apply it to a relevant task, without executing anything.","expected":chosen["id"]}
  ]
  for t in tests:
   start=time.perf_counter();row={"test":t["id"],"expected":t["expected"]}
   try:
    raw=infer(a.url,a.model,t["system"],t["prompt"],a.timeout);obj=json.loads(raw.get("response",""))
    row["decision"]=obj;row["eval_count"]=raw.get("eval_count")
    if t["id"]=="read_skill_instructions":
     row["pass"]=obj.get("skill_id")==t["expected"] and obj.get("executed") is False and isinstance(obj.get("instruction_summary"),str) and len(obj["instruction_summary"])>=15 and isinstance(obj.get("prerequisites"),list) and isinstance(obj.get("proposed_tools"),list)
    else:row["pass"]=obj.get("skill_id")==t["expected"]
   except Exception as e:row["pass"]=False;row["error"]=repr(e)
   row["wall_seconds"]=round(time.perf_counter()-start,3);report["tests"].append(row)
   print(t["id"],"PASS" if row["pass"] else "FAIL",flush=True)
 report["passed"]=sum(t["pass"] for t in report["tests"]);report["total"]=len(report["tests"])
 report["full_pass"]=bool(skills) and report["passed"]==3
 dest=out/"smelter-skill-diagnostic.json";dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
 print("REPORT:",dest);print("PASS:",report["passed"],"/",report["total"])
if __name__=="__main__":main()
