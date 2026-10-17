"""Allowlisted import/convert/validate operations for existing 3D assets.

All files must live inside SMELTER's workspace. AI selects registered operations,
never scripts, shell commands, executable paths, or arbitrary output destinations.
"""
from __future__ import annotations
import json,pathlib,subprocess

def _inside(path,root):
    path=pathlib.Path(path).resolve()
    if not path.is_relative_to(pathlib.Path(root).resolve()):
        raise ValueError("Asset path must remain inside SMELTER workspace")
    return path

def inspect_glb(source,workspace):
    source=_inside(source,workspace)
    if source.suffix.lower()!=".glb" or not source.is_file():
        raise ValueError("Expected existing GLB source")
    data=source.read_bytes()
    if len(data)<20 or data[:4]!=b"glTF":
        raise ValueError("Invalid GLB magic")
    import struct
    version,length=struct.unpack_from("<II",data,4)
    if version!=2 or length!=len(data):
        raise ValueError("Invalid GLB version or length")
    chunk_length,chunk_type=struct.unpack_from("<I4s",data,12)
    if chunk_type!=b"JSON" or 20+chunk_length>len(data):
        raise ValueError("Missing GLB JSON chunk")
    doc=json.loads(data[20:20+chunk_length])
    count=len(doc.get("meshes",[]))
    if count<1:raise ValueError("GLB has no meshes")
    return {"valid":True,"mesh_count":count,"node_names":[n.get("name","") for n in doc.get("nodes",[])][:20],"bytes":len(data)}

def _run(exe,script,workspace,timeout=90):
    proc=subprocess.run([exe,"--background","--factory-startup","--python",str(script)],
                        cwd=str(workspace),capture_output=True,text=True,timeout=timeout)
    if proc.returncode:
        raise RuntimeError("Blender conversion failed: "+(proc.stderr+"\n"+proc.stdout)[-1300:])
    return {"returncode":proc.returncode,"stdout_tail":proc.stdout[-600:]}

def convert_glb_to_obj(exe,source,destination,workspace):
    source=_inside(source,workspace)
    destination=_inside(destination,workspace)
    if source.suffix.lower()!=".glb" or destination.suffix.lower()!=".obj":
        raise ValueError("Only GLB to OBJ conversion is permitted")
    if source==destination:raise ValueError("Input and output must differ")
    inspect_glb(source,workspace)
    destination.parent.mkdir(parents=True,exist_ok=True)
    # The script is fixed by the trusted adapter; no AI-generated code is executed.
    script=destination.parent/"smelter_convert_glb_obj.py"
    script.write_text("import bpy\n"
                      "bpy.ops.object.select_all(action='SELECT')\n"
                      "bpy.ops.object.delete(use_global=False)\n"
                      "bpy.ops.import_scene.gltf(filepath="+repr(str(source))+")\n"
                      "assert any(o.type=='MESH' for o in bpy.data.objects)\n"
                      "bpy.ops.wm.obj_export(filepath="+repr(str(destination))+",export_selected_objects=False)\n",
                      encoding="utf-8")
    result=_run(exe,script,destination.parent)
    return {"converted":destination.is_file(),"obj_bytes":destination.stat().st_size if destination.is_file() else 0,**result}

def validate_obj(exe,destination,workspace):
    destination=_inside(destination,workspace)
    if destination.suffix.lower()!=".obj" or not destination.is_file():
        return {"valid":False,"reason":"OBJ missing"}
    # Parse OBJ geometry directly, independently of Blender's export success code.
    vertices=faces=0
    for line in destination.open("r",encoding="utf-8",errors="replace"):
        if line.startswith("v "):vertices+=1
        elif line.startswith("f "):faces+=1
    if vertices<3 or faces<1:
        return {"valid":False,"reason":"OBJ has insufficient geometry","vertices":vertices,"faces":faces}
    script=destination.parent/"smelter_validate_obj.py"
    script.write_text("import bpy\n"
                      "bpy.ops.object.select_all(action='SELECT')\n"
                      "bpy.ops.object.delete(use_global=False)\n"
                      "bpy.ops.wm.obj_import(filepath="+repr(str(destination))+")\n"
                      "assert any(o.type=='MESH' and len(o.data.vertices)>=3 and len(o.data.polygons)>=1 for o in bpy.data.objects)\n",
                      encoding="utf-8")
    try:_run(exe,script,destination.parent,60)
    except Exception as exc:
        return {"valid":False,"reason":"Blender OBJ reimport failed","error":str(exc)[:500]}
    return {"valid":True,"vertices":vertices,"faces":faces,"blender_reimport_verified":True,"obj_bytes":destination.stat().st_size}
