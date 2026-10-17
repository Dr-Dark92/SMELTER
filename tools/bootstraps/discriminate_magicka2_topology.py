#!/usr/bin/env python3
"""SMELTER Magicka 2 topology discrimination: read-only, deterministic."""
import argparse,datetime,json,pathlib,struct,math,random,collections,uuid
IDS=("91e92dee4343fc7d","bd494ea7299b6750")
STARTS=(1407033,4918276)
def metrics(vals):
 tris=[tuple(vals[i:i+3]) for i in range(0,len(vals)-2,3)]
 good=[t for t in tris if len(set(t))==3]
 edges=collections.Counter(tuple(sorted((t[a],t[b]))) for t in good for a,b in ((0,1),(1,2),(2,0)))
 verts=collections.Counter(v for t in good for v in t)
 return {"triangles":len(tris),"nondegenerate":len(good),"unique_vertices":len(verts),"max_index":max(vals,default=0),"shared_edges":sum(n>1 for n in edges.values()),"edge_reuse_fraction":round(sum(n>1 for n in edges.values())/max(1,len(edges)),5),"vertex_reuse_fraction":round(sum(n>1 for n in verts.values())/max(1,len(verts)),5)}
def analyze(blob,start):
 header=struct.unpack_from("<13I",blob,start);size=header[-1];begin=start+52;end=begin+size
 if end>len(blob):raise ValueError("Invalid record bounds")
 data=blob[begin:end]
 candidates=[]
 for width,fmt in ((2,"H"),(4,"I")):
  for alignment in range(width):
   for byte_at in range(alignment,min(len(data)-width*384,65536),width*192):
    vals=struct.unpack_from("<384"+fmt,data,byte_at)
    if max(vals)>16384:continue
    observed=metrics(vals)
    if observed["nondegenerate"]<96:continue
    rng=random.Random(42);shuffled=list(vals);rng.shuffle(shuffled)
    control=metrics(shuffled)
    observed["shared_edge_lift"]=round((observed["shared_edges"]+1)/(control["shared_edges"]+1),4)
    candidates.append({"width":width,"byte_offset":byte_at,"observed":observed,"shuffled_control":control})
 candidates.sort(key=lambda x:(-x["observed"]["shared_edge_lift"],-x["observed"]["edge_reuse_fraction"]))
 return {"buffer_bytes":size,"scanned_first_bytes":min(size,65536),"candidates":candidates[:20],"candidate_count":len(candidates),"warning":"A candidate is not a verified mesh; compare vertex bounds and spatial triangle coherence next."}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 root=pathlib.Path(a.root);base=root/"workspace"/"magicka2-reconstructed"
 sources=sorted((d for d in base.iterdir() if d.is_dir() and all((d/(name+".decoded.bin")).is_file() for name in IDS)),reverse=True)
 if not sources:p.error("Missing reconstructed resources")
 result={"version":3,"read_only":True,"mesh_verified":False,"source":str(sources[0]),"records":[]}
 for name,offset in zip(IDS,STARTS):
  result["records"].append({"name":name,"topology":analyze((sources[0]/(name+".decoded.bin")).read_bytes(),offset)})
 out=root/"workspace"/"magicka2-local-investigation"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+"v3-"+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 target=out/"magicka2-topology-discrimination.json";target.write_text(json.dumps(result,indent=2),encoding="utf-8")
 print("Topology discrimination:",target)
 for r in result["records"]:print(r["name"],"candidates:",r["topology"]["candidate_count"])
if __name__=="__main__":main()
