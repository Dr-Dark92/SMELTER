#!/usr/bin/env python3
"""SMELTER read-only spatial coherence test for Magicka 2 88-byte vertices."""
import argparse,datetime,json,math,pathlib,struct,uuid,statistics,collections
IDS=("91e92dee4343fc7d","bd494ea7299b6750")
RECORDS=(1407033,4918276)
def test(blob,record):
 vbytes=struct.unpack_from("<I",blob,record+48)[0]
 vstart=record+52;tail=vstart+vbytes
 count,stride=struct.unpack_from("<II",blob,tail+8)
 if stride!=88 or count*stride!=vbytes:raise ValueError("Vertex framing mismatch")
 # Offset 165 relative to tail starts with a 0,1,2,2,1,3 triangle sequence in both resources.
 index_start=tail+165
 # Only analyze the first 120 u16 values, to avoid assuming section length.
 indices=struct.unpack_from("<120H",blob,index_start)
 if max(indices)>=count:raise ValueError("Index exceeds vertex count")
 results=[]
 for offset in range(0,77,4):
  pts=[struct.unpack_from("<3f",blob,vstart+i*stride+offset) for i in range(count)]
  if not all(all(math.isfinite(v) for v in p) for p in pts):continue
  lengths=[];areas=[];zero=0
  for j in range(0,len(indices),3):
   a,b,c=(pts[indices[j+k]] for k in range(3))
   ab=tuple(b[k]-a[k] for k in range(3));ac=tuple(c[k]-a[k] for k in range(3))
   cross=(ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0])
   area=math.sqrt(sum(x*x for x in cross))/2;areas.append(area)
   if area<1e-9:zero+=1
   lengths.extend((math.dist(a,b),math.dist(b,c),math.dist(c,a)))
  spans=[max(p[k] for p in pts)-min(p[k] for p in pts) for k in range(3)]
  results.append({"offset":offset,"nonzero_triangles":40-zero,"zero_area_triangles":zero,"median_edge_length":round(statistics.median(lengths),7),"median_area":round(statistics.median(areas),9),"axis_spans":[round(x,5) for x in spans],"sample_xyz":[list(p) for p in pts[:3]]})
 results.sort(key=lambda x:(-x["nonzero_triangles"],x["zero_area_triangles"]))
 return {"vertex_count":count,"stride":stride,"index_start":index_start,"first_indices":list(indices[:24]),"candidate_positions":results,"warning":"Spatial coherence is diagnostic only; triangle list length and position semantics not yet verified."}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 root=pathlib.Path(a.root);base=root/"workspace"/"magicka2-reconstructed"
 dirs=sorted((d for d in base.iterdir() if d.is_dir() and all((d/(n+".decoded.bin")).is_file() for n in IDS)),reverse=True)
 if not dirs:p.error("Reconstructed resources not found")
 report={"tool":"SMELTER spatial coherence v1","mesh_verified":False,"read_only":True,"source":str(dirs[0]),"resources":[]}
 for name,at in zip(IDS,RECORDS):report["resources"].append({"name":name,"spatial":test((dirs[0]/(name+".decoded.bin")).read_bytes(),at)})
 out=root/"workspace"/"magicka2-spatial-coherence"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 target=out/"magicka2-spatial-coherence.json";target.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Spatial coherence report:",target)
 for r in report["resources"]:print(r["name"],"position offsets tested:",len(r["spatial"]["candidate_positions"]))
if __name__=="__main__":main()
