#!/usr/bin/env python3
"""SMELTER local-AI engineering agent diagnostic. Read-only, stdlib-only."""
import argparse,datetime,json,pathlib,time,urllib.request,urllib.error,uuid,statistics,traceback
TASKS=[
 {"id":"vertex_skinning","question":"Analyze these facts: Magicka2 character mesh has 88-byte vertex stride; XYZ floats at byte 0, UV floats at byte 48; 956 vertices, 1308 triangles; bone names Hips, Spine, Head, Hood1, Hood2, Hood3, LeftHandCloth, RightHandCloth appear in decoded binary. No bone-weight layout is verified. Suggest ONE bounded, read-only deterministic test for identifying bone indices and weights. Do not claim a byte offset is known.","required":["88","48"],"prohibited_claims":["verified weights","confirmed weight offset"]},
 {"id":"material_roles","question":"Analyze Magicka2 wizard texture evidence: resource A 256x256 colorful orange/purple clothing atlas appears coherent on mesh with UV offset 48. Resource B 1024x512 cyan cloth atlas shows coherent seams/buckles on its mesh, but its role as diffuse vs packed map is unverified. Recommend ONE automated read-only experiment to discriminate the texture roles. Do not assert original material bindings are recovered.","required":["cyan"],"prohibited_claims":["confirmed original bindings"]},
 {"id":"conversion_gate","question":"Magicka2 hooded wizard meshes, indices and candidate UVs extracted; no verified skin weights, skeleton mapping, or Skyrim SE NIF generated. User wants standalone wearable Skyrim SE outfit only, no spells/animations/gameplay modifications. Decide whether conversion is production-ready and propose ONE concrete automated next step. Never claim a working Skyrim mod exists.","required":["Skyrim"],"prohibited_claims":["mod is complete","NIF is validated"]}
]
SYSTEM=("You are SMELTER's LOCAL engineering analysis agent. You may only propose tests, not perform actions. "
"Use evidence exactly as supplied; no invented observations, paths, results, verified offsets, or tool calls. "
"Reply with ONE JSON object only with keys task_id, verdict, confidence, evidence, hypothesis, "
"next_test, acceptance_criteria, risks. "
"task_id must match the supplied task ID; verdict one of investigate, blocked, ready; "
"confidence a number 0..1; evidence and risks arrays of strings; "
"hypothesis, next_test and acceptance_criteria nonempty strings. "
"Prefer deterministic read-only tests and explicitly separate observed evidence from hypotheses.")
def post(url,payload,timeout):
 data=json.dumps(payload).encode()
 req=urllib.request.Request(url.rstrip("/")+"/api/generate",data=data,headers={"Content-Type":"application/json"},method="POST")
 with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)
def parse(s):
 try:return json.loads(s),None
 except Exception as e:
  try:
   start=s.index("{");end=s.rindex("}")+1
   return json.loads(s[start:end]),"recovered_json_from_surrounding_text"
  except Exception:return None,str(e)
def validate(obj,task):
 errs=[]
 if not isinstance(obj,dict):return ["response_not_json_object"]
 for key in ("task_id","verdict","confidence","evidence","hypothesis","next_test","acceptance_criteria","risks"):
  if key not in obj:errs.append("missing_"+key)
 if obj.get("task_id")!=task["id"]:errs.append("wrong_task_id")
 if obj.get("verdict") not in ("investigate","blocked","ready"):errs.append("invalid_verdict")
 conf=obj.get("confidence")
 if isinstance(conf,bool) or not isinstance(conf,(int,float)) or not 0<=conf<=1:errs.append("invalid_confidence")
 for key in ("hypothesis","next_test","acceptance_criteria"):
  if not isinstance(obj.get(key),str) or len(obj[key].strip())<12:errs.append("invalid_"+key)
 for key in ("evidence","risks"):
  if not isinstance(obj.get(key),list) or not all(isinstance(v,str) for v in obj[key]):errs.append("invalid_"+key)
 if obj.get("verdict")=="ready":errs.append("premature_ready_verdict")
 text=json.dumps(obj,ensure_ascii=False).lower()
 for term in task["prohibited_claims"]:
  if term.lower() in text:errs.append("potential_unsupported_phrase_"+term.replace(" ","_"))
 if not isinstance(obj.get("next_test"),str) or not any(x in obj["next_test"].lower() for x in ("scan","check","compare","inspect","validate","audit","test","extract","measure","render","parse")):errs.append("next_test_not_actionable")
 return errs
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--root",default=r"C:\SMELTER");p.add_argument("--model",default="qwen3.5:9b")
 p.add_argument("--url",default="http://127.0.0.1:11434");p.add_argument("--timeout",type=int,default=180)
 args=p.parse_args();root=pathlib.Path(args.root)
 out=root/"workspace"/"local-ai-agent-tests"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]);out.mkdir(parents=True,exist_ok=True)
 report={"tool":"SMELTER local AI agent diagnostic v1","timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"model":args.model,
 "ollama_url":args.url,"think":False,"stream":False,"read_only":True,"tests":[]}
 for task in TASKS:
  print("Testing:",task["id"],flush=True);started=time.perf_counter()
  entry={"task_id":task["id"],"input_question":task["question"]}
  payload={"model":args.model,"system":SYSTEM,"prompt":"Task ID: "+task["id"]+"\n"+task["question"],
   "stream":False,"think":False,"format":"json","options":{"temperature":0.15,"num_ctx":8192,"num_predict":1100}}
  try:
   raw=post(args.url,payload,args.timeout)
   response=raw.get("response","");obj,parse_issue=parse(response)
   errors=validate(obj,task)
   if parse_issue:errors.append("parse_issue_"+parse_issue)
   entry.update({"response":response,"parsed":obj,"errors":errors,"pass":not errors,
    "ollama_done_reason":raw.get("done_reason"),"prompt_eval_count":raw.get("prompt_eval_count"),
    "eval_count":raw.get("eval_count"),"eval_duration_ns":raw.get("eval_duration"),
    "total_duration_ns":raw.get("total_duration"),"thinking_chars":len(raw.get("thinking",""))})
  except Exception as e:entry.update({"pass":False,"errors":["request_error"],"exception":repr(e)})
  entry["wall_seconds"]=round(time.perf_counter()-started,3)
  report["tests"].append(entry);print("Result:", "PASS" if entry["pass"] else "FAIL",entry.get("errors"),flush=True)
 report["passed"]=sum(t["pass"] for t in report["tests"]);report["total"]=len(report["tests"])
 report["pass_rate"]=report["passed"]/report["total"]
 dest=out/"smelter-local-ai-agent-test.json";dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
 print("REPORT:",dest);print("SCORE:",report["passed"],"/",report["total"])
 print("No game assets or source files modified.")
if __name__=="__main__":main()
