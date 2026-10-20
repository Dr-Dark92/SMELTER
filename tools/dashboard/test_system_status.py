import tempfile
import unittest
from pathlib import Path
from database import select_database
from system_status import system_status

class SystemStatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "checkout"
        (self.root / ".smelter").mkdir(parents=True)
    def test_setup_state(self):
        result = system_status(self.root)
        self.assertEqual(result["database"]["status"], "setup_required")
        self.assertGreater(result["storage"]["total_bytes"], 0)
        self.assertTrue(result["read_only"])
    def test_configured_location(self):
        select_database(self.root, str(Path(self.tmp.name) / "data"))
        result = system_status(self.root)
        self.assertEqual(result["database"]["status"], "ready")
        self.assertTrue(result["database"]["path"].endswith("smelter.sqlite3"))
    def test_telemetry_states_are_explicit(self):
        result = system_status(self.root)
        for field in ("cpu", "memory", "gpu"):
            self.assertIn(result[field]["status"], ("ready", "sampling", "unavailable"))
        self.assertIsNone(result['gpu']['utilization_percent'])

if __name__ == "__main__":
    unittest.main()

