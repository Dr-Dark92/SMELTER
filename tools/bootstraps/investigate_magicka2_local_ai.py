#!/usr/bin/env python3
"""SMELTER local Magicka 2 investigator: bounded, read-only, optional Ollama analysis."""
import argparse,datetime,json,pathlib,struct,uuid,collections,urllib.request,urllib.error,math
IDS=("91e92dee4343fc7d","bd494ea7299b6750")
TAILS=(1407033,4918276)
def discover(root):
 base=root/"workspace"/"magicka2-reconstructed"
 if not base.is_dir():raise RuntimeError("Missing reconstructed workspace")
 matches=sorted((p for p in base.iterdir() if p.is_dir() and all((p/(n+".decoded.bin")).is_file() for n in IDS)),reverse=True)
 if not matches:raise RuntimeError("Missing reconstructed binary pair")
 return matches[0]
def analyze(blob,tail):
 if tail+52>len(blob):raise ValueError("Truncated record")
 header=struct.unpack_from("<13I",blob,tail)
 declared=header[12];body_start=tail+52
 if declared<128 or body_start+declared>len(blob):raise ValueError("Invalid declared buffer length")
 data=memoryview(blob)[body_start:body_start+declared]
 # Detect 4-float identity-like runs, probable 16-float transforms and 16-bit index patterns.
 matrices=[]
 for pos in range(0,len(data)-64,4):
  vals=struct.unpack_from("<16f",data,pos)
  if all(math.isfinite(v) for v in vals) and all(abs(vals[i]-1)<1e-5 for i in (0,5,10,15)) and sum(abs(vals[i]) for i in range(16) if i not in (0,5,10,15))<1e-4:
   matrices.append(pos)
   if len(matrices)>=20:break
 # Search 16-bit candidate indices across entire buffer, requiring diversity, not merely small values.
 index_candidates=[]
 for alignment in (0,1):
  vals=struct.unpack_from("<"+str((len(data)-alignment)//2)+"H",data,alignment)
  for bound in (256,1024,4096,16384):
   best=(0,0,0);run_start=0;run=0
   for i,v in enumerate(vals):
    if v<bound:
     if not run:run_start=i
     run+=1
     if run>=96 and (run%32==0):
      subset=vals[run_start:i+1]
      distinct=len(set(subset))
      if distinct>=24 and run>best[1]:best=(run_start,run,distinct)
    else:run=0
   if best[1]>=96:index_candidates.append({"alignment":alignment,"bound":bound,"relative_offset":alignment+best[0]*2,"length":best[1],"unique":best[2]})
 # Look for 44-byte repeated float structures, but report as attributes, not positions.
 attribute_samples=[]
 for stride in (32,36,40,44,48,52,56,60,64,68,72,76,80):
  for off in range(0,min(stride,80),4):
   count=min(128,(len(data)-off)//stride)
   if count<64:continue
   triples=[struct.unpack_from("<3f",data,off+i*stride) for i in range(count)]
   if not all(all(math.isfinite(x) and abs(x)<10000 for x in t) for t in triples):continue
   spans=[max(t[j] for t in triples)-min(t[j] for t in triples) for j in range(3)]
   if min(spans)<0.001:continue
   attribute_samples.append({"stride":stride,"offset":off,"axis_spans":[round(x,5) for x in spans],"first":list(triples[0])})
 return {"record_offset":tail,"record_u32":list(header),"declared_buffer_bytes":declared,"remaining_bytes_after_buffer":len(blob)-(body_start+declared),"identity_matrix_offsets":matrices,"candidate_index_runs":index_candidates[:20],"candidate_float_layouts":attribute_samples[:24],"note":"Heuristics only; no triangle mesh verified."}
def ollama(summary,model,url):
 prompt=("You are a cautious binary-format reverse-engineering analyst. Examine this JSON. "
         "Distinguish verified facts from hypotheses. Suggest up to five deterministic next tests. "
         "Never claim mesh recovery, never suggest editing game installs, and do not supply executable commands.\n"
         +json.dumps(summary,separators=(",",":"))[:14000])
 payload=json.dumps({"model":model,"stream":False,"prompt":prompt,"options":{"num_predict":800,"temperature":0.1}}).encode()
 req=urllib.request.Request(url.rstrip("/")+"/api/generate",data=payload,headers={"Content-Type":"application/json"})
 try:
  with urllib.request.urlopen(req,timeout=180) as res:response=json.load(res)
  return {"status":"ok","model":model,"analysis":response.get("response","")}
 except (urllib.error.URLError,TimeoutError,ValueError) as e:return {"status":"unavailable","error":str(e)}
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--root",default=r"C:\SMELTER");p.add_argument("--model",default="qwen3.5:9b")
 p.add_argument("--ollama-url",default="http://127.0.0.1:11434");p.add_argument("--no-ai",action="store_true")
 a=p.parse_args();root=pathlib.Path(a.root);source=discover(root)
 result={"tool":"SMELTER Magicka2 local investigator v1","source":str(source),"read_only":True,"mesh_verified":False,"resources":[]}
 for name,tail in zip(IDS,TAILS):
  blob=(source/(name+".decoded.bin")).read_bytes()
  result["resources"].append({"name":name,"file_size":len(blob),"inspection":analyze(blob,tail)})
 out=root/"workspace"/"magicka2-local-investigation"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:8]);out.mkdir(parents=True)
 report=out/"magicka2-local-investigation.json"
 report.write_text(json.dumps(result,indent=2),encoding="utf-8")
 ai={"status":"disabled"} if a.no_ai else ollama(result,a.model,a.ollama_url)
 (out/"magicka2-ai-analysis.json").write_text(json.dumps(ai,indent=2),encoding="utf-8")
 print("Investigation:",report);print("AI analysis:",out/"magicka2-ai-analysis.json")
 print("AI status:",ai["status"]);print("Mesh verified: NO")
if __name__=="__main__":main()
