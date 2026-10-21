"""Fail-closed Docker execution for tests and preview. Never pull images.

Only immutable, operator-selected image IDs are accepted. Containers receive a
read-only code snapshot, tmpfs scratch, no network, no host credentials/socket,
a non-root user, dropped capabilities and bounded CPU/memory/process/log limits.
"""
import subprocess
import json
import os
import re
import secrets
import shutil
import time
from pathlib import Path
from uuid import uuid4
from process_runner import run

NAME='sandbox.json'
DEFAULT={'schema_version':1,'python_image':None,'node_image':None,'opencode_image':None}


def validate(value):
    if not isinstance(value,dict) or set(value)!=set(DEFAULT) or type(value['schema_version']) is not int or value['schema_version']!=1:
        raise ValueError('Sandbox configuration requires schema_version, python_image and node_image')
    for key in ('python_image','node_image','opencode_image'):
        if value[key] is not None and (not isinstance(value[key],str) or not re.fullmatch(r'sha256:[a-f0-9]{64}',value[key])):
            raise ValueError('Select a locally installed immutable sha256 image ID; image tags/commands are not accepted')
    return value


def config(root):
    from database import chosen_database
    if chosen_database(Path(root)) is None:return dict(DEFAULT)
    from config_store import load_config
    return load_config(root,NAME)


def status(root,operation="frontend"):
    value=config(root);docker=shutil.which('docker')
    result={'configured':value,'ready':False,'docker':docker,'boundary':'Docker Linux containers; read-only snapshot, no network, no credentials, non-root; not a guarantee against container escape',
            'host_fallback':False,'opencode':'managed no-network container adapter; requires an explicit OpenCode image ID',
            'external_mcp':'blocked: no confined external server adapter'}
    try:
        if not docker:raise ValueError('Docker is not installed; execution is blocked')
        if os.environ.get('DOCKER_HOST') and not os.environ['DOCKER_HOST'].startswith(('unix://','npipe://')):
            raise ValueError('Remote Docker hosts are not supported')
        context=run([docker,'context','inspect','--format','{{.Endpoints.docker.Host}}'],timeout=5,text=True,check=True).stdout.strip()
        if not context.startswith(('unix://','npipe://')):raise ValueError('Only a local Docker daemon is supported')
        info=json.loads(run([docker,'info','--format','{{json .}}'],timeout=5,text=True,check=True).stdout)
        if info.get('OSType')!='linux':raise ValueError('Docker must use Linux containers')
        if int(str(info.get('ServerVersion','0')).split('.')[0])<28:raise ValueError('Docker Engine 28 or newer is required')
        for capability in ('MemoryLimit','SwapLimit','CpuCfsQuota','PidsLimit'):
            if info.get(capability) is not True:raise ValueError('Docker cannot enforce required resource limit: '+capability)
        if not any('seccomp' in option for option in info.get('SecurityOptions',[])):
            raise ValueError('Docker default seccomp support is required')
        required={'opencode':('opencode_image',), 'coding_python':('python_image',),
                  'coding_node':('node_image',)}.get(operation, ('python_image','node_image'))
        for key in required:
            image=value[key]
            if not image:raise ValueError('Configure the required immutable image IDs in Settings')
            actual=run([docker,'image','inspect','--format','{{.Id}}',image],timeout=5,text=True,check=True).stdout.strip()
            if actual!=image:raise ValueError('Configured image is not locally installed: '+key)
        result['ready']=True;result['reason']='Local engine and immutable images verified; no model or container task started'
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        # Status is observational; execution rechecks and fails closed.
        result['reason']=str(exc)[:500]
    return result


