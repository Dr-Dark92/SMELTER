"""Bounded fixed-command subprocesses; not a filesystem/network sandbox.

Drain both pipes concurrently, retain at most max_output bytes total, and close
owned process groups/jobs on timeout, cancellation or excessive output.
"""
import os
import signal
import subprocess
import threading
import time

MAX_OUTPUT=2*1024*1024


class OutputLimitExceeded(ValueError):
    pass


class _WindowsJob:
    def __init__(self, process):
        import ctypes
        from ctypes import wintypes as w
        class BASIC(ctypes.Structure):
            _fields_=[('PerProcessUserTimeLimit',ctypes.c_longlong),('PerJobUserTimeLimit',ctypes.c_longlong),('LimitFlags',w.DWORD),('MinimumWorkingSetSize',ctypes.c_size_t),('MaximumWorkingSetSize',ctypes.c_size_t),('ActiveProcessLimit',w.DWORD),('Affinity',ctypes.c_size_t),('PriorityClass',w.DWORD),('SchedulingClass',w.DWORD)]
        class IO(ctypes.Structure):
            _fields_=[(name,ctypes.c_ulonglong) for name in ('ReadOperationCount','WriteOperationCount','OtherOperationCount','ReadTransferCount','WriteTransferCount','OtherTransferCount')]
        class EXTENDED(ctypes.Structure):
            _fields_=[('BasicLimitInformation',BASIC),('IoInfo',IO),('ProcessMemoryLimit',ctypes.c_size_t),('JobMemoryLimit',ctypes.c_size_t),('PeakProcessMemoryUsed',ctypes.c_size_t),('PeakJobMemoryUsed',ctypes.c_size_t)]
        k=ctypes.WinDLL('kernel32',use_last_error=True)
        k.CreateJobObjectW.argtypes=[ctypes.c_void_p,w.LPCWSTR];k.CreateJobObjectW.restype=w.HANDLE
        k.SetInformationJobObject.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD]
        k.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE]
        k.CloseHandle.argtypes=[w.HANDLE]
        self.kernel,self.handle=k,k.CreateJobObjectW(None,None)
        if not self.handle:raise OSError('Cannot create owned Windows process job')
        limits=EXTENDED();limits.BasicLimitInformation.LimitFlags=0x2000  # KILL_ON_JOB_CLOSE
        if not k.SetInformationJobObject(self.handle,9,ctypes.byref(limits),ctypes.sizeof(limits)) or not k.AssignProcessToJobObject(self.handle,w.HANDLE(int(process._handle))):
            self.close();raise OSError('Cannot attach process to its Windows cleanup job')

    def close(self):
        if self.handle:self.kernel.CloseHandle(self.handle);self.handle=None


def run(args, *, timeout=30, max_output=MAX_OUTPUT, cancel=None, cwd=None,
        capture_output=False, input=None, text=False, encoding=None, errors='replace',
        stdout=None, stderr=None, stdin=None, shell=False, check=False,
        creationflags=0, env=None, **options):
    if shell or not isinstance(args,(list,tuple)) or not args or any(not isinstance(x,(str,os.PathLike)) for x in args):
        raise ValueError('Fixed argument-vector commands only; shell execution is denied')
    if not 0<timeout<=1800 or type(max_output) is not int or not 0<max_output<=16*1024*1024:
        raise ValueError('Invalid process timeout/output budget')
    if capture_output and (stdout is not None or stderr is not None):raise ValueError('capture_output cannot be combined with output targets')
    if options:raise ValueError('Unsupported process runner options: '+','.join(options))
    if input is not None and (stdin is not None or not isinstance(input,bytes) or len(input)>4*1024*1024):raise ValueError('Invalid bounded process input')
    start=time.monotonic();options={'creationflags':creationflags|getattr(subprocess,'CREATE_NO_WINDOW',0)} if os.name=='nt' else {'start_new_session':True}
    process=subprocess.Popen(args,cwd=cwd,env=env,stdin=subprocess.PIPE if input is not None else stdin if stdin is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False,**options)
    job=None;buffers=[bytearray(),bytearray()];lock=threading.Lock();excess=threading.Event();failures=[];total=0
    def terminate():
        if os.name!='nt':
            try:os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:pass
        elif job:job.close()
        elif process.poll() is None:process.kill()
    def drain(pipe,index,target):
        nonlocal total
        try:
            while True:
                chunk=pipe.read1(16384)
                if not chunk:break
                with lock:
                    keep=chunk[:max(0,max_output-total)];total+=len(keep);buffers[index].extend(keep)
                    if len(keep)<len(chunk):excess.set()
                    if target not in (None,subprocess.PIPE,subprocess.DEVNULL,subprocess.STDOUT):target.write(keep)
                if excess.is_set():break
        except (OSError,ValueError) as exc:failures.append(str(exc))
        finally:pipe.close()
    try:
        if os.name=='nt':job=_WindowsJob(process)
        threads=[threading.Thread(target=drain,args=(process.stdout,0,stdout),daemon=True),threading.Thread(target=drain,args=(process.stderr,1,stdout if stderr==subprocess.STDOUT else stderr),daemon=True)]
        if input is not None:
            def feed():
                try:process.stdin.write(input);process.stdin.close()
                except OSError:pass
            threads.append(threading.Thread(target=feed,daemon=True))
        for thread in threads:thread.start()
        reason=None
        while process.poll() is None or any(t.is_alive() for t in threads):
            if excess.is_set():reason='output';break
            if failures:reason='pipe';break
            if cancel and cancel.is_set():reason='cancelled';break
            if time.monotonic()-start>=timeout:reason='timeout';break
            time.sleep(.02)
        # Also reap descendants which retain pipes after their parent exits.
        terminate();process.wait(timeout=5)
        for thread in threads:thread.join(timeout=5)
        if any(t.is_alive() for t in threads):raise OSError('Owned process output readers did not terminate')
        out,err=bytes(buffers[0]),bytes(buffers[1])
        if text:out,err=out.decode(encoding or 'utf-8',errors),err.decode(encoding or 'utf-8',errors)
        if reason=='timeout':raise subprocess.TimeoutExpired(args,timeout,output=out,stderr=err)
        if reason=='cancelled':raise ValueError('Process cancelled; owned descendants were terminated')
        if reason=='output' or excess.is_set():raise OutputLimitExceeded('Process output exceeded '+str(max_output)+' bytes; owned descendants were terminated')
        if reason=='pipe':raise OSError('Process output capture failed: '+failures[0])
        result=subprocess.CompletedProcess(args,process.returncode,out,err)
        if check and result.returncode:raise subprocess.CalledProcessError(result.returncode,args,output=out,stderr=err)
        return result
    finally:
        terminate()
        if job:job.close()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
