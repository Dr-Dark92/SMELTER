#!/usr/bin/env python3
"""Round 9: AI selects two distinct Blender operations using a reusable adapter."""
from __future__ import annotations
import argparse,datetime,json,pathlib,sys,time,urllib.request,uuid
from smelter_blender_adapter import SHAPES,build,discover,validate

def decide(url,model,history):
    prompt=("You control SMELTER's registered Blender tools. Choose one tool call per turn. "
            "Reply with a JSON object containing tool_id and arguments. "
            "Tools: blender.build {shape: uv_sphere|cylinder}; artifact.validate {shape: uv_sphere|cylinder}. "
            "Goal: build AND validate BOTH uv_sphere and cylinder. Build each before validating it. "
            "Do not repeat successful operations. Do not choose cube. No code or paths.\n"+
            "\n".join(history))
    body={"model":model,"prompt":prompt,"stream":False,"think":False,"format":"json",
          "options":{"temperature":0,"num_ctx":8192,"num_predict":250}}
    req=urllib.request.Request(url.rstrip("/")+"/api/generate",data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=120) as response:
        out=json.load(response)
    value=json.loads(out["response"])
    if not isinstance(value,dict):raise ValueError("Decision is not an object")
    return value

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=r"C:\SMELTER");ap.add_argument("--blender",default=None)
    ap.add_argument("--model",default="qwen3.5:9b");ap.add_argument("--url",default="http://127.0.0.1:11434")
    args=ap.parse_args()
    root=pathlib.Path(args.root).resolve()
    workspace=root/"workspace"/"smelter-round9"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ-")+uuid.uuid4().hex[:6])
    workspace.mkdir(parents=True,exist_ok=True)
    report={"test":"SMELTER Round 9 reusable Blender adapter","steps":[],"full_pass":False,"target_shapes":["uv_sphere","cylinder"]}
    report_path=workspace/"smelter-round9.json"
    def save():
        report_path.write_text(json.dumps(report,indent=2),encoding="utf-8")
        print("REPORT:",report_path,"FULL PASS:",report["full_pass"],flush=True)
    try:exe=discover(args.blender)
    except Exception as exc:
        report.update({"status":"blocked","error":str(exc)});save();return 2
    report["blender_discovered"]=True
    history=["GOAL: Build and validate uv_sphere and cylinder. Current completed operations: none."]
    built=set();validated=set()
    for i in range(10):
        step={"step":i+1};start=time.perf_counter()
        try:
            d=decide(args.url,args.model,history)
            step["decision"]=d
            tool=d.get("tool_id");arguments=d.get("arguments")
            if not isinstance(arguments,dict) or set(arguments)!={"shape"}:raise ValueError("Expected arguments {shape: ...}")
            shape=arguments["shape"]
            if shape not in ("uv_sphere","cylinder"):raise ValueError("Disallowed shape")
            if tool=="blender.build":
                if shape in built:raise ValueError("Already built "+shape)
                result=build(exe,workspace,shape)
                built.add(shape)
            elif tool=="artifact.validate":
                if shape not in built:raise ValueError("Must build before validating")
                if shape in validated:raise ValueError("Already validated")
                result=validate(exe,workspace,shape)
                if result["valid"]:validated.add(shape)
            else:raise ValueError("Unknown tool")
            step.update({"pass":bool(result.get("valid",True)),"result":result})
            history.append("TOOL_RESULT: "+json.dumps({"tool":tool,"shape":shape,"success":step["pass"],"completed_builds":sorted(built),"completed_validations":sorted(validated)}))
        except Exception as exc:
            step.update({"pass":False,"error":repr(exc)[:600]})
            history.append("TOOL_ERROR: "+repr(exc)[:300]+"; completed_builds="+str(sorted(built))+"; completed_validations="+str(sorted(validated)))
        step["seconds"]=round(time.perf_counter()-start,3)
        report["steps"].append(step)
        print("STEP",i+1,step.get("decision",{}).get("tool_id"),step.get("decision",{}).get("arguments"),step["pass"],flush=True)
        if len(validated)==2:break
    independent={shape:validate(exe,workspace,shape) if shape in built else {"valid":False,"reason":"not built"} for shape in ("uv_sphere","cylinder")}
    report.update({"built":sorted(built),"model_validated":sorted(validated),"independent_validation":independent,
                   "full_pass":len(validated)==2 and all(v.get("valid") for v in independent.values())})
    report["status"]="passed" if report["full_pass"] else "failed"
    save();return 0 if report["full_pass"] else 1
if __name__=="__main__":sys.exit(main())
