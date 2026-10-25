"""Preview/apply the access-policy rows for native mod builds and read-only game folders.

Registers optional read-only game folders and an explicitly selected local immutable
CLI toolchain image. No host compiler execution grant is added. Existing rows,
including denials, are preserved. Models and task grants are unchanged.
"""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/dashboard'))


def configure(root=ROOT, *, read_folders=(), image_id=None, apply=False):
    from access_policy import current, save
    from python_tools import _plain_path
    root = _plain_path(Path(root).resolve())
    original = current(root)
    policy = json.loads(json.dumps(original.value))
    rows = []
    for folder in read_folders:
        path = _plain_path(Path(folder)).resolve(strict=True)
        if not path.is_dir():
            raise ValueError('Not a folder: ' + str(path))
        identity = 'game_' + re.sub(r'[^a-z0-9]+', '_', path.name.lower()).strip('_')[:40]
        rows.append((identity, 'Game folder (read-only): ' + path.name, path,
                     {'read': True, 'write': False, 'execute': False, 'operations': []}))
    added, notes = [], []
    for identity, label, path, flags in rows:
        if any(Path(row['path']).resolve() == path for row in policy['locations']):
            notes.append('Preserved existing location policy for ' + str(path))
            continue
        if any(row['id'] == identity for row in policy['locations']):
            raise ValueError('Existing location ID conflicts with ' + identity)
        policy['locations'].append({'id': identity, 'name': label, 'path': str(path), **flags,
                                    'exclusions': [], 'enabled': True})
        added.append({'id': identity, 'path': str(path), **flags})
    if image_id is not None:
        from sandbox import config, validate
        from process_runner import run
        import shutil
        value = {**config(root), 'cpp_image': image_id}
        validate(value)
        docker = shutil.which('docker')
        if not docker:
            raise ValueError('Local Docker is required to select the CLI toolchain')
        found = run([docker, 'image', 'inspect', '--format', '{{.Id}}', image_id], timeout=5, max_output=16384, text=True, check=True)
        if found.stdout.strip() != image_id:
            raise ValueError('The selected immutable image is not installed')
    if apply:
        from maintenance import _idle
        _idle(root)
        if added:
            save(root, policy, original.revision)
        if image_id is not None:
            from config_store import save_config
            save_config(root, 'sandbox.json', value)
    return {'mode': 'apply' if apply else 'preview', 'compiler': 'confined MinGW-w64', 'image_id': image_id,
            'added_locations': added, 'notes': notes, 'write_permissions_added': False, 'host_execution_grants_added': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--read-folder', action='append', default=[], help='Game folder to register read-only')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--image-id', help='Locally installed immutable sha256 ID of smelter-cpp:2')
    args = parser.parse_args()
    print(json.dumps(configure(args.root, read_folders=args.read_folder, image_id=args.image_id, apply=args.apply), indent=2))
