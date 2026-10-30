"""Operator-only fixed C# compiler: no MSBuild, analyzers or artifact execution.

This is deliberately not an MCP/model tool or a host fallback for native_build.
The operator reviews the source, then compiles an owned coding copy using the
installed Windows .NET Framework compiler and hash-pinned development SDK.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/dashboard'))
import coding_workspace as cw
from native_build import _inside, _name
from python_tools import _plain_path
import install_managed_sdk as sdk

FLAGS=['/nologo','/noconfig','/target:library','/platform:x64','/optimize+','/warn:4','/warnaserror+',
       '/unsafe-','/langversion:5','/nostdlib+','/codepage:65001']
FRAMEWORK_REFERENCES=['mscorlib.dll','System.dll','System.Core.dll','System.Runtime.Serialization.dll','System.Xml.dll','Microsoft.CSharp.dll']


def compiler():
    if os.name!='nt':raise ValueError('Operator C# builds currently require Windows')
    import winreg
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\Microsoft\NET Framework Setup\NDP\v4\Full') as key:
        release=winreg.QueryValueEx(key,'Release')[0]
    if release < 461808:raise ValueError('.NET Framework 4.7.2 or later is required')
    base=_plain_path(Path(os.environ.get('WINDIR',r'C:\Windows'))/'Microsoft.NET/Framework64/v4.0.30319')
    exe=_plain_path(base/'csc.exe')
    refs=[_plain_path(base/name) for name in FRAMEWORK_REFERENCES]
    if not exe.is_file() or any(not p.is_file() for p in refs):raise ValueError('Windows C# compiler/reference assemblies unavailable')
    return exe,refs,release


def manifest(mod):
    path=_plain_path(mod/'managed.json')
    if not path.is_file() or path.stat().st_size>16384:raise ValueError('Managed mod needs managed.json (max 16 KiB)')
    value=json.loads(path.read_text(encoding='utf-8'))
    if set(value)!={'schema_version','sdk','targets'} or type(value['schema_version']) is not int or value['schema_version']!=1:raise ValueError('Invalid managed manifest fields')
    if not isinstance(value['targets'],list) or not 1<=len(value['targets'])<=6:raise ValueError('Choose one to six managed targets')
    seen=set()
    for target in value['targets']:
        if not isinstance(target,dict) or not {'name','sources'} <= set(target) <= {'name','sources','sdk'}:raise ValueError('Managed target accepts name, sources and optional pinned sdk only')
        # One pinned SDK id, or a list of up to three distinct ids (e.g. a plugin that also references the Lua binding).
        ids=target.get('sdk',[]);ids=[ids] if isinstance(ids,str) else ids
        if not isinstance(ids,list) or len(ids)>3 or len(set(map(str,ids)))!=len(ids) or ('sdk' in target and not ids) or            not all(isinstance(i,str) and re.fullmatch(r'[a-z][a-z0-9_-]{0,30}',i) for i in ids):raise ValueError('Invalid target SDK identity')
        name=_name(target['name'],'managed target')
        if name.lower() in seen:raise ValueError('Duplicate managed target')
        seen.add(name.lower())
        if not isinstance(target['sources'],list) or not 1<=len(target['sources'])<=16:raise ValueError('Managed target needs 1-16 sources')
        if len({s.lower() for s in target['sources'] if isinstance(s,str)})!=len(target['sources']):raise ValueError('Duplicate or invalid source names')
        for source in target['sources']:
            if Path(_inside(mod,source,'C# source')).suffix.lower()!='.cs':raise ValueError('Managed sources must be .cs files')
    return value


def build(root, workspace_id, mod_name, target_name):
    root=Path(root).resolve();mod_name=_name(mod_name,'mod');target_name=_name(target_name,'target')
    with cw.locked(root):
        _,target=cw.load(root,workspace_id)
        mod=_plain_path(target/'mods'/mod_name)
        config=manifest(mod); matches=[t for t in config['targets'] if t['name']==target_name]
        if len(matches)!=1:raise ValueError('Choose an existing exact managed target')
        source={}
        for name in matches[0]['sources']:
            path=_plain_path(mod/name)
            if not path.is_file() or path.stat().st_size>131072:raise ValueError('Source unavailable or exceeds 128 KiB')
            raw=path.read_bytes()
            if b'\0' in raw:raise ValueError('NUL in C# source')
            raw.decode('utf-8');source[name]=raw
        if len(source)!=len(matches[0]['sources']) or sum(map(len,source.values()))>1048576:raise ValueError('Duplicate/oversized source selection')
        tree=cw.tree_digest(cw._scan(target))
    sdk_ids=matches[0].get('sdk',config['sdk']);sdk_ids=[sdk_ids] if isinstance(sdk_ids,str) else sdk_ids
    sdk_id=sdk_ids[0];pins=[];sdk_refs=[]
    for current in sdk_ids:
        dependency=sdk.inspect(root,current);pin=sdk.spec(root,current);pins.append((current,pin))
        refs_for=[Path(p) for n,p in dependency['files'].items() if n.lower().endswith('.dll') and pin['files'][n].get('reference',True)]
        if not refs_for:raise ValueError('Pinned SDK supplies no reference assembly: '+current)
        sdk_refs+=refs_for
    pin=pins[0][1]
    exe,refs,release=compiler()
    base=_plain_path(root/'.smelter/managed-builds');base.mkdir(parents=True,exist_ok=True)
    if len(list(base.iterdir()))>=20:raise ValueError('Review existing managed builds before creating more than twenty')
    run=base/str(uuid4());snapshot=run/'source';out=run/'out';out.mkdir(parents=True);snapshot.mkdir()
    for name,raw in source.items():
        p=snapshot/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    artifact=out/(target_name+'.dll')
    command=[str(exe),*FLAGS,'/out:'+str(artifact),*['/reference:'+str(p) for p in refs+sdk_refs],
             *[str(snapshot/name) for name in source]]
    receipt={'schema_version':1,'workspace_id':workspace_id,'tree_sha256':tree,'target':target_name,
        'stage':'building','scope':'operator-only compile validation; no artifact execution or game verification',
        'sdk':{'id':sdk_id,'version':pin['version'],'package_sha256':pin['package_sha256'],'redistribute':pin['redistribute']},
        **({'additional_sdks':[{'id':i,'version':q['version'],'package_sha256':q['package_sha256'],'redistribute':q['redistribute']} for i,q in pins[1:]]} if len(pins)>1 else {}),
        'source_hashes':{n:cw.digest(raw) for n,raw in source.items()},'compiler_sha256':cw.digest(exe.read_bytes()),
        'framework_release':release,'flags':FLAGS,'references':{str(p):cw.digest(p.read_bytes()) for p in refs+sdk_refs},
        'artifact_executed':False,'game_runtime_verified':False,'sdk_copied_to_output':False}
    receipt_path=run/'receipt.json';receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    try:
        result=subprocess.run(command,cwd=snapshot,stdin=subprocess.DEVNULL,capture_output=True,timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        log=(result.stdout+result.stderr)[:262144];(run/'build.log').write_bytes(log)
        receipt.update(exit_code=result.returncode,log_sha256=cw.digest(log))
        if result.returncode or not artifact.is_file() or not artifact.stat().st_size:
            receipt['stage']='compile_failed'
        else:
            if any((mod/name).read_bytes()!=raw for name,raw in source.items()):raise ValueError('Source changed during compile')
            for current in sdk_ids:sdk.inspect(root,current)
            receipt.update(stage='compiled',artifact={'path':str(artifact),'bytes':artifact.stat().st_size,'sha256':cw.digest(artifact.read_bytes())})
    except Exception as error:
        receipt.update(stage='error',error=str(error));receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8');raise
    receipt_path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    return {**receipt,'receipt_path':str(receipt_path),'log_path':str(run/'build.log')}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--workspace-id',required=True)
    parser.add_argument('--mod',required=True);parser.add_argument('--target',required=True)
    args=parser.parse_args(argv);result=build(ROOT,args.workspace_id,args.mod,args.target)
    print(json.dumps(result,indent=2))
    return 0 if result.get('stage')=='compiled' else 1


if __name__=='__main__':
    raise SystemExit(main())
