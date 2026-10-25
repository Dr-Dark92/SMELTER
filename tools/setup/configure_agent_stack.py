"""Preview/apply explicit Qwen35B and fixed REA/Ghidra settings for a checkout.

Stop the dashboard first. No downloads, target-folder grants, credentials or
model inference. Existing location rows are preserved, including denials.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/dashboard'))
MODEL='qwen3.5:35b-a3b'
RUNTIME={'context_tokens':16384,'max_output_tokens':2048,'timeout_seconds':300,
         'opencode_timeout_seconds':1800,'thinking':True}


def configure(root=ROOT, *, apply=False):
    from access_policy import current, save
    from config_store import load_config, save_config
    from ghidra_connection import status
    from job_store import active
    from python_tools import _plain_path
    root=_plain_path(Path(root).resolve())
    if active(root):raise ValueError('Finish active tasks before changing the agent stack')
    original=current(root)
    policy=json.loads(json.dumps(original.value))
    provider=status(root)
    if provider['status']!='installed':raise ValueError('Install Ghidra before configuring the native tool stack')
    paths=[('ghidra_runtime','Ghidra fixed analysis runtime',Path(provider['home'])),
           ('rea_runtime','REA fixed analysis runtime',root/'.smelter/tooling/rea')]
    notes=[]
    for identity,label,path in paths:
        path=_plain_path(path).resolve()
        if not path.is_dir():raise ValueError('Install the runtime first: '+label)
        existing=next((row for row in policy['locations'] if Path(row['path']).resolve()==path),None)
        if existing:
            notes.append('Preserved existing location policy for '+label)
            continue
        if any(row['id']==identity for row in policy['locations']):raise ValueError('Existing location ID conflicts with '+identity)
        policy['locations'].append({'id':identity,'name':label,'path':str(path),'read':False,'write':False,
                                    'execute':True,'operations':['rea'],'exclusions':[],'enabled':True})
    models=load_config(root,'model_preferences.json')
    models={'schema_version':1,'models':{**models['models'],'reasoning':MODEL}}
    report={'mode':'apply' if apply else 'preview','model_preferences':models,'runtime':RUNTIME,
            'engine_execution_locations':[str(path) for _,_,path in paths],
            'target_folder_permissions_changed':False,'notes':notes}
    if apply:
        save(root,policy,original.revision)
        save_config(root,'model_preferences.json',models)
        save_config(root,'runtime_settings.json',{'schema_version':1,'settings':RUNTIME})
        save_config(root,'component_controls.json',{'schema_version':1,'opencode':True,'mcp':True})
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    print(json.dumps(configure(args.root,apply=args.apply),indent=2))
