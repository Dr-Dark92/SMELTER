"""Operator-only retention and complete database/application-state backup.

No model tool exposes these operations. Pruning uses expiring server-side plans;
backups/restores never overwrite existing destinations or follow links.
"""
import hashlib
import json
import shutil
import sqlite3
import threading
import time
from contextlib import closing
from pathlib import Path
from uuid import UUID,uuid4
from database import chosen_database,inspect_database
from storage_budget import inventory,invalidate,MAX_BYTES,MAX_FILES,AREAS

STATE_AREAS=AREAS+('managed-skills',)
_plans={}
_lock=threading.RLock()


def _idle(root):
    from job_store import active
    if active(root):raise ValueError('Finish or reconcile active jobs before maintenance')


def _digest(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        while chunk:=stream.read(65536):h.update(chunk)
    return h.hexdigest()


def status(root):
    from job_store import list_jobs
    rows=inventory(root)
    from sandbox import owned_runs
    return {'runtime_snapshots':owned_runs(root),'artifact_bytes':sum(r['bytes'] for r in rows),'artifact_files':len(rows),
            'max_bytes':MAX_BYTES,'max_files':MAX_FILES,'jobs':list_jobs(root),
            'cleanup':'Operator-approved dry-run plan only; no automatic deletion',
            'backup_scope':'SQLite snapshot, skill state and managed manifests, GLBs, reports, audits and REA evidence.',
            'backup_exclusions':['Source code and external V2/coding copies', 'Coding workspace metadata/proposals/test logs',
                                 'MCP connection JSON, tool installations and model weights'],
            'restore_note':'Review restored absolute access locations and image IDs before admitting tasks on a new checkout.'}


def _referenced(root):
    with closing(sqlite3.connect(chosen_database(Path(root)))) as conn:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='model_attachments'").fetchone():return set()
        return {r[0] for r in conn.execute('SELECT id FROM model_attachments')}


def plan(root,days=30):
    if type(days) is not int or not 1<=days<=3650:raise ValueError('Choose retention age 1–3650 days')
    _idle(root);rows=inventory(root);known=_referenced(root);cutoff=time.time()-days*86400
    reports=sorted((r for r in rows if r['area']=='reports'),key=lambda r:r['mtime_ns'],reverse=True)
    excess={r['relative'] for r in reports[100:]};selected=[]
    for row in rows:
        path=row['path']
        if '/' in row['relative']:continue
        try:
            if str(UUID(path.stem))!=path.stem:continue
        except ValueError:continue
        if path.suffix not in ('.json','.jsonl','.glb'):continue
        if row['area']=='model-assets' and path.stem in known:continue
        if row['mtime_ns']/1e9>=cutoff and not (row['area']=='reports' and row['relative'] in excess):continue
        selected.append({**row,'path':str(path),'sha256':_digest(path)})
    token=str(uuid4())
    with _lock:
        now=time.time()
        for key in list(_plans):
            if _plans[key]['expires']<now:_plans.pop(key)
        if len(_plans)>=20:raise ValueError('Too many pending retention plans; allow old plans to expire')
        _plans[token]={'root':str(Path(root).resolve()),'entries':selected,'expires':now+600}
    return {'plan_id':token,'expires_in_seconds':600,'files':len(selected),'bytes':sum(r['bytes'] for r in selected),
            'entries':[{k:v for k,v in r.items() if k!='path'} for r in selected],
            'criteria':'Unreferenced/old artifacts; reports additionally retain newest 100. Referenced GLBs are protected.'}


def prune(root,token,approval):
    if approval is not True:raise ValueError('Explicit retention approval required')
    _idle(root)
    with _lock:entry=_plans.pop(token,None)
    if not entry or entry['root']!=str(Path(root).resolve()) or entry['expires']<time.time():raise ValueError('Retention plan expired or belongs to another workspace')
    from python_tools import _plain_path
    known=_referenced(root);removed=[];changed=[]
    for row in entry['entries']:
        path=_plain_path(Path(row['path']))
        if not path.is_file():continue
        info=path.stat()
        if info.st_size!=row['bytes'] or info.st_mtime_ns!=row['mtime_ns'] or _digest(path)!=row['sha256'] or row['area']=='model-assets' and path.stem in known:
            changed.append(row['relative']);continue
        path.unlink();removed.append(row['relative'])
    invalidate(root)
    return {'removed':len(removed),'skipped_changed':changed,'replayed_actions':False}


def _state_files(root):
    rows=inventory(root,STATE_AREAS)
    from python_tools import _plain_path
    state=_plain_path(Path(root)/'.smelter/skill-state.json')
    if state.is_file():rows.append({'area':'','relative':'skill-state.json','path':state,'bytes':state.stat().st_size,'mtime_ns':state.stat().st_mtime_ns})
    return rows


def _signature(rows):return sorted((r['area'],r['relative'],r['bytes'],r['mtime_ns']) for r in rows)


def backup(root,directory,approval):
    if approval is not True:raise ValueError('Explicit backup approval required')
    _idle(root)
    from python_tools import _plain_path
    root=Path(root).resolve();destination=_plain_path(Path(directory));db=chosen_database(root)
    if not destination.is_absolute() or destination==root or destination.is_relative_to(root) or destination==db.parent or destination.is_relative_to(db.parent):
        raise ValueError('Choose a new backup directory outside the checkout and database directory')
    if destination.exists():raise ValueError('Backup destination already exists; no overwrite')
    rows=_state_files(root)
    if len(rows)>MAX_FILES or sum(r['bytes'] for r in rows)>MAX_BYTES:raise ValueError('Backup state exceeds safety budget; review retention first')
    if shutil.disk_usage(destination.parent).free<sum(r['bytes'] for r in rows)+db.stat().st_size+64*1024*1024:raise ValueError('Insufficient backup space')
    destination.mkdir(mode=0o700);written=[]
    try:
        with closing(sqlite3.connect(db)) as source:
            version=source.execute('PRAGMA data_version').fetchone()[0]
            target=destination/'database.sqlite3'
            with target.open('xb'):written.append(target)
            with closing(sqlite3.connect(target)) as output:source.backup(output)
            manifest={'schema_version':1,'status':'complete','created_utc_epoch':time.time(),'files':[]}
            manifest['files'].append({'path':'database.sqlite3','bytes':target.stat().st_size,'sha256':_digest(target)})
            for row in rows:
                relative='state/'+('/'.join(x for x in (row['area'],row['relative']) if x))
                target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
                with target.open('xb') as out,row['path'].open('rb') as source_file:
                    written.append(target);shutil.copyfileobj(source_file,out,65536)
                manifest['files'].append({'path':relative,'bytes':target.stat().st_size,'sha256':_digest(target)})
            if version!=source.execute('PRAGMA data_version').fetchone()[0] or _signature(rows)!=_signature(_state_files(root)):
                raise ValueError('Application state changed during backup; retry while idle')
            # Compare copied bytes as well as metadata; do not silently accept concurrent edits.
            for row,item in zip(rows,manifest['files'][1:]):
                if _digest(row['path'])!=item['sha256']:raise ValueError('Application file changed during backup')
        marker=destination/'manifest.json'
        with marker.open('x',encoding='utf-8') as out:written.append(marker);json.dump(manifest,out,indent=2)
        return {'status':'backed_up','path':str(destination),'files':len(manifest['files']),'manifest_sha256':_digest(marker)}
    except Exception:
        # Only files created by this operation are cleanup candidates.
        for path in reversed(written):path.unlink(missing_ok=True)
        for folder in sorted((p for p in destination.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
            try:folder.rmdir()
            except OSError:pass
        try:destination.rmdir()
        except OSError:pass
        raise


def restore(backup_directory,root,data_directory,approval):
    if approval is not True:raise ValueError('Explicit restore approval required')
    from python_tools import _plain_path
    backup_root=_plain_path(Path(backup_directory));root=_plain_path(Path(root));data=_plain_path(Path(data_directory))
    if not all(p.is_absolute() for p in (backup_root,root,data)):raise ValueError('Restore paths must be absolute')
    if not root.is_dir() or (root/'.smelter').exists() or data.exists():raise ValueError('Restore requires a checkout without .smelter and a new data directory; no overwrite')
    if data==root or data.is_relative_to(root) or data.is_relative_to(backup_root):raise ValueError('Restore data must be outside checkout and backup')
    manifest_path=_plain_path(backup_root/'manifest.json')
    if manifest_path.stat().st_size>4*1024*1024:raise ValueError('Backup manifest too large')
    manifest=json.loads(manifest_path.read_text());rows=manifest.get('files')
    if manifest.get('schema_version')!=1 or manifest.get('status')!='complete' or not isinstance(rows,list) or not rows or len(rows)>MAX_FILES+1:raise ValueError('Invalid backup manifest')
    seen=set();total=0
    for row in rows:
        relative=row.get('path');path=Path(relative) if isinstance(relative,str) else None
        if path is None or path.is_absolute() or '..' in path.parts or '\\' in relative or ':' in relative or relative in seen:raise ValueError('Invalid backup path')
        if relative!='database.sqlite3' and not (relative=='state/skill-state.json' or any(relative.startswith('state/'+area+'/') for area in STATE_AREAS)):raise ValueError('Backup contains an unsupported state area')
        source=_plain_path(backup_root/path);total+=source.stat().st_size
        if total>MAX_BYTES+512*1024*1024 or source.stat().st_size!=row.get('bytes') or _digest(source)!=row.get('sha256'):raise ValueError('Backup file verification failed')
        seen.add(relative)
    if 'database.sqlite3' not in seen:raise ValueError('Backup has no database')
    with closing(sqlite3.connect((backup_root/'database.sqlite3').resolve().as_uri()+'?mode=ro',uri=True)) as conn:
        if conn.execute('PRAGMA quick_check').fetchone()!=('ok',):raise ValueError('Backup database integrity failed')
    state=root/'.smelter';data.mkdir(mode=0o700);state.mkdir(mode=0o700)
    try:
        shutil.copyfile(backup_root/'database.sqlite3',data/'smelter.sqlite3')
        for row in rows:
            if row['path']=='database.sqlite3':continue
            target=state/row['path'].removeprefix('state/');target.parent.mkdir(parents=True,exist_ok=True)
            with target.open('xb') as out,(backup_root/row['path']).open('rb') as source:shutil.copyfileobj(source,out,65536)
        marker=state/'database-location.json'
        with marker.open('x') as stream:json.dump({'schema_version':1,'path':str(data/'smelter.sqlite3')},stream)
        if not inspect_database(root,integrity=True)['ready']:raise ValueError('Restored database schema is invalid')
        return {'status':'restored','database':str(data/'smelter.sqlite3'),'root':str(root),'actions_replayed':False}
    except Exception:
        shutil.rmtree(state);shutil.rmtree(data);raise


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('status','backup','restore','prune','integrity'))
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--directory',type=Path)
    parser.add_argument('--data-directory',type=Path)
    parser.add_argument('--days',type=int,default=30)
    parser.add_argument('--approve',action='store_true')
    args=parser.parse_args()
    if args.action=='status':result=status(args.root)
    elif args.action=='integrity':result=inspect_database(args.root,integrity=True)
    elif args.action=='backup':
        if not args.directory:parser.error('backup requires --directory')
        result=backup(args.root,args.directory,args.approve)
    elif args.action=='restore':
        if not args.directory or not args.data_directory:parser.error('restore requires --directory and --data-directory')
        result=restore(args.directory,args.root,args.data_directory,args.approve)
    else:
        result=plan(args.root,args.days)
        if args.approve:result=prune(args.root,result['plan_id'],True)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
