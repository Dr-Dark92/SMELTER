#!/usr/bin/env python3
"""Round 12: deep integrity comparison and deliberate corruption detection."""
from __future__ import annotations
import argparse,datetime,json,pathlib,sys,uuid
from smelter_blender_adapter import discover
from smelter_integrity_adapter import fingerprint,compare,negative_mutation

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\SMELTER")
    p.add_argument("--blender",default=None)
    a=p.parse_args()
    workspace=pathlib.Path(a.root).resolve()/"workspace"
    folder=workspace/"smelter-round12"/(datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ-")+uuid.uuid4().hex[:6])
    folder.mkdir(parents=True,exist_ok=True)
    path=folder/"smelter-round12.json"
    report={"test":"SMELTER Round 12 deep asset integrity","full_pass":False,"steps":[]}
    try:
        exe=discover(a.blender)
        candidates=sorted((workspace/"smelter-round11").glob("*/textured_source.glb"),
                          key=lambda x:x.stat().st_mtime,reverse=True)
        if not candidates:raise FileNotFoundError("Round 11 fixture missing")
        source=candidates[0];target=source.parent/"textured_roundtrip.glb"
        if not target.is_file():raise FileNotFoundError("Round 11 roundtrip missing")
        a_fp=fingerprint(exe,source,workspace,"source_"+uuid.uuid4().hex[:8])
        report["steps"].append({"operation":"fingerprint.source","pass":True,
                                "meshes":len(a_fp["meshes"]),"images":len(a_fp["images"])})
        b_fp=fingerprint(exe,target,workspace,"target_"+uuid.uuid4().hex[:8])
        report["steps"].append({"operation":"fingerprint.roundtrip","pass":True,
                                "meshes":len(b_fp["meshes"]),"images":len(b_fp["images"])})
        match=compare(a_fp,b_fp)
        report["steps"].append({"operation":"integrity.compare","pass":match["valid"],"result":match})
        corrupt=compare(a_fp,negative_mutation(a_fp))
        report["steps"].append({"operation":"integrity.negative_test","pass":not corrupt["valid"],
                                "detected_categories":corrupt["mismatch_categories"]})
        report["full_pass"]=all(s["pass"] for s in report["steps"])
        report["status"]="passed" if report["full_pass"] else "failed"
    except Exception as exc:report.update({"status":"failed","error":repr(exc)[:800]})
    path.write_text(json.dumps(report,indent=2),encoding="utf-8")
    for i,s in enumerate(report["steps"],1):print("STEP",i,s["operation"],s["pass"],flush=True)
    print("REPORT:",path,"FULL PASS:",report["full_pass"],flush=True)
    return 0 if report["full_pass"] else 1
if __name__=="__main__":sys.exit(main())
