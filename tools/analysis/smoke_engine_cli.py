"""Real no-network CLI and stdio MCP fixture checks; optional read-only ARK checks.

Creates synthetic PAK/IoStore fixtures only in application-owned storage. The
Unity fixture is pinned official upstream test data. Never launches a game.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
import urllib.request
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/dashboard'))
UNITY_URL='https://raw.githubusercontent.com/Unity-Technologies/UnityDataTools/v2.4.0/TestCommon/Data/AssetBundleTypeTreeVariations/AssetBundle-NoTypeTree/small.bundle'
UNITY_SHA256='cc17a48799f1714cd912a0ac6c78ecb8505fac627ae147887f865d0217709a3c'
FIXTURE_WORKER=r'''
import pathlib,subprocess,json,base64
p=pathlib.Path('/tmp/data');p.mkdir();(p/'readme.txt').write_text('SMELTER synthetic fixture\n')
subprocess.run(['/opt/engine-cli/repak/repak','pack',str(p),'/tmp/fixture.pak','--version','V11','--quiet'],check=True,stdout=subprocess.PIPE)
p=pathlib.Path('/tmp/raw');(p/'chunks').mkdir(parents=True)
(p/'manifest.json').write_text(json.dumps({'version':'PerfectHashWithOverflow','mount_point':'../../../','chunk_paths':{'010000000000000000000002':'../../../Fixture/data.bin'}}))
(p/'chunks/010000000000000000000002').write_bytes(b'SMELTER fixture')
subprocess.run(['/opt/engine-cli/retoc/retoc','pack-raw',str(p),'/tmp/fixture.utoc'],check=True)
print(json.dumps({p.name:base64.b64encode(p.read_bytes()).decode() for p in pathlib.Path('/tmp').glob('fixture.*')}))
'''


def smoke(ark_folder=None):
    from access_policy import Policy, current, using
    from mcp_connections import exchange
    from sandbox import status
    from process_runner import run
    ready=status(ROOT,'engine_archive')
    if not ready['ready']:raise ValueError(ready['reason'])
    folder=ROOT/'.smelter/engine-cli-runs'/uuid4().hex
    fixtures=folder/'fixtures';fixtures.mkdir(parents=True)
    image=ready['configured']['engine_image']
    made=run([ready['docker'],'run','--rm','--pull','never','--network','none','--read-only',
              '--cap-drop','ALL','--security-opt','no-new-privileges','--pids-limit','64','--memory','768m',
              '--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=128m',image,'python','-I','-c',FIXTURE_WORKER],
             timeout=40,max_output=16384,text=True,check=True)
    for name,raw in json.loads(made.stdout).items():
        if name not in ('fixture.pak','fixture.utoc','fixture.ucas'):raise ValueError('Unexpected fixture output')
        (fixtures/name).write_bytes(base64.b64decode(raw))
    with urllib.request.urlopen(UNITY_URL,timeout=30) as stream:raw=stream.read(65537)
    if hashlib.sha256(raw).hexdigest()!=UNITY_SHA256:raise ValueError('Unity fixture checksum mismatch')
    (fixtures/'small.bundle').write_bytes(raw)
    (fixtures/'invalid.pak').write_bytes(b'not a pak')
    policy=current(ROOT).value
    policy['locations'].append({'id':'engine_fixture','name':'Engine inspection fixtures','path':str(fixtures),
                               'enabled':True,'read':True,'write':False,'execute':False,'operations':[],'exclusions':[]})
    observations=[]

    def call(scope,fmt,action,path,*,expected='engine_archive_completed',**options):
        done=exchange(ROOT,grants={'inventory_root':str(scope)},name='inspect_engine_archive',
                      arguments={'format':fmt,'action':action,'relative_path':path,**options},timeout=120)
        result=done.get('structuredContent',{}).get('tool_result',{})
        if result.get('status')!=expected or bool(done.get('isError'))!=(expected=='engine_archive_failed'):
            raise AssertionError(json.dumps(result))
        observations.append(result)
        return result

    with using(Policy(policy)):
        r=call(fixtures,'pak','info','fixture.pak',limit=2)
        assert r['scan_complete'] and r['page_truncated'] and r['next_offset']==2
        r=call(fixtures,'pak','info','fixture.pak',offset=2,limit=2)
        assert r['offset']==2 and r['lines'][0].startswith('version major:')
        r=call(fixtures,'pak','list','fixture.pak',contains='README')
        assert r['lines']==['readme.txt']
        r=call(fixtures,'iostore','info','fixture.utoc')
        assert any('PerfectHashWithOverflow' in line for line in r['lines'])
        r=call(fixtures,'iostore','list','fixture.utoc')
        assert any('Fixture/data.bin' in line for line in r['lines'])
        for action,needle in [('list','CAB-'),('header','22'),('metadata','6000.0.65f1'),('objects','MonoBehaviour')]:
            r=call(fixtures,'unity',action,'small.bundle')
            assert r['scan_complete'] and any(needle in line for line in r['lines'])
        call(fixtures,'pak','info','invalid.pak',expected='engine_archive_failed')
    if ark_folder:
        ark=Path(ark_folder).resolve(strict=True)
        with using(current(ROOT)):
            call(ark,'iostore','info','ShooterGame/Content/Paks/global.utoc')
            call(ark,'iostore','list','ShooterGame/Content/Paks/pakchunk0optional-Windows.utoc',contains='Ocean',limit=3)
            r=call(ark,'pak','info','ShooterGame/Content/Paks/pakchunk0optional-Windows.pak',expected='engine_archive_failed')
            assert r['compatibility']['detected_pak_version']==12
    report={'status':'passed','image':image,'game_execution':False,'fixture_origin':{'unity_url':UNITY_URL,'unity_sha256':UNITY_SHA256},
            'operations':observations,'evidence':str(folder/'report.json')}
    (folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return {k:v for k,v in report.items() if k!='operations'}|{'operations_verified':len(observations)}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--ark-folder')
    print(json.dumps(smoke(parser.parse_args().ark_folder),indent=2))
