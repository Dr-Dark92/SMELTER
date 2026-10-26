"""Verify and enable the vendored ECC instruction bridge, without downloads.

Only reviewed Markdown is copied to native OpenCode. No ECC executable plugin,
hook, package, external MCP server or model setting is installed or changed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/dashboard'))
LOCK_PATH = Path('tools/setup/ecc-bridge-lock.json')


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _relative(value):
    if not isinstance(value, str) or '\\' in value or ':' in value:
        raise ValueError('Invalid bridge source path')
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(x in ('.', '..') for x in path.parts):
        raise ValueError('Invalid bridge source path')
    if path.name != 'LICENSE' and path.suffix != '.md':
        raise ValueError('Only Markdown instructions and LICENSE may be bridged')
    return Path(*path.parts)


def verified_bundle(root):
    from python_tools import _plain_path
    from skill_manifest import parse_skill_manifest
    root = _plain_path(Path(root).resolve())
    lock_bytes = _plain_path(root / LOCK_PATH).read_bytes()
    lock = json.loads(lock_bytes)
    if (lock.get('schema_version') != 1 or lock.get('repository') != 'https://github.com/affaan-m/ECC'
            or not re.fullmatch('[a-f0-9]{40}', lock.get('revision', ''))
            or lock.get('license') != 'MIT' or not isinstance(lock.get('skills'), dict)):
        raise ValueError('Invalid ECC bridge lock')
    files = {}
    for name, item in lock['skills'].items():
        if not re.fullmatch('[a-z][a-z0-9-]{0,63}', name) or not isinstance(item.get('files'), dict):
            raise ValueError('Invalid ECC bridge skill identity')
        if 'SKILL.md' not in item['files']:
            raise ValueError('Bridge skill is missing its manifest')
        if item.get('kind') == 'adapted_ecc' and 'references/LICENSE' not in item['files']:
            raise ValueError('ECC source license must be retained')
        for relative, expected in item['files'].items():
            source = _plain_path(root / 'skills' / name / _relative(relative))
            data = source.read_bytes()
            if len(data) > 128 * 1024 or _digest(data) != expected.get('sha256'):
                raise ValueError('ECC bridge source integrity mismatch: ' + str(source))
            data.decode('utf-8')
            if relative == 'SKILL.md':
                metadata = parse_skill_manifest(data.decode('utf-8'))
                if not metadata['valid'] or metadata['name'] != name:
                    raise ValueError('Invalid bridge skill manifest: ' + name)
            files[Path('skills') / name / _relative(relative)] = data
    instructions = lock['native_instructions']
    source = _plain_path(root / _relative(instructions['path']))
    data = source.read_bytes()
    if len(data) > 8192 or _digest(data) != instructions.get('sha256'):
        raise ValueError('Native bridge instructions integrity mismatch')
    return lock, _digest(lock_bytes), files, data


def _atomic_write(path, data):
    from python_tools import _plain_path
    path = _plain_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=path.name + '.', suffix='.pending', dir=path.parent)
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def install(root=ROOT, *, native_config=None, native=True, apply=False, automatic_coding=True):
    from python_tools import _plain_path
    from skill_manager import enabled_map
    root = _plain_path(Path(root).resolve())
    lock, lock_sha, bundle, instructions = verified_bundle(root)
    state_path = _plain_path(root / '.smelter/skill-state.json')
    receipt_path = _plain_path(root / '.smelter/ecc-bridge.json')
    state_before = state_path.read_bytes() if state_path.exists() else None
    state = enabled_map(root)
    state.update({name: True for name in lock['skills']})
    copies = []
    config = None
    config_before = config_after = None
    if native:
        config = _plain_path(Path(native_config) if native_config is not None else Path.home() / '.config/opencode/opencode.json')
        if config.is_file():
            config_before = config.read_bytes()
            value = json.loads(config_before.decode('utf-8-sig'))
            model = value.get('provider', {}).get('ollama', {}).get('models', {}).get('qwen3.5:35b-a3b-128k')
            if not model or model.get('limit') != {'context': 131072, 'output': 8192}:
                raise ValueError('Preserve the existing Qwen 128K/8K profile; configure it before bridging ECC')
            selected = value.setdefault('instructions', [])
            if not isinstance(selected, list) or any(not isinstance(x, str) for x in selected):
                raise ValueError('Existing OpenCode instructions must be a list')
            destination = _plain_path(config.parent / 'smelter-ecc-coding.md')
            if str(destination) not in selected:
                selected.append(str(destination))
            config_after = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
            if value == json.loads(config_before.decode('utf-8-sig')):
                config_after = config_before
            copies = [(config.parent / path, data) for path, data in bundle.items()]
            copies.append((destination, instructions))
        elif native_config is not None:
            raise ValueError('Explicit native OpenCode configuration was not found')
        else:
            config = None
    # Check the entire plan before any mutation. Preserve user-modified native skills.
    missing = []
    for destination, data in copies:
        destination = _plain_path(destination)
        if destination.exists():
            if not destination.is_file() or destination.read_bytes() != data:
                raise ValueError('Existing native instruction differs; preserved: ' + str(destination))
        else:
            missing.append((destination, data))
    receipt = {'schema_version': 1, 'enabled': True, 'automatic_coding': bool(automatic_coding),
               'repository': lock['repository'], 'revision': lock['revision'], 'lock_sha256': lock_sha,
               'skills': list(lock['skills']), 'native_config': str(config) if config else None,
               'native_instructions': str(config.parent / 'smelter-ecc-coding.md') if config else None,
               'context_tokens': 131072, 'output_tokens': 8192,
               'mode': 'adapted_instructions_only', 'executable_plugin': False}
    result = {**receipt, 'mode': 'apply' if apply else 'preview', 'downloads': False,
              'native_files_to_create': len(missing), 'native_config_changed': config_before != config_after,
              'backup': None}
    if not apply:
        return result
    if (state_path.read_bytes() if state_path.exists() else None) != state_before:
        raise ValueError('Skill state changed during bridge preparation')
    if config is not None and config.read_bytes() != config_before:
        raise ValueError('OpenCode configuration changed during bridge preparation')
    for destination, data in missing:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open('xb') as stream:
            stream.write(data)
    if config is not None and config_before != config_after:
        backup = _plain_path(config.with_name(config.name + '.bak-ecc-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')))
        with backup.open('xb') as stream:
            stream.write(config_before)
        _atomic_write(config, config_after)
        result['backup'] = str(backup)
    state_bytes = (json.dumps(state, indent=2) + '\n').encode('utf-8')
    if state_before != state_bytes:
        _atomic_write(state_path, state_bytes)
    receipt_bytes = (json.dumps(receipt, indent=2) + '\n').encode('utf-8')
    if not receipt_path.exists() or receipt_path.read_bytes() != receipt_bytes:
        _atomic_write(receipt_path, receipt_bytes)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--native-config', type=Path)
    parser.add_argument('--no-native', action='store_true')
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--apply', action='store_true', help='Enable and bridge the reviewed instructions (the setup default)')
    mode.add_argument('--preview', action='store_true', help='Verify and preview without writing anything')
    parser.add_argument('--no-auto-coding', action='store_true', help='Keep skills enabled but require explicit/automatic task selection in the dashboard')
    args = parser.parse_args()
    print(json.dumps(install(args.root, native_config=args.native_config, native=not args.no_native,
                             apply=not args.preview, automatic_coding=not args.no_auto_coding), indent=2))
