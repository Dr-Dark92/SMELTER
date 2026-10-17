#!/usr/bin/env python3
"""SMELTER generic goal-driven Ollama agent: tool planning and failure recovery.
Writes only into workspace/smelter-goal-agent; no game-specific logic.
"""
import argparse,datetime,hashlib,json,pathlib,time,urllib.request,uuid
TOOLS=[
 {"id":"artifact.read","description":"Read a JSON artifact by filename from the sandbox. Returns missing if absent.","parameters":{"filename":"string"}},
 {"id":"artifact.write","description":"Write a JSON object to a filename in the sandbox.","parameters":{"filename":"string","data":"object"}},
 {"id":"artifact.validate","description":"Check a sandbox JSON artifact for required top-level keys and exact expected values.","parameters":{"filename":"string","required_keys":"array of strings","expected_values":"object"}},
]
def execute(folder,name,args):
 if not isinstance(args,dict):raise ValueError("arguments must be object")
 filename=args.get("filename")
 if not isinstance(filename,str) or not filename.endswith(".json") or pathlib.PurePath(filename).name!=filename or len(filename)>90:raise ValueError("invalid filename")
 path=(folder/filename).resolve()
 if not path.is_relative_to(folder.resolve()):raise ValueError("outside sandbox")
 if name=="artifact.read":
  if set(args)!={"filename"}:raise ValueError("invalid read arguments")
  if not path.exists():return {"status":"missing","filename":filename}
  return {"status":"read","data":json.loads(path.read_text(encoding="utf-8"))}
 if name=="artifact.write":
  if set(args)!={"filename","data"} or not isinstance(args["data"],dict):raise ValueError("invalid write arguments")
  data=json.dumps(args["data"],sort_keys=True,indent=2)
  if len(data)>8192:raise ValueError("oversized artifact")
  path.write_text(data,encoding="utf-8")
  return {"status":"written","sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
 if name=="artifact.validate":
  if set(args)!={"filename","required_keys","expected_values"}:raise ValueError("invalid validation arguments")
  if not isinstance(args["required_keys"],list) or not all(isinstance(k,str) for k in args["required_keys"]) or not isinstance(args["expected_values"],dict):raise ValueError("invalid validation parameters")
  if not path.exists():return {"status":"missing","valid":False}
  data=json.loads(path.read_text(encoding="utf-8"))
  missing=[k for k in args["required_keys"] if k not in data]
  mismatch=[k for k,v in args["expected_values"].items() if data.get(k)!=v]
  return {"status":"validated","valid":not missing and not mismatch,"missing":missing,"mismatch":mismatch}
 raise ValueError("unregistered tool")
def infer(url,model,system,prompt,timeout):
 payload={"model":model,"system":system,"prompt":prompt,"stream":False,"think":False,"format":"json","options":{"temperature":0,"num_ctx":8192,"num_predict":550}}
 req=urllib.request.Request(url.rstrip("/")+"/api/generate",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");p.add_argument("--url",default="http://127.0.0.1:11434");p.add_argument("--model",default="qwen3.5:9b");p.add_argument("--timeout",type=int,default=180);p.add_argument("--max-steps",type=int,default=8);a=p.parse_args()
 root=pathlib.Path(a.root).resolve();run_id=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]
 folder=root/"workspace"/"smelter-goal-agent"/run_id;folder.mkdir(parents=True)
 filename="goal-"+uuid.uuid4().hex[:10]+".json"
 goal=f"Ensure the sandbox contains JSON artifact {filename} with exactly these required values: engine=SMELTER, stage=integration, verified=true. Independently decide which tools to call, handle missing artifacts, verify the final contents, then finish."
 system=("You are SMELTER's generic local AI orchestration agent. You can use only the registered tools. "
 "Choose one tool per turn, or finish only after observing a successful artifact.validate result. "
 "Never claim a tool ran unless an ACTUAL_TOOL_RESULT appears. Handle missing artifacts by creating them. "
 "Return JSON only with keys tool_id (registered tool name or null), arguments (object), reason (string). "
 "For artifact.validate, required_keys must include engine, stage, verified and expected_values must match the goal. "
 "Tools: "+json.dumps(TOOLS))
 history=["USER_GOAL: "+goal];report={"test":"SMELTER generic goal-driven agent v3","model":a.model,"goal":goal,"artifact":filename,"tools":TOOLS,"steps":[],"max_steps":a.max_steps}
 verified=False;finished=False
 for i in range(a.max_steps):
  start=time.perf_counter();entry={"step":i+1}
  try:
   raw=infer(a.url,a.model,system,"\n".join(history),a.timeout)
   decision=json.loads(raw.get("response",""));entry["decision"]=decision;entry["eval_count"]=raw.get("eval_count")
   tool=decision.get("tool_id");args=decision.get("arguments")
   if tool is None:
    entry["status"]="finished";finished=True
    entry["pass"]=verified
    if not verified:entry["error"]="premature_finish"
   elif tool in {t["id"] for t in TOOLS}:
    if not isinstance(args,dict) or args.get("filename")!=filename:raise ValueError("incorrect artifact filename")
    result=execute(folder,tool,args);entry["tool_result"]=result;entry["status"]="executed";entry["pass"]=True
    if tool=="artifact.validate" and result.get("valid") is True and set(args.get("required_keys",[]))>={"engine","stage","verified"} and args.get("expected_values")=={"engine":"SMELTER","stage":"integration","verified":True}:verified=True
    history.append("ASSISTANT_TOOL_DECISION: "+json.dumps(decision))
    history.append("ACTUAL_TOOL_RESULT: "+json.dumps(result))
   else:raise ValueError("unregistered tool")
  except Exception as e:
   entry["status"]="error";entry["pass"]=False;entry["error"]=repr(e)
   history.append("TOOL_ERROR: "+repr(e))
  entry["wall_seconds"]=round(time.perf_counter()-start,3);report["steps"].append(entry)
  print("Step",i+1,entry["status"],entry.get("decision",{}).get("tool_id"),flush=True)
  if finished:break
 # Independent deterministic verification, not based on model claims.
 try:
  actual=json.loads((folder/filename).read_text(encoding="utf-8"))
  actual_ok=all(actual.get(k)==v for k,v in {"engine":"SMELTER","stage":"integration","verified":True}.items())
 except Exception:actual_ok=False
 report["model_validated"]=verified;report["model_finished"]=finished;report["independent_artifact_check"]=actual_ok
 report["full_pass"]=verified and finished and actual_ok
 dest=folder/"smelter-goal-agent.json";dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("REPORT:",dest);print("FULL PASS:",report["full_pass"])
if __name__=="__main__":main()
