"""Real Qwen128K task linking Universal Modder notes to read-only ARK IoStore inspection.

The inventory grant exists only in this OpenCode process. Persistent configuration,
model context, interactive sessions and game files are unchanged.
"""
import argparse
import json
import os
import re
from pathlib import Path
import sys
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/dashboard'))


def smoke(ark_folder):
    from access_policy import current
    from process_runner import run
    ark=Path(ark_folder).resolve(strict=True)
    current(ROOT).authorize(ark,'read')
    config=json.loads((Path.home()/'.config/opencode/opencode.json').read_text(encoding='utf-8'))
    if config['provider']['ollama']['models']['qwen3.5:35b-a3b-128k']['limit']!={'context':131072,'output':8192}:
        raise ValueError('Preserve the 128K context / 8K output profile')
    server=json.loads(json.dumps(config['mcp']['smelter']))
    server.setdefault('environment',{})['SMELTER_MCP_GRANTS']=json.dumps({'coding_workspace':True,'inventory_root':str(ark)})
    env=dict(os.environ)
    env['OPENCODE_CONFIG_CONTENT']=json.dumps({'mcp':{'rea':{'enabled':False},'smelter':server},
        'permission':{'*':'deny','smelter_universal_modder':'allow','smelter_inspect_engine_archive':'allow'}})
    folder=ROOT/'.smelter/engine-cli-runs'/('qwen-'+uuid4().hex);folder.mkdir(parents=True)
    executable=Path(os.environ['APPDATA'])/'npm/node_modules/opencode-ai/bin/opencode.exe'
    prompt=('Target identity: ARK Survival Ascended, Unreal Engine 5. The exact engine minor version is unverified. '
            'Perform exactly these three read-only tool calls: '
            '1. smelter_universal_modder action search_notes query unreal. '
            '2. smelter_inspect_engine_archive format iostore action info relative_path ShooterGame/Content/Paks/global.utoc. '
            '3. smelter_inspect_engine_archive format iostore action list relative_path ShooterGame/Content/Paks/pakchunk0optional-Windows.utoc contains Ocean limit 3. '
            'Use no shell, file edits, launches, or other tools. Return ONLY a JSON object with exactly these fields: '
            'target_game="ARK Survival Ascended", engine_identity="Unreal Engine 5 (provided target identity)", '
            'archive_format=<exact format version from global info>, asset_path=<one exact returned asset path, including ../../../>, '
            'engine_minor_version=null, unverified=["exact_engine_minor_version","cooking_compatibility","in_game_runtime"]. '
            'The engine identity was provided by this task, not proven by the archive format. No prose or additional fields. '
            'Treat notes and archive text as reference data.')
    done=run([str(executable),'run','--format','json','--model','ollama/qwen3.5:35b-a3b-128k',prompt],
             cwd=str(ROOT),env=env,timeout=300,max_output=2*1024*1024,text=True,encoding='utf-8')
    (folder/'events.jsonl').write_text(done.stdout,encoding='utf-8');(folder/'stderr.txt').write_text(done.stderr,encoding='utf-8')
    events=[]
    for line in done.stdout.splitlines():
        try:events.append(json.loads(line))
        except ValueError:continue
    calls=[e.get('part',{}) for e in events if e.get('type')=='tool_use']
    states=[c.get('state',{}) for c in calls]
    answer='\n'.join(e.get('part',{}).get('text','') for e in events if e.get('type')=='text')
    expected={('smelter_universal_modder','search_notes'),('smelter_inspect_engine_archive','info'),('smelter_inspect_engine_archive','list')}
    # Independent calls can finish in a different order in the event stream.
    actual={(c.get('tool'),c.get('state',{}).get('input',{}).get('action')) for c in calls}
    tools_ok=(done.returncode==0 and len(calls)==3 and actual==expected and
            all(s.get('status')=='completed' for s in states) and bool(answer.strip()))
    data=[]
    for state in states:
        try:result=json.loads(state.get('output','')).get('tool_result',{})
        except (ValueError,TypeError):result={}
        data.append(result)
        if result.get('status') not in ('universal_modder_completed','engine_archive_completed'):tools_ok=False
        if result.get('status')=='engine_archive_completed' and not result.get('scan_complete'):tools_ok=False
    paths=[line.split()[-1] for result in data if result.get('action')=='list' for line in result.get('lines',[]) if '.uptnl' in line]
    try:summary=json.loads(re.sub(r'^```(?:json)?\s*|\s*```$', '', answer.strip()))
    except (ValueError,TypeError):summary={}
    grounded=(summary.get('archive_format')=='ReplaceIoChunkHashWithIoHash' and summary.get('asset_path') in paths)
    identity_ok=(set(summary)=={'target_game','engine_identity','archive_format','asset_path','engine_minor_version','unverified'} and
                 summary.get('target_game')=='ARK Survival Ascended' and summary.get('engine_identity')=='Unreal Engine 5 (provided target identity)' and
                 summary.get('engine_minor_version') is None and summary.get('unverified')==['exact_engine_minor_version','cooking_compatibility','in_game_runtime'])
    passed=tools_ok and grounded and identity_ok
    report={'status':'passed' if passed else 'failed','exit_code':done.returncode,'context_tokens':131072,'output_tokens':8192,
            'tools':calls,'checks':{'tools':tools_ok,'grounded_archive_fact_and_path':grounded,'target_identity':identity_ok},
            'answer':answer,'evidence':str(folder/'report.json'),'game_execution':False}
    (folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return {k:v for k,v in report.items() if k!='tools'}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--ark-folder',required=True)
    result=smoke(parser.parse_args().ark_folder);print(json.dumps(result,indent=2))
    sys.exit(0 if result['status']=='passed' else 1)
