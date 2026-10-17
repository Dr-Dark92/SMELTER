#!/usr/bin/env python3
"""SMELTER Magicka2 88-byte vertex record and triangle binding audit (read-only)."""
import argparse,datetime,json,math,pathlib,struct,uuid,collections
IDS=("91e92dee4343fc7d","bd494ea7299b6750")
OFFSETS=(1407033,4918276)
def geometry(blob,at):
 count_bytes=struct.unpack_from("<I",blob,at+48)[0]
 vstart=at+52;tail=vstart+count_bytes
 vertex_count,stride=struct.unpack_from("<II",blob,tail+8)
 if stride!=88 or vertex_count*stride!=count_bytes:raise ValueError("88-byte vertex framing not verified")
 # Find candidate u16 index starts near the beginning of the tail; score topology and index range.
 choices=[]
 for align in range(0,min(320,len(blob)-tail-512)):
  n=min(1200,(len(blob)-tail-align)//2)
  n-=n%3
  if n<120:continue
  values=struct.unpack_from("<"+str(n)+"H",blob,tail+align)
  # Evaluate 120 indices to avoid mixing neighboring sections.
  values=values[:120]
  valid=sum(v<vertex_count for v in values)
  triangles=[values[i:i+3] for i in range(0,len(values),3)]
  distinct=[t for t in triangles if len(set(t))==3 and max(t)<vertex_count]
  edges=collections.Counter(tuple(sorted((t[a],t[b]))) for t in distinct for a,b in ((0,1),(1,2),(2,0)))
  shared=sum(v>1 for v in edges.values())
  if valid>=115 and len(distinct)>=34 and shared>=12:
   choices.append({"relative_offset":align,"absolute_offset":tail+align,"valid_indices":valid,"max_index":max(values),"distinct_triangles":len(distinct),"shared_edges":shared,"first_24_indices":list(values[:24])})
 choices.sort(key=lambda x:(-x["shared_edges"],-x["valid_indices"]))
 # Check potential xyz at every 4-byte offset in 88-byte records using all vertices.
 layouts=[]
 for offset in range(0,77,4):
  xyz=[struct.unpack_from("<3f",blob,vstart+i*88+offset) for i in range(vertex_count)]
  if not all(all(math.isfinite(v) and abs(v)<100000 for v in p) for p in xyz):continue
  spans=[max(p[j] for p in xyz)-min(p[j] for p in xyz) for j in range(3)]
  unique=len(set(xyz));integer=sum(all(abs(v-round(v))<1e-6 for v in p) for p in xyz)
  # A position field should vary on all axes, not be mostly exact small integers.
  if min(spans)>0.01:
   layouts.append({"offset":offset,"unique_vertices":unique,"integer_triplets":integer,"axis_spans":[round(v,5) for v in spans],"first_three":[list(x) for x in xyz[:3]]})
 layouts.sort(key=lambda x:(-x["unique_vertices"],x["integer_triplets"]))
 return {"vertex_count":vertex_count,"vertex_stride":stride,"vertex_bytes":count_bytes,"exact_size_match":vertex_count*stride==count_bytes,"tail_start":tail,"index_candidates":choices[:16],"position_candidates":layouts[:12],"warning":"88-byte records verified by size arithmetic; position offsets and index bindings remain hypotheses."}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 root=pathlib.Path(a.root);base=root/"workspace"/"magicka2-reconstructed"
 folders=sorted((d for d in base.iterdir() if d.is_dir() and all((d/(n+".decoded.bin")).is_file() for n in IDS)),reverse=True)
 if not folders:p.error("Missing reconstructed resources")
 result={"tool":"Magicka2 vertex-index binding v1","read_only":True,"mesh_verified":False,"source":str(folders[0]),"resources":[]}
 for name,at in zip(IDS,OFFSETS):
  result["resources"].append({"name":name,"audit":geometry((folders[0]/(name+".decoded.bin")).read_bytes(),at)})
 out=root/"workspace"/"magicka2-vertex-binding"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 path=out/"magicka2-vertex-binding.json";path.write_text(json.dumps(result,indent=2),encoding="utf-8")
 print("Vertex binding audit:",path)
 for r in result["resources"]:print(r["name"],"vertices:",r["audit"]["vertex_count"],"index candidates:",len(r["audit"]["index_candidates"]))
if __name__=="__main__":main()
