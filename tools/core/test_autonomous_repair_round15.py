#!/usr/bin/env python3
"""Round 15B: autonomously repair Round 14 modules against combined regression gates.

Never modifies the original artifact or SMELTER source tree. Generated modules run
only in the existing locked-down Docker sandbox; review required before promotion.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
import time
import uuid

import test_autonomous_developer_round14 as base
import test_artifact_review_round15 as review

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",default=r"C:\SMELTER")
    p.add_argument("--model",default="qwen3.5:9b")
    p.add_argument("--url",default="http://127.0.0.1:11434")
    p.add_argument("--attempts",type=int,default=6)
    a=p.parse_args()
    if not 1<=a.attempts<=10:p.error("attempts must be 1..10")
    root=Path(a.root).resolve()
    image=base.preflight()
    source_reports=sorted((root/"workspace"/"smelter-round14").glob("*/smelter-round14.json"),reverse=True)
    source=None
    for item in source_reports:
        try:
            if json.loads(item.read_text(encoding="utf-8")).get("full_pass") and all((item.parent/f).is_file() for f in base.ALLOWED):
                source=item.parent
                break
        except (ValueError,OSError):pass
    if source is None:raise RuntimeError("No successful Round 14 source available")
    run_id=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+uuid.uuid4().hex[:8]
    folder=root/"workspace"/"smelter-round15-repair"/run_id
    folder.mkdir(parents=True,exist_ok=False)
    (folder/"acceptance_test.py").write_text(base.TESTS,encoding="utf-8")
    (folder/"round15_regression_test.py").write_text(review.TESTS,encoding="utf-8")
    tests=(("acceptance_test.py","round14"),("round15_regression_test.py","round15"))
    events=[]
    def emit(event,**kwargs):
        row={"event":event,"timestamp":base.stamp(),**kwargs}
        events.append(row)
        with (folder/"events.jsonl").open("a",encoding="utf-8") as f:f.write(json.dumps(row)+"\n")
        print(event,json.dumps(kwargs)[:320],flush=True)
    def docker_test(test_name):
        # Identical isolation settings to Round 14; fixed test filenames only.
        cmd=["docker","run","--rm","--pull=never","--network=none","--read-only",
             "--cap-drop=ALL","--security-opt=no-new-privileges","--pids-limit=64",
             "--memory=256m","--cpus=1","--user=65534:65534",
             "--tmpfs=/tmp:rw,noexec,nosuid,size=16m",
             "--mount",f"type=bind,source={folder.resolve()},target=/work,readonly",
             "--workdir=/work",base.IMAGE,"python","-I","-B","-S","-c",
             "import sys,runpy;sys.path.insert(0,'/work');runpy.run_path('/work/"+test_name+"',run_name='__main__')"]
        try:
            r=base.call(cmd,timeout=45)
            return {"passed":r.returncode==0,"exit_code":r.returncode,"stderr":r.stderr[-4000:]}
        except Exception as e:return {"passed":False,"error":str(e)[:500]}
    previous={f:(source/f).read_text(encoding="utf-8") for f in base.ALLOWED}
    prompt=base.TASK+"\nExisting implementation (repair, do not merely describe fixes):\n"+json.dumps(previous)
    feedback="Independent regression failures: inventory(['A.PAK','b.pak']) must count '.pak' as 2; detect_engine([r'Game\\Content\\Paks\\MAIN.PAK']) must return 'unreal'. Preserve all Round 14 behavior."
    # Explain Windows path semantics explicitly: pathlib.Path on Linux does not
    # interpret backslashes as separators. Qwen must normalize in-memory strings.
    windows_hint=(
        "IMPORTANT CROSS-PLATFORM CONTRACT: Docker runs Linux Python, but inputs "
        "may contain Windows backslash separators. pathlib.Path on Linux treats "
        "backslash as an ordinary character. Normalize each supplied path string "
        "by replacing chr(92) with '/' BEFORE matching path components. "
        "Then lowercase/casefold the normalized path. Example: "
        "Game\\Content\\Paks\\MAIN.PAK must match unreal. "
        "Do not access the filesystem. Keep the other two modules working."
    )
    inventory_hint=(
        "INVENTORY CONTRACT: for each input path, normalize separators with "
        "replace(chr(92), '/'), isolate the final filename, then lowercase "
        "the extension BEFORE using it as a dictionary key. "
        "inventory(['A.PAK','b.pak']) must yield extensions['.pak']==2. "
        "Preserve Windows-path Unreal detection simultaneously."
    )
    seen=set()
    passed=False
    start=time.monotonic()
    try:
        emit("sandbox.ready",image_id=image,source_run=source.name)
        for attempt in range(1,a.attempts+1):
            if time.monotonic()-start>1200:break
            emit("attempt.begin",attempt=attempt)
            try:
                obj=base.model_call(a.url,a.model,prompt+"\nCROSS-PLATFORM REQUIREMENT:\n"+windows_hint+"\nINVENTORY REQUIREMENT:\n"+inventory_hint+"\nTEST FEEDBACK:\n"+feedback[-5500:])
                files=obj["files"]
                if set(files)!=set(base.ALLOWED):raise ValueError("Must supply exactly three files")
                if any(not isinstance(v,str) for v in files.values()):raise ValueError("File content must be string")
                for content in files.values():base.validate_code(content)
                digest=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()
                if digest in seen:
                    emit("loop.detected",sha256=digest);break
                seen.add(digest)
                for name,content in files.items():(folder/name).write_text(content,encoding="utf-8")
                emit("candidate.written",attempt=attempt,sha256=digest)
                static={f:review.check_source(folder/f) for f in base.ALLOWED}
                issues={k:v["issues"] for k,v in static.items() if v["issues"]}
                outcomes={label:docker_test(test) for test,label in tests}
                passed=not issues and all(x["passed"] for x in outcomes.values())
                emit("tests.finished",attempt=attempt,passed=passed,static_issues=issues,outcomes=outcomes)
                if passed:break
                feedback=json.dumps({"static_issues":issues,"outcomes":outcomes})
                prompt=base.TASK+"\nPrevious candidate:\n"+json.dumps(files)
                if not outcomes["round15"]["passed"]:
                    feedback+="\n"+windows_hint+"\n"+inventory_hint
            except Exception as exc:
                feedback=f"{type(exc).__name__}: {str(exc)[:1000]}"
                emit("attempt.error",attempt=attempt,error=feedback)
        if not passed:
            for f in base.ALLOWED:(folder/f).unlink(missing_ok=True)
            emit("rollback.completed")
    finally:
        result={"round":"15-repair","full_pass":passed,"source_run":source.name,
                "model":a.model,"iterations":sum(e["event"]=="attempt.begin" for e in events),
                "elapsed_seconds":round(time.monotonic()-start,2),"events":events,
                "promotion":"not authorized","notes":"Passing source retained only in disposable workspace. No automatic merge."}
        report=folder/"smelter-round15-repair.json"
        report.write_text(json.dumps(result,indent=2),encoding="utf-8")
        print("REPORT:",report,"FULL PASS:",passed,flush=True)
    return 0 if passed else 1

if __name__=="__main__":
    try:sys.exit(main())
    except Exception as e:
        print("ROUND 15 REPAIR BLOCKED:",type(e).__name__,str(e),file=sys.stderr)
        sys.exit(2)
