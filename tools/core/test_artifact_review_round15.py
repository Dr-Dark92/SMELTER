#!/usr/bin/env python3
"""Round 15 pre-production gate: inspect and regression-test Round 14 artifacts.

Runs generated modules only inside Docker. Never promotes code or mounts the repo.
"""
from __future__ import annotations
import argparse
import ast
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys

FILES = ("engine_detector.py", "archive_inventory.py", "report_generator.py")
IMAGE = "python:3.12-alpine"
TESTS = r'''import unittest,json
from engine_detector import detect_engine
from archive_inventory import inventory
from report_generator import build_report
class Regression(unittest.TestCase):
 def test_empty(self): self.assertEqual(build_report([])["inventory"],{"total":0,"extensions":{}})
 def test_windows_separators(self):
  self.assertEqual(detect_engine([r"Game\Content\Paks\MAIN.PAK"]),"unreal")
 def test_uppercase_extensions(self):
  self.assertEqual(inventory(["A.PAK","b.pak"])["extensions"][".pak"],2)
 def test_duplicate_counts(self):
  self.assertEqual(inventory(["a.pck","a.pck"])["total"],2)
 def test_report_shape(self):
  self.assertEqual(set(build_report(["a.pck"])),{"schema_version","engine","inventory"})
 def test_no_mutation(self):
  data=["A.PAK","a.pak"]
  build_report(data)
  self.assertEqual(data,["A.PAK","a.pak"])
 def test_json(self):
  self.assertIsInstance(json.dumps(build_report(["a.pck"])),str)
 def test_unknown(self):
  self.assertEqual(detect_engine(["notes.txt","file.zip"]),"unknown")
 def test_godot(self):
  self.assertEqual(detect_engine(["GAME.PCK"]),"godot")
 def test_unity(self):
  self.assertEqual(detect_engine(["Demo_Data/globalgamemanagers"]),"unity")
if __name__=="__main__":unittest.main()
'''
def check_source(path):
    source=path.read_text(encoding="utf-8")
    tree=ast.parse(source,filename=path.name)
    issues=[]
    forbidden={"subprocess","socket","ctypes","multiprocessing","urllib","requests","pickle","importlib"}
    dangerous_calls={"eval","exec","compile","open","__import__","input"}
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in forbidden: issues.append("forbidden import "+alias.name)
        if isinstance(node,ast.ImportFrom) and (node.module or "").split(".")[0] in forbidden:
            issues.append("forbidden import "+str(node.module))
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in dangerous_calls:
            issues.append("risky call "+node.func.id)
    return {"sha256":hashlib.sha256(source.encode()).hexdigest(),"bytes":len(source.encode()),
            "issues":issues,"functions":[n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\SMELTER")
    a=p.parse_args()
    root=Path(a.root).resolve()
    candidates=sorted((root/"workspace"/"smelter-round14").glob("*/smelter-round14.json"),reverse=True)
    successful=[]
    for report in candidates:
        try:
            if json.loads(report.read_text(encoding="utf-8")).get("full_pass") and all((report.parent/f).is_file() for f in FILES):
                successful.append(report.parent)
        except (ValueError,OSError): continue
    if not successful:
        print("ROUND 15 BLOCKED: No retained passing Round 14 source found",file=sys.stderr)
        return 2
    source_dir=successful[0]
    audit={f:check_source(source_dir/f) for f in FILES}
    problems={f:entry["issues"] for f,entry in audit.items() if entry["issues"]}
    output={"round":15,"source_round":14,"source_run":source_dir.name,
            "review":audit,"static_pass":not bool(problems),"dynamic_pass":False,
            "full_pass":False,"promotion":"not authorized"}
    # Read-only bind of the disposable source directory; never mount host repo.
    test_path=source_dir/"round15_regression_test.py"
    test_path.write_text(TESTS,encoding="utf-8")
    cmd=["docker","run","--rm","--pull=never","--network=none","--read-only",
         "--cap-drop=ALL","--security-opt=no-new-privileges","--pids-limit=64",
         "--memory=256m","--cpus=1","--user=65534:65534",
         "--tmpfs=/tmp:rw,noexec,nosuid,size=16m",
         "--mount",f"type=bind,source={source_dir},target=/work,readonly",
         "--workdir=/work",IMAGE,"python","-I","-B","-S","-c",
         "import sys,runpy;sys.path.insert(0,'/work');runpy.run_path('/work/round15_regression_test.py',run_name='__main__')"]
    try:
        result=subprocess.run(cmd,text=True,capture_output=True,timeout=45,check=False)
        output["dynamic_pass"]=result.returncode==0
        output["test_exit_code"]=result.returncode
        output["test_stdout"]=result.stdout[-3000:]
        output["test_stderr"]=result.stderr[-5000:]
    except (subprocess.TimeoutExpired,OSError) as exc:
        output["test_error"]=str(exc)[:500]
    output["full_pass"]=output["static_pass"] and output["dynamic_pass"]
    output["status"]="passed" if output["full_pass"] else "failed"
    output["timestamp"]=dt.datetime.now(dt.timezone.utc).isoformat()
    report_path=source_dir/"smelter-round15.json"
    report_path.write_text(json.dumps(output,indent=2),encoding="utf-8")
    print("REPORT:",report_path,"FULL PASS:",output["full_pass"])
    print("Static issues:",problems)
    print(output.get("test_stderr",output.get("test_error",""))[-3000:])
    return 0 if output["full_pass"] else 1
if __name__=="__main__":sys.exit(main())
