"""Operator-only pure C# registry fixture over an explicitly reviewed source hash.

No SDK, game, native calls or plugin execution. Not an MCP tool.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from uuid import uuid4

import build_managed_mod as managed
import coding_workspace as cw
from python_tools import _plain_path

ROOT=Path(__file__).resolve().parents[2]
SUBJECT='mods/gta-ark/common/managed/EntityRegistry.cs'


def check(root,source,reviewed_sha256):
    root=Path(root).resolve();source=_plain_path(Path(source).resolve())
    raw=source.read_bytes();actual=hashlib.sha256(raw).hexdigest()
    if actual!=reviewed_sha256 or len(raw)>131072:raise ValueError('Source hash differs from explicit operator review or exceeds 128 KiB')
    raw.decode('utf-8')
    base=_plain_path(root/'.smelter/entity-registry-runs');base.mkdir(parents=True,exist_ok=True)
    if len(list(base.iterdir()))>=20:raise ValueError('Review retained registry runs before exceeding twenty')
    folder=base/str(uuid4());folder.mkdir();(folder/'EntityRegistry.cs').write_bytes(raw)
    fixture=_plain_path(root/'tools/setup/fixtures/EntityRegistryFixture.cs')
    (folder/fixture.name).write_bytes(fixture.read_bytes())
    exe,refs,release=managed.compiler();output=folder/'EntityRegistryFixture.exe'
    args=[str(exe),*[f for f in managed.FLAGS if f!='/target:library'],'/target:exe','/out:'+str(output),
          *['/reference:'+str(p) for p in refs],str(folder/'EntityRegistry.cs'),str(folder/fixture.name)]
    receipt={'schema_version':1,'scope':'Reviewed pure C# offline identity/ownership registry fixture only',
             'source_sha256':actual,'fixture_sha256':hashlib.sha256(fixture.read_bytes()).hexdigest(),
             'framework_release':release,'game_runtime_verified':False,'sdk_referenced':False,'stage':'ERROR'}
    try:
        compiled=subprocess.run(args,capture_output=True,timeout=30,cwd=folder,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        (folder/'compile.log').write_bytes(compiled.stdout+compiled.stderr)
        receipt['compile_exit_code']=compiled.returncode
        if compiled.returncode:
            receipt['stage']='RED'
        else:
            result=subprocess.run([str(output)],cwd=folder,capture_output=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            log=result.stdout+result.stderr;(folder/'test.log').write_bytes(log)
            lines=log.decode('utf-8',errors='replace').splitlines()
            summaries=[line for line in lines if line.startswith('REGISTRY_RESULT|')]
            summary=re.fullmatch(r'REGISTRY_RESULT\|checks=([1-9][0-9]*);failures=0',summaries[0]) if len(summaries)==1 else None
            passed=sum(line.startswith('[REGISTRY PASS] ') for line in lines)
            verified=summary is not None and int(summary.group(1))==passed
            receipt.update(exit_code=result.returncode,log_sha256=hashlib.sha256(log).hexdigest(),
                           checks=passed,stage='GREEN' if result.returncode==0 and verified else 'RED')
        if source.read_bytes()!=raw:raise ValueError('Registry source changed during check')
    finally:
        (folder/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return {**receipt,'receipt':str(folder/'receipt.json'),'log':str(folder/'test.log')}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace-id',required=True)
    parser.add_argument('--reviewed-sha256',required=True);args=parser.parse_args()
    _,target=cw.load(ROOT,args.workspace_id)
    result=check(ROOT,target/SUBJECT,args.reviewed_sha256)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['stage']=='GREEN' else 1)
