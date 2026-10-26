"""Gracefully reload this checkout's idle Windows dashboard; never force-kill.

Requires the exact old PID and launch log. Authenticates its root/port, checks
the job journal, and sends Ctrl+C only to a console containing that dashboard
and this helper. Other console processes, identity changes or active jobs abort.
"""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/dashboard'))


def _process(pid):
    from process_runner import run
    command='Get-CimInstance Win32_Process -Filter "ProcessId='+str(pid)+'" | Select-Object ProcessId,ExecutablePath,CommandLine | ConvertTo-Json -Compress'
    result=run(['powershell','-NoProfile','-NonInteractive','-Command',command],timeout=10,max_output=16384,text=True,check=True)
    return json.loads(result.stdout)


def _url(log,port):
    from python_tools import _plain_path
    log=_plain_path(log)
    if not log.is_file() or log.stat().st_size>1024*1024:raise ValueError('Expected dashboard launch log is unavailable')
    match=re.search(r'http://127\.0\.0\.1:'+str(port)+r'/#token=([A-Za-z0-9_-]{32,100})',log.read_text(encoding='utf-8'))
    if not match:raise ValueError('Launch log does not identify this port/session')
    return match.group(1)


def _verify(root,port,token):
    from maintenance import _idle
    _idle(root)
    request=Request('http://127.0.0.1:'+str(port)+'/api/access-policy',headers={'X-Smelter-Token':token,'Origin':'http://127.0.0.1:'+str(port)})
    with urlopen(request,timeout=10) as response:data=json.load(response)
    if not any(Path(row['path']).resolve()==root and row['id']=='source' for row in data['locations']):
        raise ValueError('The authenticated dashboard belongs to another checkout')


def _launch(root,port,kernel):
    # The helper ignores Ctrl+C while signalling its attached console. Windows
    # inherits that flag even with CREATE_NEW_CONSOLE; clear it before spawning.
    if not kernel.SetConsoleCtrlHandler(None,False):
        raise ValueError('Could not restore console interrupts before dashboard launch')
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    stdout=root/'.smelter/dashboard-knowledge.stdout.log';stderr=root/'.smelter/dashboard-knowledge.stderr.log'
    with stdout.open('wb') as out,stderr.open('wb') as err:
        return subprocess.Popen([sys.executable,'-u',str(root/'tools/dashboard/dashboard.py'),'--no-browser','--port',str(port)],
            cwd=str(root),stdin=subprocess.DEVNULL,stdout=out,stderr=err,startupinfo=startup,creationflags=subprocess.CREATE_NEW_CONSOLE,close_fds=True)


def reload(root,pid,log,port=8768):
    if os.name!='nt':raise ValueError('This console-safe helper is Windows only')
    from python_tools import _plain_path
    root=_plain_path(Path(root).resolve());log=_plain_path(Path(log).resolve())
    if not log.is_relative_to(root/'.smelter') or type(pid) is not int or pid<=0 or not 1024<=port<=65535:raise ValueError('Use this checkout’s launch log, exact PID and local port')
    token=_url(log,port);_verify(root,port,token);process=_process(pid)
    command=process.get('CommandLine','')
    if process.get('ProcessId')!=pid or not re.search(r'tools[/\\]dashboard[/\\]dashboard\.py',command) or '--port '+str(port) not in command:
        raise ValueError('Exact dashboard command/PID was not confirmed')
    listener=subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',
        '(Get-NetTCPConnection -LocalPort '+str(port)+' -State Listen).OwningProcess'],capture_output=True,text=True,timeout=10,check=True)
    if listener.stdout.strip()!=str(pid):raise ValueError('Dashboard listener identity changed')
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD];kernel.WaitForSingleObject.restype=wintypes.DWORD
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    kernel.GetConsoleProcessList.argtypes=[ctypes.POINTER(wintypes.DWORD),wintypes.DWORD];kernel.GetConsoleProcessList.restype=wintypes.DWORD
    handle=kernel.OpenProcess(0x00100000|0x1000,False,pid)
    if not handle:raise ValueError('Cannot observe the exact dashboard process')
    attached=False
    try:
        if kernel.WaitForSingleObject(handle,0)!=258:raise ValueError('Dashboard already exited')
        kernel.FreeConsole()
        if not kernel.AttachConsole(pid):raise ValueError('Dashboard has no independently attachable console; no process was stopped')
        attached=True;members=(wintypes.DWORD*32)();count=kernel.GetConsoleProcessList(members,32)
        if count<1 or count>32 or set(members[:count])!={pid,os.getpid()}:
            raise ValueError('Dashboard console contains another process; no signal was sent')
        _verify(root,port,token)
        if not kernel.SetConsoleCtrlHandler(None,True):raise ValueError('Could not protect the reload helper from Ctrl+C')
        if not kernel.GenerateConsoleCtrlEvent(0,0):raise ValueError('Graceful Ctrl+C was not delivered')
        deadline=time.monotonic()+45
        while kernel.WaitForSingleObject(handle,100)==258:
            if time.monotonic()>deadline:raise ValueError('Dashboard did not exit gracefully; it was not force-terminated')
    finally:
        if attached:kernel.FreeConsole()
        kernel.CloseHandle(handle)
    # Start hidden in its own console so future graceful reloads remain possible.
    stdout=root/'.smelter/dashboard-knowledge.stdout.log';stderr=root/'.smelter/dashboard-knowledge.stderr.log'
    child=_launch(root,port,kernel)
    deadline=time.monotonic()+45
    while time.monotonic()<deadline:
        if child.poll() is not None:raise ValueError('Updated dashboard exited; inspect its launch log')
        try:
            current=_url(stdout,port)
            request=Request('http://127.0.0.1:'+str(port)+'/api/project-memory',headers={'X-Smelter-Token':current,'Origin':'http://127.0.0.1:'+str(port)})
            with urlopen(request,timeout=2) as response:ready=json.load(response)
            return {'status':'reloaded','old_pid':pid,'pid':child.pid,'port':port,'memory_notes':ready['notes'],'graceful':True}
        except (ValueError,OSError):time.sleep(.2)
    raise ValueError('Updated dashboard health was not confirmed; inspect its log')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--pid',type=int,required=True);parser.add_argument('--log',type=Path,required=True);parser.add_argument('--port',type=int,default=8768);args=parser.parse_args()
    result=reload(args.root,args.pid,args.log,args.port);(args.root/'.smelter/knowledge-gui-refresh.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
