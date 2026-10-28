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
DEFAULT={'schema_version':1,'python_image':None,'node_image':None,'opencode_image':None,'cpp_image':None,'engine_image':None}
IMAGES=('python_image','node_image','opencode_image','cpp_image','engine_image')


def validate(value):
    # Later image keys remain optional for configurations written by older versions.
    if not isinstance(value,dict) or not set(DEFAULT)-{'cpp_image','engine_image'}<=set(value)<=set(DEFAULT) or type(value['schema_version']) is not int or value['schema_version']!=1:
        raise ValueError('Sandbox configuration requires schema_version, python_image and node_image')
    for key in IMAGES:
        if value.get(key) is not None and (not isinstance(value[key],str) or not re.fullmatch(r'sha256:[a-f0-9]{64}',value[key])):
            raise ValueError('Select a locally installed immutable sha256 image ID; image tags/commands are not accepted')
    return value


def config(root):
    from database import chosen_database
    if chosen_database(Path(root)) is None:
        saved={}
    else:
        from config_store import load_config
        saved=load_config(root,NAME)
    value={**DEFAULT,**saved}
    # Setup selection lives separately until a new GUI saves its expanded schema.
    # Older running backends must still be able to validate their existing row.
    if 'engine_image' not in saved:
        from python_tools import _plain_path
        selected=_plain_path(Path(root)/'.smelter/tooling/engine-cli/selection.json')
        if selected.is_file() and selected.stat().st_size<=4096:
            try:
                selection=json.loads(selected.read_text(encoding='utf-8'))
                image=selection.get('image_id')
                if isinstance(image,str) and re.fullmatch(r'sha256:[a-f0-9]{64}',image):
                    value['engine_image']=image
            except (OSError,ValueError):pass
    return value


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
                  'coding_node':('node_image',), 'coding_cpp':('cpp_image',), 'coding_lua':('cpp_image',),
                  'engine_archive':('engine_image',)}.get(operation, ('python_image','node_image'))
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


def _flags(docker,name,snapshot,exec_scratch=False):
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
            '--env','SMELTER_SANDBOX=1','--workdir','/workspace']+(
            # Only the C++ profile runs binaries it compiles; they get their own exec-able scratch.
            ['--tmpfs','/build:rw,exec,nosuid,nodev,size=256m,mode=1777'] if exec_scratch else [])


