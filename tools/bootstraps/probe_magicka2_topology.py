#!/usr/bin/env python3
"""Read-only analysis of reconstructed Magicka 2 structured buffers."""
import argparse,datetime,json,math,pathlib,struct,uuid
IDS=("91e92dee4343fc7d","bd494ea7299b6750")
START=(1407033,4918276)
def triples(data,start,stride,n):
 return [struct.unpack_from("<fff",data,start+i*stride) for i in range(n)]
def evaluate(data,base,size):
 results=[]
 for off in range(52,129,4):
  for stride in range(12,81,4):
   n=min(256,(size-off)//stride)
   if n<64:continue
   pts=triples(data,base+off,stride,n)
   valid=[p for p in pts if all(math.isfinite(x) and abs(x)<1000 for x in p)]
   if len(valid)!=n:continue
   small=sum(all(abs(x)<0.000001 for x in p) for p in valid)
   repeats=len(valid)-len(set(valid))
   distances=[math.dist(a,b) for a,b in zip(valid,valid[1:])]
   distances.sort()
   spans=[max(p[k] for p in valid)-min(p[k] for p in valid) for k in range(3)]
   score=(sum(s>0.01 for s in spans),-small,-repeats,-distances[len(distances)//2])
   results.append((score,{"offset":off,"stride":stride,"sample_count":n,"near_zero_points":small,"repeated_points":repeats,"axis_spans":spans,"median_step":distances[len(distances)//2],"first_three":valid[:3]}))
 results.sort(key=lambda x:x[0],reverse=True)
 return [x[1] for x in results[:30]]
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"C:\SMELTER");args=ap.parse_args()
 root=pathlib.Path(args.root);folder=root/"workspace"/"magicka2-reconstructed"
 pairs=sorted((d for d in folder.iterdir() if d.is_dir() and all((d/(name+".decoded.bin")).is_file() for name in IDS)),reverse=True)
 if not pairs:ap.error("Reconstructed files not found")
 out=root/"workspace"/"magicka2-topology"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:8]);out.mkdir(parents=True)
 report={"source":str(pairs[0]),"mesh_verified":False,"read_only":True,"resources":[]}
 for name,base in zip(IDS,START):
  data=(pairs[0]/(name+".decoded.bin")).read_bytes()
  if base+64>=len(data):ap.error("Invalid offset for "+name)
  header=struct.unpack_from("<13I",data,base)
  size=header[12]
  if base+52+size>len(data):ap.error("Buffer size exceeds file: "+name)
  report["resources"].append({"name":name,"start":base,"header_u32":header,"buffer_size":size,"candidate_positions":evaluate(data,base,size)})
 path=out/"magicka2-topology.json";path.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Report:",path)
 for r in report["resources"]:print(r["name"],"candidates:",len(r["candidate_positions"]))
if __name__=="__main__":main()