def _flags(docker,name,snapshot):
    # Values are fixed by trusted code, not skill text or model arguments.
    if any(c in str(snapshot) for c in (',','\n','\r','\x00')):raise ValueError('Unsupported sandbox mount path')
    return [docker,'run','--pull','never','--name',name,'--label','smelter.owner='+name,
            '--read-only','--network','none','--user','65534:65534','--cap-drop','ALL',
            '--security-opt','no-new-privileges=true','--pids-limit','128',
            '--memory','768m','--memory-swap','768m','--cpus','2',
            '--log-driver','local','--log-opt','max-size=1m','--log-opt','max-file=2',
            '--mount','type=bind,source='+str(snapshot)+',target=/workspace,readonly',
            '--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=256m,mode=1777',
            '--tmpfs','/run:rw,noexec,nosuid,nodev,size=128m,mode=1777',
            '--tmpfs','/home/app:rw,noexec,nosuid,nodev,size=32m,mode=0700,uid=65534,gid=65534',
            '--tmpfs','/workspace/.smelter:rw,noexec,nosuid,nodev,size=128m,mode=0700,uid=65534,gid=65534',
            '--env','HOME=/home/app','--env','PYTHONDONTWRITEBYTECODE=1',
            '--env','SMELTER_SANDBOX=1','--workdir','/workspace']


def snapshot(root,target):
    from python_tools import _plain_path
    from frontend_workspace import _source_files, MAX_COPY
    base=_plain_path(Path(root)/'.smelter/sandbox-runs')
    files=_source_files(Path(target))
    from storage_budget import inventory
    staged=inventory(root,('sandbox-runs',))
    expected=sum(path.stat().st_size for path in files.values())
    if sum(row['bytes'] for row in staged)+expected>1024*1024*1024 or base.is_dir() and len(list(base.iterdir()))>=20:
        raise ValueError('Runtime snapshot budget reached; reconcile interrupted containers in Settings')
    if shutil.disk_usage(Path(root)).free<expected+64*1024*1024:raise ValueError('Insufficient space for isolated code snapshot')
    folder=_plain_path(base/str(uuid4()))
    folder.mkdir(parents=True);folder.chmod(0o755)
    code=folder/'code';code.mkdir(mode=0o755)
    size=0
    try:
        for relative,source in files.items():
            if source.name.startswith('.env') or source.name in ('.npmrc','.pypirc','credentials.json','secrets.json') or source.suffix.lower() in ('.pem','.pfx','.key'):
                continue
            raw=source.read_bytes();size+=len(raw)
            if size>MAX_COPY:raise ValueError('Sandbox code snapshot is too large')
            out=code/relative;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw);out.chmod(0o644)
        (code/'.smelter').mkdir()
        for directory in code.rglob('*'):
            if directory.is_dir():directory.chmod(0o755)
        # Optional viewer bundle is code, not ambient app state or credentials.
        viewer=Path(target)/'.smelter/tooling/model-viewer/node_modules/@google/model-viewer/dist/model-viewer.min.js'
        if viewer.is_file():
            _plain_path(viewer);raw=viewer.read_bytes()
            if len(raw)>8*1024*1024:raise ValueError('Viewer bundle is too large')
            (code/'viewer.min.js').write_bytes(raw)
        return folder,code
    except Exception:shutil.rmtree(folder);raise


def _remove(docker,name):
    """Only remove a container carrying this invocation's ownership label."""
    if not re.fullmatch(r'smelter-(?:tests|preview|opencode)-[a-f0-9]{32}',name):return False
    try:
        found=run([docker,'inspect','--format','{{json .Config.Labels}}',name],timeout=5,max_output=16384,text=True)
        if found.returncode:
            return 'No such' in (found.stderr or '')
        labels=json.loads(found.stdout)
        if not isinstance(labels,dict) or labels.get('smelter.owner')!=name:return False
        return run([docker,'rm','--force',name],timeout=10,max_output=16384).returncode==0
    except (ValueError,OSError,subprocess.SubprocessError):return False


