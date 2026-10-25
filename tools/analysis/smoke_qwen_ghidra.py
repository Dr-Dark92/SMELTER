"""Live Qwen/OpenCode/MCP acceptance using an existing generated-binary smoke.

No production chat, access policy, model setting or game file is changed.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time

REPO=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(REPO/'tools/dashboard'))


def smoke(native_evidence, model='qwen3.5:35b-a3b'):
    native_evidence=Path(native_evidence).resolve()
    previous=json.loads(native_evidence.read_text(encoding='utf-8'))
    if previous.get('status')!='PASS' or previous.get('target_executed') is not False:
        raise ValueError('Use the PASS evidence from smoke_ghidra.py')
    output=native_evidence.parent
    report_path=output/'live-qwen-evidence.json'
    if report_path.exists():raise ValueError('Live evidence already exists; use a fresh native fixture')
    root=output/'checkout'
    from frontend_workspace import _source_files
    for relative,source in _source_files(REPO).items():
        target=root/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(source.read_bytes())
    from sandbox import config
    from config_store import save_config
    images=config(REPO)
    if not images.get('opencode_image'):raise ValueError('Configure the production OpenCode image first')
    save_config(root,'sandbox.json',images)
    save_config(root,'model_preferences.json',{'schema_version':1,'models':{'reasoning':model}})
    settings={'context_tokens':16384,'max_output_tokens':1024,'timeout_seconds':300,
              'opencode_timeout_seconds':900,'thinking':False}
    save_config(root,'runtime_settings.json',{'schema_version':1,'settings':settings})
    from chats import create_chat
    from access_policy import current
    from chat_jobs import Control
    from task_contract import configuration
    from opencode_runtime import ask
    import opencode_pool
    cid=create_chat(root,'Generated ELF: live Qwen/Ghidra acceptance')['id']
    control=Control();control.configuration=configuration(root);control.access_policy=current(root)
    analysis=previous['results']['rea_ghidra_analyze']['analysis_id']
    prompt=('Inspect the existing generated fixture analysis '+analysis+'. '
            'Call rea_ghidra_functions with that analysis_id and query smelter_add, '
            'then call rea_ghidra_decompile with its returned address. '
            'Explain what that function computes, citing its address. Use those two real tools. '
            'Do not inspect source files or call rea_capabilities; the known fixture is already analyzed.')
    started=time.monotonic()
    try:
        result=ask(root,cid,prompt,model_key='local/'+model,approval=True,agent_mode=True,control=control,
                   tool_permissions={'rea_analysis':True,'rea_root':str(output/'fixtures')})
        from chats import read_chat
        messages=read_chat(root,cid)['messages']
        assistant=next(m for m in reversed(messages) if m['role']=='assistant')
        execution=assistant.get('execution') or {}
        events=(execution.get('events') or [])
        receipts=[e for e in events if e.get('source')=='controller']
        names={e.get('tool') for e in receipts if (e.get('result') or {}).get('status')=='rea_completed'}
        success={'rea_ghidra_functions','rea_ghidra_decompile'}<=names and result.get('status')=='completed'
        report={'status':'PASS' if success else 'FAIL','model':model,'elapsed_seconds':round(time.monotonic()-started,2),
                'configuration':control.configuration,'result':result,'controller_tools':sorted(names),
                'target_executed':False,'production_state_changed':False,'native_evidence':str(native_evidence)}
        report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
        if not success:raise ValueError('Live task did not confirm both required Ghidra receipts; inspect '+str(report_path))
        print(json.dumps({'status':'PASS','model':model,'elapsed_seconds':report['elapsed_seconds'],'evidence':str(report_path)}))
    finally:opencode_pool.stop(force=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-evidence',required=True,type=Path)
    parser.add_argument('--model',default='qwen3.5:35b-a3b')
    args=parser.parse_args()
    smoke(args.native_evidence,args.model)
