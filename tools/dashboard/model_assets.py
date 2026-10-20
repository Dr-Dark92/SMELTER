"""Bounded GLB attachments for local browser preview, independent of inference."""
import base64
import hashlib
import json
import sqlite3
import struct
from contextlib import closing
from pathlib import Path
from uuid import uuid4
from chats import _db, _id
from python_tools import _plain_path

MAX_BYTES = 25 * 1024 * 1024
VIEWER_VERSION = '4.1.0'
SCHEMA = '''CREATE TABLE IF NOT EXISTS model_attachments (
id TEXT PRIMARY KEY, message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
filename TEXT NOT NULL, metadata TEXT NOT NULL)'''


def inspect_glb(raw):
    if not isinstance(raw, bytes) or not 20 <= len(raw) <= MAX_BYTES:
        raise ValueError('GLB must be between 20 bytes and 25 MiB')
    magic, version, length = struct.unpack_from('<4sII', raw)
    if magic != b'glTF' or version != 2 or length != len(raw):
        raise ValueError('Expected a complete glTF 2.0 GLB container')
    chunks, offset = [], 12
    while offset < len(raw):
        if offset + 8 > len(raw):
            raise ValueError('Truncated GLB chunk header')
        size, kind = struct.unpack_from('<II', raw, offset)
        offset += 8
        if size % 4 or offset + size > len(raw):
            raise ValueError('Invalid GLB chunk length')
        chunks.append((kind, offset, size))
        offset += size
    if not chunks or chunks[0][0] != 0x4e4f534a or len(chunks) > 2 or len(chunks) == 2 and chunks[1][0] != 0x004e4942:
        raise ValueError('Expected JSON followed by optional embedded BIN data')
    _, start, size = chunks[0]
    if size > 2 * 1024 * 1024:
        raise ValueError('GLB JSON exceeds 2 MiB')
    try:
        document = json.loads(raw[start:start + size])
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError('Invalid GLB JSON') from exc
    if not isinstance(document, dict) or not isinstance(document.get('asset'), dict) or document['asset'].get('version') != '2.0':
        raise ValueError('Invalid glTF asset version')
    # All assets must be embedded. Do not let an uploaded model fetch URLs.
    stack, count = [document], 0
    while stack:
        value = stack.pop()
        count += 1
        if count > 200000:
            raise ValueError('GLB metadata is too complex')
        if isinstance(value, dict):
            if 'uri' in value:
                raise ValueError('Only embedded GLB assets are supported; URI resources are rejected')
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
    used, required = document.get('extensionsUsed', []), document.get('extensionsRequired', [])
    if not isinstance(used, list) or not isinstance(required, list) or any(
            x in used + required for x in ('KHR_draco_mesh_compression', 'EXT_meshopt_compression', 'KHR_texture_basisu')):
        raise ValueError('Compressed models requiring external decoders are not supported yet')
    summary = {}
    for key in ('meshes', 'nodes', 'materials', 'images', 'animations'):
        values = document.get(key, [])
        if not isinstance(values, list) or len(values) > 10000:
            raise ValueError('Invalid or excessive ' + key)
        summary[key] = len(values)
    clips = document.get('animations', [])
    if any(not isinstance(clip, dict) or not isinstance(clip.get('name', ''), str) for clip in clips):
        raise ValueError('Invalid animation names')
    summary['animation_clips'] = [{'index': i, 'source_name': clip.get('name')} for i, clip in enumerate(clips)]
    accessors = document.get('accessors', [])
    if not isinstance(accessors, list) or any(not isinstance(x, dict) or type(x.get('count', 0)) is not int or not 0 <= x.get('count', 0) <= 10000000 for x in accessors):
        raise ValueError('Invalid or excessive accessor count')
    buffers = document.get('buffers', [])
    embedded_size = chunks[1][2] if len(chunks) > 1 else 0
    if not isinstance(buffers, list) or len(buffers) > 1 or any(not isinstance(x, dict) or type(x.get('byteLength')) is not int or not 0 <= x['byteLength'] <= embedded_size for x in buffers):
        raise ValueError('Invalid embedded buffer declaration')
    return {**summary, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'validation': 'Container and resource-policy checks only; browser verifies renderability'}