def tests(root,target):
    ready=status(root)
    if not ready['ready']:raise ValueError('Confined tests unavailable: '+ready['reason'])
    folder,code=snapshot(root,target);checks=[]
    operations=[('python_image',['python','-m','unittest','discover','-s','tools/dashboard','-p','test_*.py']),
                ('node_image',['node','--test','tools/dashboard/test_chat_renderer.js','tools/dashboard/test_session_auth.js','tools/dashboard/test_file_activity.js','tools/dashboard/test_operations_ui.js'])]
    try:
        for index,(key,command) in enumerate(operations):
            name='smelter-tests-'+uuid4().hex
            try:
                record_owner(folder,name,ready['configured'][key],'tests')
                if key=='python_image':
                    guarded=['python','-c',"import os,sys,threading,runpy; t=threading.Timer(175,lambda:os._exit(124));t.daemon=True;t.start();sys.argv=['unittest','discover','-s','tools/dashboard','-p','test_*.py'];runpy.run_module('unittest',run_name='__main__')"]
                else:
                    guarded=['node','-e',"const p=require('node:child_process').spawn(process.execPath,['--test','tools/dashboard/test_chat_renderer.js','tools/dashboard/test_session_auth.js','tools/dashboard/test_file_activity.js','tools/dashboard/test_operations_ui.js'],{stdio:'inherit'});const t=setTimeout(()=>process.exit(124),175000);p.on('exit',code=>{clearTimeout(t);process.exit(code??1)});"]
                result=run(_flags(ready['docker'],name,code)+['--rm',ready['configured'][key],*guarded],timeout=180,max_output=2*1024*1024)
                log=result.stdout+result.stderr
                checks.append({'command':command,'exit_code':result.returncode,'output':log,'sandbox':'docker-no-network','image':ready['configured'][key]})
            finally:
                record_owner(folder,name,ready['configured'][key],'tests',finished=True)
                if not _remove(ready['docker'],name):raise ValueError('Owned test container cleanup was not confirmed: '+name)
        shutil.rmtree(folder)
        return checks
    except Exception:
        # Preserve ownership metadata when cleanup is unconfirmed.
        raise


CODING_PYTHON = r'''
import json,os,sys,threading,unittest
timer=threading.Timer(60,lambda:os._exit(124));timer.daemon=True;timer.start()
suite=unittest.defaultTestLoader.discover('tools/dashboard',pattern='test_*.py')
result=unittest.TextTestRunner(verbosity=2).run(suite)
print('SMELTER_TEST_RESULT|'+json.dumps({'tests':result.testsRun,'failures':len(result.failures),
 'errors':len(result.errors),'skipped':len(result.skipped)}),flush=True)
timer.cancel()
sys.exit(0 if result.wasSuccessful() and result.testsRun>len(result.skipped) else 1)
'''
CODING_NODE = r'''
const fs=require('node:fs'),cp=require('node:child_process'),os=require('node:os'),path=require('node:path');
const files=fs.readdirSync('tools/dashboard').filter(n=>/^test_[A-Za-z0-9_.-]+\.js$/.test(n)).sort();
if(!files.length||files.length>64)process.exit(2);
// A private reporter classifies actual test events. Finding ERR_ASSERTION in
// prose cannot turn a simultaneous missing import or runner failure into RED.
const reporter=path.join(os.tmpdir(),'smelter-reporter-'+require('node:crypto').randomUUID()+'.cjs');
fs.writeFileSync(reporter,`module.exports=async function* (source){
 let assertion_failures=0,errors=0;
 for await(const event of source){
  if(event.type!=='test:fail'||event.data.todo)continue;
  const error=event.data.details?.error;
  if(error?.failureType==='subtestsFailed')continue;
  if(error?.code==='ERR_ASSERTION'||error?.cause?.code==='ERR_ASSERTION')assertion_failures++;
  else errors++;
 }
 yield 'SMELTER_NODE_FAILURES|'+JSON.stringify({assertion_failures,errors})+'\\n';
};`,{flag:'wx'});
const child=cp.spawn(process.execPath,['--test','--test-reporter=tap','--test-reporter='+require('node:url').pathToFileURL(reporter).href,
 '--test-reporter-destination=stdout','--test-reporter-destination=stdout',
 ...files.map(n=>'tools/dashboard/'+n)],{stdio:'inherit'});
const timer=setTimeout(()=>process.exit(124),60000);
child.on('error',()=>process.exit(2));child.on('exit',code=>{clearTimeout(timer);fs.unlinkSync(reporter);process.exit(code??2)});
'''


