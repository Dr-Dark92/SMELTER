"""Safe, reusable Blender geometry adapter for SMELTER.

Only predefined primitive operations are accepted. AI never supplies executable
Python, arbitrary command-line flags, or output paths.
"""
from __future__ import annotations
import json,os,pathlib,shutil,struct,subprocess

SHAPES=("cube","uv_sphere","cylinder")
def discover(explicit=None):
    if explicit:
        p=pathlib.Path(explicit).resolve()
        if not p.is_file():raise FileNotFoundError(str(p))
        return str(p)
    candidates=[]
    found=shutil.which("blender")
    if found:candidates.append(pathlib.Path(found))
    if os.name=="nt":
        for env in ("ProgramFiles","ProgramFiles(x86)"):
            base=os.getenv(env)
            if base:candidates+=sorted(pathlib.Path(base,"Blender Foundation").glob("Blender */blender.exe"),reverse=True)
        for drive in ("C:","D:","E:"):
            for folder in ("Blender","SteamLibrary/steamapps/common/Blender","Program Files/Steam/steamapps/common/Blender","Program Files (x86)/Steam/steamapps/common/Blender"):
                candidates.append(pathlib.Path(drive+"/",folder,"blender.exe"))
    for p in candidates:
        if p.is_file():return str(p.resolve())
    raise FileNotFoundError("Blender not found; supply --blender C:\\Blender\\blender.exe")

def _run(exe,args,cwd,timeout=120):
    p=subprocess.run([exe,*args],cwd=str(cwd),capture_output=True,text=True,timeout=timeout)
    if p.returncode:raise RuntimeError("Blender returned "+str(p.returncode)+": "+(p.stderr+"\n"+p.stdout)[-1400:])
    return {"returncode":p.returncode,"stdout_tail":p.stdout[-800:]}

def build(exe,workspace,shape):
    if shape not in SHAPES:raise ValueError("Shape not allowed: "+repr(shape))
    workspace=pathlib.Path(workspace).resolve()
    workspace.mkdir(parents=True,exist_ok=True)
    blend=workspace/(shape+".blend");glb=workspace/(shape+".glb")
    script=workspace/("build_"+shape+".py")
    operations={"cube":"bpy.ops.mesh.primitive_cube_add(size=2)","uv_sphere":"bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=1)","cylinder":"bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=1,depth=2)"}
    script.write_text("import bpy\nbpy.ops.object.select_all(action='SELECT')\nbpy.ops.object.delete(use_global=False)\n"+
                      operations[shape]+"\nbpy.context.object.name="+repr("SMELTER_"+shape)+
                      "\nbpy.ops.wm.save_as_mainfile(filepath="+repr(str(blend))+
                      ")\nbpy.ops.export_scene.gltf(filepath="+repr(str(glb))+",export_format='GLB',export_apply=True)\n",encoding="utf-8")
    output=_run(exe,["--background","--factory-startup","--python",str(script)],workspace)
    return {"shape":shape,"blend":str(blend),"glb":str(glb),**output}

def validate(exe,workspace,shape):
    if shape not in SHAPES:raise ValueError("Shape not allowed")
    workspace=pathlib.Path(workspace).resolve()
    blend=workspace/(shape+".blend");glb=workspace/(shape+".glb")
    if not blend.is_file() or blend.stat().st_size<100:return {"valid":False,"reason":"missing blend"}
    header=blend.open("rb").read(8)
    if not (header.startswith(b"BLENDER") or header.startswith(bytes.fromhex("28b52ffd"))):
        return {"valid":False,"reason":"invalid blend header","header_hex":header.hex()}
    try:
        _run(exe,["--background","--factory-startup",str(blend),"--python-expr",
                  "import bpy; assert bpy.data.objects.get("+repr("SMELTER_"+shape)+") is not None"],workspace,60)
    except Exception as exc:return {"valid":False,"reason":"Blender reopen failed","detail":str(exc)[:500]}
    if not glb.is_file() or glb.stat().st_size<20:return {"valid":False,"reason":"missing glb"}
    data=glb.read_bytes()
    magic,version,length=struct.unpack_from("<4sII",data)
    if magic!=b"glTF" or version!=2 or length!=len(data):return {"valid":False,"reason":"invalid glb header"}
    size,kind=struct.unpack_from("<I4s",data,12)
    if kind!=b"JSON" or size+20>len(data):return {"valid":False,"reason":"invalid glb JSON chunk"}
    doc=json.loads(data[20:20+size])
    names=[node.get("name") for node in doc.get("nodes",[])]
    valid="SMELTER_"+shape in names and len(doc.get("meshes",[]))>0
    return {"valid":valid,"shape":shape,"mesh_count":len(doc.get("meshes",[])),
            "node_found":"SMELTER_"+shape in names,"blender_reopen_verified":True,
            "blend_bytes":blend.stat().st_size,"glb_bytes":len(data)}
