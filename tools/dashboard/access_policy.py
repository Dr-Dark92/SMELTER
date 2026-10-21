"""Central application path policy. Registered operations only; not an OS sandbox."""
import copy
import fnmatch
import hashlib
import json
import re
from pathlib import Path

OPERATIONS = ('tests', 'preview', 'rea', 'archive', 'media', 'blender')
NAME = 'access_policy.json'


def defaults(root):
    root = Path(root).resolve()
    return {'schema_version': 1, 'locations': [
        {'id':'source', 'name':'Original source', 'path':str(root), 'read':True, 'write':False, 'execute':False,
         'operations':[], 'exclusions':['.git/**', '.smelter/**', 'projects/**'], 'enabled':True},
        {'id':'development', 'name':'Development workspace', 'path':str(root.with_name(root.name+'V2')),
         'read':True, 'write':True, 'execute':True, 'operations':['tests','preview'],
         'exclusions':['.git/**', '.smelter/**', 'projects/**'], 'enabled':True},
        {'id':'diagnostics', 'name':'New diagnostic reports', 'path':str(root/'diagnostics'),
         'read':True, 'write':True, 'execute':False, 'operations':[], 'exclusions':[], 'enabled':True}]}


def plain(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or str(path).startswith(('\\\\','//')):
        raise ValueError('Access locations must be absolute local paths without traversal')
    if any(':' in part for part in path.parts[1:]):
        raise ValueError('Alternate data streams are not allowed')
    from python_tools import _plain_path
    return _plain_path(path).resolve()


def validate(value):
    if not isinstance(value, dict) or set(value) != {'schema_version','locations'} or type(value['schema_version']) is not int or value['schema_version'] != 1:
        raise ValueError('Access policy requires schema_version=1 and locations')
    rows = value['locations']
    if not isinstance(rows, list) or len(rows)>32:
        raise ValueError('Configure up to 32 access locations')
    ids, paths = set(), set()
    for row in rows:
        if not isinstance(row,dict) or set(row) != {'id','name','path','read','write','execute','operations','exclusions','enabled'}:
            raise ValueError('Invalid access-location fields')
        if not isinstance(row['id'],str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,47}',row['id']) or row['id'] in ids:
            raise ValueError('Location IDs must be distinct plain identifiers')
        ids.add(row['id'])
        if not isinstance(row['name'],str) or not row['name'].strip() or len(row['name'])>100:
            raise ValueError('Provide a location name')
        if not isinstance(row['path'],str) or not row['path'] or len(row['path'])>1000:
            raise ValueError('Provide an absolute local path')
        path=plain(row['path'])
        if path.parent==path:
            raise ValueError('Whole-drive or filesystem-root grants are not allowed')
        key=str(path).casefold()
        if key in paths:raise ValueError('Duplicate access location')
        paths.add(key)
        if any(type(row[k]) is not bool for k in ('read','write','execute','enabled')):
            raise ValueError('Access flags must be boolean')
        if not isinstance(row['operations'],list) or any(x not in OPERATIONS for x in row['operations']) or len(set(row['operations']))!=len(row['operations']):
            raise ValueError('Choose registered execution operations only')
        if row['operations'] and not row['execute']:
            raise ValueError('Operations require the execute flag')
        if not isinstance(row['exclusions'],list) or len(row['exclusions'])>32 or any(not isinstance(x,str) or not x or len(x)>200 or x.startswith(('/','\\')) or '\\' in x or ':' in x or '..' in x.split('/') for x in row['exclusions']):
            raise ValueError('Exclusions must be relative forward-slash patterns')
    return value


def load(root):
    from config_store import load_config
    return load_config(Path(root), NAME)


def save(root,value,expected_revision=None):
    from config_store import save_config,_db
    validate(value)
    if expected_revision is None:save_config(Path(root),NAME,value)
    else:
        if not isinstance(expected_revision,str) or not re.fullmatch(r'[a-f0-9]{64}',expected_revision):raise ValueError('Invalid expected policy revision')
        import sqlite3
        from contextlib import closing
        # Serialize the revision comparison and write across dashboard processes.
        with closing(sqlite3.connect(_db(Path(root)),timeout=5)) as conn,conn:
            conn.execute('BEGIN IMMEDIATE')
            row=conn.execute('SELECT payload FROM config_snapshots WHERE name=?',(NAME,)).fetchone()
            stored=Policy(json.loads(row[0]) if row else defaults(root))
            if stored.revision!=expected_revision:raise ValueError('Access policy changed in another window. Revert/reload before applying your draft.')
            conn.execute('INSERT INTO config_snapshots(name,payload,imported_at) VALUES(?,?,CURRENT_TIMESTAMP) ON CONFLICT(name) DO UPDATE SET payload=excluded.payload,imported_at=CURRENT_TIMESTAMP',(NAME,json.dumps(value)))
    return Policy(value).report()


class Policy:
    def __init__(self,value):
        self.value=copy.deepcopy(validate(value))
        self.revision=hashlib.sha256(json.dumps(self.value,sort_keys=True).encode()).hexdigest()

    def authorize(self,path,action,operation=None):
        if action not in ('read','write','execute'):raise ValueError('Unknown access action')
        target=plain(path)
        matches=[]
        for row in self.value['locations']:
            if not row['enabled']:continue
            base=plain(row['path'])
            if target==base or target.is_relative_to(base):matches.append((len(base.parts),row,base))
        if not matches:raise ValueError('Access denied: location is not registered: '+str(target))
        _,row,base=max(matches,key=lambda x:x[0])
        rel=target.relative_to(base).as_posix()
        prefixes=['/'.join(target.relative_to(base).parts[:i]) for i in range(1,len(target.relative_to(base).parts)+1)]
        excluded=any(fnmatch.fnmatchcase(rel,p) or any(fnmatch.fnmatchcase(x,p) or x==p.removesuffix('/**') for x in prefixes) for p in row['exclusions'])
        if excluded or not row[action] or action=='execute' and operation not in row['operations']:
            raise ValueError('Access denied: '+action+((' / '+str(operation)) if operation else '')+' at '+str(target))
        return target

    def report(self):
        return {**copy.deepcopy(self.value),'revision':self.revision,
                'enforcement':'Application path checks for registered built-ins and OpenCode read rules; not an OS sandbox',
                'external_mcp':'blocked: arbitrary external servers require a confined runner',
                'operations':list(OPERATIONS)}


def current(root):
    from database import chosen_database
    return Policy(load(root) if chosen_database(Path(root)) is not None else defaults(root))


def check_grants(root,grants,policy):
    for key in ('inventory_root','rea_root'):
        if grants.get(key):policy.authorize(grants[key],'read')
    if grants.get('write_diagnostics'):policy.authorize(Path(root).resolve()/'diagnostics','write')
    if grants.get('frontend_workspace'):
        policy.authorize(Path(root).resolve()/'tools','read')
        policy.authorize(Path(root).resolve().with_name(Path(root).resolve().name+'V2'),'write')
    return grants


from contextvars import ContextVar
from contextlib import contextmanager
_active = ContextVar('smelter_access_policy', default=None)

@contextmanager
def using(policy):
    token=_active.set(policy)
    try:yield
    finally:_active.reset(token)

def require(path,action,operation=None):
    policy=_active.get()
    if policy is not None:policy.authorize(path,action,operation)

def allowed(path,action):
    try:require(path,action);return True
    except ValueError:return False
