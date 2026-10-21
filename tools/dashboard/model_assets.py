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
    from storage_budget import require
    require(root,len(raw))
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


def inspect_attachment(root, grants, arguments):
    """Read an approved saved GLB; durations come from embedded time accessors."""
    import math
    if not isinstance(arguments, dict) or set(arguments) - {'attachment_id', 'animation_offset', 'animation_limit'}:
        raise ValueError('Unknown model inspection argument')
    aid = _id(arguments.get('attachment_id'))
    if aid not in grants.get('model_ids', []):
        raise ValueError('Model attachment was not approved for this message')
    offset, limit = arguments.get('animation_offset', 0), arguments.get('animation_limit', 50)
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('Choose a nonnegative animation offset and a limit from 1 to 100')
    raw = model_path(root, aid).read_bytes()
    summary = inspect_glb(raw)
    size = struct.unpack_from('<I', raw, 12)[0]
    document = json.loads(raw[20:20 + size])
    bin_start = 28 + size if 28 + size <= len(raw) else len(raw)
    views, accessors = document.get('bufferViews', []), document.get('accessors', [])
    if not isinstance(views, list):
        raise ValueError('Invalid buffer views')
    embedded_length = document['buffers'][0]['byteLength'] if document.get('buffers') else 0
    cache, sampled = {}, 0

    def time_bounds(index):
        nonlocal sampled
        if type(index) is not int or not 0 <= index < len(accessors):
            raise ValueError('Invalid animation time accessor')
        if index in cache:
            return cache[index]
        item = accessors[index]
        if item.get('componentType') != 5126 or item.get('type') != 'SCALAR' or 'sparse' in item or item.get('normalized'):
            return None, 'Unsupported time accessor layout'
        view_index, count = item.get('bufferView'), item.get('count')
        if type(view_index) is not int or not 0 <= view_index < len(views) or type(count) is not int or count < 1:
            raise ValueError('Invalid animation time buffer')
        view = views[view_index]
        if not isinstance(view, dict) or view.get('buffer') != 0:
            raise ValueError('Animation time buffer must be embedded')
        start, byte_offset, length, stride = item.get('byteOffset', 0), view.get('byteOffset', 0), view.get('byteLength'), view.get('byteStride', 4)
        if any(type(x) is not int for x in (start, byte_offset, length, stride)) or min(start, byte_offset, length) < 0 or not 4 <= stride <= 252 or stride % 4:
            raise ValueError('Invalid animation time offsets')
        if start + (count - 1) * stride + 4 > length or byte_offset + length > embedded_length or bin_start + byte_offset + length > len(raw):
            raise ValueError('Animation time accessor exceeds embedded buffer')
        if sampled + count > 250000:
            cache[index] = (None, 'Time sampling budget reached')
            return cache[index]
        sampled += count
        first, previous = None, -1.0
        for i in range(count):
            value = struct.unpack_from('<f', raw, bin_start + byte_offset + start + i * stride)[0]
            if not math.isfinite(value) or value < 0 or value <= previous:
                raise ValueError('Animation times must be finite, nonnegative and strictly increasing')
            if first is None:
                first = value
            previous = value
        cache[index] = ((first, previous), None)
        return cache[index]

    animations = document.get('animations', [])
    clips = []
    for index in range(offset, min(len(animations), offset + limit)):
        animation = animations[index]
        samplers, channels = animation.get('samplers', []), animation.get('channels', [])
        if not isinstance(samplers, list) or not isinstance(channels, list) or any(not isinstance(s, dict) for s in samplers):
            raise ValueError('Invalid animation samplers or channels')
        bounds, reasons = [], []
        for sampler in samplers:
            bound, reason = time_bounds(sampler.get('input'))
            if bound is not None:
                bounds.append(bound)
            if reason:
                reasons.append(reason)
        start = min((x[0] for x in bounds), default=None)
        end = max((x[1] for x in bounds), default=None)
        clips.append({'index': index, 'source_name': animation.get('name'), 'channels': len(channels),
                      'duration_seconds': end if bounds and not reasons else None,
                      'first_keyframe_seconds': start, 'zero_duration': end == 0 if bounds and not reasons else None,
                      'duration_status': 'verified_embedded_keyframe_times' if bounds and not reasons else 'unknown',
                      'limitations': sorted(set(reasons)) or ([] if bounds else ['No animation samplers'])})
    skins = document.get('skins', [])
    if not isinstance(skins, list) or len(skins) > 10000:
        raise ValueError('Invalid skins')
    joint_counts = []
    for skin in skins:
        joints = skin.get('joints') if isinstance(skin, dict) else None
        if not isinstance(joints, list) or any(type(i) is not int or not 0 <= i < summary['nodes'] for i in joints):
            raise ValueError('Invalid skeleton joints')
        joint_counts.append(len(joints))
    with closing(sqlite3.connect(_db(root))) as conn:
        row = conn.execute('SELECT filename,metadata FROM model_attachments WHERE id=?', (aid,)).fetchone()
        if row is None:
            raise ValueError('Model attachment no longer exists')
        aliases = json.loads(row[1]).get('animation_labels', {})
    for clip in clips:
        clip['label'] = aliases.get(str(clip['index']))
    summary.pop('animation_clips', None)
    return {'status': 'model_inspected', 'attachment_id': aid, 'filename': row[0], **summary,
            'skins': len(skins), 'joints_per_skin': joint_counts, 'animation_clips': clips,
            'animation_offset': offset, 'animation_limit': limit,
            'next_animation_offset': offset + len(clips) if offset + len(clips) < len(animations) else None,
            'scope': 'Read-only GLB structure and embedded animation time values; no rendering, extraction, semantic animation classification or engine compatibility validation'}
