#!/usr/bin/env python3
"""SMELTER generic local AI orchestrator integration test.

Discovers installed skills; invokes registered, sandboxed capabilities using
Qwen-generated arguments; verifies outcomes independently. No game assets touched.
"""
from __future__ import annotations
import argparse,datetime,json,pathlib,sys,time,urllib.request,uuid
from smelter_registry import Capability,Registry

def ask(url,model,system,prompt,timeout):
    payload={"model":model,"system":system,"prompt":prompt,"stream":False,
             "think":False,"format":"json",
             "options":{"temperature":0,"num_ctx":8192,"num_predict":650}}
    req=urllib.request.Request(url.rstrip("/")+"/api/generate",
        data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        result=json.load(response)
    obj=json.loads(result.get("response",""))
    if not isinstance(obj,dict):raise ValueError("Model output must be JSON object")
    return obj,result.get("eval_count")

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--root",default=r"C:\SMELTER")
    parser.add_argument("--model",default="qwen3.5:9b")
    parser.add_argument("--url",default="http://127.0.0.1:11434")
    parser.add_argument("--timeout",type=int,default=180)
    parser.add_argument("--max-steps",type=int,default=7)
    args=parser.parse_args()
    root=pathlib.Path(args.root).resolve()
    run=root/"workspace"/"smelter-orchestrator"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6])
    run.mkdir(parents=True)
    registry=Registry(root)
    filename="integration-"+uuid.uuid4().hex[:8]+".json"
    expected={"engine":"SMELTER","phase":"orchestration","validated":True}
    target=run/filename
    def write(a):
        payload=json.dumps(a["data"],indent=2,sort_keys=True)
        if len(payload)>4096:raise ValueError("Artifact too large")
        target.write_text(payload,encoding="utf-8")
        return {"status":"written","filename":filename}
    def read(a):
        if not target.is_file():return {"status":"missing"}
        return {"status":"read","data":json.loads(target.read_text(encoding="utf-8"))}
    def validate(a):
        if not target.is_file():return {"status":"missing","valid":False}
        actual=json.loads(target.read_text(encoding="utf-8"))
        return {"status":"validated","valid":all(actual.get(k)==v for k,v in a["expected"].items()),"actual":actual}
    def skills(a):
        return {"skills":[{"id":s["id"],"description":s["description"]} for s in registry.skills()]}
    def skill_read(a):
        return {"skill_id":a["skill_id"],"instructions":registry.skill_instructions(a["skill_id"],limit=8000)}
    registry.register(Capability("skills.list","Discover installed skills",{},skills))
    registry.register(Capability("skills.read","Read a specific installed skill's instructions",{"skill_id":"string"},skill_read))
    registry.register(Capability("artifact.read","Read the named sandbox JSON artifact",{"filename":"string"},read))
    registry.register(Capability("artifact.write","Write the named sandbox JSON artifact",{"filename":"string","data":"object"},write,read_only=False))
    registry.register(Capability("artifact.validate","Validate artifact values",{"filename":"string","expected":"object"},validate))
    goal=("Discover installed SMELTER skills and read the asset-pipeline skill instructions. "
          "Then create and validate JSON artifact "+filename+" with these exact values: "+json.dumps(expected)+
          ". Use registered tools, not imaginary tools. Finish only after validation succeeds.")
    report={"test":"SMELTER unified registry orchestration v1","model":args.model,
            "goal":goal,"skills_discovered":len(registry.skills()),"capabilities":registry.catalog(),
            "steps":[],"artifact":filename}
    history=["USER_GOAL: "+goal]
    skill_listed=False;skill_read=False;validated=False;seen=set()
    system=("You are SMELTER's local AI agent. Registered tools are the ONLY executable operations. "
            "Choose exactly one tool each turn. Return JSON object with tool_id, arguments, reason. "
            "Do not claim any execution before seeing ACTUAL_TOOL_RESULT. "
            "Use skills.list first, then skills.read for universal-modder-asset-pipeline, then write and validate the artifact. "
            "Do not repeat successful calls. Do not invent tools. Tool catalog: "+json.dumps(registry.catalog()))
    for n in range(max(1,min(args.max_steps,12))):
        started=time.perf_counter();entry={"step":n+1}
        try:
            decision,tokens=ask(args.url,args.model,system,"\n".join(history),args.timeout)
            entry["decision"]=decision;entry["eval_count"]=tokens
            tool=decision.get("tool_id");params=decision.get("arguments")
            if tool is None:raise ValueError("Premature completion")
            if tool in ("artifact.write","artifact.read","artifact.validate") and (not isinstance(params,dict) or params.get("filename")!=filename):
                raise ValueError("Wrong artifact filename")
            if tool=="skills.read" and (not isinstance(params,dict) or params.get("skill_id")!="universal-modder-asset-pipeline"):
                raise ValueError("Wrong skill selection")
            if tool=="artifact.write" and not skill_read:raise ValueError("Must read skill first")
            if tool=="artifact.validate" and not target.is_file():raise ValueError("Artifact not yet written")
            signature=json.dumps([tool,params],sort_keys=True)
            if signature in seen:raise ValueError("Repeated identical tool call")
            seen.add(signature)
            result=registry.invoke(tool,params,allow_writes=(tool=="artifact.write"))
            if tool=="skills.list":skill_listed=True
            if tool=="skills.read":
                if not skill_listed:raise ValueError("Skill list must precede skill read")
                skill_read=True
                # Don't persist full skill body in diagnostics or history.
                result={"skill_id":result["skill_id"],"instructions":result["instructions"][:6000]}
            if tool=="artifact.validate":
                validated=(result.get("valid") is True and params["expected"]==expected and skill_read)
            entry["result"]=result if tool!="skills.read" else {"skill_id":result["skill_id"],"instructions_loaded":True}
            entry["pass"]=True
            history.extend(["ASSISTANT_DECISION: "+json.dumps(decision),
                            "ACTUAL_TOOL_RESULT: "+json.dumps(result)])
        except Exception as exc:
            entry["pass"]=False;entry["error"]=repr(exc)
            history.append("TOOL_ERROR: "+repr(exc))
        entry["wall_seconds"]=round(time.perf_counter()-started,3)
        report["steps"].append(entry)
        print("STEP",n+1,entry.get("decision",{}).get("tool_id"),"PASS" if entry["pass"] else "FAIL",flush=True)
        if validated:break
    try:actual=json.loads(target.read_text(encoding="utf-8"))
    except (OSError,ValueError):actual={}
    report["skill_listed"]=skill_listed;report["skill_read"]=skill_read
    report["validated"]=validated;report["independent_check"]=actual==expected
    report["full_pass"]=skill_listed and skill_read and validated and actual==expected
    report["completion_source"]="deterministic_validation_gate" if validated else "step_limit"
    dest=run/"smelter-unified-orchestrator.json"
    dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
    print("REPORT:",dest);print("FULL PASS:",report["full_pass"])
    return 0 if report["full_pass"] else 1
if __name__=="__main__":sys.exit(main())
