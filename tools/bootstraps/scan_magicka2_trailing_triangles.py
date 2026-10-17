#!/usr/bin/env python3
"""Read-only Magicka2 trailing-region triangle-list investigation."""
import argparse,datetime,json,pathlib,struct,uuid,collections
IDS=("91e92dee4343fc7d","bd494ea7299b6750")
OFFSETS=(1407033,4918276)
def inspect(blob,at):
 size=struct.unpack_from("<I",blob,at+48)[0];start=at+52+size
 tail=blob[start:];report={"tail_start":start,"tail_bytes":len(tail),"prefix_u32":[struct.unpack_from("<I",tail,i)[0] for i in range(0,min(len(tail)-3,160),4)],"candidates":[]}
 # Seek runs of the canonical two-triangles-per-quad pattern, with arbitrary base.
 for alignment in (0,1):
  n=(len(tail)-alignment)//2
  if n<24:continue
  vals=struct.unpack_from("<"+str(n)+"H",tail,alignment)
  hits=[]
  for i in range(0,n-11):
   v=vals[i:i+12];base=v[0]
   if base>65523:continue
   if v[:6] in ((base,base+1,base+2,base+2,base+1,base+3),(base,base+1,base+2,base+2,base+3,base+1)):
    hits.append(i)
  # Rank windows by number of shared edges and locally contiguous indices.
  for i in hits[:30]:
   left=max(0,i-12);right=min(n,i+96);window=vals[left:right]
   tri=[window[j:j+3] for j in range(0,len(window)-2,3)]
   edges=collections.Counter(tuple(sorted((t[a],t[b]))) for t in tri if len(set(t))==3 for a,b in ((0,1),(1,2),(2,0)))
   report["candidates"].append({"byte_offset":alignment+i*2,"pattern_indices":list(vals[i:i+12]),"nearby_min":min(window),"nearby_max":max(window),"shared_edges":sum(v>1 for v in edges.values()),"sample_count":len(window)})
 report["candidates"].sort(key=lambda x:-x["shared_edges"])
 report["candidates"]=report["candidates"][:30]
 # Find repeated 32-bit 0x58 fields as possible section descriptors, not assumed.
 report["descriptor_0x58_offsets"]=[i for i in range(0,min(len(tail)-4,512),4) if struct.unpack_from("<I",tail,i)[0]==88]
 report["caveat"]="Pattern matches suggest triangle-list data but do not validate vertex binding."
 return report
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 root=pathlib.Path(a.root);base=root/"workspace"/"magicka2-reconstructed"
 folders=sorted((d for d in base.iterdir() if d.is_dir() and all((d/(name+".decoded.bin")).is_file() for name in IDS)),reverse=True)
 if not folders:p.error("Missing reconstructed files")
 result={"read_only":True,"mesh_verified":False,"source":str(folders[0]),"resources":[]}
 for name,at in zip(IDS,OFFSETS):
  result["resources"].append({"name":name,"triangle_scan":inspect((folders[0]/(name+".decoded.bin")).read_bytes(),at)})
 out=root/"workspace"/"magicka2-triangle-scan"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 path=out/"magicka2-trailing-triangles.json";path.write_text(json.dumps(result,indent=2),encoding="utf-8")
 print("Triangle scan:",path)
 for r in result["resources"]:print(r["name"],"pattern candidates:",len(r["triangle_scan"]["candidates"]))
if __name__=="__main__":main()
