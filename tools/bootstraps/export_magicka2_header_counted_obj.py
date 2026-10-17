#!/usr/bin/env python3
"""Export Magicka2 bounded, header-counted OBJ meshes (no game modification)."""
import argparse,datetime,json,math,pathlib,struct,uuid,collections
RES=(("91e92dee4343fc7d",1407033),("bd494ea7299b6750",4918276))
def extract(blob,at,dest):
 vbytes=struct.unpack_from("<I",blob,at+48)[0];vstart=at+52;tail=vstart+vbytes
 n,stride=struct.unpack_from("<II",blob,tail+8)
 if stride!=88 or n*stride!=vbytes:raise ValueError("Vertex header mismatch")
 icount,ibytes=struct.unpack_from("<II",blob,tail+151)
 if icount<=0 or icount%3 or ibytes!=icount*2:raise ValueError("Index count/byte length mismatch")
 istart=tail+159
 if istart+ibytes>len(blob):raise ValueError("Truncated index buffer")
 indices=struct.unpack_from("<"+str(icount)+"H",blob,istart)
 if max(indices)>=n:raise ValueError("Index out of vertex bounds")
 vertices=[struct.unpack_from("<3f",blob,vstart+i*stride) for i in range(n)]
 if not all(all(math.isfinite(x) for x in v) for v in vertices):raise ValueError("Invalid vertex coordinate")
 zero=0
 with dest.open("w",encoding="utf-8") as f:
  f.write("# SMELTER Magicka2 index-counted OBJ; UV/rig/materials not yet decoded\n")
  for v in vertices:f.write("v %.9g %.9g %.9g\n"%v)
  f.write("o magicka2_index_counted\n")
  for i in range(0,icount,3):
   tri=indices[i:i+3]
   a,b,c=(vertices[j] for j in tri)
   ab=[b[k]-a[k] for k in range(3)];ac=[c[k]-a[k] for k in range(3)]
   cross=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0])
   if len(set(tri))<3 or sum(x*x for x in cross)<1e-18:zero+=1
   f.write("f %d %d %d\n"%tuple(x+1 for x in tri))
 return {"vertex_count":n,"vertex_stride":stride,"index_count":icount,"index_bytes":ibytes,"triangle_count":icount//3,"zero_area_triangles":zero,"referenced_vertices":len(set(indices)),"index_start":istart,"obj":str(dest),"header_length_consistent":True,"rigging_verified":False,"materials_verified":False,"visual_mesh_verified":False}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 root=pathlib.Path(a.root);base=root/"workspace"/"magicka2-reconstructed"
 dirs=sorted((d for d in base.iterdir() if d.is_dir() and all((d/(name+".decoded.bin")).is_file() for name,_ in RES)),reverse=True)
 if not dirs:p.error("Reconstructed Magicka2 files missing")
 out=root/"workspace"/"magicka2-full-geometry"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 report={"tool":"SMELTER header-counted Magicka2 OBJ v1","read_only_game_sources":True,"geometry_header_verified":True,"visual_mesh_verified":False,"resources":[]}
 for name,at in RES:
  info=extract((dirs[0]/(name+".decoded.bin")).read_bytes(),at,out/(name+".obj"))
  report["resources"].append({"name":name,**info})
 path=out/"magicka2-full-geometry.json";path.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Geometry report:",path)
 for item in report["resources"]:print(item["name"],item["triangle_count"],"triangles,",item["zero_area_triangles"],"zero-area; OBJ:",item["obj"])
 print("Geometry preview only; not a Skyrim outfit or rigged NIF.")
if __name__=="__main__":main()
