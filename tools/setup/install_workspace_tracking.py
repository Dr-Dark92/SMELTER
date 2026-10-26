"""Enable the bundled diagrams skill and native workspace continuity instructions.

Uses Python's standard library. Downloads nothing and preserves model, permission,
MCP and credential settings. Conflicting native instructions are never replaced.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/dashboard'))


def install(root=ROOT, *, native_config=None, apply=False):
    from install_ecc_bridge import _atomic_write
    from python_tools import _plain_path
    from skill_manager import enabled_map
    from skill_manifest import parse_skill_manifest
    root = _plain_path(Path(root).resolve())
    manifest = _plain_path(root / 'skills/diagrams/SKILL.md').read_bytes()
    parsed = parse_skill_manifest(manifest.decode('utf-8'))
    if not parsed['valid'] or parsed['name'] != 'diagrams':
        raise ValueError('Invalid bundled diagrams skill')
    instruction = _plain_path(root / 'tools/dashboard/workspace_native_instructions.md').read_bytes()
    state_path = _plain_path(root / '.smelter/skill-state.json')
    state_before = state_path.read_bytes() if state_path.exists() else None
    state = {**enabled_map(root), 'diagrams': True}
    config = _plain_path(Path(native_config) if native_config else Path.home() / '.config/opencode/opencode.json')
    if native_config and not config.is_file():
        raise ValueError('Explicit native configuration does not exist')
    before = config.read_bytes() if config.is_file() else None
    after, copies = before, []
    if before is not None:
        value = json.loads(before.decode('utf-8-sig'))
        selected = value.setdefault('instructions', [])
        if not isinstance(selected, list) or any(not isinstance(x, str) for x in selected):
            raise ValueError('Native instructions must be a list of paths')
        destination = config.parent / 'smelter-workspace-tracking.md'
        if str(destination) not in selected:
            selected.append(str(destination))
            after = (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
        copies = [(config.parent / 'skills/diagrams/SKILL.md', manifest), (destination, instruction)]
    missing = []
    for path, raw in copies:
        path = _plain_path(path)
        if path.exists():
            if not path.is_file() or path.read_bytes() != raw:
                raise ValueError('Conflicting native instruction preserved: ' + str(path))
        else:
            missing.append((path, raw))
    receipt = {'schema_version': 1, 'enabled': True, 'skills': ['diagrams'],
               'native_config': str(config) if before is not None else None,
               'skill_sha256': hashlib.sha256(manifest).hexdigest(),
               'instruction_sha256': hashlib.sha256(instruction).hexdigest(),
               'runtime': 'Python standard library + browser SVG', 'downloads': False}
    result = {**receipt, 'mode': 'apply' if apply else 'preview', 'native_files_to_create': len(missing), 'backup': None}
    if not apply:
        return result
    if (state_path.read_bytes() if state_path.exists() else None) != state_before:
        raise ValueError('Skill state changed during preparation')
    if before is not None and config.read_bytes() != before:
        raise ValueError('Native configuration changed during preparation')
    for path, raw in missing:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
    if before != after:
        backup = _plain_path(config.with_name(config.name + '.bak-tracking-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')))
        with backup.open('xb') as stream:
            stream.write(before)
        _atomic_write(config, after)
        result['backup'] = str(backup)
    _atomic_write(state_path, (json.dumps(state, indent=2) + '\n').encode())
    _atomic_write(root / '.smelter/workspace-tracking-bridge.json', (json.dumps(receipt, indent=2) + '\n').encode())
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--native-config', type=Path)
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    print(json.dumps(install(args.root, native_config=args.native_config, apply=not args.preview), indent=2))
