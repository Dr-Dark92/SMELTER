"""Register the local scoped OpenCode recovery plugin; no downloads or inference."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/dashboard'))


def configure(root=ROOT,config=None,apply=False):
    from python_tools import _plain_path
    root=_plain_path(Path(root).resolve())
    config=_plain_path(Path(config) if config else Path.home()/'.config/opencode/opencode.json')
    raw=config.read_bytes();value=json.loads(raw.decode('utf-8-sig'))
    if value.get('mcp',{}).get('smelter',{}).get('type')!='local':
        raise ValueError('Existing local SMELTER MCP registration required')
    plugin=_plain_path(root/'tools/dashboard/native_recovery_plugin.mjs')
    if not plugin.is_file():raise ValueError('Local recovery plugin source missing')
    plugins=value.setdefault('plugin',[])
    if not isinstance(plugins,list):raise ValueError('Existing plugin configuration must be a list')
    entry=[plugin.as_uri(),{'root':str(root)}]
    matched=[p for p in plugins if p==entry or p==entry[0] or isinstance(p,list) and p and p[0]==entry[0]]
    if matched and matched!=[entry]:raise ValueError('Existing recovery plugin options differ; preserved for review')
    if not matched:plugins.append(entry)
    provider=value.get('provider',{}).get('ollama')
    timeouts={}
    if isinstance(provider,dict):
        options=provider.setdefault('options',{})
        if not isinstance(options,dict):raise ValueError('Ollama options must be an object')
        # Keep explicit existing choices. Defaults bound inference, not tools;
        # OpenCode owns provider retries and cancellation in the existing turn.
        for name,limit in {'timeout':900000,'headerTimeout':300000,'chunkTimeout':180000}.items():
            options.setdefault(name,limit);timeouts[name]=options[name]
    changed=json.loads(raw.decode('utf-8-sig'))!=value
    result={'mode':'apply' if apply else 'preview','changed':changed,'config':str(config),'plugin':entry,
            'dependencies':[],'downloads':False,'backup':None,'activation':'Next OpenCode process startup; current tasks are not restarted',
            'scope':'Hooks guard only enabled exact session/directory binding; Ollama defaults bound provider requests. No automatic approvals or new model turns',
            'ollama_request_timeouts_ms':timeouts}
    if apply and changed:
        if config.read_bytes()!=raw:raise ValueError('OpenCode configuration changed during preview')
        backup=_plain_path(config.with_name(config.name+'.bak-smelter-recovery-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')))
        with backup.open('xb') as stream:stream.write(raw)
        pending=_plain_path(config.with_name(config.name+'.smelter-recovery.pending'))
        with pending.open('xb') as stream:stream.write((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
        pending.replace(config);result['backup']=str(backup)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--config',type=Path);parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();print(json.dumps(configure(args.root,args.config,args.apply),indent=2))
