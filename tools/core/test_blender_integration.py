#!/usr/bin/env python3
"""SMELTER Round 8: controlled headless Blender integration via local Ollama.

Blender is invoked only via an approved argv, with a generated script in a
dedicated workspace. No game installations or existing assets are touched.
"""
from __future__ import annotations
import argparse,datetime,json,os,pathlib,shutil,struct,subprocess,sys,time,urllib.request,uuid

def ask(url,model,system,history,timeout):
    payload={"model":model,"system":system,"prompt":"\n".join(history),"stream":False,
             "think":False,"format":"json","options":{"temperature":0,"num_ctx":8192,"num_predict":450}}
    req=urllib.request.Request(url.rstrip("/")+"/api/generate",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as r:response=json.load(r)
    decision=json.loads(response["response"])
    if not isinstance(decision,dict):raise ValueError("Decision must be JSON object")
    return decision

def locate_blender():
    candidates=[]
    onpath=shutil.which("blender")
    if onpath:candidates.append(pathlib.Path(onpath))
    if os.name=="nt":
        for env in ("ProgramFiles","ProgramFiles(x86)"):
            base=os.environ.get(env)
            if base:
                candidates.extend(sorted(pathlib.Path(base,"Blender Foundation").glob("Blender */blender.exe"),reverse=True))
    if os.name=="nt":
        for env in ("LOCALAPPDATA","USERPROFILE"):
            base=os.environ.get(env)
            if base:
                for relative in ("Programs/Blender Foundation","scoop/apps/blender/current","scoop/apps/blender"):
                    folder=pathlib.Path(base,relative)
                    if folder.is_dir():
                        candidates.extend(folder.glob("**/blender.exe"))
        for drive in ("C:","D:","E:"):
            for relative in ("SteamLibrary/steamapps/common/Blender","Program Files (x86)/Steam/steamapps/common/Blender","Program Files/Steam/steamapps/common/Blender","Blender"):
                folder=pathlib.Path(drive+"/",relative)
                if folder.is_dir():
                    candidates.extend(folder.glob("blender.exe"))
                    candidates.extend(folder.glob("*/blender.exe"))
    for candidate in candidates:
        if candidate.is_file():return str(candidate.resolve())
    return None

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\SMELTER");p.add_argument("--model",default="qwen3.5:9b")
    p.add_argument("--url",default="http://127.0.0.1:11434");p.add_argument("--timeout",type=int,default=180)
    p.add_argument("--blender",default=None,help="Explicit path to trusted Blender executable")
    a=p.parse_args();root=pathlib.Path(a.root).resolve()
    run=root/"workspace"/"smelter-blender"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6])
    run.mkdir(parents=True,exist_ok=True)
    report={"test":"SMELTER headless Blender integration v1","model":a.model,"steps":[],"full_pass":False}
    report_path=run/"smelter-blender.json"
    def save():
        report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
        print("REPORT:",report_path,"FULL PASS:",report["full_pass"],flush=True)
    exe=str(pathlib.Path(a.blender).resolve()) if a.blender else locate_blender()
    if not exe or not pathlib.Path(exe).is_file():
        report.update({"status":"blocked","reason":"Blender executable not found; install Blender or pass --blender with its executable path"})
        save();return 2
    try:
        version=subprocess.run([exe,"--version"],capture_output=True,text=True,timeout=25,check=True)
        report["blender_version"]=version.stdout.splitlines()[0][:120]
    except Exception as exc:
        report.update({"status":"blocked","reason":"Blender version check failed: "+repr(exc)})
        save();return 2
    blend=run/"smelter_cube.blend";glb=run/"smelter_cube.glb";script=run/"make_asset.py"
    # Generated script is static, not AI-provided code.
    script.write_text(
        "import bpy\n"
        "bpy.ops.object.select_all(action='SELECT')\n"
        "bpy.ops.object.delete(use_global=False)\n"
        "bpy.ops.mesh.primitive_cube_add(size=2, location=(0,0,0))\n"
        "bpy.context.object.name='SMELTER_TestCube'\n"
        "bpy.ops.wm.save_as_mainfile(filepath="+repr(str(blend)) +")\n"
        "bpy.ops.export_scene.gltf(filepath="+repr(str(glb))+", export_format='GLB', export_apply=True)\n",
        encoding="utf-8")
    def run_blender():
        proc=subprocess.run([exe,"--background","--factory-startup","--python",str(script)],
                            cwd=str(run),capture_output=True,text=True,timeout=150)
        result={"returncode":proc.returncode,"stdout_tail":proc.stdout[-1800:],"stderr_tail":proc.stderr[-1800:]}
        if proc.returncode!=0:raise RuntimeError("Blender failed: "+json.dumps(result))
        return result
    def validate():
        if not blend.is_file() or blend.stat().st_size<100:return {"valid":False,"reason":"missing blend"}
        header=blend.open("rb").read(16)
        if not header.startswith(b"BLENDER"):return {"valid":False,"reason":"invalid blend header","header_hex":header.hex(),"header_repr":repr(header),"file_size":blend.stat().st_size}
        if not glb.is_file() or glb.stat().st_size<20:return {"valid":False,"reason":"missing glb"}
        data=glb.read_bytes()
        magic,version,length=struct.unpack_from("<4sII",data)
        if magic!=b"glTF" or version!=2 or length!=len(data):return {"valid":False,"reason":"invalid GLB header"}
        chunk_length,chunk_type=struct.unpack_from("<I4s",data,12)
        if chunk_type!=b"JSON" or 20+chunk_length>len(data):return {"valid":False,"reason":"missing GLB JSON"}
        gltf=json.loads(data[20:20+chunk_length].decode("utf-8"))
        names=[x.get("name","") for x in gltf.get("nodes",[])]
        meshes=gltf.get("meshes",[])
        return {"valid":"SMELTER_TestCube" in names and bool(meshes),
                "node_found":"SMELTER_TestCube" in names,"mesh_count":len(meshes),
                "blend_bytes":blend.stat().st_size,"glb_bytes":len(data)}
    system=("You are SMELTER's local asset integration agent. Only tools are blender.build_cube and artifact.validate. "
            "Choose one tool per response and return JSON object with tool_id, arguments, reason. "
            "First call blender.build_cube with empty arguments {}, then artifact.validate with empty arguments {}. "
            "Never invent paths, code, or command lines. Do not repeat successful steps.")
    history=["GOAL: Create a test 3D mesh with approved headless Blender tool and validate real .blend and .glb files."]
    built=False;verified=False
    for i in range(5):
        entry={"step":i+1};started=time.perf_counter()
        try:
            decision=ask(a.url,a.model,system,history,a.timeout);entry["decision"]=decision
            tool=decision.get("tool_id");arguments=decision.get("arguments")
            if arguments!={}:raise ValueError("Tool arguments must be empty object")
            if tool=="blender.build_cube":
                if built:raise ValueError("Already built")
                result=run_blender();built=True
            elif tool=="artifact.validate":
                if not built:raise ValueError("Build first")
                result=validate();verified=result.get("valid") is True
            else:raise ValueError("Unknown tool")
            entry["result"]=result;entry["pass"]=True
            history.extend(["MODEL_DECISION: "+json.dumps(decision),"ACTUAL_TOOL_RESULT: "+json.dumps(result)])
        except Exception as exc:
            entry["pass"]=False;entry["error"]=repr(exc)[:2400]
            history.append("TOOL_ERROR: "+repr(exc)[:600]+"; use the next required registered tool.")
        entry["wall_seconds"]=round(time.perf_counter()-started,3)
        report["steps"].append(entry)
        print("STEP",i+1,entry.get("decision",{}).get("tool_id"),"PASS" if entry["pass"] else "FAIL",flush=True)
        if verified:break
    final_check=validate()
    report.update({"built":built,"model_validated":verified,"independent_validation":final_check,
                   "full_pass":built and verified and final_check.get("valid") is True,
                   "status":"passed" if built and verified and final_check.get("valid") is True else "failed"})
    save();return 0 if report["full_pass"] else 1
if __name__=="__main__":sys.exit(main())
