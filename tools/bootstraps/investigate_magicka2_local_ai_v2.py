#!/usr/bin/env python3
"""SMELTER bounded local investigation v2. Read-only evidence, no AI code execution."""
import argparse,datetime,json,math,pathlib,struct,urllib.request,urllib.error,uuid
IDS=("91e92dee4343fc7d","bd494ea7299b6750")
OFFSETS=(1407033,4918276)
def source(root):
 base=root/"workspace"/"magicka2-reconstructed"
 if not base.is_dir():raise RuntimeError("Missing reconstruction workspace")
 found=sorted((d for d in base.iterdir() if d.is_dir() and all((d/(n+".decoded.bin")).is_file() for n in IDS)),reverse=True)
 if not found:raise RuntimeError("Reconstructed files missing")
 return found[0]
def inspect(name,blob,at):
 if at+52>len(blob):raise ValueError("Missing record")
 header=struct.unpack_from("<13I",blob,at)
 size=header[12];start=at+52;end=start+size
 if size<128 or end>len(blob):raise ValueError("Invalid record size")
 body=memoryview(blob)[start:end]
 # Deterministic tests with explicit caveats: no inference of rendering state.
 record={"name":name,"header":list(header),"body_start":start,"body_end":end,"body_bytes":size,"trailing_bytes":len(blob)-end,"tests":[]}
 record["tests"].append({"id":"boundary","passed":True,"evidence":{"body_bytes":size,"trailing_bytes":len(blob)-end}})
 # Float alignment: test fixed stride and offset against full buffer, not just 128 samples.
 ranked=[]
 for stride in (32,36,40,44,48,52,56,60,64,68,72,76,80):
  for offset in range(0,stride,4):
   count=min(1024,(size-offset)//stride)
   if count<128:continue
   points=[struct.unpack_from("<3f",body,offset+i*stride) for i in range(count)]
   finite=[p for p in points if all(math.isfinite(x) and abs(x)<10000 for x in p)]
   if len(finite)!=count:continue
   spans=[max(p[k] for p in finite)-min(p[k] for p in finite) for k in range(3)]
   exact_int=sum(all(abs(x-round(x))<1e-7 for x in p) for p in finite)
   unique=len(set(finite))
   ranked.append({"stride":stride,"offset":offset,"sample_count":count,"axis_spans":[round(x,5) for x in spans],"unique_triples":unique,"integer_triples":exact_int})
 ranked.sort(key=lambda x:(-x["unique_triples"],x["integer_triples"]))
 record["tests"].append({"id":"float_layouts","passed":bool(ranked),"evidence":{"tested_layouts":sum(s//4 for s in (32,36,40,44,48,52,56,60,64,68,72,76,80)),"plausible_layouts":len(ranked),"top_candidates":ranked[:6]},"caveat":"Plausible float triples do not establish vertex positions."})
 # 16/32-bit index scan: bounded sample windows, test triangle diversity.
 candidates=[]
 for width,fmt in ((2,"H"),(4,"I")):
  for align in range(width):
   n=(len(body)-align)//width
   values=struct.unpack_from("<"+str(n)+fmt,body,align)
   for window in (96,192):
    step=window
    for i in range(0,len(values)-window+1,step):
     chunk=values[i:i+window]
     if max(chunk)>=65536 or len(set(chunk))<24:continue
     if len(chunk)%3:continue
     distinct_triangles=len({tuple(chunk[j:j+3]) for j in range(0,window,3)})
     nondegenerate=sum(len(set(chunk[j:j+3]))==3 for j in range(0,window,3))
     if nondegenerate>=window//4:
      candidates.append({"width":width,"byte_offset":align+i*width,"values":window,"unique_indices":len(set(chunk)),"nondegenerate_triangles":nondegenerate,"unique_triangles":distinct_triangles})
     if len(candidates)>=20:break
    if len(candidates)>=20:break
   if len(candidates)>=20:break
  if len(candidates)>=20:break
 record["tests"].append({"id":"index_windows","passed":bool(candidates),"evidence":{"candidates":candidates},"caveat":"Index-like windows are unverified without vertex count and topology."})
 return record
def ask(url,model,evidence):
 prompt=("Act as a cautious offline binary reverse engineering reviewer. "
 "Summarize verified observations and propose exactly 3 concrete next deterministic checks. "
 "Never infer that a missing identity matrix implies a broken renderer. "
 "No executable code or commands. Do not claim geometry extraction. "
 "Keep response under 300 words.\n"+json.dumps(evidence,separators=(",",":"))[:12000])
 data=json.dumps({"model":model,"prompt":prompt,"stream":False,"think":False,"options":{"num_predict":700,"temperature":0.1}}).encode()
 req=urllib.request.Request(url.rstrip("/")+"/api/generate",data=data,headers={"Content-Type":"application/json"})
 try:
  with urllib.request.urlopen(req,timeout=180) as response:obj=json.load(response)
  answer=(obj.get("response") or "").strip()
  return {"status":"ok" if answer else "empty_response","response":answer,"done_reason":obj.get("done_reason"),"eval_count":obj.get("eval_count")}
 except (urllib.error.URLError,TimeoutError,ValueError) as e:return {"status":"error","error":str(e)}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");p.add_argument("--model",default="qwen3.5:9b");p.add_argument("--url",default="http://127.0.0.1:11434");p.add_argument("--no-ai",action="store_true");a=p.parse_args()
 root=pathlib.Path(a.root);src=source(root)
 report={"version":2,"source":str(src),"read_only":True,"mesh_verified":False,"records":[]}
 for name,offset in zip(IDS,OFFSETS):report["records"].append(inspect(name,(src/(name+".decoded.bin")).read_bytes(),offset))
 out=root/"workspace"/"magicka2-local-investigation"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+"v2-"+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 ai={"status":"disabled"} if a.no_ai else ask(a.url,a.model,report)
 (out/"magicka2-investigation-v2.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
 (out/"magicka2-ai-v2.json").write_text(json.dumps(ai,indent=2),encoding="utf-8")
 print("Evidence:",out/"magicka2-investigation-v2.json");print("AI:",out/"magicka2-ai-v2.json");print("AI status:",ai["status"]);print("Mesh verified: NO")
if __name__=="__main__":main()
