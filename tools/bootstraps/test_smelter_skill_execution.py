#!/usr/bin/env python3
"""SMELTER skill-to-tool bridge smoke test: skill-guided, sandboxed execution."""
import argparse,datetime,json,pathlib,struct,time,urllib.request,uuid,zlib
def call(url,model,system,prompt,timeout):
 req=urllib.request.Request(url.rstrip("/")+"/api/generate",data=json.dumps({"model":model,"system":system,"prompt":prompt,"stream":False,"think":False,"format":"json","options":{"temperature":0,"num_ctx":8192,"num_predict":550}}).encode(),headers={"Content-Type":"application/json"})
 with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)
def png_chunk(kind,payload):
 import binascii
 return struct.pack(">I",len(payload))+kind+payload+struct.pack(">I",binascii.crc32(kind+payload)&0xffffffff)
def make_png(path):
 # Deterministic 2x3 RGBA PNG; synthetic fixture, not a game asset.
 rows=b"".join(b"\x00"+b"\xff\x00\x80\xff"*2 for _ in range(3))
 path.write_bytes(b"\x89PNG\r\n\x1a\n"+png_chunk(b"IHDR",struct.pack(">IIBBBBB",2,3,8,6,0,0,0))+png_chunk(b"IDAT",zlib.compress(rows))+png_chunk(b"IEND",b""))
def run_tool(folder,tool,args):
 if not isinstance(args,dict):raise ValueError("arguments_not_object")
 if tool=="image.inspect_png":
  if args!={"filename":"fixture.png"}:raise ValueError("unapproved_image")
  b=(folder/"fixture.png").read_bytes()
  if b[:8]!=b"\x89PNG\r\n\x1a\n" or b[12:16]!=b"IHDR":raise ValueError("invalid_png")
  w,h,depth,kind,_,_,_=struct.unpack(">IIBBBBB",b[16:29])
  return {"status":"inspected","filename":"fixture.png","width":w,"height":h,"bit_depth":depth,"color_type":kind,"alpha":kind in (4,6)}
 if tool=="artifact.write_json":
  if set(args)!={"filename","data"} or args["filename"]!="asset-inspection.json" or not isinstance(args["data"],dict):raise ValueError("invalid_artifact_arguments")
  data=json.dumps(args["data"],indent=2)
  if len(data)>4096:raise ValueError("oversized_artifact")
  (folder/"asset-inspection.json").write_text(data,encoding="utf-8")
  return {"status":"written","filename":"asset-inspection.json"}
 raise ValueError("tool_not_registered")
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",default=r"C:\SMELTER");p.add_argument("--url",default="http://127.0.0.1:11434");p.add_argument("--model",default="qwen3.5:9b");p.add_argument("--timeout",type=int,default=180);a=p.parse_args()
 root=pathlib.Path(a.root);skills_dir=root/".agents"/"skills"
 out=root/"workspace"/"smelter-skill-execution"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S-")+uuid.uuid4().hex[:6]);out.mkdir(parents=True)
 make_png(out/"fixture.png")
 skills=[]
 for d in sorted(skills_dir.iterdir()) if skills_dir.is_dir() else []:
  f=d/"SKILL.md"
  if f.is_file():
   raw=f.read_text(encoding="utf-8-sig",errors="replace")
   desc=next((line.partition(":")[2].strip() for line in raw.splitlines() if line.startswith("description:")),"")
   skills.append({"id":d.name,"description":desc[:600],"path":str(f)})
 report={"test":"SMELTER skill-to-tool execution bridge v1","model":a.model,"skills_found":len(skills),"sandbox":str(out),"stages":[]}
 def stage(name,fn):
  start=time.perf_counter();entry={"stage":name}
  try:entry.update(fn())
  except Exception as e:entry.update({"pass":False,"error":repr(e)})
  entry["wall_seconds"]=round(time.perf_counter()-start,3);report["stages"].append(entry)
  print(name,"PASS" if entry.get("pass") else "FAIL",flush=True)
  return entry
 def select():
  raw=call(a.url,a.model,"You are SMELTER skill selector. Select one skill from this installed catalog. Return JSON with skill_id and reason. Never invent skills. "+json.dumps(skills),"Select the installed skill for inspecting image dimensions, alpha channel and preparing game-ready art assets.",a.timeout)
  obj=json.loads(raw.get("response",""));sid=obj.get("skill_id")
  return {"decision":obj,"pass":sid=="universal-modder-asset-pipeline"}
 selection=stage("skill_selection",select)
 if selection.get("pass"):
  skill=next(s for s in skills if s["id"]==selection["decision"]["skill_id"])
  body=pathlib.Path(skill["path"]).read_text(encoding="utf-8-sig",errors="replace")[:12000]
  tools=[{"id":"image.inspect_png","description":"Inspect the PNG header and report actual width, height, bit depth and alpha","args":{"filename":"fixture.png"}},{"id":"artifact.write_json","description":"Write a structured JSON report","args":{"filename":"asset-inspection.json","data":"object"}}]
  def inspect():
   prompt="TASK: Inspect fixture.png to determine its image properties. Choose a registered tool; output JSON with tool_id, arguments, reason. Do not claim execution.\nSKILL:\n"+body+"\nTOOLS:\n"+json.dumps(tools)
   obj=json.loads(call(a.url,a.model,"You are a skill-guided tool agent. Only registered tools. JSON only.",prompt,a.timeout).get("response",""))
   if obj.get("tool_id")!="image.inspect_png":return {"decision":obj,"pass":False}
   result=run_tool(out,obj["tool_id"],obj.get("arguments"));return {"decision":obj,"result":result,"pass":result["width"]==2 and result["height"]==3 and result["alpha"]}
  inspected=stage("skill_guided_inspection",inspect)
  if inspected.get("pass"):
   def report_stage():
    prompt="SKILL: "+skill["id"]+"\nACTUAL_TOOL_RESULT: "+json.dumps(inspected["result"])+"\nWrite asset-inspection.json using artifact.write_json with data containing source_skill, filename, width, height, alpha. Use the actual inspection values. Return JSON with tool_id, arguments, reason. TOOLS: "+json.dumps(tools)
    obj=json.loads(call(a.url,a.model,"You are a skill-guided tool agent. Never invent measurements. JSON only.",prompt,a.timeout).get("response",""))
    if obj.get("tool_id")!="artifact.write_json":return {"decision":obj,"pass":False}
    result=run_tool(out,obj["tool_id"],obj.get("arguments"))
    actual=json.loads((out/"asset-inspection.json").read_text(encoding="utf-8"))
    ok=all(actual.get(k)==v for k,v in {"source_skill":skill["id"],"filename":"fixture.png","width":2,"height":3,"alpha":True}.items())
    return {"decision":obj,"result":result,"independent_check":ok,"pass":ok}
   stage("skill_guided_report",report_stage)
 report["full_pass"]=len(report["stages"])==3 and all(s.get("pass") for s in report["stages"])
 dest=out/"smelter-skill-execution.json";dest.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding="utf-8")
 print("REPORT:",dest);print("FULL PASS:",report["full_pass"])
if __name__=="__main__":main()
