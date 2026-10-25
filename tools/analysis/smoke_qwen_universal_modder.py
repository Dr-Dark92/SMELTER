"""One real native Qwen/Universal Modder task with only the read-only UM tool allowed.

Uses a per-process OpenCode configuration overlay; never rewrites native config.
Context stays 128K. No shell, edits, game control, external REA startup or paid APIs.
"""
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/dashboard'))


def smoke():
    from process_runner import run
    config = json.loads((Path.home() / '.config/opencode/opencode.json').read_text(encoding='utf-8'))
    limit = config['provider']['ollama']['models']['qwen3.5:35b-a3b-128k']['limit']
    if limit != {'context':131072,'output':8192}:
        raise ValueError('Native Qwen profile must retain 128K context / 8K output')
    executable = Path(os.environ.get('APPDATA', '')) / 'npm/node_modules/opencode-ai/bin/opencode.exe'
    if not executable.is_file():
        raise ValueError('Expected installed native OpenCode executable was not found')
    folder = ROOT / '.smelter/universal-modder-runs' / ('qwen-' + uuid4().hex)
    folder.mkdir(parents=True)
    environment = dict(os.environ)
    environment['OPENCODE_CONFIG_CONTENT'] = json.dumps({
        'mcp':{'rea':{'enabled':False}},
        'permission':{'*':'deny','smelter_universal_modder':'allow'}})
    prompt = ('Use smelter_universal_modder with action search_notes and query grand theft auto. '
              'Then call the SAME tool with action read_note and the exact GTA passthrough note path returned, limit 3000. '
              'Only this tool is authorized for this test. Do not use shell, file reads/edits or other tools. '
              'Finally give one short paragraph naming the returned note and explaining one way its architecture '
              'can inform a GTA-to-ARK camera-link prototype. Treat it as reference evidence; do not claim '
              'that the note proves compatibility with the installed games. Perform both tool calls now.')
    done = run([str(executable),'run','--format','json','--model','ollama/qwen3.5:35b-a3b-128k',prompt],
               cwd=str(ROOT), env=environment, timeout=300, max_output=2*1024*1024, text=True,encoding='utf-8')
    (folder / 'events.jsonl').write_text(done.stdout,encoding='utf-8')
    (folder / 'stderr.txt').write_text(done.stderr,encoding='utf-8')
    events=[]
    for line in done.stdout.splitlines():
        try:events.append(json.loads(line))
        except ValueError:continue
    tools=[e.get('part',{}) for e in events if e.get('type')=='tool_use']
    calls=[{'tool':p.get('tool'),'state':p.get('state',{})} for p in tools]
    text='\n'.join(e.get('part',{}).get('text','') for e in events if e.get('type')=='text')
    successful=[c for c in calls if c['tool']=='smelter_universal_modder' and c['state'].get('status')=='completed']
    actions={c['state'].get('input',{}).get('action') for c in successful}
    passed=done.returncode==0 and {'search_notes','read_note'}<=actions and bool(text.strip()) and all(c['tool']=='smelter_universal_modder' for c in calls)
    report={'status':'passed' if passed else 'failed','exit_code':done.returncode,'context_tokens':131072,
            'output_tokens':8192,'tools':calls,'answer':text,'evidence':str(folder),'game_execution':False}
    (folder / 'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report


if __name__ == '__main__':
    result=smoke()
    print(json.dumps({k:v for k,v in result.items() if k!='tools'},indent=2))
    raise SystemExit(0 if result['status']=='passed' else 1)
