"""Controller-owned read-only access requests. Human decisions resume the same job.

This does not grant shell, writes, target execution or OS administrator rights.
Existing operator denials and exclusions require review in Settings.
"""
import copy
import hashlib
import json
from pathlib import Path
import threading
import time
from uuid import uuid4

ACCESS_WAIT_SECONDS = 300


def candidate(root, policy, folder):
    from python_tools import permissions
    from access_policy import Policy, plain
    folder = Path(permissions(root, {'inventory_root': str(folder)})['inventory_root'])
    # A quick request may add an unregistered location; it may not erase a deny.
    matches = [row for row in policy.value['locations'] if row['enabled'] and folder.is_relative_to(plain(row['path']))]
    if matches:
        policy.authorize(folder, 'read')
        return folder, policy
    value = copy.deepcopy(policy.value)
    identity = 'access_' + hashlib.sha256(str(folder).casefold().encode()).hexdigest()[:16]
    if any(row['id'] == identity for row in value['locations']):
        raise ValueError('Access location identity conflicts; review Settings')
    value['locations'].append({'id': identity, 'name': 'Approved folder: ' + folder.name, 'path': str(folder),
        'read': True, 'write': False, 'execute': False, 'operations': [], 'enabled': True,
        'exclusions': ['.git/**', '.smelter/**', 'projects/**', '.env', '.env.*',
                       '**/.env', '**/.env.*', 'credentials.json', '**/credentials.json',
                       'secrets.json', '**/secrets.json', '*.pem', '*.pfx', '*.key']})
    return folder, Policy(value)


class AccessRequests:
    def __init__(self, root, job_id, conversation_id, control, session):
        self.root, self.job_id, self.conversation_id = Path(root), job_id, conversation_id
        self.control, self.session = control, session
        self.lock = threading.RLock()
        self.changed = threading.Event()
        self.pending = None
        self.decision = None
        self.allowed = []
        self.denied = set()
        self.count = 0

    def snapshot(self):
        with self.lock:
            if not self.pending or self.decision is not None:
                return None
            row = {k:v for k,v in self.pending.items() if k != 'deadline'}
            row['expires_in_seconds'] = max(0, round(self.pending['deadline'] - time.monotonic()))
            return copy.deepcopy(row)

    def _record(self, event):
        from python_tools import _plain_path
        from storage_budget import require
        base = _plain_path(self.root / '.smelter/access-requests')
        base.mkdir(parents=True, exist_ok=True)
        path = _plain_path(base / (self.job_id + '.jsonl'))
        raw = json.dumps({'job_id': self.job_id, 'conversation_id': self.conversation_id,
                          'timestamp': time.time(), **event}) + '\n'
        require(self.root, len(raw.encode()), new_file=not path.exists())
        with path.open('a', encoding='utf-8') as stream:
            stream.write(raw)

    def request(self, arguments):
        if not isinstance(arguments, dict) or set(arguments) != {'directory', 'reason'}:
            raise ValueError('Request an absolute directory and a short reason only')
        reason = arguments['reason']
        if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 300 or any(ord(c)<32 for c in reason):
            raise ValueError('Access reason must be 1–300 plain characters')
        from access_policy import current
        self.control.check()
        policy=current(self.root)
        folder, preflight = candidate(self.root, policy, arguments['directory'])
        with self.lock:
            if any(folder.is_relative_to(path) or path.is_relative_to(folder) for path in self.denied):
                return {'status':'access_denied', 'directory':str(folder), 'read_only':True,
                        'message':'The user declined this folder for this task. Continue other work; do not ask again.'}
            if any(folder.is_relative_to(path) for path in self.allowed):
                self._activate(folder, self._effective(policy))
                return self._approved(folder, 'task')
            # Registered project read permission is already an operator decision.
            # Reuse it instead of asking the user to grant the same scope again.
            if preflight is policy:
                self._activate(folder,self._effective(policy))
                return self._approved(folder,'project')
            if self.pending:
                raise ValueError('An access request is already waiting')
            if self.count >= 8:
                raise ValueError('This task reached its eight-directory request limit')
            self.count += 1
            self.changed.clear()
            self.decision = None
            self.pending = {'id':uuid4().hex, 'job_id':self.job_id, 'directory':str(folder),
                'reason':reason.strip(), 'access':'read', 'policy_revision':current(self.root).revision,
                'deadline':time.monotonic()+ACCESS_WAIT_SECONDS}
            try:self._record({'event':'requested', **self.snapshot()})
            except (ValueError,OSError):
                self.pending=None
                raise
        start = time.monotonic()
        old_phase = self.control.phase
        try:
            with self.control.lock:
                self.control.check()
                self.control.access_wait_started = start
                self.control.phase = 'Waiting for directory access'
            while not self.changed.wait(0.1):
                self.control.check()
                if time.monotonic() >= start + ACCESS_WAIT_SECONDS:
                    with self.lock:
                        self.decision = {'status':'access_denied','directory':str(folder),'read_only':True,
                                         'message':'Access request expired. Completed work is preserved.'}
                        self._record({'event':'expired','directory':str(folder)})
                    break
            self.control.check()
            with self.lock:
                return copy.deepcopy(self.decision)
        finally:
            with self.control.lock:
                self.control.access_wait_seconds += time.monotonic() - start
                self.control.access_wait_started = None
                if not self.control.cancelled.is_set():
                    self.control.phase = old_phase
            with self.lock:
                self.pending = None

    def _activate(self, folder, policy):
        self.session.policy = policy
        self.session.grants['inventory_root'] = str(folder)
        if self.session.grants.get('rea_analysis'):
            self.session.grants['rea_root'] = str(folder)
        self.control.access_policy = policy

    def _effective(self,policy,extra=None):
        for path in [*self.allowed,*([extra] if extra is not None else [])]:
            _,policy=candidate(self.root,policy,path)
        return policy

    @staticmethod
    def _approved(folder, duration):
        return {'status':'access_granted','directory':str(folder),'duration':duration,'read_only':True,
                'message':'Continue the same task using inventory_directory, read_inventory_file, inspect_game_files or inspect_engine_archive with paths relative to this directory. No write or execute access was granted.'}

    def resolve(self, request_id, decision, expected_revision):
        if decision not in ('allow_task','allow_project','deny'):
            raise ValueError('Choose Allow for this task, Remember for this project, or Deny')
        with self.lock:
            self.control.check()
            row = self.pending
            if not row or row['id'] != request_id or self.decision is not None or time.monotonic() >= row['deadline']:
                raise ValueError('Access request is stale or no longer waiting')
            if decision == 'deny':
                result = {'status':'access_denied','directory':row['directory'],'read_only':True,
                          'message':'The user denied this folder. Continue other work without accessing it.'}
            else:
                from access_policy import current, save
                policy = current(self.root)
                if expected_revision != row['policy_revision'] or policy.revision != expected_revision:
                    raise ValueError('Access policy changed. Deny this request and request the folder again after reviewing Settings.')
                folder, extended = candidate(self.root, policy, row['directory'])
                effective=self._effective(extended,folder)
                result = self._approved(folder, 'project' if decision == 'allow_project' else 'task')
            # Reserve and record the exact human decision before changing authority.
            self._record({'event':'decision','id':request_id,'decision':decision,'directory':row['directory']})
            if decision=='deny':
                self.denied.add(Path(row['directory']))
            else:
                if decision == 'allow_project' and extended.revision != policy.revision:
                    save(self.root, extended.value, policy.revision)
                self._activate(folder, effective)
                self.allowed.append(folder)
            self.decision = result
            self.changed.set()
            return copy.deepcopy(result)
