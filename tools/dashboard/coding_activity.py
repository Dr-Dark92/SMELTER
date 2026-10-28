"""Controller file cards for coding proposals and confirmed applied bytes."""
import copy
import json
import threading

from access_policy import using

MAX_TEXT = 16000


class CodingActivity:
    def __init__(self, root, frontend, policy):
        self.root, self.frontend, self.policy = root, frontend, policy
        self.cards = {}
        self.lock = threading.RLock()

    def _changes(self, call):
        function = call.get('function', {}) if isinstance(call, dict) else {}
        if not isinstance(function, dict):return []
        name, args = function.get('name'), function.get('arguments', {})
        if isinstance(args, str):
            try:args = json.loads(args)
            except ValueError:return []
        if not isinstance(args, dict):return []
        try:
            from coding_workspace import load, proposal, relative_path, _file, MAX_FILE, edit_changes, read_checkpoint
            with using(self.policy):
                sid = args.get('workspace_id')
                if name not in ('read_coding_file','propose_coding_patch','propose_coding_edit','propose_coding_edits','propose_coding_restore','apply_coding_patch'):return []
                _, target = load(self.root, sid)
                if name == 'read_coding_file':
                    changes = [{'relative_path': args.get('relative_path')}]
                elif name == 'propose_coding_patch':
                    changes = args.get('changes', [])
                elif name == 'propose_coding_edits':
                    changes = edit_changes(target, args.get('changes'))
                elif name == 'propose_coding_edit':
                    changes = edit_changes(target,[{'relative_path':args.get('relative_path'),'expected_sha256':args.get('expected_sha256'),
                        'edits':[{'old_text':args.get('old_text'),'new_text':args.get('new_text')}]}])
                elif name == 'propose_coding_restore':
                    paths = args.get('relative_paths', [])
                    if not isinstance(paths, list) or not 1 <= len(paths) <= 6:return []
                    changes = []
                    for relative in paths:
                        relative_path(relative, edit=True)
                        if 'checkpoint_sha256' in args:
                            raw = read_checkpoint(self.root, sid, relative, args['checkpoint_sha256'])
                            changes.append({'relative_path': relative, 'content': raw.decode('utf-8')})
                            continue
                        source = _file(self.root, relative)
                        if not source.is_file() or source.stat().st_size > MAX_FILE:return []
                        changes.append({'relative_path': relative, 'content': source.read_bytes().decode('utf-8')})
                else:
                    _, plan = proposal(self.root, sid, args.get('proposal_id'))
                    changes = plan['changes']
                if not isinstance(changes, list) or len(changes) > 6:return []
                result = []
                for change in changes:
                    relative = relative_path(change['relative_path'])
                    path = _file(target, relative)
                    if path.is_file() and path.stat().st_size > MAX_FILE:continue
                    text = path.read_bytes().decode('utf-8') if path.is_file() else ''
                    result.append((name, sid, relative, change.get('content', ''), text))
                return result
        except (ValueError, OSError, UnicodeError, KeyError, TypeError):
            return []

    def _card(self, sid, relative, before):
        key = 'coding:' + sid + ':' + relative
        if key not in self.cards and len(self.cards) < 6:
            self.cards[key] = {'id': key, 'workspace_id': sid, 'path': relative, 'area': 'coding',
                'status': 'reading', 'before': before[:MAX_TEXT], 'after': None, 'draft': '',
                'before_truncated': len(before) > MAX_TEXT, 'after_truncated': False,
                'error': '', 'saved_edits': 0, 'kind': 'code'}
        return self.cards.get(key)

    def propose(self, call):
        self.frontend.propose(call)
        with self.lock:
            for name, sid, relative, content, text in self._changes(call):
                if name in ('propose_coding_patch','propose_coding_edit','propose_coding_edits','propose_coding_restore') and isinstance(content, str):
                    card = self._card(sid, relative, text)
                    if card is not None:card.update(status='proposed', draft=content[:MAX_TEXT], error='')

    def begin(self, call):
        self.frontend.begin(call)
        self.propose(call)
        with self.lock:
            for name, sid, relative, content, text in self._changes(call):
                card = self._card(sid, relative, text)
                if card is not None:
                    card['status'] = 'writing' if name == 'apply_coding_patch' else 'reading' if name == 'read_coding_file' else 'proposed'
                    if isinstance(content, str) and name != 'read_coding_file':card['draft'] = content[:MAX_TEXT]

    def finish(self, call, result):
        self.frontend.finish(call, result)
        with self.lock:
            for name, sid, relative, _, text in self._changes(call):
                card = self._card(sid, relative, text)
                if card is None:continue
                if name == 'apply_coding_patch' and result.get('status') == 'coding_patch_applied':
                    card.update(status='saved', after=text[:MAX_TEXT], after_truncated=len(text)>MAX_TEXT,
                                saved_edits=card['saved_edits'] + (0 if result.get('reused') else 1), error='')
                elif name in ('propose_coding_patch','propose_coding_edit','propose_coding_edits','propose_coding_restore') and result.get('status') == 'coding_patch_proposed':
                    card['status'] = 'proposed'
                elif name == 'read_coding_file' and result.get('status') == 'coding_file_read':
                    card['status'] = 'saved' if card['saved_edits'] else 'read'
                else:
                    card.update(status='error', error=str(result.get('error','No confirmed edit'))[:1000])

    def settle(self, cancelled=False):
        self.frontend.settle(cancelled)
        with self.lock:
            for card in self.cards.values():
                if card['status'] in ('reading','writing'):
                    card['status'] = 'stopped' if cancelled else 'unconfirmed'

    def snapshot(self):
        with self.lock:
            return (self.frontend.snapshot() + copy.deepcopy(list(self.cards.values())))[:12]