def node_test_result(exit_code, output):
    counts={key:int(value) for key,value in re.findall(r'^# (tests|pass|fail|cancelled|skipped) (\d+)\s*$',output,re.M)}
    packets=re.findall(r'^SMELTER_NODE_FAILURES\|(\{[^\n]+\})\s*$',output,re.M)
    failures={}
    if len(packets)==1:
        try:failures=json.loads(packets[0])
        except ValueError:pass
    valid=set(failures)=={'assertion_failures','errors'} and all(type(n)is int and n>=0 for n in failures.values())
    if not valid or counts.get('cancelled',0) or failures['errors']:
        return 'ERROR',counts
    if exit_code==0 and counts.get('pass',0)>0 and counts.get('fail')==0 and failures['assertion_failures']==0:
        return 'GREEN',counts
    if exit_code==1 and counts.get('fail',0)>0 and failures['assertion_failures']>0:
        return 'RED',counts
    return 'ERROR',counts


def coding_test(root,target,profile):
    """One fixed test profile over a read-only snapshot; never a host command."""
    if profile not in ('python','node'):raise ValueError('Unsupported coding test profile')
    from access_policy import require
    require(target,'execute','tests')
    ready=status(root,operation='coding_'+profile)
    if not ready['ready']:raise ValueError('Confined coding tests unavailable: '+ready['reason'])
    folder,code=snapshot(root,target)
    name='smelter-tests-'+uuid4().hex
    image=ready['configured'][profile+'_image']
    command=['python','-I','-c',CODING_PYTHON] if profile=='python' else ['node','-e',CODING_NODE]
    confirmed=False
    try:
        record_owner(folder,name,image,'tests')
        result=run(_flags(ready['docker'],name,code)+['--rm',image,*command],
                   timeout=70,max_output=2*1024*1024)
        raw=result.stdout+result.stderr
        output=raw.decode('utf-8',errors='replace')
        counts={}
        if profile=='python':
            matches=re.findall(r'^SMELTER_TEST_RESULT\|(\{[^\n]+\})\s*$',output,re.M)
            if len(matches)==1:
                try:counts=json.loads(matches[0])
                except ValueError:pass
            valid=set(counts)=={'tests','failures','errors','skipped'} and all(type(n)is int and n>=0 for n in counts.values())
            stage=('GREEN' if result.returncode==0 and counts['tests']>counts['skipped'] and not counts['errors'] and not counts['failures'] else
                   'RED' if result.returncode==1 and counts['failures']>0 and counts['errors']==0 else 'ERROR') if valid else 'ERROR'
        else:
            stage,counts=node_test_result(result.returncode,output)
        evidence={'exit_code':result.returncode,'stage':stage,'counts':counts,'image':image,
                  'sandbox':'docker-no-network','profile':profile,'coverage':'not measured',
                  'log_tail':output[-6000:],'_raw_output':raw}
    finally:
        confirmed=_remove(ready['docker'],name)
        record_owner(folder,name,image,'tests',finished=confirmed)
        if confirmed:shutil.rmtree(folder)
        else:raise ValueError('Coding test container cleanup was not confirmed: '+name)
    return {**evidence,'cleanup_confirmed':confirmed}


