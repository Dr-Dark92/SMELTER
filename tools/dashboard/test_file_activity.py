import json
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from file_activity import FileActivity, READABLE, MAX_TEXT
from frontend_workspace import prepare
from python_tools import ToolSession


def call(name, **arguments):
    return {'function': {'name': name, 'arguments': arguments}}


class FileActivityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / 'SMELTER'
        for relative in READABLE:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('HTML = "<style>body{color:red}</style><button>Send</button>"\n' if relative.endswith('.py') else 'const fixture = true;')
        prepare(self.root, {})

    def test_six_files_have_six_cards_and_reads_do_not_claim_writes(self):
        session = ToolSession(self.root, {'frontend_workspace': True})
        for relative in READABLE:
            result = session.execute(call('read_frontend_file', relative_path=relative))
            self.assertEqual(result['status'], 'workspace_read')
        cards = session.file_activity.snapshot()
        self.assertEqual(len(cards), 6)
        self.assertTrue(all(card['before'] and card['after'] is None and card['status'] == 'read' for card in cards))

    def test_real_write_keeps_original_and_failed_edit_keeps_last_saved(self):
        session = ToolSession(self.root, {'frontend_workspace': True})
        read = session.execute(call('read_frontend_file'))
        edit = call('replace_frontend_css', expected_sha256=read['sha256'], old_text='color:red', new_text='color:blue')
        session.file_activity.propose(edit)
        self.assertEqual(session.file_activity.snapshot()[0]['status'], 'proposed')
        result = session.execute(edit)
        self.assertEqual(result['status'], 'workspace_edited')
        saved = session.file_activity.snapshot()[0]
        self.assertIn('color:red', saved['before'])
        self.assertIn('color:blue', saved['after'])
        self.assertEqual(saved['status'], 'saved')
        result = session.execute(call('replace_frontend_css', expected_sha256='stale', old_text='color:blue', new_text='color:green'))
        self.assertEqual(result['status'], 'error')
        failed = session.file_activity.snapshot()[0]
        self.assertEqual(failed['before'], saved['before'])
        self.assertEqual(failed['after'], saved['after'])
        self.assertEqual(failed['status'], 'error')
        self.assertEqual(failed['draft'], 'color:green')

    def test_unapproved_and_arbitrary_paths_do_not_read_any_file(self):
        with patch.object(FileActivity, '_snapshot', side_effect=AssertionError('must not read')):
            disabled = FileActivity(self.root)
            disabled.begin(call('read_frontend_file'))
            enabled = FileActivity(self.root, True)
            enabled.begin(call('read_frontend_file', relative_path='../../secret'))
            enabled.begin(call('some_external_mcp_editor', path='/etc/passwd'))
        self.assertEqual(disabled.snapshot(), [])
        self.assertEqual(enabled.snapshot(), [])

    def test_proposal_stop_is_unconfirmed_and_snapshot_is_independent(self):
        activity = FileActivity(self.root, True)
        activity.propose(call('replace_frontend_css', new_text='draft'))
        snapshot = activity.snapshot()
        snapshot[0]['status'] = 'saved'
        activity.settle(True)
        self.assertEqual(activity.snapshot()[0]['status'], 'stopped')
        self.assertIsNone(activity.snapshot()[0]['after'])

    def test_large_previews_are_bounded_and_labeled(self):
        target = self.root.with_name('SMELTERV2') / READABLE[1]
        target.write_text('x' * (MAX_TEXT + 100))
        activity = FileActivity(self.root, True)
        activity.begin(call('read_frontend_file', relative_path=READABLE[1]))
        card = activity.snapshot()[0]
        self.assertEqual(len(card['before']), MAX_TEXT)
        self.assertTrue(card['before_truncated'])

    def test_file_cards_persist_in_actual_chat_execution_record(self):
        from chat_inference import ask
        from chats import create_chat, read_chat
        from database import select_database
        from frontend_workspace import read_file
        select_database(self.root, str(self.root.parent / 'source-data'))
        cid = create_chat(self.root, 'File activity persistence')['id']
        sha = read_file(self.root, {})['sha256']
        replies = iter([
            {'content':'', 'tool_calls':[call('read_frontend_file')]},
            {'content':'', 'tool_calls':[call('replace_frontend_css', expected_sha256=sha, old_text='color:red', new_text='color:blue')]},
            {'content':'CSS saved.'}])
        def opener(*args, **kwargs):
            return io.BytesIO(json.dumps({'message':next(replies), 'done_reason':'stop'}).encode())
        ask(self.root, cid, 'Update the CSS', opener=opener, tool_permissions={'frontend_workspace':True})
        record = read_chat(self.root, cid)['messages'][-1]['execution']['files']
        self.assertEqual(len(record), 1)
        self.assertEqual(record[0]['status'], 'saved')
        self.assertIn('color:red', record[0]['before'])
        self.assertIn('color:blue', record[0]['after'])
