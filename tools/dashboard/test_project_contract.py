import tempfile
import unittest
from pathlib import Path
from project_contract import HANDOVER_HEADINGS, inspect_project

class ProjectContractTests(unittest.TestCase):
    def test_missing_docs_are_reported_without_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            status = inspect_project(folder)
            self.assertFalse(status["handover_ready"])
            self.assertEqual(sorted(Path(folder).iterdir()), [])
    def test_complete_handover(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "README.md").write_text("# Demo", encoding="utf-8")
            (root / "HANDOVER.md").write_text("\n".join("## " + x for x in HANDOVER_HEADINGS), encoding="utf-8")
            status = inspect_project(folder)
            self.assertTrue(status["handover_ready"])
    def test_invalid_path(self):
        with self.assertRaises(FileNotFoundError):
            inspect_project("nonexistent-smelter-project-test-xyz")

if __name__ == "__main__":
    unittest.main()
