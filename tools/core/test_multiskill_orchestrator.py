#!/usr/bin/env python3
"""Round 7: model-directed multi-skill coordination with real sandboxed PNG inspection."""
from __future__ import annotations
import argparse,datetime,json,pathlib,struct,sys,time,urllib.request,uuid,zlib
from smelter_registry import Registry,Capability

SKILLS=("universal-modder-game-recon","universal-modder-asset-pipeline")
def infer(url,model,system,history,timeout):
    payload={"model":model,"system":system,"prompt":"\n".join(history),"stream":False,"think":False,"format":"json","options":{"temperature":0,"num_ctx":8192,"num_predict":600}}
    req=urllib.request.Request(url.rstrip("/")+"/api/generate",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as response: data=json.load(response)
    decision=json.loads(data["response"])
    if not isinstance(decision,dict):raise ValueError("Model decision must be an object")
    return decision,data.get("eval_count")

def png_bytes():
    def chunk(tag,payload):return struct.pack(">I",len(payload))+tag+payload+struct.pack(">I",zlib.crc32(tag+payload)&0xffffffff)
    scan=b"".join(b"\x00"+b"\x00\x80\xff\xff"*3 for _ in range(2))
    return b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",3,2,8,6,0,0,0))+chunk(b"IDAT",zlib.compress(scan))+chunk(b"IEND",b"")

def main():
    p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");p.add_argument("--model",default="qwen3.5:9b")
    p.add_argument("--url",default="http://127.0.0.1:11434");p.add_argument("--timeout",type=int,default=180);p.add_argument("--max-steps",type=int,default=10)
    a=p.parse_args();root=pathlib.Path(a.root).resolve()
    run=root/"workspace"/"smelter-multiskill"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6])
    run.mkdir(parents=True,exist_ok=True)
    fixture=run/"fixture.png";fixture.write_bytes(png_bytes())
    output=run/"inspection.json"
    registry=Registry(root);loaded=set();inspected=False;written=False;validated=False;model_validated=False;seen=set()
    def skills_list(x):return {"skills":[{"id":s["id"],"description":s["description"]} for s in registry.skills()]}
    def skills_read(x):return {"skill_id":x["skill_id"],"instructions":registry.skill_instructions(x["skill_id"],limit=3500)}
    def inspect(x):
        if x["filename"]!="fixture.png":raise ValueError("Only approved fixture.png")
        data=fixture.read_bytes()
        if len(data)<33 or data[:8]!=b"\x89PNG\r\n\x1a\n" or data[12:16]!=b"IHDR":raise ValueError("Invalid PNG")
        width,height,depth,ctype=struct.unpack(">IIBB",data[16:26])
        return {"filename":"fixture.png","width":width,"height":height,"bit_depth":depth,"color_type":ctype,"alpha":ctype in (4,6)}
    def write(x):
        if x["filename"]!="inspection.json":raise ValueError("Only approved inspection.json")
        payload=json.dumps(x["data"],indent=2,sort_keys=True)
        if len(payload)>4096:raise ValueError("Artifact too large")
        output.write_text(payload,encoding="utf-8")
        return {"status":"written"}
    def validate(x):
        if x["filename"]!="inspection.json":raise ValueError("Only approved inspection.json")
        if not output.is_file():return {"valid":False,"reason":"missing"}
        actual=json.loads(output.read_text(encoding="utf-8"))
        expected={"source_skills":list(SKILLS),"image":"fixture.png","width":3,"height":2,"alpha":True}
        return {"valid":actual==expected,"expected":expected}
    registry.register(Capability("skills.list","List installed skills",{},skills_list))
    registry.register(Capability("skills.read","Read installed skill instructions",{"skill_id":"string"},skills_read))
    registry.register(Capability("image.inspect_png","Inspect approved sandbox PNG header",{"filename":"string"},inspect))
    registry.register(Capability("artifact.write","Write sandbox JSON report",{"filename":"string","data":"object"},write,read_only=False))
    registry.register(Capability("artifact.validate","Independently validate sandbox report",{"filename":"string"},validate))
    expected={"source_skills":list(SKILLS),"image":"fixture.png","width":3,"height":2,"alpha":True}
    goal=("Discover installed skills, read BOTH game-recon and asset-pipeline instructions, inspect fixture.png using image.inspect_png, "
          "then write inspection.json with exact JSON object "+json.dumps(expected)+", then validate it. "
          "Use only registered capabilities and never touch game installations.")
    system=("You are SMELTER's bounded multi-skill agent. One tool per turn; respond with JSON object "
            '{"tool_id":"registered.name","arguments":{},"reason":"..."}. '
            "Call skills.list, read BOTH skills "+json.dumps(SKILLS)+", inspect fixture.png, write inspection.json, validate inspection.json. "
            "Do not skip or repeat steps. Parameter type labels (string/object) are schema, NOT argument values. "
            "For artifact.write, data must be actual JSON object "+json.dumps(expected)+". "
            "Available tools: "+json.dumps(registry.catalog()))
    history=["USER_GOAL: "+goal];report={"test":"SMELTER multi-skill execution v1","model":a.model,"goal":goal,"steps":[],"skills_discovered":len(registry.skills())}
    for i in range(max(1,min(a.max_steps,14))):
        entry={"step":i+1};start=time.perf_counter()
        try:
            d,tokens=infer(a.url,a.model,system,history,a.timeout);entry["decision"]=d;entry["eval_count"]=tokens
            tool=d.get("tool_id");params=d.get("arguments")
            if tool=="skills.read" and params.get("skill_id") not in SKILLS:raise ValueError("Unrelated skill")
            if tool=="skills.read" and not any(s.get("decision",{}).get("tool_id")=="skills.list" and s.get("pass") for s in report["steps"]):raise ValueError("Discover skills first")
            if tool=="image.inspect_png" and loaded!=set(SKILLS):raise ValueError("Read both skills first")
            if tool=="artifact.write" and not inspected:raise ValueError("Inspect PNG first")
            if tool=="artifact.validate" and not written:raise ValueError("Write report first")
            signature=json.dumps([tool,params],sort_keys=True)
            if signature in seen:raise ValueError("Repeated tool call; correct arguments")
            seen.add(signature)
            result=registry.invoke(tool,params,allow_writes=(tool=="artifact.write"))
            if tool=="skills.read":loaded.add(params["skill_id"])
            if tool=="image.inspect_png":inspected=(result["width"]==3 and result["height"]==2 and result["alpha"] is True)
            if tool=="artifact.write":written=True
            if tool=="artifact.validate":model_validated=(result["valid"] is True)
            entry["pass"]=True
            entry["result"]=result if tool!="skills.read" else {"skill_id":params["skill_id"],"instructions_loaded":True}
            history.extend(["MODEL_DECISION: "+json.dumps(d),"ACTUAL_TOOL_RESULT: "+json.dumps(result if tool!="skills.read" else {"skill_id":params["skill_id"],"instructions":result["instructions"][:2500]})])
        except Exception as e:
            entry["pass"]=False;entry["error"]=repr(e)
            history.append("TOOL_ERROR: "+repr(e)+"; use actual JSON argument values and select next incomplete step.")
        entry["wall_seconds"]=round(time.perf_counter()-start,3);report["steps"].append(entry)
        print("STEP",i+1,entry.get("decision",{}).get("tool_id"),"PASS" if entry["pass"] else "FAIL",flush=True)
        if model_validated:break
    try:independent=json.loads(output.read_text(encoding="utf-8"))==expected
    except (OSError,ValueError):independent=False
    report.update({"skills_loaded":sorted(loaded),"png_inspected":inspected,"report_written":written,"model_validated":model_validated,
                   "independent_check":independent,"full_pass":loaded==set(SKILLS) and inspected and written and model_validated and independent,
                   "completion_source":"model_tool_validation" if model_validated else "step_limit"})
    dest=run/"smelter-multiskill.json";dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("REPORT:",dest,"FULL PASS:",report["full_pass"])
    return 0 if report["full_pass"] else 1
if __name__=="__main__":sys.exit(main())
