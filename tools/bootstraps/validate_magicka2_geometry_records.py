#!/usr/bin/env python3
"""Read-only focused analysis of Magicka 2 post-texture structured geometry."""
import argparse,datetime,json,math,pathlib,struct,uuid
NAMES=("91e92dee4343fc7d","bd494ea7299b6750")
TAIL={"91e92dee4343fc7d":1407033,"bd494ea7299b6750":4918276}
def u32(b,p):return struct.unpack_from("<I",b,p)[0]
def floats(b,p,count):
 return struct.unpack_from("<"+str(count)+"f",b,p)
def stats(values):
 finite=[x for x in values if math.isfinite(x)]
 return {"count":len(values),"finite":len(finite),"min":min(finite) if finite else None,"max":max(finite) if finite else None,"under_10":sum(abs(x)<=10 for x in finite),"sample":list(values[:12])}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--root",default=r"C:\SMELTER");a=ap.parse_args()
 base=pathlib.Path(a.root)/"workspace"/"magicka2-reconstructed"
 sources=sorted((p for p in base.iterdir() if p.is_dir() and all((p/(n+".decoded.bin")).is_file() for n in NAMES)),reverse=True)
 if not sources:ap.error("No reconstructed resource pair found")
 out=pathlib.Path(a.root)/"workspace"/"magicka2-record-validation"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:8]);out.mkdir(parents=True)
 report={"source":str(sources[0]),"read_only":True,"mesh_verified":False,"resources":[]}
 for name in NAMES:
  b=(sources[0]/(name+".decoded.bin")).read_bytes();p=TAIL[name]
  if len(b)<p+256:ap.error("Resource shorter than expected: "+name)
  fields=[u32(b,p+i*4) for i in range(16)]
  # Probe the header's apparent length fields without assuming their meaning.
  candidates=[]
  for k in range(5,16):
   v=fields[k]
   if 16<=v<=len(b)-p:
    for delta in (0,32,40,44,48,52,56):
     start=p+delta
     if start+min(v,4096)>len(b):continue
     n=min(v//4,1024)
     if n<8:continue
     vals=floats(b,start,n)
     s=stats(vals)
     candidates.append({"field_index":k,"declared_value":v,"offset_from_record":delta,"float_stats":s})
  # Compare possible fixed-width float vertex layouts; this is not mesh export.
  layouts=[]
  for offset in (44,48,52,56,60,64):
   for stride in (12,16,20,24,28,32,36,40,44,48,56,64):
    triples=[]
    for j in range(128):
     at=p+offset+j*stride
     if at+12>len(b):break
     triples.append(struct.unpack_from("<3f",b,at))
    good=[v for v in triples if all(math.isfinite(x) and abs(x)<1000 for x in v)]
    if len(good)<100:continue
    axes=[[v[k] for v in good] for k in range(3)]
    spans=[max(x)-min(x) for x in axes]
    layouts.append({"offset":offset,"stride":stride,"plausible":len(good),"axis_spans":spans,"first_3":good[:3]})
  layouts.sort(key=lambda x:(-x["plausible"],-sum(s>0.01 for s in x["axis_spans"])))
  report["resources"].append({"file":name,"post_texture_start":p,"header_u32":fields,"header_hex":b[p:p+64].hex(),"header_field_probes":candidates,"candidate_float_layouts":layouts[:24],"last_256_hex":b[-256:].hex()})
 dest=out/"magicka2-record-validation.json";dest.write_text(json.dumps(report,indent=2),encoding="utf-8")
 print("Report:",dest)
 for r in report["resources"]:print(r["file"],"record",r["post_texture_start"],"header",r["header_u32"][8:13],"layouts",len(r["candidate_float_layouts"]))
if __name__=="__main__":main()
