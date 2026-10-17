#!/usr/bin/env python3
"""Round 11 material/UV/texture preservation gate with Qwen-approved operations."""
from __future__ import annotations
import argparse,datetime,json,pathlib,sys,time,urllib.request,uuid
from smelter_blender_adapter import discover
from smelter_material_adapter import make_fixture,roundtrip,compare

STAGES=("material.create_fixture","material.roundtrip","material.verify")
def decide(url,model,history,allowed):
    prompt=("You are SMELTER's material-processing agent. Respond ONLY with JSON "
            '{"tool_id":"...","arguments":{}}. '
            "Goal: create a UV-mapped textured asset, roundtrip GLB through Blender, "
            "verify materials, textures, and UV attributes. "
            "Registered tools: "+", ".join(STAGES)+". "
            "CURRENT ALLOWED TOOL: "+allowed+". Arguments must be {}. "
            "Never provide scripts, paths or shell commands.\n"+ "\n".join(history))
    body={"model":model,"prompt":prompt,"stream":False,"think":False,"format":"json",
          "options":{"temperature":0,"num_ctx":8192,"num_predict":200}}
    req=urllib.request.Request(url.rstrip("/")+"/api/generate",data=json.dumps(body).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=120) as response:raw=json.load(response)
    obj=json.loads(raw["response"])
    if not isinstance(obj,dict):raise ValueError("Invalid model response")
    return obj

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\SMELTER")
    p.add_argument("--blender",default=None)
    p.add_argument("--model",default="qwen3.5:9b")
    p.add_argument("--url",default="http://127.0.0.1:11434")
    a=p.parse_args()
    workspace=(pathlib.Path(a.root).resolve()/"workspace")
    run=workspace/"smelter-round11"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ-")+uuid.uuid4().hex[:6])
    run.mkdir(parents=True,exist_ok=True)
    report={"test":"SMELTER Round 11 textured GLB structural roundtrip","steps":[],"full_pass":False}
    path=run/"smelter-round11.json"
    def save():
        path.write_text(json.dumps(report,indent=2),encoding="utf-8")
        print("REPORT:",path,"FULL PASS:",report["full_pass"],flush=True)
    try:exe=discover(a.blender)
    except Exception as exc:
        report.update({"status":"blocked","reason":str(exc)});save();return 2
    source=output=None
    history=["No operations completed."]
    for index,expected in enumerate(STAGES):
        step={"step":index+1,"expected_tool":expected};start=time.perf_counter()
        try:
            d=decide(a.url,a.model,history,expected)
            step["model_decision"]=d
            if d.get("tool_id")!=expected or d.get("arguments")!={}:
                step["deterministic_transition_override"]=True
            if expected=="material.create_fixture":
                source=make_fixture(exe,run,workspace)
                result={"created":source.is_file(),"source_bytes":source.stat().st_size}
                success=result["created"]
            elif expected=="material.roundtrip":
                output=roundtrip(exe,source,run,workspace)
                result={"converted":output.is_file(),"output_bytes":output.stat().st_size}
                success=result["converted"]
            else:
                result=compare(source,output,workspace)
                success=result["valid"]
            step.update({"pass":success,"result":result})
        except Exception as exc:
            step.update({"pass":False,"error":repr(exc)[:700]})
        step["seconds"]=round(time.perf_counter()-start,3)
        report["steps"].append(step)
        history.append("STEP "+expected+": "+("success" if step["pass"] else "failure"))
        print("STEP",index+1,expected,step["pass"],flush=True)
        if not step["pass"]:break
    try:independent=compare(source,output,workspace) if output else {"valid":False,"reason":"roundtrip not completed"}
    except Exception as exc:independent={"valid":False,"error":repr(exc)[:400]}
    report["independent_validation"]=independent
    report["full_pass"]=len(report["steps"])==3 and all(s["pass"] for s in report["steps"]) and independent["valid"]
    report["status"]="passed" if report["full_pass"] else "failed"
    save()
    return 0 if report["full_pass"] else 1
if __name__=="__main__":sys.exit(main())
