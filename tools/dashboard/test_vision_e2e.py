"""Vision integration coverage: real image -> chat -> Ollama payload -> SQLite.

Mock transport tests always run and never require Ollama. Set
SMELTER_VISION_LIVE=1 to additionally exercise the real local Ollama model.
Tests use an isolated temporary database outside the checkout.
"""
import base64
import io
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from urllib.request import urlopen

from chat_inference import ask
from chats import create_chat, read_chat
from database import select_database
from vision_probe import png_test_card


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


class VisionEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.root = base / "checkout"
        (self.root / ".smelter").mkdir(parents=True)
        select_database(self.root, str(base / "data"))
        self.cid = create_chat(self.root, "Vision integration")["id"]
        self.png = png_test_card()
        self.image = {"mime": "image/png", "base64": base64.b64encode(self.png).decode("ascii")}

    def test_image_reaches_ollama_request_and_chat_is_preserved(self):
        captured = []

        def fake_ollama(request, timeout):
            self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
            self.assertEqual(request.get_header("Content-type"), "application/json")
            payload = json.loads(request.data)
            captured.append(payload)
            return _Response(json.dumps({
                "message": {"role": "assistant", "content": "red"},
                "done_reason": "stop",
            }).encode("utf-8"))

        result = ask(self.root, self.cid, "What color is the square?", opener=fake_ollama, image=self.image)
        self.assertEqual(len(captured), 1)
        payload = captured[0]
        self.assertEqual(payload["model"], "qwen3.5:9b")
        self.assertIs(payload["think"], False)
        self.assertEqual(payload["messages"][-1]["role"], "user")
        self.assertEqual(len(payload["messages"][-1]["images"]), 1)
        self.assertEqual(base64.b64decode(payload["messages"][-1]["images"][0]), self.png)
        self.assertEqual(result["reply"], "red")
        self.assertFalse(result["tools_executed"])
        messages = read_chat(self.root, self.cid)["messages"]
        self.assertEqual([m["role"] for m in messages], ["user", "assistant"])
        self.assertNotIn(self.image["base64"], messages[0]["content"])

    def test_invalid_image_rejected_before_ollama_or_database_write(self):
        calls = []

        def should_not_call(*args, **kwargs):
            calls.append(True)
            raise AssertionError("Ollama must not be called")

        with self.assertRaises(ValueError):
            ask(self.root, self.cid, "Describe the image", opener=should_not_call,
                image={"mime": "image/png", "base64": "not-base64"})
        self.assertFalse(calls)
        self.assertEqual(read_chat(self.root, self.cid)["messages"], [])

    def test_text_chat_has_no_image_field(self):
        def fake_ollama(request, timeout):
            payload = json.loads(request.data)
            self.assertNotIn("images", payload["messages"][-1])
            return _Response(b'{"message":{"content":"hello"},"done_reason":"stop"}')

        self.assertEqual(ask(self.root, self.cid, "Hello", opener=fake_ollama)["reply"], "hello")

    @unittest.skipUnless(os.environ.get("SMELTER_VISION_LIVE") == "1",
                         "Set SMELTER_VISION_LIVE=1 for actual Ollama visual recognition")
    def test_live_qwen_recognizes_image_through_chat_pipeline(self):
        result = ask(self.root, self.cid,
                     "What color is the central square in the attached image? Answer with one color word.",
                     opener=urlopen, image=self.image)
        self.assertRegex(result["reply"].lower(), r"\\bred\\b")
        self.assertEqual(len(read_chat(self.root, self.cid)["messages"]), 2)


if __name__ == "__main__":
    unittest.main()