def snapshot(root,target):
    from python_tools import _plain_path
    from frontend_workspace import _source_files, MAX_COPY
    base=_plain_path(Path(root)/'.smelter/sandbox-runs')
    files=_source_files(Path(target),('mods',))
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
    if not re.fullmatch(r'smelter-(?:tests|preview|opencode|native|engine)-[a-f0-9]{32}',name):return False
    def absent():
        # An auto-removed container is already clean. Docker versions/locales
        # differ in error wording; only a successful exact-name listing proves
        # absence. A failed daemon request cannot establish cleanup.
        listed=run([docker,'ps','--all','--filter','name=^/'+name+'$','--format','{{.ID}}'],
                   timeout=5,max_output=16384,text=True)
        return listed.returncode==0 and not listed.stdout.strip()
    try:
        found=run([docker,'inspect','--format','{{json .Config.Labels}}',name],timeout=5,max_output=16384,text=True)
        if found.returncode:return absent()
        labels=json.loads(found.stdout)
        if not isinstance(labels,dict) or labels.get('smelter.owner')!=name:return False
        removed=run([docker,'rm','--force',name],timeout=10,max_output=16384)
        # --rm can finish between inspection and explicit removal.
        return removed.returncode==0 or absent()
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
# Each mod's tests/ is its own import root; test modules are forgotten between mods so two
# mods may both have test_link.py. Tests reach their mod's code via their own sys.path setup.
CODING_MODS = r'''
import json,os,subprocess,sys,threading
from pathlib import Path
timer=threading.Timer(60,lambda:os._exit(124));timer.daemon=True;timer.start()
counts={'tests':0,'failures':0,'errors':0,'skipped':0}
for tests in sorted(Path('mods').glob('*/tests')):
 if not any(tests.glob('test_*.py')):continue
 # A fresh interpreter isolates helpers as well as test_* modules between mods.
 script="import json,unittest; r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover('.',pattern='test_*.py')); print('SMELTER_MOD_RESULT|'+json.dumps({'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors),'skipped':len(r.skipped)}))"
 one=subprocess.run([sys.executable,'-I','-c',script],cwd=tests,capture_output=True,text=True,timeout=55)
 print(one.stdout+one.stderr,flush=True)
 lines=[line for line in one.stdout.splitlines() if line.startswith('SMELTER_MOD_RESULT|')]
 if len(lines)!=1:counts['errors']+=1;continue
 found=json.loads(lines[0].split('|',1)[1])
 for key in counts:counts[key]+=found[key]
print('SMELTER_TEST_RESULT|'+json.dumps(counts),flush=True)
timer.cancel()
sys.exit(0 if counts['tests']>counts['skipped'] and not counts['failures'] and not counts['errors'] else 1)
'''
# Each mods/<mod>/tests/cpp/test_*.cpp is one test program: g++ -std=c++17 -Wall -Wextra -Werror with
# the mod folder on the include path, then run. Exit 0 passes; a nonzero exit (assert, return 1) is a
# failure (RED); a compile error or timeout is an error. Only portable code compiles here (no Win32).
CODING_CPP = r'''
import json,os,subprocess,sys,threading
from pathlib import Path
timer=threading.Timer(150,lambda:os._exit(124));timer.daemon=True;timer.start()
tests=sorted(Path('mods').glob('*/tests/cpp/test_*.cpp'))
counts={'tests':0,'failures':0,'errors':0,'skipped':0}
if len(tests)>64:
 print('ERROR: C++ suite exceeds the 64-program limit; nothing was silently omitted',flush=True)
 counts['errors']=1;tests=[]
for test in tests:
 mod=test.parents[2];binary=Path('/build')/(mod.name+'__'+test.stem);counts['tests']+=1
 try:
  built=subprocess.run(['g++','-std=c++17','-O1','-Wall','-Wextra','-Werror','-I',str(mod),str(test),'-o',str(binary),'-lm'],capture_output=True,text=True,timeout=60)
 except subprocess.TimeoutExpired:
  counts['errors']+=1;print('ERROR (compile timeout)',test,flush=True);continue
 if built.returncode:
  counts['errors']+=1;print('ERROR (compile)',test,'\n'+built.stderr[-3000:],flush=True);continue
 try:
  ran=subprocess.run([str(binary)],capture_output=True,text=True,timeout=20)
 except subprocess.TimeoutExpired:
  counts['errors']+=1;print('ERROR (run timeout)',test,flush=True);continue
 print(ran.stdout[-2000:]+ran.stderr[-2000:],flush=True)
 if ran.returncode:counts['failures']+=1;print('FAIL',test,'exit',ran.returncode,flush=True)
 else:print('PASS',test,flush=True)
print('SMELTER_TEST_RESULT|'+json.dumps(counts),flush=True)
timer.cancel()
sys.exit(0 if counts['tests'] and not counts['failures'] and not counts['errors'] else 1)
'''
CODING_LUA = r'''
import hashlib,json,os,re,subprocess,sys,threading,time
from pathlib import Path
timer=threading.Timer(60,lambda:os._exit(124));timer.daemon=True;timer.start()
tests=sorted(Path('mods').glob('*/tests/test_*.lua'))
counts={'tests':0,'failures':0,'errors':0,'skipped':0}
syntax={'files_total':0,'files_checked':0,'errors':0,'failed_files':[]}
deadline=time.monotonic()+55
if len(tests)>64:counts['errors']=1;tests=[];print('ERROR: Lua suite exceeds 64 programs',flush=True)
# Compile every Lua source in each tested mod, including modules no test imports.
# loadfile only compiles: the chunk is never called and its environment is empty.
# The path is input data, not a Lua argument (which would execute it after -e).
check='local p=io.read("*a");local f,e=loadfile(p,"t",{});if not f then io.stderr:write(tostring(e),"\\n");os.exit(1) end'
sources=[]
for mod in sorted({test.parents[1] for test in tests}):
 for source in sorted(mod.rglob('*')):
  if source.is_file() and source.suffix.lower()=='.lua':sources.append(source)
syntax['files_total']=len(sources)
manifest={p.as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources} if len(sources)<=512 else {}
programs=[]
# Trace the actual standard Lua file searcher, preserving loader and loader-data.
# Hex fields keep paths/module names data rather than interpolated source code.
bootstrap="""local original=package.searchers[2]
local function hex(s) return (tostring(s):gsub('.',function(c) return string.format('%02x',string.byte(c)) end)) end
package.searchers[2]=function(name)
 local loader,path=original(name)
 if type(loader)=='function' then io.stdout:write('SMELTER_LUA_IMPORT|'..hex(name)..'|'..hex(path)..'\\n');io.stdout:flush() end
 return loader,path
end"""
if len(sources)>512:
 counts['errors']+=1;syntax['errors']+=1
 print('ERROR: Lua source syntax suite exceeds 512 files; nothing was silently omitted',flush=True)
else:
 for source in sources:
  try:
   remaining=deadline-time.monotonic()
   if remaining<=0:raise subprocess.TimeoutExpired('Lua syntax preflight',55)
   result=subprocess.run(['lua5.4','-e',check],input=source.as_posix(),capture_output=True,text=True,timeout=min(5,remaining))
   syntax['files_checked']+=1
   if result.returncode:
    counts['errors']+=1;syntax['errors']+=1
    detail={'path':source.as_posix(),'error':(result.stdout+result.stderr)[-1200:]}
    if len(syntax['failed_files'])<32:syntax['failed_files'].append(detail)
    print('LUA_SYNTAX_ERROR '+source.as_posix()+': '+detail['error'],flush=True)
  except (OSError,subprocess.TimeoutExpired) as exc:
   counts['errors']+=1;syntax['errors']+=1
   print('ERROR: Lua syntax preflight '+type(exc).__name__,flush=True)
   break
if counts['errors']:
 print('ERROR: Source syntax preflight failed; behavioral tests were not run',flush=True)
 tests=[]
print('SMELTER_LUA_SYNTAX_RESULT|'+json.dumps(syntax),flush=True)
for test in tests:
 counts['tests']+=1
 try:
  remaining=deadline-time.monotonic()
  if remaining<=0:raise subprocess.TimeoutExpired('lua5.4',55)
  result=subprocess.run(['lua5.4','-e',bootstrap,str(test.relative_to(test.parents[1]))],cwd=test.parents[1],capture_output=True,text=True,timeout=min(15,remaining))
  imports=[]
  for module_hex,path_hex in re.findall(r'^SMELTER_LUA_IMPORT\|([a-f0-9]+)\|([a-f0-9]+)\s*$',result.stdout,re.M)[:64]:
   if len(module_hex)>1024 or len(path_hex)>4096:continue
   module=bytes.fromhex(module_hex).decode('utf-8',errors='replace')
   resolved=(test.parents[1]/bytes.fromhex(path_hex).decode('utf-8',errors='replace')).resolve()
   try:
    relative=resolved.relative_to(Path.cwd().resolve()).as_posix()
    imports.append({'module':module,'path':relative,'sha256':manifest.get(relative),'scope':'standard Lua file loader'})
   except ValueError:imports.append({'module':module,'outside_snapshot':True})
  programs.append({'test':test.as_posix(),'working_directory':test.parents[1].as_posix(),'exit_code':result.returncode,'imports':imports})
  print(result.stdout[-3000:]+result.stderr[-3000:],flush=True)
  if result.returncode:
   # A Lua runtime/import exception is not a deliberate TDD assertion failure.
   runtime_error=bool(re.search(r'^lua[\d.]*: .+\.lua:\d+:',result.stderr,re.M))
   counts['errors' if runtime_error and 'assertion failed' not in result.stderr else 'failures']+=1
 except (OSError,subprocess.TimeoutExpired) as exc:counts['errors']+=1;print(type(exc).__name__,flush=True)
print('SMELTER_LUA_EXECUTION|'+json.dumps({'manifest':manifest,'programs':programs}),flush=True)
print('SMELTER_TEST_RESULT|'+json.dumps(counts),flush=True)
timer.cancel()
sys.exit(0 if counts['tests'] and not counts['failures'] and not counts['errors'] else 1)
'''


