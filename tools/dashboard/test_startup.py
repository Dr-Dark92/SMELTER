import tempfile
import unittest
from pathlib import Path
from database import select_database
from startup import startup_report

class StartupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.root = base / "checkout"
        (self.root / ".smelter").mkdir(parents=True)
        self.data = base / "data"
    def test_requires_database_selection(self):
        report = startup_report(self.root, lambda: {"tools":[]}, lambda a,b: {"status":"offline"})
        self.assertFalse(report["ready"])
        self.assertEqual(report["status"], "setup_required")
    def test_offline_ollama_does_not_block(self):
        select_database(self.root, str(self.data))
        report = startup_report(self.root, lambda: {"tools":[{"name":"ollama","status":"missing"}]}, lambda a,b: {"status":"offline"})
        self.assertTrue(report["ready"])
        self.assertEqual(report["services"]["opencode"], "not_started")
    def test_corrupt_configuration_blocks(self):
        select_database(self.root, str(self.data))
        from database import chosen_database
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(chosen_database(self.root))) as conn, conn:
            conn.execute("INSERT INTO config_snapshots(name,payload) VALUES(?,?)", ("extensions.json", '{"schema_version":1,"enabled":["invalid"]}'))
        report = startup_report(self.root, lambda: {"tools":[]}, lambda a,b: {"status":"offline"})
        self.assertFalse(report["ready"])

if __name__ == "__main__":
    unittest.main()