def viewer_bundle(root):
    package = _plain_path(Path(root) / '.smelter/tooling/model-viewer/node_modules/@google/model-viewer')
    manifest = _plain_path(package / 'package.json')
    if not manifest.is_file() or manifest.stat().st_size > 100000:
        raise ValueError('Install local @google/model-viewer@4.1.0 first')
    info = json.loads(manifest.read_text(encoding='utf-8'))
    if info.get('name') != '@google/model-viewer' or info.get('version') != VIEWER_VERSION:
        raise ValueError('Model viewer must be @google/model-viewer@4.1.0')
    path = _plain_path(package / 'dist/model-viewer.min.js')
    if not path.is_file() or path.stat().st_size > 10 * 1024 * 1024:
        raise ValueError('Local viewer bundle is missing or invalid')
    return path


def viewer_status(root):
    try:
        viewer_bundle(root)
        return {'status': 'installed', 'version': VIEWER_VERSION}
    except (OSError, ValueError) as exc:
        return {'status': 'missing', 'error': str(exc)}


def attach_model(root, data):
    cid = _id(data.get('conversation_id'))
    filename = data.get('filename')
    if not isinstance(filename, str) or not filename.lower().endswith('.glb') or len(filename) > 160 or any(c in filename for c in '/\\\x00\r\n'):
        raise ValueError('Choose a .glb filename without directory components')
    encoded = data.get('base64')
    if not isinstance(encoded, str) or len(encoded) > (MAX_BYTES + 2) // 3 * 4:
        raise ValueError('GLB upload exceeds 25 MiB')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except ValueError as exc:
        raise ValueError('Invalid GLB upload encoding') from exc
    metadata = inspect_glb(raw)
    aid = str(uuid4())
    folder = _plain_path(Path(root) / '.smelter/model-assets')
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (aid + '.glb')
    created = False
    try:
        with closing(sqlite3.connect(_db(root), timeout=5)) as conn, conn:
            conn.execute('PRAGMA foreign_keys=ON')
            if not conn.execute('SELECT 1 FROM conversations WHERE id=?', (cid,)).fetchone():
                raise ValueError('Conversation not found')
            conn.execute(SCHEMA)
            with path.open('xb') as stream:
                created = True
                stream.write(raw)
            mid = conn.execute("INSERT INTO messages(conversation_id,role,content) VALUES(?,'user',?)", (cid, '3D attachment: ' + filename)).lastrowid
            conn.execute('INSERT INTO model_attachments(id,message_id,filename,metadata) VALUES(?,?,?,?)', (aid, mid, filename, json.dumps(metadata)))
    except Exception:
        if created:
            path.unlink(missing_ok=True)
        raise
    return {'id': aid, 'filename': filename, **metadata}


def model_path(root, aid):
    aid = _id(aid)
    with closing(sqlite3.connect(_db(root))) as conn:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='model_attachments'").fetchone() or not conn.execute('SELECT 1 FROM model_attachments WHERE id=?', (aid,)).fetchone():
            raise ValueError('Model attachment not found')
    path = _plain_path(Path(root) / '.smelter/model-assets' / (aid + '.glb'))
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError('Model asset is missing or exceeds size limit')
    return path


def rename_animation(root, data):
    aid = _id(data.get('id'))
    index, label = data.get('index'), data.get('label')
    if type(index) is not int or index < 0:
        raise ValueError('Choose a valid animation index')
    if not isinstance(label, str) or not label.strip() or len(label) > 120 or any(ord(c) < 32 or ord(c) == 127 for c in label):
        raise ValueError('Animation label must be 1-120 characters without control characters')
    clips = inspect_glb(model_path(root, aid).read_bytes())['animation_clips']
    if index >= len(clips):
        raise ValueError('Animation index does not exist')
    with closing(sqlite3.connect(_db(root), timeout=5)) as conn, conn:
        conn.execute('BEGIN IMMEDIATE')
        row = conn.execute('SELECT filename,metadata FROM model_attachments WHERE id=?', (aid,)).fetchone()
        if not row:
            raise ValueError('Model attachment not found')
        metadata = json.loads(row[1])
        metadata['animation_clips'] = clips
        metadata.setdefault('animation_labels', {})[str(index)] = label.strip()
        conn.execute('UPDATE model_attachments SET metadata=? WHERE id=?', (json.dumps(metadata), aid))
    return {'id': aid, 'filename': row[0], **metadata}
