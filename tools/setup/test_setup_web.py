"""Unit tests for the SMELTER Vanilla setup wizard's safety gates."""
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import setup_web

class SetupWebTests(unittest.TestCase):
    def test_plan_contains_no_optional_installs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = root / "requirements.txt"
            scanner = root / "check_requirements.py"
            req.write_text("# stdlib only\n", encoding="utf-8")
            scanner.write_text("", encoding="utf-8")
            with patch.object(setup_web, "REQ", req), patch.object(setup_web, "SCANNER", scanner):
                plan = setup_web.Engine().plan()
            self.assertEqual(plan["optional_installations"], [])
            self.assertFalse(plan["downloads"])
            self.assertFalse(plan["system_package_changes"])

    def test_reject_unreviewed_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = root / "requirements.txt"
            scanner = root / "check_requirements.py"
            req.write_text("requests==2.0\n", encoding="utf-8")
            scanner.write_text("", encoding="utf-8")
            with patch.object(setup_web, "REQ", req), patch.object(setup_web, "SCANNER", scanner):
                with self.assertRaisesRegex(ValueError, "refuses third-party"):
                    setup_web.Engine().plan()

    def test_apply_requires_valid_plan_and_approval(self):
        engine = setup_web.Engine()
        with self.assertRaisesRegex(ValueError, "Explicit approval"):
            engine.apply("invalid", True)
        with self.assertRaisesRegex(ValueError, "Explicit approval"):
            engine.apply("invalid", False)


# Owned, bounded, cancellable setup children (R08). Survivors would write a marker
# file after a delay; a missing marker proves the owned process tree was killed.
SURVIVOR = "import pathlib,sys,time; time.sleep(%s); pathlib.Path(sys.argv[1]).write_text('survived')"


class SupervisedChildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.marker = Path(self.tmp.name) / "survived.txt"

    def assert_killed(self, wait=3.5):
        time.sleep(wait)
        self.assertFalse(self.marker.exists(), "an owned child survived")

    def started(self, owner, target):
        with owner.lock:
            owner.status = "running"
            owner._start(target)

    def wait_done(self, owner, limit=20):
        deadline = time.monotonic() + limit
        while owner.progress()["status"] == "running" and time.monotonic() < deadline:
            time.sleep(0.05)
        return owner.progress()

    def test_hung_child_is_killed_at_its_deadline(self):
        engine = setup_web.Engine()
        began = time.monotonic()
        with self.assertRaisesRegex(RuntimeError, "deadline"):
            engine.child([sys.executable, "-c", SURVIVOR % 2.5, str(self.marker)], 1)
        self.assertLess(time.monotonic() - began, 10)
        self.assert_killed()

    def test_descendant_holding_the_output_pipe_is_reaped(self):
        # The parent exits at once; its grandchild keeps stdout open and would survive.
        parent = ("import subprocess,sys; subprocess.Popen([sys.executable,'-c',%r,sys.argv[1]]); print('parent done', flush=True)"
                  % (SURVIVOR % 2.5))
        engine = setup_web.Engine()
        with self.assertRaisesRegex(RuntimeError, "deadline"):
            engine.child([sys.executable, "-c", parent, str(self.marker)], 1.5)
        self.assertIn("parent done", engine.progress()["lines"])
        self.assert_killed()

    def test_cancel_terminates_the_running_child(self):
        engine = setup_web.Engine()
        self.started(engine, lambda: engine.child([sys.executable, "-c", SURVIVOR % 2.5, str(self.marker)], 60))
        time.sleep(0.5)
        self.assertEqual(engine.cancel(), {"status": "cancelling"})
        result = self.wait_done(engine)
        self.assertEqual(result["status"], "cancelled")
        self.assertIn("Cancelled; owned child processes were terminated.", result["lines"])
        self.assert_killed()
        with self.assertRaisesRegex(ValueError, "Nothing is running"):
            engine.cancel()

    def test_shutdown_cancels_and_reaps_installer_children(self):
        installer = setup_web.DependencyInstaller()
        self.started(installer, lambda: installer.child([sys.executable, "-c", SURVIVOR % 2.5, str(self.marker)], 60))
        time.sleep(0.5)
        self.assertTrue(installer.shutdown(timeout=15))
        self.assertEqual(installer.progress()["status"], "cancelled")
        self.assert_killed()

    def test_output_budget_stops_a_flooding_child(self):
        engine = setup_web.Engine()
        flood = "import sys\nwhile True: sys.stdout.write('x' * 1000 + '\\n')"
        with patch.object(setup_web, "CHILD_OUTPUT", 64 * 1024):
            with self.assertRaisesRegex(ValueError, "exceeded"):
                engine.child([sys.executable, "-c", flood], 30)
        self.assertLessEqual(len(engine.progress()["lines"]), 400)

    def test_output_streams_as_bounded_lines_and_exit_code_is_reported(self):
        engine = setup_web.Engine()
        with self.assertRaisesRegex(RuntimeError, "exit code 3"):
            engine.execute([sys.executable, "-c", "print('one'); print('x' * 1000); raise SystemExit(3)"], 30)
        lines = engine.progress()["lines"]
        self.assertIn("one", lines)
        self.assertTrue(all(len(line) <= 400 for line in lines))

    def test_failed_step_reports_failed_not_cancelled(self):
        engine = setup_web.Engine()
        self.started(engine, lambda: engine.execute([sys.executable, "-c", "raise SystemExit(1)"], 30))
        self.assertEqual(self.wait_done(engine)["status"], "failed")

    def test_cancel_routes_require_the_token(self):
        import http.client
        import json
        from http.server import ThreadingHTTPServer
        server = ThreadingHTTPServer(("127.0.0.1", 0), setup_web.handler_factory(setup_web.Engine(), "t", 0))
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            def post(path, token):
                client = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                try:
                    client.request("POST", path, "{}", {"X-Smelter-Token": token})
                    response = client.getresponse()
                    return response.status, json.loads(response.read())
                finally:
                    client.close()
            self.assertEqual(post("/api/cancel", "wrong")[0], 403)
            self.assertEqual(post("/api/install-cancel", "t"), (400, {"error": "Nothing is running"}))
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
