"""Real temp files/SQLite with mocked Ollama transport; no game files or live AI."""
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from chat_inference import ask
from chats import create_chat, read_chat
from database import select_database
from python_tools import ToolSession, inventory, permissions, write_markdown, MAX_CALLS


def call(name, **arguments):
    return {"function": {"name": name, "arguments": arguments}}


class PythonToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "checkout"
        self.root.mkdir()
        self.game = self.base / "game"
        self.game.mkdir()
        (self.game / "sample.pak").write_bytes(b"fixture")
        (self.game / "textures").mkdir()
        (self.game / "textures" / "sample.dds").write_bytes(b"dds")
        select_database(self.root, str(self.base / "data"))
        from access_policy import defaults, save
        policy = defaults(self.root)
        policy['locations'].append({'id':'game','name':'Fixture game','path':str(self.game), 'read':True,'write':False,'execute':False,'operations':[],'exclusions':[],'enabled':True})
        save(self.root, policy)
        self.cid = create_chat(self.root, "Python tools")["id"]
        self.grants = permissions(self.root, {"inventory_root": str(self.game), "write_diagnostics": True})

    def transport(self, *responses):
        self.requests = []
        sequence = iter(responses)

        def opener(request, timeout):
            self.requests.append(json.loads(request.data))
            reply = next(sequence)
            if isinstance(reply, Exception):
                raise reply
            return io.BytesIO(json.dumps({"message": reply, "done_reason": "stop"}).encode())
        return opener

    def test_default_chat_still_has_no_tools(self):
        result = ask(self.root, self.cid, "Hello", opener=self.transport({"content": "Hello"}))
        self.assertNotIn("tools", self.requests[0])
        self.assertFalse(result["tools_executed"])
        self.assertEqual(result["tool_events"], [])

    def test_plain_text_claim_cannot_substitute_for_real_file_write(self):
        result = ask(self.root, self.cid, "Save", tool_permissions={"write_diagnostics": True},
                     opener=self.transport({"content": "I saved your file."}))
        self.assertFalse((self.root / "diagnostics").exists())
        self.assertIn("No tool calls were received", result["reply"])
        self.assertFalse(result["tools_executed"])

    def test_unapproved_model_calls_never_execute(self):
        response = {"content": "", "tool_calls": [call("write_diagnostic_markdown", filename="bad.md", content="No") ]}
        result = ask(self.root, self.cid, "Save", opener=self.transport(response))
        self.assertFalse((self.root / "diagnostics").exists())
        self.assertFalse(result["tools_executed"])
        self.assertIn("No Python tools were approved", result["reply"])

    def test_inventory_scoped_and_reports_partial_depth(self):
        report = inventory(self.grants, {"relative_path": ".", "max_depth": 0})
        self.assertEqual(report["files_observed"], 1)
        self.assertTrue(report["truncated"])
        self.assertFalse(report["scan_complete"])
        self.assertIn("depth_limit", report["scan_stop_reasons"])
        complete = inventory(self.grants, {"relative_path": "."})
        self.assertEqual(complete["files_observed"], 2)
        self.assertEqual(complete["extensions_observed"], {".pak": 1, ".dds": 1})
        self.assertTrue(complete["scan_complete"])
        self.assertFalse(complete["entries_truncated"])

    def test_completed_scan_with_short_sample_does_not_claim_incomplete_counts(self):
        for index in range(200):
            (self.game / f"sample-{index:03d}.oppc").touch()
        report = inventory(self.grants, {"relative_path": "."})
        self.assertTrue(report["scan_complete"])
        self.assertEqual(report["scan_stop_reasons"], [])
        self.assertEqual(report["files_observed"], 202)
        self.assertEqual(report["extensions_observed"][".oppc"], 200)
        self.assertTrue(report["entries_truncated"])
        self.assertLess(report["returned_entries"], report["observed_entries"])
        self.assertEqual(report["returned_entries"], len(report["entries"]))
        self.assertLessEqual(len(json.dumps(report, ensure_ascii=True)), 8000)
        self.assertIn("response_size_limit", report["listing_limit_reasons"])

    def test_scan_entry_limit_is_distinct_from_response_limit(self):
        with patch("python_tools.MAX_VISITED", 1):
            report = inventory(self.grants, {"relative_path": "."})
        self.assertFalse(report["scan_complete"])
        self.assertIn("entry_scan_limit", report["scan_stop_reasons"])

    def test_inventory_rejects_escapes_and_invalid_args(self):
        for relative in ("../checkout", str(self.root), "C:/Windows", "..\\checkout", "//server/share"):
            with self.subTest(path=relative), self.assertRaises(ValueError):
                inventory(self.grants, {"relative_path": relative})
        for args in ({"relative_path": ".", "max_depth": True}, {"relative_path": ".", "command": "whoami"}):
            with self.assertRaises(ValueError):
                inventory(self.grants, args)

    def test_projects_scope_and_parent_rejected(self):
        folder = self.root / "projects"
        folder.mkdir()
        for path in (folder, self.root, self.base):
            with self.assertRaises(ValueError):
                permissions(self.root, {"inventory_root": str(path)})

    def test_invalid_permissions_fail_before_model_request(self):
        for grant in ({"write_diagnostics": "yes"}, {"inventory_root": "."}, {"shell": True}):
            with self.subTest(grant=grant), self.assertRaises(ValueError):
                ask(self.root, self.cid, "Hello", opener=lambda *a, **k: self.fail("Called model"), tool_permissions=grant)

    def test_write_lf_hash_and_collision_preserve_original(self):
        args = {"filename": "handover.md", "content": "# Report\r\nVerified\r\n"}
        first = write_markdown(self.root, self.grants, args)
        second = write_markdown(self.root, self.grants, args)
        self.assertNotEqual(first["path"], second["path"])
        self.assertTrue(second["path"].endswith("handover_01.md"))
        raw = Path(first["path"]).read_bytes()
        self.assertEqual(raw, b"# Report\nVerified\n")
        self.assertEqual(first["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertFalse(first["content_verified"])

    def test_write_denied_traversal_reserved_size_and_extra_args(self):
        with self.assertRaises(ValueError):
            write_markdown(self.root, permissions(self.root), {"filename": "x.md", "content": "x"})
        for name in ("../x.md", "C:/x.md", "x.ps1", "sub/x.md", "CON.md", "x.md:stream"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                write_markdown(self.root, self.grants, {"filename": name, "content": "x"})
        with self.assertRaises(ValueError):
            write_markdown(self.root, self.grants, {"filename": "x.md", "content": "x" * 32769})
        with self.assertRaises(ValueError):
            write_markdown(self.root, self.grants, {"filename": "x.md", "content": "x", "overwrite": True})

    def test_symlink_and_windows_reparse_rejected(self):
        with patch("python_tools._linked", return_value=True):
            with self.assertRaises(ValueError):
                permissions(self.root, {"inventory_root": str(self.game)})
            with self.assertRaises(ValueError):
                write_markdown(self.root, self.grants, {"filename": "x.md", "content": "x"})
        link = self.game / "escape"
        try:
            link.symlink_to(self.root, target_is_directory=True)
        except (OSError, NotImplementedError):
            return  # Windows may require developer mode/admin for symlink creation.
        report = inventory(self.grants, {"relative_path": "."})
        self.assertEqual(report["skipped_links"], 1)
        with self.assertRaises(ValueError):
            inventory(self.grants, {"relative_path": "escape"})

    def test_inventory_then_write_loop_receipts_audit_and_history(self):
        opener = self.transport(
            {"content": "", "tool_calls": [call("inventory_directory", relative_path=".")]},
            {"content": "", "tool_calls": [call("write_diagnostic_markdown", filename="handover.md", content="# Test\n2 observed files; no content inspected.")]},
            {"content": "Report saved."})
        result = ask(self.root, self.cid, "Inventory and write a report", opener=opener, tool_permissions=self.grants)
        self.assertTrue(result["tools_executed"])
        self.assertEqual(len(result["tool_events"]), 2)
        tool_message = self.requests[1]["messages"][-1]
        self.assertEqual(tool_message["role"], "tool")
        self.assertEqual(tool_message["tool_name"], "inventory_directory")
        self.assertEqual(json.loads(tool_message["content"])["files_observed"], 2)
        self.assertIn("SHA256", result["reply"])
        audit = [json.loads(line) for line in Path(result["tool_audit_path"]).read_text().splitlines()]
        self.assertEqual([x["phase"] for x in audit], ["requested", "result", "requested", "result"])
        self.assertEqual(read_chat(self.root, self.cid)["messages"][-1]["content"], result["reply"])
        ask(self.root, self.cid, "Hello again", opener=self.transport({"content": "Hello"}))
        self.assertNotIn("tools", self.requests[0])  # approval did not persist

    def test_duplicate_write_returns_receipt_without_second_file(self):
        repeated = {"content": "", "tool_calls": [call("write_diagnostic_markdown", filename="handover.md", content="# Saved")]}
        result = ask(self.root, self.cid, "Save", tool_permissions={"write_diagnostics": True},
                     opener=self.transport(repeated, repeated, {"content": "Done"}))
        self.assertEqual(len(list((self.root / "diagnostics").glob("*.md"))), 1)
        self.assertTrue(result["tool_events"][1]["reused"])
        self.assertFalse(result["tool_events"][1]["executed"])

    def test_failed_followup_after_write_retains_receipt_and_file(self):
        response = {"content": "", "tool_calls": [call("write_diagnostic_markdown", filename="saved.md", content="# Saved")]}
        result = ask(self.root, self.cid, "Save", tool_permissions={"write_diagnostics": True},
                     opener=self.transport(response, URLError("offline")))
        self.assertTrue((self.root / "diagnostics" / "saved.md").is_file())
        self.assertIn("Model follow-up failed", result["reply"])
        self.assertIn("SHA256", result["reply"])
        self.assertTrue(Path(result["tool_audit_path"]).is_file())

    def test_call_limit_bounds_repeated_or_unregistered_calls(self):
        response = {"content": "", "tool_calls": [call("run_python", code="raise Exception()") ]}
        result = ask(self.root, self.cid, "Do work", tool_permissions={"write_diagnostics": True},
                     opener=self.transport(*([response] * (MAX_CALLS + 1))))
        self.assertEqual(len(result["tool_events"]), MAX_CALLS)
        self.assertTrue(all(e["result"]["status"] == "error" for e in result["tool_events"]))
        self.assertFalse(result["tools_executed"])
        self.assertIn("call limit reached", result["reply"])
        self.assertNotIn("tools", self.requests[-1])

    def test_malformed_function_is_denied_without_crashing(self):
        session = ToolSession(self.root, {"write_diagnostics": True})
        for malformed in ({"function": "not-object"}, {"function": {"name": [], "arguments": {}}}):
            self.assertEqual(session.execute(malformed)["status"], "error")

    def test_tools_ui_has_explicit_one_message_controls(self):
        from dashboard import HTML
        HTML += Path(__file__).with_name("dashboard_shell.js").read_text(encoding="utf-8")
        self.assertIn("approveInventory", HTML)
        self.assertIn("approveDiagnostics", HTML)
        self.assertIn("readGrant.checked=false;writeGrant.checked=false", HTML)
        self.assertIn("tool_permissions:toolPermissions", HTML)

    def test_http_chat_route_forwards_explicit_grants(self):
        from dashboard import handler
        from http.server import ThreadingHTTPServer
        from http.client import HTTPConnection
        from threading import Thread
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler("test-token"))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        try:
            with patch("dashboard.JOBS.start", return_value={"id": "job-fixture", "state": "running"}) as mocked:
                body = json.dumps({"action": "ask", "id": self.cid, "content": "Inspect", "tool_permissions": self.grants})
                connection.request("POST", "/api/chats", body=body,
                                   headers={"X-Smelter-Token": "test-token", "Content-Type": "application/json"})
                response = connection.getresponse()
                self.assertEqual(response.status, 202)
                self.assertEqual(json.loads(response.read())["state"], "running")
                self.assertEqual(mocked.call_args.args[1]["tool_permissions"], self.grants)
        finally:
            connection.close()
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
