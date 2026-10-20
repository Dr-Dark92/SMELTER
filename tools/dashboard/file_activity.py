"""Bounded, controller-owned file previews for approved workspace operations."""
import copy
import json
import threading
from pathlib import Path

MAX_FILES = 12
MAX_TEXT = 128 * 1024
READABLE = ('tools/dashboard/dashboard.py', 'tools/dashboard/model_preview.js',
            'tools/dashboard/model_animations.js', 'tools/dashboard/mcp_ui.js',
            'tools/dashboard/session_auth.js', 'tools/dashboard/chat_renderer.js')


class FileActivity:
    def __init__(self, root, enabled=False):
        self.root = Path(root)
        self.enabled = enabled
        self.lock = threading.RLock()
        self.cards = {}

    def _call(self, call):
        if not self.enabled or not isinstance(call, dict):
            return None
        function = call.get('function', {})
        if not isinstance(function, dict):
            return None
        name, arguments = function.get('name'), function.get('arguments', {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except ValueError:
                return None
        if not isinstance(arguments, dict) or name not in ('read_frontend_file', 'replace_frontend_css'):
            return None
        relative = arguments.get('relative_path', READABLE[0]) if name == 'read_frontend_file' else READABLE[0]
        area = arguments.get('area', 'destination') if name == 'read_frontend_file' else 'destination'
        if relative not in READABLE or area not in ('source', 'destination'):
            return None
        return name, arguments, area, relative

    def _card(self, area, relative):
        key = area + ':' + relative
        if key not in self.cards:
            if len(self.cards) >= MAX_FILES:
                return None
            self.cards[key] = {'id': key, 'path': relative, 'area': area,
                'status': 'reading', 'before': None, 'after': None, 'draft': '',
                'before_truncated': False, 'after_truncated': False,
                'error': '', 'saved_edits': 0}
        return self.cards[key]

    def _snapshot(self, area, relative):
        from frontend_workspace import target_path, _load
        from python_tools import _plain_path
        if area == 'destination':
            _load(self.root)
        base = self.root if area == 'source' else target_path(self.root)
        path = _plain_path(base / relative)
        with path.open('r', encoding='utf-8') as stream:
            text = stream.read(MAX_TEXT + 1)
        return text[:MAX_TEXT], len(text) > MAX_TEXT

    def propose(self, call):
        parsed = self._call(call)
        if not parsed or parsed[0] != 'replace_frontend_css':
            return
        _, arguments, area, relative = parsed
        draft = arguments.get('new_text')
        if not isinstance(draft, str):
            return
        with self.lock:
            card = self._card(area, relative)
            if card is not None:
                card.update(status='proposed', draft=draft[:MAX_TEXT], error='')

    def begin(self, call):
        parsed = self._call(call)
        if not parsed:
            return
        name, _, area, relative = parsed
        self.propose(call)
        with self.lock:
            card = self._card(area, relative)
            if card is None:
                return
            if card['before'] is None:
                try:
                    card['before'], card['before_truncated'] = self._snapshot(area, relative)
                except (OSError, ValueError, UnicodeError) as exc:
                    card['error'] = 'Original preview unavailable: ' + str(exc)[:300]
            card['status'] = 'writing' if name == 'replace_frontend_css' else 'reading'

    def finish(self, call, result):
        parsed = self._call(call)
        if not parsed:
            return
        name, _, area, relative = parsed
        with self.lock:
            card = self._card(area, relative)
            if card is None:
                return
            if result.get('status') == 'workspace_edited' and name == 'replace_frontend_css':
                card.update(status='saved', saved_edits=card['saved_edits'] + 1, error='')
                try:
                    card['after'], card['after_truncated'] = self._snapshot(area, relative)
                except (OSError, ValueError, UnicodeError) as exc:
                    card['after'] = None
                    card['error'] = 'Saved by tool; updated preview unavailable: ' + str(exc)[:300]
            elif result.get('status') == 'workspace_read':
                card['status'] = 'saved' if card['saved_edits'] else 'read'
            else:
                card.update(status='error', error=str(result.get('error', 'File tool did not confirm success'))[:1000])

    def settle(self, cancelled=False):
        with self.lock:
            for card in self.cards.values():
                if card['status'] in ('proposed', 'writing', 'reading'):
                    card['status'] = 'stopped' if cancelled else 'unconfirmed'

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(list(self.cards.values()))
