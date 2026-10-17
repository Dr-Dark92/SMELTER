#!/usr/bin/env python3
"""Read-only survey of Magicka2 88-byte vertex records for skinning fields.
Does not assert a rig or create Skyrim files.
"""
import argparse,collections,datetime,json,math,pathlib,struct,uuid
RES=(("91e92dee4343fc7d",1407033),("bd494ea7299b6750",4918276))
def analyze(blob,at):
 size=struct.unpack_from("<I",blob,at+48)[0];start=at+52;tail=start+size
 n,stride=struct.unpack_from("<II",blob,tail+8)
 if n*stride!=size or stride!=88:raise ValueError("Vertex framing mismatch")
 records=[blob[start+i*stride:start+(i+1)*stride] for i in range(n)]
 fields=[]
 for off in range(0,85,4):
  floats=[struct.unpack_from("<f",r,off)[0] for r in records]
  finite=[v for v in floats if math.isfinite(v)]
  ints=[struct.unpack_from("<I",r,off)[0] for r in records]
  fields.append({"offset":off,"float_finite_fraction":round(len(finite)/n,4),
   "float_unit_fraction":round(sum(0<=v<=1 for v in finite)/n,4),
   "float_min":min(finite) if finite else None,"float_max":max(finite) if finite else None,
   "float_unique":len(set(finite)),"u32_min":min(ints),"u32_max":max(ints)})
 candidates=[]
 for off in range(0,85,4):
  samples=[r[off:off+4] for r in records]
  if any(len(s)!=4 for s in samples):continue
  sums=[sum(s) for s in samples]
  candidates.append({"offset":off,"byte_component_max":[max(s[j] for s in samples) for j in range(4)],
    "sum_255_fraction":round(sum(abs(v-255)<=2 for v in sums)/n,5),
    "sum_256_fraction":round(sum(abs(v-256)<=2 for v in sums)/n,5),
    "zero_component_fraction":round(sum(any(b==0 for b in s) for s in samples)/n,5),
    "distinct_tuples":len(set(samples)),"first_eight":[list(s) for s in samples[:8]]})
 candidates.sort(key=lambda x:(-max(x["sum_255_fraction"],x["sum_256_fraction"]),x["offset"]))
 pairs=[]
 for off in range(0,73,4):
  for weightoff in range(0,73,4):
   if off==weightoff or abs(off-weightoff)>24:continue
   ids=[r[off:off+4] for r in records]
   weights=[r[weightoff:weightoff+4] for r in records]
   sums=[sum(w) for w in weights]
   hit=sum(abs(s-255)<=2 for s in sums)/n
   if hit>.1:
    pairs.append({"index_offset":off,"weight_offset":weightoff,"normalized_weight_fraction":round(hit,5),
      "max_bone_id":max(max(i) for i in ids),"unique_bone_ids":len({v for i in ids for v in i})})
 pairs.sort(key=lambda x:-x["normalized_weight_fraction"])
 return {"vertex_count":n,"stride":stride,"fields_float_u32":fields,"byte_weight_candidates":candidates[:20],
  "possible_index_weight_pairs":pairs[:30],"skinning_verified":False}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");a=p.parse_args()
 root=pathlib.Path(a.root);base=root/"workspace"/"magicka2-reconstructed"
 dirs=sorted((d for d in base.iterdir() if d.is_dir() and all((d/(name+".decoded.bin")).is_file() for name,_ in RES)),reverse=True)
 if not dirs:p.error("Reconstructed binary resources missing")
 report={"tool":"SMELTER Magicka2 vertex skinning survey","read_only":True,"bone_indices_verified":False,"bone_weights_verified":False,"resources":[]}
 for name,at in RES:report["resources"].append({"name":name,**analyze((dirs[0]/(name+".decoded.bin")).read_bytes(),at)})
 out=root/"workspace"/"magicka2-skinning-survey"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 path=out/"magicka2-skinning-survey.json";path.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Report:",path)
 for r in report["resources"]:
  print(r["name"],"candidate weight fields:",[(c["offset"],c["sum_255_fraction"]) for c in r["byte_weight_candidates"][:8]])
 print("No skeleton bindings asserted; no game files changed.")
if __name__=="__main__":main()
