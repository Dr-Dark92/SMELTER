import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from canonicalize_database import canonicalize
from database import select_database, chosen_database


class CanonicalDatabaseTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup); self.base = Path(tmp.name)
        self.root = self.base / 'app'; self.root.mkdir()
        self.alias = self.base / 'alias'; self.alias.mkdir()
        select_database(self.root, str(self.base / 'data'))
        self.database = chosen_database(self.root)
        self.marker = self.root / '.smelter/database-location.json'
        self.legacy = str(self.alias / '..' / 'data' / 'smelter.sqlite3')
        self.marker.write_text(json.dumps({'schema_version': 1, 'path': self.legacy}))
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute("INSERT INTO conversations(id,title) VALUES('fixture','Preserve this chat')")

    def test_preview_does_not_write_and_apply_preserves_data_with_valid_backup(self):
        raw = self.marker.read_bytes(); preview = canonicalize(self.root)
        self.assertTrue(preview['changed']); self.assertEqual(self.marker.read_bytes(), raw)
        self.assertFalse((self.root / '.smelter/database-pointer-backups').exists())
        result = canonicalize(self.root, apply=True)
        self.assertFalse(result['data_moved']); self.assertEqual(chosen_database(self.root), self.database.resolve())
        backup = Path(result['backup']); self.assertEqual((backup / 'database-location.json').read_bytes(), raw)
        with closing(sqlite3.connect(backup / 'smelter.sqlite3')) as connection:
            self.assertEqual(connection.execute('SELECT title FROM conversations').fetchone()[0], 'Preserve this chat')
            self.assertEqual(connection.execute('PRAGMA quick_check').fetchone(), ('ok',))
        self.alias.rmdir(); self.assertTrue(chosen_database(self.root).is_file())
        self.assertFalse(canonicalize(self.root, apply=True)['changed'])

    def test_missing_database_is_not_replaced(self):
        self.database.unlink(); before = self.marker.read_bytes()
        with self.assertRaisesRegex(ValueError, 'not readable/ready'): canonicalize(self.root, apply=True)
        self.assertEqual(self.marker.read_bytes(), before); self.assertFalse(self.database.exists())

    def test_live_jobs_block_pointer_changes(self):
        before = self.marker.read_bytes()
        with patch('maintenance._idle', side_effect=ValueError('Live task')):
            with self.assertRaisesRegex(ValueError, 'Live task'): canonicalize(self.root, apply=True)
        self.assertEqual(self.marker.read_bytes(), before)


if __name__ == '__main__': unittest.main()
