"""Operator-registered, controller-owned acceptance outside model-editable copies."""
import hashlib
import json
from pathlib import Path
import re
from uuid import uuid4

_EXECUTION_SHA=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

DEFINITIONS = {'entity-policy-v1': {'profile':'lua','verifier':'entity_policy_v1.lua','checks':30,
    'contract':'All entity/policy map entries must have string keys and boolean values. Only true entries participate. Optional maps are absent only at nil. Present empty/all-disabled any_traits rejects. Validate all entries before matching. Comments and editable test expectations cannot override this contract.'}}


def _config(root,sid):
    import coding_workspace as cw
    return cw.base_path(root)/cw.identifier(sid)/'acceptance.json'


def verifier_path(identity):
    from python_tools import _plain_path
    if identity not in DEFINITIONS:raise ValueError('Unknown controller acceptance contract')
    path=_plain_path(Path(__file__).parent/'acceptance'/DEFINITIONS[identity]['verifier'])
    if not path.is_file() or path.stat().st_size>32768:raise ValueError('Controller acceptance verifier unavailable')
    return path


def register(root,sid,identity,subject_path):
    """Trusted operator API only. Deliberately absent from the model tool registry."""
    import coding_workspace as cw
    with cw.locked(root):
        _,target=cw.load(root,sid)
        subject_path=cw.relative_path(subject_path)
        path=cw._file(target,subject_path)
        if path.suffix!='.lua' or not path.is_file() or path.stat().st_size>cw.MAX_FILE:raise ValueError('Choose an existing Lua subject of at most 128 KiB')
        current=load(root,sid,target)
        if any(c['id']==identity for c in current):raise ValueError('Contract already registered; explicit operator migration required')
        if len(current)>=4:raise ValueError('At most four controller acceptance contracts')
        source=verifier_path(identity)
        contract={'id':identity,'profile':DEFINITIONS[identity]['profile'],'subject_path':subject_path,
                  'verifier_sha256':cw.digest(source.read_bytes())}
        config={'schema_version':1,'workspace_id':sid,'contracts':current+[contract]}
        raw=json.dumps(config).encode('utf-8');cw.reserve_metadata(root,len(raw),1)
        cw._save(_config(root,sid),config)
        return summary(config['contracts'])


def load(root,sid,target):
    import coding_workspace as cw
    from python_tools import _plain_path
    path=_plain_path(_config(root,sid))
    if not path.exists():return []
    if path.stat().st_size>16384:raise ValueError('Acceptance registry exceeds 16 KiB')
    value=json.loads(path.read_text(encoding='utf-8'))
    if value.get('schema_version')!=1 or value.get('workspace_id')!=sid:raise ValueError('Acceptance registry ownership mismatch')
    contracts=value.get('contracts')
    if not isinstance(contracts,list) or not 1<=len(contracts)<=4:raise ValueError('Invalid acceptance contract count')
    seen=set()
    for spec in contracts:
        if not isinstance(spec,dict) or set(spec)!={'id','profile','subject_path','verifier_sha256'}:raise ValueError('Invalid acceptance definition')
        identity=spec['id'];source=verifier_path(identity)
        if identity in seen or spec['profile']!=DEFINITIONS[identity]['profile']:raise ValueError('Invalid acceptance identity/profile')
        seen.add(identity)
        if cw.digest(source.read_bytes())!=spec['verifier_sha256']:raise ValueError('Frozen verifier changed; operator review required')
        cw._file(target,spec['subject_path'])  # Recheck subject read access, including missing subjects.
    return contracts


def revision(contracts):
    return _revision(contracts,_EXECUTION_SHA)


