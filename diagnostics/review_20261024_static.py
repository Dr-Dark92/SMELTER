"""Inventory and syntax/link checks; never imports project programs."""
import ast
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
paths = subprocess.check_output(['git','ls-files'], cwd=ROOT, text=True).splitlines()
report = {'tracked_files':len(paths), 'python':{'checked':0,'errors':[]},
          'javascript':{'checked':0,'errors':[]}, 'markdown':{'checked':0,'missing_local_targets':[]}}
for relative in paths:
    path = ROOT/relative
    if path.suffix == '.py':
        report['python']['checked'] += 1
        try: ast.parse(path.read_text(encoding='utf-8-sig'), filename=relative)
        except (SyntaxError, UnicodeError) as error:
            report['python']['errors'].append({'file':relative,'error':str(error)})
    elif path.suffix in ('.js','.mjs','.cjs'):
        report['javascript']['checked'] += 1
        result = subprocess.run(['node','--check',str(path)], capture_output=True, text=True)
        if result.returncode:
            report['javascript']['errors'].append({'file':relative,'error':result.stderr[:2000]})
    elif path.suffix == '.md':
        report['markdown']['checked'] += 1
        for target in re.findall(r'\]\(([^)\s]+)(?:\s+"[^"]*")?\)',path.read_text(encoding='utf-8-sig')):
            if target.startswith(('#','/','http:','https:','mailto:','app:','plugin:','codex:')): continue
            target=unquote(target.split('#')[0].strip('<>'))
            if not target or ':' in target: continue
            if not (path.parent/target).exists():
                report['markdown']['missing_local_targets'].append({'file':relative,'target':target})
print(json.dumps(report,indent=2))
