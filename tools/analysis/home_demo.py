"""Known inputs and isolated GUI workspace for an operator-run home demo."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools/dashboard'))


def animated_glb():
    binary = (struct.pack('<9f', -.5, 0, 0, .5, 0, 0, 0, 1, 0) +
              struct.pack('<3H', 0, 1, 2) + b'\0\0' +
              struct.pack('<2f6f2f6f', 0, 1, 0, 0, 0, 0, 1, 0,
                          0, 2, 0, 0, 0, 1, 0, 0))
    document = {
        'asset': {'version': '2.0', 'generator': 'SMELTER known-input smoke fixture'},
        'scene': 0, 'scenes': [{'nodes': [0]}], 'nodes': [{'mesh': 0}],
        'meshes': [{'primitives': [{'attributes': {'POSITION': 0}, 'indices': 1, 'material': 0}]}],
        'materials': [{'doubleSided': True, 'pbrMetallicRoughness': {
            'baseColorFactor': [1, .45, .05, 1], 'metallicFactor': 0, 'roughnessFactor': 1}}],
        'buffers': [{'byteLength': len(binary)}],
        'bufferViews': [{'buffer': 0, 'byteOffset': offset, 'byteLength': size}
                        for offset, size in [(0, 36), (36, 6), (44, 8), (52, 24), (76, 8), (84, 24)]],
        'accessors': [
            {'bufferView': 0, 'componentType': 5126, 'count': 3, 'type': 'VEC3',
             'min': [-.5, 0, 0], 'max': [.5, 1, 0]},
            {'bufferView': 1, 'componentType': 5123, 'count': 3, 'type': 'SCALAR'},
            {'bufferView': 2, 'componentType': 5126, 'count': 2, 'type': 'SCALAR', 'min': [0], 'max': [1]},
            {'bufferView': 3, 'componentType': 5126, 'count': 2, 'type': 'VEC3'},
            {'bufferView': 4, 'componentType': 5126, 'count': 2, 'type': 'SCALAR', 'min': [0], 'max': [2]},
            {'bufferView': 5, 'componentType': 5126, 'count': 2, 'type': 'VEC3'}],
        'animations': [{'name': name, 'samplers': [{'input': index, 'output': index + 1,
                         'interpolation': 'LINEAR'}],
                        'channels': [{'sampler': 0, 'target': {'node': 0, 'path': 'translation'}}]}
                       for name, index in [('Lift_1s', 2), ('Slide_2s', 4)]]}
    encoded = json.dumps(document, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    return (struct.pack('<4sII', b'glTF', 2, 28 + len(encoded) + len(binary)) +
            struct.pack('<I4s', len(encoded), b'JSON') + encoded +
            struct.pack('<I4s', len(binary), b'BIN\0') + binary)


def create_fixtures(directory):
    directory = Path(directory)
    directory.mkdir(exist_ok=False)
    inventory = directory / 'inventory'
    (inventory / 'nested').mkdir(parents=True)
    files = {'alpha.txt': b'alpha\n', 'beta.json': b'{"demo":true}\n', 'nested/gamma.txt': b'gamma\n'}
    for name, raw in files.items():
        (inventory / name).write_bytes(raw)
    outside = directory / 'outside'
    outside.mkdir()
    (outside / 'do-not-read.txt').write_text('Outside the approved inventory scope.\n', encoding='utf-8')
    model = directory / 'two-clips.glb'
    model.write_bytes(animated_glb())
    manifest = {'inventory': {'path': str(inventory.resolve()), 'files': 3, 'directories': 1,
                            'total_file_bytes': sum(map(len, files.values())),
                            'extensions': {'.txt': 2, '.json': 1}},
                'outside': str(outside.resolve()),
                'model': {'path': str(model.resolve()), 'sha256': hashlib.sha256(model.read_bytes()).hexdigest(),
                          'meshes': 1, 'animations': [{'name': 'Lift_1s', 'seconds': 1},
                                                    {'name': 'Slide_2s', 'seconds': 2}]}}
    (directory / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    return manifest


def prepare_demo(repository, directory, images, fixtures, ecc_manifests=()):
    """Create new code + databases; never reuse the user's source/V2 or DB."""
    from frontend_workspace import _source_files, prepare
    from database import select_database
    from config_store import save_config
    from access_policy import defaults, using, current
    from model_assets import viewer_bundle
    source = Path(directory) / 'SMELTER-DEMO'
    source.mkdir(exist_ok=False)
    for relative, path in _source_files(Path(repository)).items():
        destination = source / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(path.read_bytes())
    select_database(source, str(source.with_name(source.name + '-Data').resolve()))
    save_config(source, 'sandbox.json', {'schema_version': 1, **images})
    save_config(source, 'runtime_settings.json', {'schema_version': 1, 'settings': {
        'context_tokens': 16384, 'max_output_tokens': 1024, 'timeout_seconds': 180, 'thinking': False}})
    policy = defaults(source)
    policy['locations'].append({'id': 'smoke-input', 'name': 'Smoke inventory (read only)',
        'path': fixtures['inventory']['path'], 'read': True, 'write': False, 'execute': False,
        'operations': [], 'exclusions': [], 'enabled': True})
    save_config(source, 'access_policy.json', policy)
    if ecc_manifests:
        from install_ecc_skills import REPOSITORY
        from skill_collections import install_collection
        selected = [{key: m[key] for key in ('id', 'url', 'sha256')} for m in ecc_manifests]
        cache = {m['url']: m for m in ecc_manifests}
        install_collection(source, REPOSITORY, selected, approval=True, discover=cache.__getitem__)
    with using(current(source)):
        workspace = prepare(source, {})
    try:
        bundle = viewer_bundle(repository)
    except (OSError, ValueError) as exc:
        viewer = {'status': 'BLOCKED', 'reason': str(exc)}
    else:
        relative = '.smelter/tooling/model-viewer/node_modules/@google/model-viewer'
        for root in (source, Path(workspace['target'])):
            package = root / relative
            (package / 'dist').mkdir(parents=True, exist_ok=True)
            shutil.copyfile(bundle, package / 'dist/model-viewer.min.js')
            shutil.copyfile(bundle.parent.parent / 'package.json', package / 'package.json')
        viewer = {'status': 'PASS', 'version': '4.1.0'}
    return {'source': str(source.resolve()), 'target': workspace['target'],
            'database': str(source.with_name(source.name + '-Data').resolve()),
            'port': 8780, 'preview_port': 8770, 'viewer': viewer,
            'launch_argv': [sys.executable, str(source / 'tools/dashboard/dashboard.py'), '--port', '8780', '--no-browser'],
            'started': False, 'existing_source_and_v2_preserved': True}
