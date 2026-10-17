#!/usr/bin/env python3
"""Round 10: Qwen routes an existing sandbox GLB through inspect -> convert -> validate."""
from __future__ import annotations
import argparse,datetime,json,pathlib,sys,time,urllib.request,uuid
from smelter_blender_adapter import discover
from smelter_asset_adapter import inspect_glb,convert_glb_to_obj,validate_obj

def choose(url,model,history):
    prompt=("You are SMELTER's asset-processing agent. Return ONLY one JSON object: "
            '{"tool_id":"...","arguments":{}}. Registered tools: asset.inspect, '
            "asset.convert_glb_to_obj, asset.validate_obj. All tools require exactly empty arguments {}. "
            "Your goal is to inspect an existing GLB asset, convert it to OBJ, and validate the result. "
            "Use tools in that order, exactly once each. Never propose paths or code.\n"+
            "\n".join(history))
    body={"model":model,"prompt":prompt,"think":False,"stream":False,"format":"json",
          "options":{"temperature":0,"num_ctx":8192,"num_predict":200}}
    req=urllib.request.Request(url.rstrip("/")+"/api/generate",data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=120) as response:out=json.load(response)
    d=json.loads(out["response"])
    if not isinstance(d,dict):raise ValueError("Model response not an object")
    return d

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\SMELTER")
    p.add_argument("--blender",default=None)
    p.add_argument("--source",default=None,help="Existing GLB within workspace; default newest Round 9 UV sphere")
    p.add_argument("--model",default="qwen3.5:9b")
    p.add_argument("--url",default="http://127.0.0.1:11434")
    a=p.parse_args()
    root=pathlib.Path(a.root).resolve()
    workspace=(root/"workspace").resolve()
    run=workspace/"smelter-round10"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ-")+uuid.uuid4().hex[:6])
    run.mkdir(parents=True,exist_ok=True)
    output=run/"converted.obj"
    report={"test":"SMELTER Round 10 existing-asset GLB-to-OBJ workflow","steps":[],"full_pass":False}
    report_path=run/"smelter-round10.json"
    def save():
        report_path.write_text(json.dumps(report,indent=2),encoding="utf-8")
        print("REPORT:",report_path,"FULL PASS:",report["full_pass"],flush=True)
    try:
        exe=discover(a.blender)
        candidates=sorted((workspace/"smelter-round9").glob("*/uv_sphere.glb"),key=lambda x:x.stat().st_mtime,reverse=True)
        if not a.source and not candidates:raise FileNotFoundError("No Round 9 GLB found. Run Round 9 first or pass --source")
        source=pathlib.Path(a.source).resolve() if a.source else candidates[0].resolve()
        if not source.is_relative_to(workspace):raise ValueError("Source must be within workspace")
        if not source.is_file():raise FileNotFoundError("Source missing")
        report["source_bytes"]=source.stat().st_size
    except Exception as exc:
        report.update({"status":"blocked","reason":str(exc)});save();return 2
    history=["GOAL: inspect source GLB, convert to OBJ, validate converted OBJ. No steps complete."]
    inspected=converted=validated=False
    for i in range(7):
        step={"step":i+1};start=time.perf_counter()
        try:
            d=choose(a.url,a.model,history)
            step["decision"]=d
            if d.get("arguments")!={}:raise ValueError("Arguments must be {}")
            tool=d.get("tool_id")
            if tool=="asset.inspect":
                if inspected:raise ValueError("Already inspected")
                result=inspect_glb(source,workspace);inspected=result["valid"]
            elif tool=="asset.convert_glb_to_obj":
                if not inspected or converted:raise ValueError("Inspect first; do not reconvert")
                result=convert_glb_to_obj(exe,source,output,workspace);converted=result["converted"]
            elif tool=="asset.validate_obj":
                if not converted or validated:raise ValueError("Convert first; do not revalidate")
                result=validate_obj(exe,output,workspace);validated=result["valid"]
            else:raise ValueError("Unregistered tool")
            step.update({"pass":bool(result.get("valid",result.get("converted",False))),"result":result})
        except Exception as exc:
            step.update({"pass":False,"error":repr(exc)[:600]})
        history.append("LAST_STEP: "+json.dumps({"tool":step.get("decision",{}).get("tool_id"),
                       "success":step["pass"],"inspected":inspected,"converted":converted,"validated":validated}))
        step["seconds"]=round(time.perf_counter()-start,3)
        report["steps"].append(step)
        print("STEP",i+1,step.get("decision",{}).get("tool_id"),step["pass"],flush=True)
        if validated:break
    independent=validate_obj(exe,output,workspace) if converted else {"valid":False,"reason":"not converted"}
    report.update({"inspected":inspected,"converted":converted,"model_validated":validated,
                   "independent_validation":independent,
                   "full_pass":inspected and converted and validated and independent.get("valid") is True})
    report["status"]="passed" if report["full_pass"] else "failed"
    save()
    return 0 if report["full_pass"] else 1
if __name__=="__main__":sys.exit(main())
