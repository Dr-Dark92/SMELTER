import tempfile
import unittest
from pathlib import Path
from uuid import uuid4
from reports import attach_inputs, list_reports, save_report, validate_inputs

class ReportTests(unittest.TestCase):
    def test_existing_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "sample.txt"
            path.write_text("test", encoding="utf-8")
            self.assertEqual(validate_inputs([str(path)])[0]["status"], "valid")
    def test_missing_file_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            report = attach_inputs({"status": "ready"}, [str(Path(d) / "missing")])
            self.assertEqual(report["status"], "blocked")
            self.assertEqual(report["output_validation"]["status"], "not_applicable")
    def test_reject_relative_and_many_inputs(self):
        with self.assertRaises(ValueError):
            validate_inputs(["relative.txt"])
        with self.assertRaises(ValueError):
            validate_inputs(["/tmp"] * 17)
    def test_report_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            report = {"run_id": str(uuid4()), "mode": "dry_run", "timestamp_utc": "2026-10-18T12:00:00Z", "status": "ready"}
            save_report(Path(d), report)
            self.assertEqual(list_reports(Path(d))[0]["run_id"], report["run_id"])
            with self.assertRaises(FileExistsError):
                save_report(Path(d), report)
    def test_ignores_invalid_report(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "random.json").write_text("{}", encoding="utf-8")
            self.assertEqual(list_reports(Path(d)), [])

if __name__ == "__main__":
    unittest.main()
