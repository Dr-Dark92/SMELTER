#!/usr/bin/env python3
"""SMELTER generic AI tool-chain test: real arguments, artifacts, and feedback."""
import argparse,datetime,json,pathlib,time,urllib.request,uuid,hashlib
TOOLS=[
 {"id":"artifact.write_json","description":"Write a JSON artifact into workspace/smelter-agent-sandbox using a relative filename and object data.","arguments":{"filename":"string","data":"object"}},
 {"id":"artifact.read_json","description":"Read an existing JSON artifact from workspace/smelter-agent-sandbox by relative filename.","arguments":{"filename":"string"}},
 {"id":"artifact.validate_json","description":"Validate that a JSON artifact contains required top-level keys.","arguments":{"filename":"string","required_keys":"array of strings"}},
]
def execute(root,tool,args):
 if not isinstance(args,dict):raise ValueError("arguments_not_object")
 folder=root/"workspace"/"smelter-agent-sandbox";folder.mkdir(parents=True,exist_ok=True)
 filename=args.get("filename")
 if not isinstance(filename,str) or not filename.endswith(".json") or filename!=pathlib.Path(filename).name or len(filename)>80:
  raise ValueError("invalid_artifact_filename")
 path=(folder/filename).resolve()
 if not path.is_relative_to(folder.resolve()):raise ValueError("outside_sandbox")
 if tool=="artifact.write_json":
  if set(args)!={"filename","data"} or not isinstance(args["data"],dict):raise ValueError("invalid_write_arguments")
  content=json.dumps(args["data"],indent=2,sort_keys=True)
  if len(content)>10000:raise ValueError("artifact_too_large")
  path.write_text(content,encoding="utf-8")
  return {"status":"written","filename":filename,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
 if tool=="artifact.read_json":
  if set(args)!={"filename"}:raise ValueError("invalid_read_arguments")
  if not path.is_file():return {"status":"missing","filename":filename}
  if path.stat().st_size>10000:raise ValueError("artifact_too_large")
  return {"status":"read","filename":filename,"data":json.loads(path.read_text(encoding="utf-8"))}
 if tool=="artifact.validate_json":
  if set(args)!={"filename","required_keys"} or not isinstance(args["required_keys"],list) or not all(isinstance(k,str) for k in args["required_keys"]):raise ValueError("invalid_validation_arguments")
  if not path.is_file():return {"status":"missing","valid":False}
  data=json.loads(path.read_text(encoding="utf-8"))
  missing=[k for k in args["required_keys"] if k not in data]
  return {"status":"validated","valid":not missing,"missing_keys":missing}
 raise ValueError("unregistered_tool")
def infer(url,model,messages,timeout):
 system=("You are SMELTER's generic tool orchestration agent. Choose exactly one registered tool per turn or finish. "
 "Return a single JSON object with keys tool_id (string or null), arguments (object), reason (string). "
 "Do not claim a tool was run unless its actual result appears in the transcript. "
 "Use the precise filename from the user task. Do not invent tools. "
 "Tool definitions: "+json.dumps(TOOLS))
 req=urllib.request.Request(url.rstrip("/")+"/api/generate",data=json.dumps({
  "model":model,"system":system,"prompt":"\n".join(messages),
  "stream":False,"think":False,"format":"json",
  "options":{"temperature":0,"num_ctx":8192,"num_predict":400}}).encode(),headers={"Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=timeout) as resp:return json.load(resp)
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER")
 p.add_argument("--url",default="http://127.0.0.1:11434");p.add_argument("--model",default="qwen3.5:9b")
 p.add_argument("--timeout",type=int,default=180);a=p.parse_args()
 root=pathlib.Path(a.root).resolve();out=root/"workspace"/"smelter-core-chaining"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 filename="smelter-chain-"+uuid.uuid4().hex[:10]+".json"
 steps=[
  {"id":"write","instruction":f"Write JSON artifact named {filename} containing keys engine with value SMELTER and status with value testing. Call artifact.write_json.","expected":"artifact.write_json"},
  {"id":"read","instruction":f"Read JSON artifact {filename} using artifact.read_json.","expected":"artifact.read_json"},
  {"id":"validate","instruction":f"Validate JSON artifact {filename} requires keys engine and status using artifact.validate_json.","expected":"artifact.validate_json"},
 ]
 report={"test":"SMELTER generic local AI tool chain v2","model":a.model,"artifact":filename,"read_only_game_files":True,"steps":[]}
 history=[]
 for step in steps:
  started=time.perf_counter();row={"step":step["id"],"expected_tool":step["expected"],"instruction":step["instruction"]}
  try:
   history.append("USER: "+step["instruction"])
   raw=infer(a.url,a.model,history,a.timeout)
   decision=json.loads(raw.get("response",""));row["decision"]=decision
   tool=decision.get("tool_id");args=decision.get("arguments")
   row["routing_valid"]=tool==step["expected"]
   if tool not in {t["id"] for t in TOOLS}:raise ValueError("unregistered_tool")
   if not row["routing_valid"]:raise ValueError("wrong_tool")
   if not isinstance(args,dict) or args.get("filename")!=filename:raise ValueError("wrong_or_missing_filename")
   result=execute(root,tool,args);row["tool_result"]=result
   if step["id"]=="write":row["pass"]=result.get("status")=="written" and args.get("data")=={"engine":"SMELTER","status":"testing"}
   elif step["id"]=="read":row["pass"]=result.get("data")=={"engine":"SMELTER","status":"testing"}
   else:row["pass"]=result.get("valid") is True and set(args.get("required_keys",[]))=={"engine","status"}
   history.append("ASSISTANT_TOOL_DECISION: "+json.dumps(decision))
   history.append("ACTUAL_TOOL_RESULT: "+json.dumps(result))
   row["eval_count"]=raw.get("eval_count")
  except Exception as e:row["pass"]=False;row["error"]=repr(e)
  row["wall_seconds"]=round(time.perf_counter()-started,3)
  report["steps"].append(row);print(step["id"],"PASS" if row["pass"] else "FAIL",flush=True)
  if not row["pass"]:break
 report["passed"]=sum(s["pass"] for s in report["steps"]);report["total"]=len(steps)
 report["full_chain_pass"]=report["passed"]==len(steps)
 dest=out/"smelter-core-tool-chain.json";dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("REPORT:",dest);print("PASS:",report["passed"],"/",report["total"])
if __name__=="__main__":main()
