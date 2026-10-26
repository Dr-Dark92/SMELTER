"""Conservative quotas for application-owned artifacts, not project files."""
import os
import threading
import time
from pathlib import Path

AREAS=('model-assets','tool-runs','rea-evidence','reports','access-requests','web-cache','project-memory')
MAX_BYTES=1024*1024*1024
MAX_FILES=10000
_lock=threading.Lock()
_cache={}


def inventory(root,areas=AREAS):
    from python_tools import _plain_path
    result=[]
    for area in areas:
        base=_plain_path(Path(root)/'.smelter'/area)
        if not base.is_dir():continue
        pending=[base]
        while pending:
            folder=pending.pop()
            with os.scandir(folder) as entries:
                for entry in entries:
                    if entry.is_symlink():continue
                    info=entry.stat(follow_symlinks=False)
                    if getattr(info,'st_file_attributes',0)&0x400:continue
                    if entry.is_dir(follow_symlinks=False):pending.append(Path(entry.path))
                    elif entry.is_file(follow_symlinks=False):
                        result.append({'area':area,'relative':Path(entry.path).relative_to(base).as_posix(),'path':Path(entry.path),'bytes':info.st_size,'mtime_ns':info.st_mtime_ns})
                    if len(result)+len(pending)>20000:raise ValueError('Artifact inventory exceeds safety limit; inspect storage manually')
    return result


def require(root,amount, *, new_file=True):
    if type(amount) is not int or amount<0 or amount>MAX_BYTES:raise ValueError('Invalid artifact byte reservation')
    key=str(Path(root).resolve());now=time.monotonic()
    with _lock:
        if key not in _cache or now-_cache[key][0]>=2:
            rows=inventory(root);_cache[key]=[now,sum(r['bytes'] for r in rows),len(rows)]
        entry=_cache[key]
        if entry[1]+amount>MAX_BYTES or entry[2]+int(new_file)>MAX_FILES:
            raise ValueError('Artifact quota reached (1 GiB / 10,000 files). Review retention in Settings; nothing was deleted automatically.')
        entry[1]+=amount;entry[2]+=int(new_file)


def invalidate(root):
    with _lock:_cache.pop(str(Path(root).resolve()),None)
