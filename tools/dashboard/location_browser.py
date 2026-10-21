"""Authenticated operator folder navigation; metadata only, no grants or execution.

The HTTP route is not a model tool. Browsing may navigate outside registered
scopes so the operator can select a new location; only Apply changes policy.
"""
import os
from pathlib import Path
from access_policy import plain,current

MAX_DIRECTORIES=200
MAX_VISITED=3000


def _roots(root):
    candidates=[('Home',Path.home()),('Current checkout',Path(root))]
    if os.name=='nt':
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetLogicalDrives.restype=wintypes.DWORD
        kernel.GetDriveTypeW.argtypes=[wintypes.LPCWSTR];kernel.GetDriveTypeW.restype=wintypes.UINT
        mask=kernel.GetLogicalDrives()
        for index in range(26):
            drive=chr(65+index)+':\\'
            if mask&(1<<index) and kernel.GetDriveTypeW(drive)==3:candidates.append((drive,Path(drive)))
    else:candidates.append(('Filesystem',Path('/')))
    candidates.extend((row['name'],Path(row['path'])) for row in current(root).value['locations'])
    found=[];seen=set()
    for label,target in candidates:
        try:
            target=plain(target);key=str(target).casefold() if os.name=='nt' else str(target)
            if key in seen or not target.is_dir():continue
        except (ValueError,OSError):continue
        seen.add(key);found.append({'name':label,'path':str(target)})
    return found


def browse(root,path=None,show_hidden=False):
    if type(show_hidden) is not bool:raise ValueError('Invalid hidden-folder option')
    result={'roots':_roots(root),'current_path':None,'parent':None,'breadcrumbs':[],
            'directories':[],'selectable':False,'truncated':False,'read_only':True,
            'scope':'Operator directory names only. Browsing does not register or grant access.'}
    if path is None or path=='':return result
    if not isinstance(path,str) or len(path)>1000:raise ValueError('Provide a local absolute directory path')
    target=plain(path)
    if not target.is_dir():raise ValueError('Folder is missing or cannot be accessed')
    from python_tools import _linked
    rows=[];visited=0;truncated=False
    try:
        with os.scandir(target) as entries:
            for entry in entries:
                visited+=1
                if visited>MAX_VISITED:truncated=True;break
                if not show_hidden and entry.name.startswith('.'):continue
                try:
                    child=Path(entry.path)
                    if entry.is_dir(follow_symlinks=False) and not _linked(child):
                        if len(rows)>=MAX_DIRECTORIES:truncated=True;break
                        rows.append({'name':entry.name,'path':str(child)})
                except (OSError,ValueError):continue
    except OSError as exc:raise ValueError('Cannot browse folder: '+str(exc)[:300]) from exc
    parents=list(reversed(target.parents))+[target]
    return {**result,'current_path':str(target),'parent':str(target.parent) if target.parent!=target else None,
            'breadcrumbs':[{'name':part.name or str(part),'path':str(part)} for part in parents],
            'directories':sorted(rows,key=lambda row:row['name'].casefold()),'selectable':target.parent!=target,
            'truncated':truncated,'visited_entries':min(visited,MAX_VISITED)}
