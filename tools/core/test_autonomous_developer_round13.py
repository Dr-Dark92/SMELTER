#!/usr/bin/env python3
"""SMELTER Round 13: sandboxed autonomous Qwen developer experiment.

SECURITY BOUNDARY: Requires a local Docker daemon and pre-pulled Python image.
Generated code executes ONLY inside a network-disabled, resource-limited container.
The agent cannot choose host commands, mounts, tests, or container flags.
No game directories, git credentials, Docker socket, or host repository are mounted.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import uuid

IMAGE = "python:3.12-alpine"
ALLOWED = ("engine_detector.py",)
MAX_CODE_BYTES = 24000
TESTS = r'''import unittest
from engine_detector import detect_engine, inventory
class ReconTests(unittest.TestCase):
 def test_unreal(self):
  self.assertEqual(detect_engine(["Game/Content/Paks/main.pak"]), "unreal")
 def test_unity(self):
  self.assertEqual(detect_engine(["Demo_Data/globalgamemanagers"]), "unity")
 def test_godot(self):
  self.assertEqual(detect_engine(["data/game.pck"]), "godot")
 def test_unknown(self):
  self.assertEqual(detect_engine(["readme.txt"]), "unknown")
 def test_case_insensitive(self):
  self.assertEqual(detect_engine(["GAME/CONTENT/PAKS/MAIN.PAK"]), "unreal")
 def test_inventory(self):
  result=inventory(["x.pak","y.pck","notes.txt","z.bundle"])
  self.assertIsInstance(result,dict)
  self.assertEqual(result["total"],4)
  self.assertEqual(result["extensions"][".pak"],1)
  self.assertEqual(result["extensions"][".pck"],1)
 def test_no_mutation(self):
  names=["x.pak","notes.txt"]
  inventory(names)
  self.assertEqual(names,["x.pak","notes.txt"])
if __name__=="__main__":unittest.main()
'''
TASK = """Implement one standalone Python module engine_detector.py, using only Python
standard library. Export detect_engine(paths: list[str]) -> str returning one of
'unreal','unity','godot','unknown'. Recognize Unreal .pak under Content/Paks,
Unity *_Data/globalgamemanagers, Godot .pck; case insensitive; never inspect
the host filesystem. Export inventory(paths: list[str]) -> dict with total
count and extensions mapping (lowercase extension to count). This is synthetic
fixture reconnaissance, NOT real engine detection certification. Do not use
network, subprocess, shell, dynamic execution, filesystem access, or imports
of third-party packages. Respond with JSON object containing 'code' string
of the full Python module, and 'explanation' string. No Markdown fences."""

def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

def call(cmd, *, timeout=20):
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False)

def preflight():
    if not shutil.which("docker"):
        raise RuntimeError("Docker CLI missing. Install/start Docker Desktop; no unsandboxed fallback.")
    daemon=call(["docker","info","--format","{{.ServerVersion}}"])
    if daemon.returncode:
        raise RuntimeError("Docker daemon unavailable: "+daemon.stderr[-400:])
    image=call(["docker","image","inspect",IMAGE,"--format","{{.Id}}"])
    if image.returncode:
        raise RuntimeError("Sandbox image missing: run 'docker pull "+IMAGE+"' first. No automatic download.")
    return image.stdout.strip()

def model_call(url,model,prompt):
    payload={"model":model,"prompt":prompt,"stream":False,"think":False,"format":"json",
             "options":{"temperature":0,"num_ctx":8192,"num_predict":3600}}
    req=urllib.request.Request(url.rstrip("/")+"/api/generate",
        data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
    with urllib.request.urlopen(req,timeout=150) as res:
        response=json.load(res)
    obj=json.loads(response["response"])
    if not isinstance(obj,dict) or not isinstance(obj.get("code"),str):
        raise ValueError("Model response lacks a code string")
    return obj

def validate_code(code):
    if len(code.encode("utf-8"))>MAX_CODE_BYTES:raise ValueError("Generated module too large")
    if "\x00" in code:raise ValueError("NUL in generated code")
    # Not a security sandbox: this is only a quality guard. Docker is the boundary.
    import ast
    tree=ast.parse(code)
    banned={"subprocess","socket","ctypes","multiprocessing","urllib","requests","pickle","importlib"}
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):
            if any(a.name.split(".")[0] in banned for a in node.names):
                raise ValueError("Disallowed module")
        if isinstance(node,ast.ImportFrom) and (node.module or "").split(".")[0] in banned:
            raise ValueError("Disallowed module")
    return True

def run_tests(folder):
    # Bind only disposable experiment files; host repo, credentials, game assets excluded.
    mount=str(folder.resolve())
    cmd=["docker","run","--rm","--pull=never","--network=none",
         "--read-only","--cap-drop=ALL","--security-opt=no-new-privileges",
         "--pids-limit=64","--memory=256m","--cpus=1",
         "--user=65534:65534","--tmpfs=/tmp:rw,noexec,nosuid,size=16m",
         "--mount",f"type=bind,source={mount},target=/work,readonly",
         "--workdir=/work",IMAGE,"python","-I","-B","-S","/work/acceptance_test.py"]
    try:
        result=call(cmd,timeout=40)
        return {"pass":result.returncode==0,"exit_code":result.returncode,
                "stdout":result.stdout[-6000:],"stderr":result.stderr[-6000:]}
    except subprocess.TimeoutExpired:
        return {"pass":False,"exit_code":None,"stderr":"Sandbox execution timed out","stdout":""}

def run(args):
    root=Path(args.root).resolve()
    workspace=root/"workspace"
    if not workspace.is_dir():raise RuntimeError("SMELTER workspace missing")
    image_digest=preflight()
    run_id=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:8]
    folder=workspace/"smelter-round13"/run_id
    folder.mkdir(parents=True,exist_ok=False)
    log=folder/"events.jsonl"
    report=folder/"smelter-round13.json"
    test=folder/"acceptance_test.py"
    test.write_text(TESTS,encoding="utf-8")
    events=[]
    def emit(kind,**fields):
        item={"timestamp":stamp(),"event":kind,**fields}
        events.append(item)
        with log.open("a",encoding="utf-8") as stream:
            stream.write(json.dumps(item,ensure_ascii=False)+"\n")
        print(f"[{item['timestamp']}] {kind} "+json.dumps(fields,ensure_ascii=False)[:240],flush=True)
    start=time.monotonic()
    success=False
    previous_hashes=set()
    feedback="No previous attempt."
    try:
        emit("sandbox.ready",image=IMAGE,image_id=image_digest,network="none",workspace=str(folder))
        for attempt in range(1,args.attempts+1):
            if time.monotonic()-start>args.budget_seconds:
                emit("budget.exhausted");break
            emit("attempt.begin",attempt=attempt)
            prompt=TASK+"\nPREVIOUS TEST FEEDBACK:\n"+feedback[-4500:]
            try:
                obj=model_call(args.url,args.model,prompt)
                code=obj["code"]
                validate_code(code)
                digest=hashlib.sha256(code.encode()).hexdigest()
                if digest in previous_hashes:
                    emit("loop.detected",sha256=digest);break
                previous_hashes.add(digest)
                candidate=folder/ALLOWED[0]
                candidate.write_text(code,encoding="utf-8")
                emit("candidate.written",attempt=attempt,sha256=digest,bytes=len(code.encode()))
                outcome=run_tests(folder)
                emit("tests.finished",attempt=attempt,passed=outcome["pass"],
                     exit_code=outcome["exit_code"],stdout=outcome["stdout"],stderr=outcome["stderr"])
                if outcome["pass"]:
                    success=True
                    emit("acceptance.passed",attempt=attempt)
                    break
                feedback="Test failed:\n"+outcome["stdout"]+"\n"+outcome["stderr"]
            except Exception as exc:
                feedback=f"{type(exc).__name__}: {str(exc)[:1500]}"
                emit("attempt.error",attempt=attempt,error=feedback)
        if not success:
            # Rollback candidate. Logs, test fixture, report retained for analysis.
            (folder/ALLOWED[0]).unlink(missing_ok=True)
            emit("rollback.completed",reason="No passing candidate; generated code deleted")
    finally:
        data={"round":13,"full_pass":success,"status":"passed" if success else "failed",
              "model":args.model,"sandbox_image":IMAGE,"sandbox_image_id":image_digest,
              "iterations":sum(e["event"]=="attempt.begin" for e in events),
              "elapsed_seconds":round(time.monotonic()-start,2),
              "events":events,
              "notes":"Synthetic game recon module only. No host-side execution of model code. Passing artifact remains disposable and is not merged into the repository."}
        report.write_text(json.dumps(data,indent=2),encoding="utf-8")
        emit("report.saved",report=str(report),full_pass=success)
    print("REPORT:",report,"FULL PASS:",success,flush=True)
    return 0 if success else 1

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\SMELTER")
    p.add_argument("--model",default="qwen3.5:9b")
    p.add_argument("--url",default="http://127.0.0.1:11434")
    p.add_argument("--attempts",type=int,default=6)
    p.add_argument("--budget-seconds",type=int,default=1200)
    a=p.parse_args()
    if not 1<=a.attempts<=10: p.error("--attempts must be 1..10")
    if not 60<=a.budget_seconds<=1800:p.error("--budget-seconds must be 60..1800")
    try:return run(a)
    except Exception as exc:
        print("ROUND 13 BLOCKED:",type(exc).__name__,str(exc),file=sys.stderr)
        return 2
if __name__=="__main__":sys.exit(main())
