#!/usr/bin/env python3
"""Read-only structural audit; does not claim or export mesh geometry."""
import argparse,collections,datetime,json,pathlib,struct,uuid,math
IDS=("91e92dee4343fc7d","bd494ea7299b6750")
START=(1407033,4918276)
def inspect(blob,start,length):
 end=min(len(blob),start+52+length)
 body=blob[start+52:end]
 report={"body_length":len(body),"first_128_hex":body[:128].hex(),"last_128_hex":body[-128:].hex(),"aligned_word_stats":[],"possible_index_runs":[]}
 for align in range(4):
  nums=[struct.unpack_from("<I",body,i)[0] for i in range(align,len(body)-3,4)]
  report["aligned_word_stats"].append({"byte_alignment":align,"zero":nums.count(0),"one":nums.count(1),"two":nums.count(2),"top_values":collections.Counter(nums).most_common(12)})
 for width,fmt in ((2,"H"),(4,"I")):
  for align in range(width):
   vals=[v[0] for v in struct.iter_unpack("<"+fmt,body[align:len(body)-(len(body)-align)%width])]
   for bound in (256,1024,4096,16384):
    best=(0,0);run=0;run_start=0
    for i,v in enumerate(vals):
     if v<bound:
      if not run:run_start=i
      run+=1
      if run>best[1]:best=(run_start,run)
     else:run=0
    if best[1]>=48:
     report["possible_index_runs"].append({"width":width,"alignment":align,"upper_bound":bound,"byte_offset":align+best[0]*width,"value_count":best[1],"first_18":vals[best[0]:best[0]+18]})
 report["possible_index_runs"].sort(key=lambda x:x["value_count"],reverse=True)
 report["possible_index_runs"]=report["possible_index_runs"][:30]
 return report
def main():
 a=argparse.ArgumentParser();a.add_argument("--root",default=r"C:\SMELTER");args=a.parse_args()
 root=pathlib.Path(args.root)
 folder=root/"workspace"/"magicka2-reconstructed"
 candidates=sorted((x for x in folder.iterdir() if x.is_dir() and all((x/(i+".decoded.bin")).is_file() for i in IDS)),reverse=True)
 if not candidates:a.error("Missing reconstructed binaries")
 src=candidates[0];out=root/"workspace"/"magicka2-structure"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:8]);out.mkdir(parents=True)
 doc={"source":str(src),"mesh_verified":False,"notes":"Index runs are heuristic only; constant fields can produce false positives.","resources":[]}
 for name,offset in zip(IDS,START):
  blob=(src/(name+".decoded.bin")).read_bytes()
  header=struct.unpack_from("<13I",blob,offset)
  size=header[-1]
  if offset+52+size>len(blob):a.error("Truncated buffer "+name)
  doc["resources"].append({"resource":name,"offset":offset,"header_u32":list(header),"analysis":inspect(blob,offset,size)})
 path=out/"magicka2-structure.json";path.write_text(json.dumps(doc,indent=2),encoding="utf-8")
 print("Structural audit:",path)
if __name__=="__main__":main()