PREVIEW_BOOT=r'''
import os,sys,shutil,threading
from pathlib import Path
sys.path.insert(0,'/workspace/tools/dashboard')
from database import select_database
root=Path('/workspace');select_database(root,'/run/smelter-data')
if (root/'viewer.min.js').is_file():
 destination=root/'.smelter/tooling/model-viewer/node_modules/@google/model-viewer/dist/model-viewer.min.js'
 destination.parent.mkdir(parents=True);shutil.copyfile(root/'viewer.min.js',destination)
 (destination.parent.parent/'package.json').write_text('{"name":"@google/model-viewer","version":"4.1.0"}')
import dashboard
from http.server import ThreadingHTTPServer
from skill_runtime import initialize
initialize(root)
server=ThreadingHTTPServer(('127.0.0.1',8770),dashboard.handler(os.environ['SMELTER_PREVIEW_TOKEN']))
timer=threading.Timer(3600,lambda:os._exit(0));timer.daemon=True;timer.start()
server.serve_forever()
'''


def preview(root,target):
    ready=status(root)
    if not ready['ready']:raise ValueError('Confined preview unavailable: '+ready['reason'])
    folder,code=snapshot(root,target);name='smelter-preview-'+uuid4().hex;token=secrets.token_urlsafe(32)
    try:
        environment=dict(os.environ);environment['SMELTER_PREVIEW_TOKEN']=token
        command=_flags(ready['docker'],name,code)+['--detach','--env','SMELTER_PREVIEW_TOKEN',ready['configured']['python_image'],'python','-u','-c',PREVIEW_BOOT]
        record_owner(folder,name,ready['configured']['python_image'],'preview')
        run(command,timeout=15,text=True,check=True,env=environment)
        from sandbox_preview import start
        def cleanup():
            record_owner(folder,name,ready['configured']['python_image'],'preview',finished=True)
            removed=_remove(ready['docker'],name)
            if removed:shutil.rmtree(folder,ignore_errors=True)
            return removed
        result=start(ready['docker'],name,token,cleanup)
        return {**result,'sandbox':'docker-no-network','image':ready['configured']['python_image'],'container':name}
    except Exception:
        record_owner(folder,name,ready['configured']['python_image'],'preview',finished=True)
        if _remove(ready['docker'],name):shutil.rmtree(folder,ignore_errors=True)
        raise


def owned_runs(root):
    from python_tools import _plain_path
    base=_plain_path(Path(root)/'.smelter/sandbox-runs')
    if not base.is_dir():return []
    result=[]
    for folder in sorted(base.iterdir()):
        if len(result)>=100:break
        if folder.is_symlink() or not folder.is_dir():continue
        marker=_plain_path(folder/'owner.json')
        if not marker.is_file() or marker.stat().st_size>16384:continue
        try:
            row=json.loads(marker.read_text())
            if re.fullmatch(r'smelter-(?:tests|preview|opencode)-[a-f0-9]{32}',row.get('container','')):result.append({**row,'folder':str(folder)})
        except (ValueError,OSError,TypeError):continue
    return result


def reconcile(root,approval):
    if approval is not True:raise ValueError('Explicit container reconciliation approval required')
    from maintenance import _idle
    from job_store import alive,identity
    _idle(root);docker=shutil.which('docker')
    if not docker:raise ValueError('Docker is required to confirm container cleanup')
    removed=[];pending=[]
    for row in owned_runs(root):
        running_owner=alive(row.get('owner_pid',0)) and row.get('owner_identity')==identity(row.get('owner_pid',0))
        if running_owner and not row.get('finished'):continue
        if _remove(docker,row['container']):
            shutil.rmtree(Path(row['folder']));removed.append(row['container'])
        else:pending.append(row['container'])
    return {'removed':removed,'cleanup_pending':pending,'actions_replayed':False}


def record_owner(folder,name,image,kind,finished=False):
    from job_store import identity
    if not Path(folder).is_dir():return
    marker=Path(folder)/'owner.json'
    record={'container':name,'image':image,'kind':kind,'owner_pid':os.getpid(),'owner_identity':identity(os.getpid()),'created':time.time(),'finished':finished}
    temporary=marker.with_suffix('.tmp');temporary.write_text(json.dumps(record));temporary.replace(marker)