def _revision(contracts,runner_sha):
    identity={'contracts':contracts,'runner_sha256':runner_sha}
    return hashlib.sha256(json.dumps(identity,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def summary(contracts):
    return [{'id':c['id'],'profile':c['profile'],'subject_path':c['subject_path'],
             'verifier_sha256':c['verifier_sha256'],'checks':DEFINITIONS[c['id']]['checks'],
             'contract':DEFINITIONS[c['id']]['contract'],'model_editable':False} for c in contracts]


def fresh(root,sid,target,profile,saved):
    contracts=[c for c in load(root,sid,target) if c['profile']==profile]
    current_runner=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return not contracts or saved.get('acceptance_revision')==_revision(contracts,current_runner)


DRIVER=r'''
import hashlib,json,subprocess
from pathlib import Path
manifest=json.loads(Path('/contracts/manifest.json').read_text())
results=[]
for spec in manifest:
 subject=Path(spec['subject_path']);source=Path('/contracts')/(spec['id']+'.lua')
 item={k:spec[k] for k in ('id','subject_path','verifier_sha256')}
 item['subject_sha256']=hashlib.sha256(subject.read_bytes()).hexdigest() if subject.is_file() else None
 if not subject.is_file():
  item.update(stage='ERROR',error='subject missing');results.append(item);continue
 if hashlib.sha256(source.read_bytes()).hexdigest()!=spec['verifier_sha256']:
  item.update(stage='ERROR',error='verifier hash mismatch');results.append(item);continue
 try:
  ran=subprocess.run(['lua5.4',str(source),spec['subject_path']],capture_output=True,text=True,timeout=12)
  print(ran.stdout+ran.stderr,flush=True)
  import re
  packets=re.findall(r'^SMELTER_ACCEPTANCE_CHECKS\|(\{[^\n]+\})\s*$',ran.stdout,re.M)
  counts=json.loads(packets[0]) if len(packets)==1 else {}
  valid=set(counts)=={'checks','failures'} and type(counts['checks']) is int and type(counts['failures']) is int and counts['checks']==spec['expected_checks'] and 0<=counts['failures']<=counts['checks']
  stage='GREEN' if valid and ran.returncode==0 and counts['failures']==0 else 'RED' if valid and ran.returncode==1 and counts['failures']>0 else 'ERROR'
  item.update(stage=stage,exit_code=ran.returncode,counts=counts)
 except (OSError,subprocess.TimeoutExpired,ValueError) as exc:item.update(stage='ERROR',error=type(exc).__name__)
 results.append(item)
print('SMELTER_ACCEPTANCE_RESULT|'+json.dumps(results),flush=True)
raise SystemExit(0 if all(r['stage']=='GREEN' for r in results) else 1)
'''


def run(root,target,contracts,expected_files):
    """Run pinned verifiers separately from editable tests in a fresh RO snapshot."""
    import coding_workspace as cw
    import sandbox
    from python_tools import _plain_path
    ready=sandbox.status(root,operation='coding_lua')
    if not ready['ready']:raise ValueError('Acceptance runner unavailable: '+ready['reason'])
    folder,code=sandbox.snapshot(root,target);name='smelter-tests-'+uuid4().hex;confirmed=False
    image=ready['configured']['cpp_image']
    try:
        contract_dir=_plain_path(folder/'contracts');contract_dir.mkdir(mode=0o755)
        manifest=[]
        for spec in contracts:
            source=verifier_path(spec['id']);raw=source.read_bytes()
            if cw.digest(raw)!=spec['verifier_sha256']:raise ValueError('Frozen verifier changed before execution')
            destination=contract_dir/(spec['id']+'.lua');destination.write_bytes(raw);destination.chmod(0o644)
            manifest.append({**spec,'expected_checks':DEFINITIONS[spec['id']]['checks']})
        (contract_dir/'manifest.json').write_text(json.dumps(manifest),encoding='utf-8');(contract_dir/'manifest.json').chmod(0o644)
        if any(c in str(contract_dir) for c in (',','\n','\r')):raise ValueError('Unsupported contract mount path')
        sandbox.record_owner(folder,name,image,'tests')
        args=sandbox._flags(ready['docker'],name,code)+['--mount','type=bind,source='+str(contract_dir)+',target=/contracts,readonly','--rm',image,'python','-I','-c',DRIVER]
        ran=sandbox.run(args,timeout=60,max_output=256*1024);raw=ran.stdout+ran.stderr
        packets=re.findall(rb'^SMELTER_ACCEPTANCE_RESULT\|(\{[^\n]+\}|\[[^\n]+\])\s*$',raw,re.M)
        results=json.loads(packets[0]) if len(packets)==1 else []
        valid=isinstance(results,list) and len(results)==len(contracts)
        if valid:
            for spec,item in zip(contracts,results):
                if (not isinstance(item,dict) or item.get('id')!=spec['id'] or
                    item.get('verifier_sha256')!=spec['verifier_sha256'] or item.get('subject_path')!=spec['subject_path'] or
                    item.get('subject_sha256')!=expected_files.get(spec['subject_path']) or item.get('stage') not in ('GREEN','RED','ERROR')):
                    valid=False;break
        stage='ERROR' if not valid or any(i.get('stage')=='ERROR' for i in results) else 'RED' if any(i['stage']=='RED' for i in results) else 'GREEN'
        if stage=='GREEN' and ran.returncode!=0:stage='ERROR'
        return {'stage':stage,'contracts_revision':revision(contracts),'runner_sha256':_EXECUTION_SHA,'contracts':results if valid else [],
                'snapshot_id':folder.name,'sandbox':'docker-no-network','model_editable':False,
                'log_tail':raw.decode('utf-8',errors='replace')[-10000:],'_raw_output':raw,
                'scope':'Controller-owned pure-module acceptance, independently bound to exact subject and verifier hashes'}
    finally:
        confirmed=sandbox._remove(ready['docker'],name)
        sandbox.record_owner(folder,name,image,'tests',finished=confirmed)
        if confirmed:
            import shutil
            if folder.resolve().parent!=(Path(root)/'.smelter/sandbox-runs').resolve():raise ValueError('Unexpected acceptance snapshot cleanup path')
            shutil.rmtree(folder)
        else:raise ValueError('Acceptance container cleanup was not confirmed: '+name)