def lua_runner_sha256():
    """Invalidate earlier Lua receipts when the host-controlled runner changes."""
    import hashlib
    return hashlib.sha256(CODING_LUA.encode('utf-8')).hexdigest()


def lua_snapshot_manifest(code):
    """Host hashes of the fresh mounted copy, independent of gameplay test output."""
    import hashlib
    tests=sorted(Path(code).glob('mods/*/tests/test_*.lua'))
    sources=sorted({p for test in tests for p in test.parents[1].rglob('*') if p.is_file() and p.suffix.lower()=='.lua'})
    if len(sources)>512:return {}
    return {p.relative_to(code).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}


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
    if profile not in ('python','node','mods','cpp','lua'):raise ValueError('Unsupported coding test profile')
    from access_policy import require
    require(target,'execute','tests')
    ready=status(root,operation='coding_'+('python' if profile=='mods' else profile))
    image_key={'mods':'python','cpp':'cpp','lua':'cpp'}.get(profile,profile)+'_image'
    if not ready['ready']:raise ValueError('Confined coding tests unavailable: '+ready['reason'])
    folder,code=snapshot(root,target)
    name='smelter-tests-'+uuid4().hex
    expected_lua=lua_snapshot_manifest(code) if profile=='lua' else None
    image=ready['configured'][image_key]
    command={'python':['python','-I','-c',CODING_PYTHON],'mods':['python','-I','-c',CODING_MODS],
             'cpp':['python','-I','-c',CODING_CPP], 'lua':['python','-I','-c',CODING_LUA]}.get(profile,['node','-e',CODING_NODE])
    confirmed=False
    try:
        record_owner(folder,name,image,'tests')
        result=run(_flags(ready['docker'],name,code,exec_scratch=profile=='cpp')+['--rm',image,*command],
                   timeout=160 if profile=='cpp' else 70,max_output=2*1024*1024)
        raw=result.stdout+result.stderr
        output=raw.decode('utf-8',errors='replace')
        counts={}
        if profile in ('python','mods','cpp','lua'):
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
        evidence['source_snapshot']={'id':folder.name,'mode':'fresh_copy_per_invocation',
            'mount':'read_only_bind','image_role':'runtime_toolchain_only; source is not an image layer'}
        if profile=='mods':
            evidence['validation_scope']='Python unittest discovery under mods/*/tests; this profile does not run Lua. Use profile=lua for test_*.lua.'
        if profile=='lua':
            markers=re.findall(r'^SMELTER_LUA_SYNTAX_RESULT\|(\{[^\n]+\})\s*$',output,re.M)
            syntax=None
            if len(markers)==1:
                try:syntax=json.loads(markers[0])
                except ValueError:pass
            valid=(isinstance(syntax,dict) and
                   all(type(syntax.get(k)) is int and syntax[k]>=0 for k in ('files_total','files_checked','errors')) and
                   isinstance(syntax.get('failed_files'),list) and
                   syntax['files_checked']<=syntax['files_total'])
            if not valid or syntax['errors'] or syntax['files_checked']!=syntax['files_total']:
                evidence['stage']='ERROR'
            evidence.update(source_syntax=syntax if valid else None, runner_sha256=lua_runner_sha256(),
                validation_scope='Lua 5.4 source syntax in tested mods, then test-program exit codes. Tests must import actual implementations and assert failures; behavioral coverage and game compatibility are not measured.')
            executions=re.findall(r'^SMELTER_LUA_EXECUTION\|(\{[^\n]+\})\s*$',output,re.M)
            execution=None
            if len(executions)==1:
                try:execution=json.loads(executions[0])
                except ValueError:pass
            proof=(isinstance(execution,dict) and execution.get('manifest')==expected_lua and
                   isinstance(execution.get('programs'),list) and len(execution['programs'])<=64 and
                   len(execution['programs'])==counts.get('tests'))
            import hashlib
            checksum=lambda value:hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            observed=execution.get('manifest') if isinstance(execution,dict) else None
            evidence['source_snapshot'].update(lua_files_total=len(expected_lua),
                expected_lua_sha256=checksum(expected_lua),observed_lua_sha256=checksum(observed) if isinstance(observed,dict) else None,
                bytes_match=proof,files=[{'path':p,'sha256':sha} for p,sha in list(expected_lua.items())[:64]],files_truncated=len(expected_lua)>64)
            evidence['test_programs']=[]
            if proof:
                remaining_imports=128
                for item in execution['programs']:
                    if not isinstance(item,dict) or not isinstance(item.get('test'),str) or not isinstance(item.get('working_directory'),str) or type(item.get('exit_code')) is not int or not isinstance(item.get('imports'),list):
                        proof=False;break
                    if item['test'] not in expected_lua or item['working_directory']!=Path(item['test']).parents[1].as_posix():
                        proof=False;break
                    if any(not isinstance(entry,dict) or not isinstance(entry.get('module'),str) or
                           not entry.get('outside_snapshot') and (entry.get('path') not in expected_lua or
                           entry.get('sha256')!=expected_lua.get(entry.get('path'))) for entry in item['imports']):
                        proof=False;break
                    imports=item['imports'][:min(16,remaining_imports)]
                    remaining_imports-=len(imports)
                    evidence['test_programs'].append({**item,'imports':imports,'imports_truncated':len(imports)<len(item['imports'])})
            evidence['source_snapshot']['bytes_match']=proof
            if not proof:
                evidence['stage']='ERROR'
                evidence['source_snapshot']['error']='Missing or inconsistent container source/execution receipt; no cache rebuild was attempted.'
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
            if re.fullmatch(r'smelter-(?:tests|preview|opencode|native|engine)-[a-f0-9]{32}',row.get('container','')):result.append({**row,'folder':str(folder)})
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
