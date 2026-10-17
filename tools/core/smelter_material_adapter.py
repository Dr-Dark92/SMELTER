"""Round 11: deterministic textured GLB round-trip with structural invariants.

All outputs remain inside SMELTER workspace; no user-supplied Python is executed.
"""
from __future__ import annotations
import json,pathlib,subprocess,struct

def _path(p,root):
    p=pathlib.Path(p).resolve()
    if not p.is_relative_to(pathlib.Path(root).resolve()):
        raise ValueError("Path outside SMELTER workspace")
    return p

def _execute(exe,script,folder):
    p=subprocess.run([exe,"--background","--factory-startup","--python",str(script)],
                     cwd=str(folder),capture_output=True,text=True,timeout=120)
    if p.returncode:
        raise RuntimeError("Blender failed: "+(p.stdout+"\n"+p.stderr)[-1200:])
    return {"exit_code":p.returncode,"stdout_tail":p.stdout[-350:]}

def _script(folder,name,body):
    path=folder/name
    path.write_text(body,encoding="utf-8")
    return path

def make_fixture(exe,folder,workspace):
    folder=_path(folder,workspace);folder.mkdir(parents=True,exist_ok=True)
    dest=folder/"textured_source.glb"
    body=("import bpy\n"
          "bpy.ops.object.select_all(action='SELECT')\n"
          "bpy.ops.object.delete(use_global=False)\n"
          "bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16)\n"
          "obj=bpy.context.object\nobj.name='SMELTER_TexturedSphere'\n"
          "assert obj.data.uv_layers.active is not None\n"
          "img=bpy.data.images.new('SMELTER_Checker',width=4,height=4,alpha=True)\n"
          "pixels=[]\n"
          "for y in range(4):\n"
          " for x in range(4):\n"
          "  pixels.extend((1.0,0.15,0.1,1.0) if (x+y)%2 else (0.1,0.45,1.0,1.0))\n"
          "img.pixels[:]=pixels\nimg.pack()\n"
          "mat=bpy.data.materials.new('SMELTER_TexturedMaterial')\n"
          "mat.use_nodes=True\n"
          "nodes=mat.node_tree.nodes\n"
          "shader=nodes.get('Principled BSDF')\n"
          "tex=nodes.new('ShaderNodeTexImage')\ntex.image=img\n"
          "mat.node_tree.links.new(tex.outputs['Color'],shader.inputs['Base Color'])\n"
          "obj.data.materials.append(mat)\n"
          "bpy.ops.export_scene.gltf(filepath="+repr(str(dest))+",export_format='GLB')\n")
    _execute(exe,_script(folder,"round11_fixture.py",body),folder)
    return dest

def roundtrip(exe,source,folder,workspace):
    source=_path(source,workspace);folder=_path(folder,workspace)
    if source.suffix.lower()!=".glb" or not source.is_file():
        raise ValueError("Source must be an existing GLB")
    folder.mkdir(parents=True,exist_ok=True)
    output=folder/"textured_roundtrip.glb"
    body=("import bpy\n"
          "bpy.ops.object.select_all(action='SELECT')\n"
          "bpy.ops.object.delete(use_global=False)\n"
          "bpy.ops.import_scene.gltf(filepath="+repr(str(source))+")\n"
          "assert any(o.type=='MESH' for o in bpy.data.objects)\n"
          "bpy.ops.export_scene.gltf(filepath="+repr(str(output))+",export_format='GLB')\n")
    _execute(exe,_script(folder,"round11_roundtrip.py",body),folder)
    return output

def inspect(source,workspace):
    source=_path(source,workspace)
    data=source.read_bytes()
    if len(data)<20 or data[:4]!=b"glTF":raise ValueError("Bad GLB")
    version,length=struct.unpack_from("<II",data,4)
    size,kind=struct.unpack_from("<I4s",data,12)
    if version!=2 or length!=len(data) or kind!=b"JSON" or 20+size>len(data):
        raise ValueError("Bad GLB header or JSON")
    doc=json.loads(data[20:20+size])
    meshes=doc.get("meshes",[])
    primitives=[p for mesh in meshes for p in mesh.get("primitives",[])]
    textured=sum("TEXCOORD_0" in p.get("attributes",{}) for p in primitives)
    materials=doc.get("materials",[])
    textured_materials=sum(bool(m.get("pbrMetallicRoughness",{}).get("baseColorTexture")) for m in materials)
    result={"mesh_count":len(meshes),"primitive_count":len(primitives),
            "uv_primitives":textured,"material_count":len(materials),
            "textured_materials":textured_materials,
            "image_count":len(doc.get("images",[])),
            "texture_count":len(doc.get("textures",[])),
            "bytes":len(data)}
    result["valid"]=all((result["mesh_count"]>0,result["uv_primitives"]>0,
                         result["material_count"]>0,result["textured_materials"]>0,
                         result["image_count"]>0,result["texture_count"]>0))
    return result

def compare(source,target,workspace):
    a=inspect(source,workspace);b=inspect(target,workspace)
    keys=("mesh_count","primitive_count","uv_primitives","material_count",
          "textured_materials","image_count","texture_count")
    differences={k:{"source":a[k],"roundtrip":b[k]} for k in keys if a[k]!=b[k]}
    return {"valid":a["valid"] and b["valid"] and not differences,
            "source":a,"roundtrip":b,"differences":differences,
            "scope":"structural counts only; not pixel/vertex equivalence"}
