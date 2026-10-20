import base64
import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from chats import create_chat, read_chat, delete_chat
from database import select_database
from model_assets import inspect_glb, attach_model, model_path


def glb(document):
    raw = json.dumps(document).encode()
    raw += b' ' * (-len(raw) % 4)
    return struct.pack('<4sIIII', b'glTF', 2, len(raw) + 20, len(raw), 0x4e4f534a) + raw


class ModelAssetTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / 'checkout'
        self.root.mkdir()
        select_database(self.root, str(Path(temp.name) / 'data'))
        self.cid = create_chat(self.root, 'GLB fixture')['id']
        self.raw = glb({'asset': {'version': '2.0'}, 'nodes': [], 'meshes': []})

    def test_attach_persists_bytes_and_metadata_without_ai(self):
        result = attach_model(self.root, {'conversation_id': self.cid, 'filename': 'fixture.glb', 'base64': base64.b64encode(self.raw).decode()})
        self.assertEqual(model_path(self.root, result['id']).read_bytes(), self.raw)
        message = read_chat(self.root, self.cid)['messages'][0]
        self.assertEqual(message['model_attachment']['sha256'], result['sha256'])
        self.assertEqual(message['role'], 'user')
        path = model_path(self.root, result['id'])
        delete_chat(self.root, self.cid)
        self.assertTrue(path.is_file())
        with self.assertRaises(ValueError):
            model_path(self.root, result['id'])

    def test_external_resources_and_compression_rejected(self):
        for extra in ({'images': [{'uri': 'https://example.test/image.png'}]},
                      {'buffers': [{'uri': 'file:///etc/passwd'}]},
                      {'extensionsUsed': ['KHR_draco_mesh_compression']}, {'asset': []}):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                inspect_glb(glb({'asset': {'version': '2.0'}, **extra}))

    def test_truncated_and_oversized_containers_rejected(self):
        with self.assertRaises(ValueError):
            inspect_glb(self.raw[:-1])
        with patch('model_assets.MAX_BYTES', 20), self.assertRaises(ValueError):
            inspect_glb(self.raw)

    def test_filename_escape_and_missing_conversation_do_not_write(self):
        for filename in ('../fixture.glb', 'C:\\fixture.glb', 'fixture.txt'):
            with self.assertRaises(ValueError):
                attach_model(self.root, {'conversation_id': self.cid, 'filename': filename, 'base64': base64.b64encode(self.raw).decode()})
        self.assertFalse((self.root / '.smelter/model-assets').exists())

    def test_opaque_ids_only(self):
        with self.assertRaises(ValueError):
            model_path(self.root, '../../fixture')
