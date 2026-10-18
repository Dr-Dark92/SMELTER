import json
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from database import chosen_database, inspect_database, select_database

class DatabaseBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "checkout"
        (self.root / ".smelter").mkdir(parents=True)
        (self.root / ".smelter" / "extensions.json").write_text('{"schema_version":1,"enabled":[]}')
        self.destination = self.base / "data"
    def test_first_boot_and_import(self):
        self.assertEqual(inspect_database(self.root)["status"], "setup_required")
        result = select_database(self.root, str(self.destination))
        self.assertTrue(result["legacy_files_preserved"])
        self.assertEqual(inspect_database(self.root)["status"], "ready")
        with closing(sqlite3.connect(chosen_database(self.root))) as conn:
            row = conn.execute("SELECT payload FROM config_snapshots WHERE name='extensions.json'").fetchone()
        self.assertEqual(json.loads(row[0])["enabled"], [])
    def test_refuse_reselection(self):
        select_database(self.root, str(self.destination))
        with self.assertRaisesRegex(ValueError, "already selected"):
            select_database(self.root, str(self.base / "another"))
    def test_refuse_checkout(self):
        with self.assertRaisesRegex(ValueError, "outside"):
            select_database(self.root, str(self.root / "projects"))
    def test_missing_database_blocks(self):
        select_database(self.root, str(self.destination))
        chosen_database(self.root).unlink()
        self.assertFalse(inspect_database(self.root)["ready"])

if __name__ == "__main__":
    unittest.main()
