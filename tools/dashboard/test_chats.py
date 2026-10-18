import tempfile
import unittest
from pathlib import Path
from database import select_database
from chats import list_chats, create_chat, read_chat, add_note, rename_chat, delete_chat

class ChatPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.root = base / "checkout"
        (self.root / ".smelter").mkdir(parents=True)
        select_database(self.root, str(base / "data"))
    def test_roundtrip(self):
        cid = create_chat(self.root, "Testing")["id"]
        add_note(self.root, cid, "Persistent note")
        self.assertEqual(read_chat(self.root, cid)["messages"][0]["content"], "Persistent note")
        self.assertEqual(list_chats(self.root)["conversations"][0]["title"], "Testing")
        rename_chat(self.root, cid, "Renamed")
        self.assertEqual(read_chat(self.root, cid)["title"], "Renamed")
        delete_chat(self.root, cid)
        self.assertEqual(list_chats(self.root)["conversations"], [])
    def test_invalid_ids(self):
        with self.assertRaises(ValueError):
            read_chat(self.root, "../projects")
    def test_note_requires_existing_conversation(self):
        with self.assertRaises(ValueError):
            add_note(self.root, "11111111-1111-4111-8111-111111111111", "hi")
    def test_note_size_limit(self):
        cid = create_chat(self.root)["id"]
        with self.assertRaises(ValueError):
            add_note(self.root, cid, "x"*1801)

if __name__ == "__main__":
    unittest.main()
