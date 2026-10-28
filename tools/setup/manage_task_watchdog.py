"""Install/start the scoped watchdog; status never prints prompts or credentials."""
import argparse
from contextlib import closing
from datetime import datetime,timezone
import json
import hashlib
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
from urllib.request import Request,urlopen
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/dashboard'))


def install(root=ROOT,config_path=None):
    from python_tools import _plain_path
    from watchdog_store import configure
    root=_plain_path(Path(root).resolve());path=_plain_path(Path(config_path) if config_path else Path.home()/'.config/opencode/opencode.json')
    raw=path.read_bytes();value=json.loads(raw.decode('utf-8-sig'))
    if value.get('mcp',{}).get('smelter',{}).get('type')!='local':raise ValueError('Existing local SMELTER registration required')
    source=_plain_path(root/'tools/dashboard/watchdog_capture_plugin.mjs')
    if not source.is_file():raise ValueError('Watchdog capture source unavailable')
    raw_plugin=source.read_bytes()
    if len(raw_plugin)>65536:raise ValueError('Watchdog plugin exceeds 64 KiB')
    cache=_plain_path(root/'.smelter/watchdog/plugins');cache.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(raw_plugin).hexdigest()
    installed=_plain_path(cache/('watchdog_capture_'+digest[:20]+'.mjs'))
    if not installed.exists():
        if len(list(cache.glob('watchdog_capture_*.mjs')))>=16:raise ValueError('Watchdog plugin revision capacity reached')
        with installed.open('xb') as out:out.write(raw_plugin)
    elif installed.read_bytes()!=raw_plugin:raise ValueError('Installed watchdog plugin bytes changed')
    plugins=value.setdefault('plugin',[])
    if not isinstance(plugins,list):raise ValueError('Expected a plugin list')
    options={'root':str(root),'python':str(Path(sys.executable).resolve())}
    entry=[installed.as_uri(),options]
    def ours(item):
        name=item[0] if isinstance(item,list) and item else item
        return isinstance(name,str) and (name==source.as_uri() or name.startswith(cache.as_uri()+'/watchdog_capture_'))
    old=[p for p in plugins if ours(p)]
    if len(old)>1 or old and (not isinstance(old[0],list) or len(old[0])!=2 or old[0][1]!=options):raise ValueError('Existing watchdog plugin configuration differs')
    if old:plugins[plugins.index(old[0])]=entry
    else:plugins.append(entry)
    changed=json.loads(raw.decode('utf-8-sig'))!=value;backup=None
    if changed:
        if path.read_bytes()!=raw:raise ValueError('OpenCode configuration changed concurrently')
        backup=_plain_path(path.with_name(path.name+'.bak-watchdog-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')))
        with backup.open('xb') as out:out.write(raw)
        pending=_plain_path(path.with_name(path.name+'.watchdog.pending'))
        with pending.open('xb') as out:out.write((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
        pending.replace(path)
    configure(root,True)
    return {'installed':True,'config_changed':changed,'backup':str(backup) if backup else None,'max_retries':3,'capture_sha256':digest,'new_dependencies':[]}


def runtime(root):
    from watchdog_store import folder,process_running
    from python_tools import _plain_path
    from job_store import alive,identity
    path=_plain_path(folder(root)/'runtime.json')
    if not path.is_file() or path.stat().st_size>4096:return None
    value=json.loads(path.read_text(encoding='utf-8'))
    if value.get('source_root')!=str(Path(root).resolve()) or not process_running(value.get('pid',0),value.get('owner_identity')):return None
    return value


def start(root=ROOT):
    from watchdog_store import folder,config
    if not config(root).get('enabled'):raise ValueError('Watchdog disabled; enable it before starting')
    current=runtime(root)
    if current:return {'running':True,'pid':current['pid'],'reused':True}
    log=folder(root)/'daemon.log'
    with log.open('ab') as out:
        child=subprocess.Popen([sys.executable,str(Path(root)/'tools/dashboard/task_watchdog.py'),'--root',str(Path(root).resolve())],
            cwd=str(root),stdin=subprocess.DEVNULL,stdout=out,stderr=out,env={**os.environ,'PYTHONUTF8':'1'},
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,start_new_session=os.name!='nt')
    for _ in range(25):
        current=runtime(root)
        if current and current['pid']==child.pid:return {'running':True,'pid':child.pid,'reused':False}
        if child.poll() is not None:raise ValueError('Watchdog exited during startup; inspect its private daemon log')
        time.sleep(.2)
    raise ValueError('Watchdog startup not confirmed')


def candidates(root):
    from watchdog_store import binding
    from task_trace import LocalInspector
    from native_progress import same_directory
    b=binding(root)['binding'];inspector=LocalInspector();found=[]
    for port in inspector.ports_now():
        try:
            owner=inspector.get(port,'/session/'+b['session_id'],b['directory'])
            if owner.get('id')==b['session_id'] and same_directory(owner.get('directory',''),b['directory']):found.append(port)
        except (OSError,ValueError):continue
    if len(found)!=1:raise ValueError('Exact single originating ACP listener required')
    return b,found[0]


def activate(root=ROOT):
    """Dispose only an idle bound instance so it loads the newly registered plugin."""
    b,port=candidates(root)
    from urllib.request import build_opener,ProxyHandler
    from native_progress import NoRedirect
    opener=build_opener(ProxyHandler({}),NoRedirect())
    def call(route,body=None):
        url='http://127.0.0.1:'+str(port)+route+'?'+urlencode({'directory':b['directory']})
        req=Request(url,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='GET' if body is None else 'POST')
        with opener.open(req,timeout=15) as reply:raw=reply.read(10*1024*1024)
        return json.loads(raw) if raw.strip() else None
    if any(s.get('type')!='idle' for s in call('/session/status').values()) or call('/permission') or call('/question'):
        return {'activated':False,'reason':'native_work_or_human_wait_active','next':'next native instance startup'}
    paths=call('/doc').get('paths',{})
    if '/instance/dispose' not in paths or 'post' not in paths['/instance/dispose']:raise ValueError('Supported instance reload route unavailable')
    call('/instance/dispose',{})
    # Read-only initialization; neither creates a session nor submits a prompt.
    call('/agent');call('/mcp')
    return {'activated':True,'port':port,'conversation_preserved':True,'inference_submitted':False}


def adopt(root=ROOT,*,resume_legacy=False):
    """Explicit operator capture of only the current bound human prompt."""
    from watchdog_store import binding,Store
    from watchdog_native import Native
    b,port=candidates(root)
    command="$p=@(Get-NetTCPConnection -State Listen | Where-Object {$_.LocalAddress -eq '127.0.0.1' -and $_.LocalPort -eq "+str(port)+"} | Select-Object -ExpandProperty OwningProcess -Unique); $p | ConvertTo-Json -Compress"
    done=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],capture_output=True,text=True,timeout=6,creationflags=subprocess.CREATE_NO_WINDOW)
    pid=json.loads(done.stdout)
    if type(pid) is not int:raise ValueError('Originating ACP process is ambiguous')
    native=Native(root)
    with closing(sqlite3.connect(native.path.resolve().as_uri()+'?mode=ro',uri=True,timeout=1)) as db:
        db.execute('PRAGMA query_only=ON')
        row=db.execute("""SELECT id,time_created,json_extract(data,'$.model.providerID'),json_extract(data,'$.model.modelID'),json_extract(data,'$.agent'),json_extract(data,'$.variant'),
            json_extract(data,'$.tools'),json_extract(data,'$.system'),json_extract(data,'$.format')
            FROM message m WHERE session_id=? AND json_extract(data,'$.role')='user'
            AND EXISTS(SELECT 1 FROM part p WHERE p.message_id=m.id AND json_extract(p.data,'$.type')='text' AND coalesce(json_extract(p.data,'$.synthetic'),0)=0)
            ORDER BY time_created DESC,id DESC LIMIT 1""",(b['session_id'],)).fetchone()
        if not row or row[0].startswith('msg_smelter_wd_'):raise ValueError('No new current human prompt to adopt')
        parts=db.execute("SELECT json_extract(data,'$.text'),json_extract(data,'$.type'),coalesce(json_extract(data,'$.synthetic'),0) FROM part WHERE session_id=? AND message_id=? ORDER BY id",(b['session_id'],row[0])).fetchall()
    text='\n'.join(p[0] for p in parts if p[1]=='text' and not p[2] and isinstance(p[0],str))
    options={}
    if row[6] is not None:options['tools']=json.loads(row[6])
    if row[7] is not None:options['system']=row[7]
    if row[8] is not None:options['format']=json.loads(row[8])
    store=Store(root)
    if resume_legacy:
        old=store.current()
        if not old or old['origin_id']!=row[0]:raise ValueError('Current human prompt differs from the legacy watch')
        observed=native.snapshot(old,store.attempts(old['id']))
        if (not observed.get('available') or observed.get('cancelled') or observed.get('superseded')
                or observed.get('endings') or observed.get('native_phase')!='idle' or observed.get('active_tools')
                or observed.get('pending_access') or observed.get('pending_question')):
            raise ValueError('Cannot rearm an explicitly finished, cancelled, replaced, active or waiting task')
    result=store.capture({'session_id':b['session_id'],'directory':b['directory'],'message_id':row[0],
        'created_ms':row[1],'text':text,'model':{'providerID':row[2],'modelID':row[3]},'agent':row[4],'variant':row[5],'request_options':options,
        'server_port':port,'native_pid':pid,'has_attachments':any(p[1]=='file' for p in parts)},binding(root),rearm_legacy_red=resume_legacy)
    return result


def resume(root=ROOT):
    """Operator migration only: old automatic RED, never an explicit end/Stop."""
    return adopt(root,resume_legacy=True)


def status(root=ROOT):
    from watchdog_store import Store,config
    value=runtime(root)
    return {'enabled':config(root).get('enabled'),'running':bool(value),'pid':value.get('pid') if value else None,'task':Store(root).public()}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('action',choices=['install','start','status','disable','activate','adopt','resume'])
    parser.add_argument('--root',type=Path,default=ROOT);args=parser.parse_args()
    if args.action=='disable':
        from watchdog_store import configure
        result=configure(args.root,False)
    else:result=globals()[args.action](args.root)
    print(json.dumps(result,indent=2))
