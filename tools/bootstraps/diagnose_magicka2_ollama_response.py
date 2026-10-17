#!/usr/bin/env python3
"""Read-only Ollama response diagnostic and repair for SMELTER Magicka2 investigator."""
import argparse,datetime,json,pathlib,urllib.request,urllib.error,uuid
def request(url,payload,timeout=180):
 req=urllib.request.Request(url.rstrip("/")+"/api/generate",data=json.dumps(payload).encode("utf-8"),headers={"Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=timeout) as response:return json.load(response)
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");p.add_argument("--model",default="qwen3.5:9b");p.add_argument("--url",default="http://127.0.0.1:11434");a=p.parse_args()
 base=pathlib.Path(a.root)/"workspace"/"magicka2-local-investigation"
 folders=sorted((d for d in base.iterdir() if d.is_dir() and (d/"magicka2-local-investigation.json").is_file()),reverse=True)
 if not folders:p.error("Run the local investigator first")
 source=folders[0];report=json.loads((source/"magicka2-local-investigation.json").read_text(encoding="utf-8"))
 summary={"mesh_verified":report.get("mesh_verified"),"resources":[{"name":r["name"],"declared_buffer_bytes":r["inspection"]["declared_buffer_bytes"],"index_runs":len(r["inspection"]["candidate_index_runs"]),"identity_matrices":len(r["inspection"]["identity_matrix_offsets"]),"float_candidates":len(r["inspection"]["candidate_float_layouts"])} for r in report["resources"]]}
 prompt="Analyze this Magicka 2 binary survey. Give exactly three evidence-based next diagnostic tests. Do not claim a recovered mesh. Respond in plain English.\n"+json.dumps(summary)
 out=base/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+"ollama-"+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 attempts=[]
 for mode in ("thinking_disabled","default"):
  payload={"model":a.model,"prompt":prompt,"stream":False,"options":{"num_predict":1400,"temperature":0.1}}
  if mode=="thinking_disabled":payload["think"]=False
  try:
   data=request(a.url,payload)
   response=data.get("response") or ""
   thinking=data.get("thinking") or ""
   attempts.append({"mode":mode,"done":data.get("done"),"done_reason":data.get("done_reason"),"eval_count":data.get("eval_count"),"response_length":len(response),"thinking_length":len(thinking),"response":response,"thinking_preview":thinking[:1200]})
   if response.strip():break
  except (urllib.error.URLError,TimeoutError,ValueError) as e:attempts.append({"mode":mode,"error":str(e)})
 result={"source":str(source),"model":a.model,"status":"ok" if attempts and (attempts[-1].get("response") or "").strip() else "empty_or_unavailable","attempts":attempts}
 path=out/"magicka2-ollama-response-diagnostic.json";path.write_text(json.dumps(result,indent=2),encoding="utf-8")
 print("Report:",path);print("Status:",result["status"])
 for x in attempts:print(x["mode"],"response chars:",x.get("response_length",0),"thinking chars:",x.get("thinking_length",0),"done reason:",x.get("done_reason"))
if __name__=="__main__":main()
