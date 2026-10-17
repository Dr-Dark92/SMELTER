"""Round 12 Blender scene fingerprints and negative integrity tests.

Fingerprints use imported Blender mesh loops in polygon traversal order, quantized
positions/UVs, material PBR factors, and decoded image pixels. This is a strict
round-trip check, not a general topology-invariant mesh comparison.
"""
from __future__ import annotations
import json,pathlib,subprocess

def _inside(p,workspace):
    p=pathlib.Path(p).resolve()
    if not p.is_relative_to(pathlib.Path(workspace).resolve()):raise ValueError("Outside workspace")
    if p.suffix.lower()!=".glb" or not p.is_file():raise ValueError("Existing GLB required")
    return p

def fingerprint(exe,source,workspace,tag):
    source=_inside(source,workspace)
    folder=pathlib.Path(workspace).resolve()/"smelter-round12"/"fingerprints"
    folder.mkdir(parents=True,exist_ok=True)
    if not tag.isidentifier():raise ValueError("Invalid tag")
    output=folder/(tag+".json")
    script=folder/(tag+".py")
    body=r'''import bpy,json,hashlib,struct,math
from mathutils import Vector
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=SOURCE)
def quant(v):return round(float(v),5)
def digest(values):
 h=hashlib.sha256()
 for row in values:
  h.update(json.dumps(row,separators=(",",":"),sort_keys=True).encode())
  h.update(b"\n")
 return h.hexdigest()
meshes=[]
for ob in sorted((x for x in bpy.data.objects if x.type=="MESH"),key=lambda x:x.name):
 mesh=ob.data
 mesh.calc_loop_triangles()
 uv=mesh.uv_layers.active
 rows=[]
 for poly in mesh.polygons:
  for li in poly.loop_indices:
   v=mesh.vertices[mesh.loops[li].vertex_index]
   pos=ob.matrix_world @ v.co
   tex=uv.data[li].uv if uv else None
   rows.append([*[quant(x) for x in pos],*([quant(x) for x in tex] if tex else [])])
 vertices=[[quant(x) for x in ob.matrix_world @ v.co] for v in mesh.vertices]
 meshes.append({"name":ob.name,"vertices":len(mesh.vertices),"polygons":len(mesh.polygons),
  "triangles":len(mesh.loop_triangles),"uv_present":uv is not None,
  "loop_fingerprint":digest(rows),"position_fingerprint":digest(sorted(vertices)),
  "bounds_min":[min(v[i] for v in vertices) for i in range(3)] if vertices else [],
  "bounds_max":[max(v[i] for v in vertices) for i in range(3)] if vertices else []})
materials=[]
for m in sorted(bpy.data.materials,key=lambda x:x.name):
 if m.users<1:continue
 node=m.node_tree.nodes.get("Principled BSDF") if m.use_nodes else None
 pbr={}
 if node:
  for field in ("Base Color","Metallic","Roughness"):
   socket=node.inputs.get(field)
   if socket:
    val=socket.default_value
    pbr[field]=[quant(x) for x in val] if hasattr(val,"__len__") else quant(val)
 materials.append({"name":m.name,"pbr":pbr})
images=[]
for img in sorted(bpy.data.images,key=lambda x:x.name):
 if img.users<1:continue
 img.pixels[0] if len(img.pixels)>0 else None
 h=hashlib.sha256()
 # Pixel float32 serialization allows tiny decoder drift tolerance through quantization.
 for i in range(0,len(img.pixels),4096):
  for v in img.pixels[i:i+4096]:h.update(struct.pack("<I",round(max(0,min(1,float(v)))*255)))
 images.append({"name":img.name,"width":img.size[0],"height":img.size[1],"pixel_sha256":h.hexdigest()})
with open(OUTPUT,"w",encoding="utf-8") as f:
 json.dump({"meshes":meshes,"materials":materials,"images":images},f,indent=2)
'''
    script.write_text(body.replace("SOURCE",repr(str(source))).replace("OUTPUT",repr(str(output))),encoding="utf-8")
    proc=subprocess.run([exe,"--background","--factory-startup","--python",str(script)],
                        cwd=str(folder),capture_output=True,text=True,timeout=120)
    if proc.returncode:raise RuntimeError("Blender fingerprint failed: "+(proc.stderr+"\n"+proc.stdout)[-1000:])
    return json.loads(output.read_text(encoding="utf-8"))

def compare(a,b):
    # Blender may rename imported images or materials on re-export; compare contents.
    def normalize(fp):
        return {"meshes":[{k:v for k,v in m.items() if k!="name"} for m in fp["meshes"]],
                "materials":[m["pbr"] for m in fp["materials"]],
                "images":[{k:v for k,v in i.items() if k!="name"} for i in fp["images"]]}
    left,right=normalize(a),normalize(b)
    # GLB round-trips can split vertices at UV/material seams. A changed
    # vertex count is diagnostic metadata, not proof of altered geometry.
    # Polygon-corner world positions + UVs remain the strict geometry gate.
    def canonical_meshes(meshes):
        return [{k:v for k,v in mesh.items() if k not in ("vertices","position_fingerprint")} for mesh in meshes]
    mismatches={}
    for key in left:
        lhs=canonical_meshes(left[key]) if key=="meshes" else left[key]
        rhs=canonical_meshes(right[key]) if key=="meshes" else right[key]
        if lhs!=rhs:mismatches[key]={"source":lhs,"target":rhs}
    vertex_count_changes=[{"mesh":i,"source":x["vertices"],"target":y["vertices"]}
                          for i,(x,y) in enumerate(zip(left["meshes"],right["meshes"]))
                          if x["vertices"]!=y["vertices"]]
    return {"valid":not mismatches and bool(left["meshes"]) and bool(left["materials"]) and bool(left["images"]),
            "mismatch_categories":list(mismatches),"details":mismatches,
            "vertex_representation_changes":vertex_count_changes,
            "comparison":"quantized Blender-imported polygon-corner world positions/UVs, topology counts, bounds, material PBR defaults, decoded 8-bit pixels; vertex count differences reported separately"}

def negative_mutation(fp):
    altered=json.loads(json.dumps(fp))
    if not altered["meshes"]:raise ValueError("No mesh to mutate")
    altered["meshes"][0]["bounds_max"][0]+=0.25
    return altered
