"""Startup skill snapshots and passive manifest change detection. No execution."""
import hashlib
import json
import re
import shutil
import threading
from pathlib import Path
from skills_catalog import catalog_skills

_monitors = {}


def skill_folder(root, skill):
    if skill['source'] == 'bundled':
        return Path(root) / 'skills' / skill['id']
    base = Path(root) / '.smelter/managed-skills'
    return base / ('collections/' + skill['id'] if skill['source'] == 'collection' else skill['id'])


def inspect_skill(root, skill):
    from python_tools import _plain_path
    folder = skill_folder(root, skill)
    manifest = _plain_path(folder / 'SKILL.md')
    if manifest.stat().st_size > 65536:
        raise ValueError('Skill manifest exceeds 64 KiB')
    raw = manifest.read_bytes()
    configuration = _plain_path(folder / 'smelter.json')
    extra = b''
    requirements = None
    if configuration.is_file():
        if configuration.stat().st_size > 16384:
            raise ValueError('smelter.json exceeds 16 KiB')
        extra = configuration.read_bytes()
        data = json.loads(extra)
        if not isinstance(data, dict) or set(data) != {'schema_version', 'requires'} or data['schema_version'] != 1:
            raise ValueError('smelter.json requires schema_version=1 and requires only')
        requirements = data['requires']
        if not isinstance(requirements, list) or len(requirements) > 20 or any(
                not isinstance(name, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_.+-]{0,63}', name) for name in requirements):
            raise ValueError('requires must list up to 20 executable names without paths or arguments')
    fingerprint = hashlib.sha256(raw + b'\0' + extra).hexdigest()
    return {'fingerprint': fingerprint, 'text': raw.decode('utf-8'), 'manifest': str(manifest),
            'dependencies': None if requirements is None else [
                {'name': name, 'path': shutil.which(name), 'status': 'found' if shutil.which(name) else 'missing'} for name in requirements]}


class SkillMonitor:
    def __init__(self, root):
        self.root = Path(root)
        self.lock = threading.Lock()
        self.baseline = self._scan()

    def _scan(self):
        result = {}
        for skill in catalog_skills(self.root)['skills']:
            try:
                result[skill['id']] = {**skill, **inspect_skill(self.root, skill)}
            except (OSError, ValueError, UnicodeError) as exc:
                result[skill['id']] = {**skill, 'fingerprint': None, 'error': str(exc), 'dependencies': None}
        return result

    def status(self):
        with self.lock:
            current = self._scan()
            skills, changes = [], []
            for sid, skill in current.items():
                old = self.baseline.get(sid)
                change = 'added' if old is None else 'changed' if old.get('fingerprint') != skill.get('fingerprint') else None
                loaded = bool(old and skill.get('fingerprint') and old.get('fingerprint') == skill['fingerprint'])
                record = {k: v for k, v in skill.items() if k != 'text'}
                record.update(change=change, active_snapshot=loaded,
                              activation='invalid' if skill.get('error') or skill['status'] != 'ready' else 'restart_required' if not loaded else 'enabled' if skill['enabled'] else 'disabled')
                skills.append(record)
                if change:
                    changes.append({'id': sid, 'change': change})
            changes.extend({'id': sid, 'change': 'removed'} for sid in self.baseline.keys() - current.keys())
            signature = hashlib.sha256(json.dumps(changes, sort_keys=True).encode() +
                json.dumps({sid: x.get('fingerprint') for sid, x in current.items()}, sort_keys=True).encode()).hexdigest()
            return {'skills': skills, 'count': len(skills), 'changes': changes, 'revision': signature,
                    'read_only': True,
                    'restart_required': bool(changes), 'watched': [str(self.root / 'skills'), str(self.root / '.smelter/managed-skills')],
                    'scope': 'SKILL.md and optional smelter.json in supported skill folders; scripts are not executed or monitored'}

    def manifest(self, sid):
        status = next((x for x in self.status()['skills'] if x['id'] == sid), None)
        if not status or not status['active_snapshot'] or status['activation'] == 'invalid':
            raise ValueError('Skill is new, changed or invalid; review it and restart the dashboard: ' + sid)
        return self.baseline[sid]['text']

    def review(self, sid):
        current = self._scan().get(sid)
        if not current or 'text' not in current:
            raise ValueError('Skill manifest is unavailable')
        return {key: current[key] for key in ('id', 'text', 'manifest', 'fingerprint', 'dependencies')}


def initialize(root):
    monitor = SkillMonitor(root)
    _monitors[str(Path(root).resolve())] = monitor
    return monitor


def monitor(root):
    key = str(Path(root).resolve())
    if key not in _monitors:
        initialize(root)
    return _monitors[key]


def runtime_manifest(root, sid):
    instance = _monitors.get(str(Path(root).resolve()))
    return instance.manifest(sid) if instance else None


def active_ids(root):
    instance = _monitors.get(str(Path(root).resolve()))
    if instance is None:
        return None
    return {s['id'] for s in instance.status()['skills'] if s['activation'] == 'enabled'}


def tools_status(root):
    from rea_connection import package_status
    rea = package_status(root)
    return [{'name': 'inventory_directory', 'status': 'connected', 'detail': 'Requires an approved folder for each message'},
            {'name': 'write_diagnostic_markdown', 'status': 'connected', 'detail': 'Requires diagnostic write approval'},
            {'name': 'rea_capabilities / rea_inspect_pe_resources', 'status': rea['status'], 'detail': rea['reason']},
            {'name': 'Blender modeling', 'status': 'not_connected', 'detail': 'Skill instructions do not provide an execution adapter'}]


def export_snapshot(root):
    """Compact startup fingerprints; never transfer manifest instructions as authority."""
    import base64, zlib
    instance = monitor(root)
    raw = json.dumps({sid: x.get('fingerprint') for sid, x in instance.baseline.items()}, sort_keys=True).encode()
    if len(raw) > 128 * 1024:
        raise ValueError('Skill snapshot exceeds transport budget')
    return base64.b64encode(zlib.compress(raw)).decode('ascii')


def inherit_snapshot(root, encoded):
    import base64, zlib
    if not isinstance(encoded, str) or len(encoded) > 32700:
        raise ValueError('Invalid inherited skill snapshot')
    decoder = zlib.decompressobj()
    raw = decoder.decompress(base64.b64decode(encoded, validate=True), 128 * 1024 + 1)
    if len(raw) > 128 * 1024 or not decoder.eof or decoder.unused_data:
        raise ValueError('Invalid inherited skill snapshot')
    expected = json.loads(raw)
    if not isinstance(expected, dict) or any(not isinstance(k, str) or v is not None and (not isinstance(v, str) or not re.fullmatch(r'[a-f0-9]{64}', v)) for k,v in expected.items()):
        raise ValueError('Invalid inherited skill fingerprints')
    instance = initialize(root)
    # Keep current text only when its fingerprint matches the parent's startup
    # baseline. manifest() rejects mismatches and newly added IDs.
    instance.baseline = {sid: {**skill, 'fingerprint': expected[sid]}
                         for sid, skill in instance.baseline.items() if sid in expected}
    return instance
