"""Operator-only offline Lua 5.4 bridge checks; never load a game or RPH.

Compiles/runs the reviewed fixture, not a gameplay plugin. No arbitrary commands.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/dashboard'))
import acceptance_contracts as acceptance
import build_managed_mod as managed
import coding_workspace as cw
import install_managed_sdk as sdk
from python_tools import _plain_path

SUBJECTS = {'entity_policy': 'entity-policy-v1', 'predator_controller': 'predator-controller-v1',
            'engine_adapter': 'provider-admission-v1', 'raptor_system_main': 'predator-system-v1'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def prepare(root, folder, target):
    """Snapshot operator fixtures, four pure modules and unchanged frozen verifiers."""
    root, folder, target = map(lambda p: _plain_path(Path(p).resolve()), (root, folder, target))
    if folder.exists():
        raise ValueError('Choose a new fixture output folder')
    dependency = sdk.inspect(root, 'keralua')
    folder.mkdir(parents=True)
    hashes = {}
    for name in ['KeraLua.dll', 'lua54.dll', 'LICENSE']:
        source = _plain_path(Path(dependency['files'][name]))
        (folder / name).write_bytes(source.read_bytes())
        hashes[name] = digest(folder / name)
    for name in ['subjects', 'contracts', 'driver']:
        (folder / name).mkdir()
    for subject, identity in SUBJECTS.items():
        source = _plain_path(target / 'mods/gta-ark/Mods/GtaArkLink/Scripts' / (subject + '.lua'))
        if source.stat().st_size > 131072:
            raise ValueError('Oversized contract subject')
        (folder / 'subjects' / source.name).write_bytes(source.read_bytes())
        verifier = _plain_path(root / 'tools/dashboard/acceptance' / acceptance.DEFINITIONS[identity]['verifier'])
        (folder / 'contracts' / verifier.name).write_bytes(verifier.read_bytes())
    files = ['mods/gta-ark/common/managed/LuaModuleHost.cs', 'tools/setup/fixtures/LuaHostFixture.cs']
    for name in files:
        source = _plain_path(root / name)
        (folder / 'driver' / source.name).write_bytes(source.read_bytes())
    compiler, refs, release = managed.compiler()
    exe = folder / 'LuaHostFixture.exe'
    args = [str(compiler), *[flag for flag in managed.FLAGS if flag != '/target:library'],
            '/target:exe', '/out:' + str(exe), *['/reference:' + str(p) for p in refs],
            '/reference:' + str(folder / 'KeraLua.dll'),
            *[str(folder / 'driver' / Path(name).name) for name in files]]
    result = subprocess.run(args, cwd=folder, capture_output=True, timeout=30,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    (folder / 'compile.log').write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise ValueError((result.stdout + result.stderr).decode(errors='replace'))
    return {'sdk': {'id': 'keralua', 'version': dependency['version'],
                    'package_sha256': dependency['package_sha256']},
            'runtime_files': hashes, 'compiler_sha256': digest(compiler), 'framework_release': release,
            'snapshot_hashes': {str(p.relative_to(folder)).replace('\\', '/'): digest(p)
                                for name in ['subjects', 'contracts', 'driver'] for p in (folder / name).iterdir()},
            'fixture_sha256': digest(exe), 'game_runtime_verified': False, 'rph_loaded': False}


def execute(folder, mode, snapshot=None):
    if mode not in ('gameplay', 'boundaries', 'failures', 'contracts'):
        raise ValueError('Unsupported reviewed fixture mode')
    folder = _plain_path(Path(folder).resolve())
    result = subprocess.run([str(folder / 'LuaHostFixture.exe'), mode, str(snapshot or folder)],
                            cwd=folder, capture_output=True, timeout=15,
                            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    output = (result.stdout + result.stderr).decode('utf-8', errors='replace')
    return {'exit_code': result.returncode, 'output': output}


def mutant_snapshot(folder):
    """A disposable missing-attack mutant must fail the unchanged frozen tests."""
    folder = Path(folder)
    target = folder / 'mutant'
    if target.exists():
        raise ValueError('Mutant fixture already exists')
    target.mkdir()
    for name in ['subjects', 'contracts']:
        shutil.copytree(folder / name, target / name)
    path = target / 'subjects/predator_controller.lua'
    text = path.read_text(encoding='utf-8')
    old = 'call(deps.adapter.attack, actor_id, s.target)'
    if text.count(old) != 1:
        raise ValueError('Current controller needs a reviewed attack mutation anchor')
    path.write_text(text.replace(old, 'true, "mutant_without_attack"'), encoding='utf-8')
    return target


def check(root=ROOT, workspace_id=None):
    root = _plain_path(Path(root).resolve())
    target = root if workspace_id is None else cw.load(root, workspace_id)[1]
    base = _plain_path(root / '.smelter/managed-lua-runs')
    base.mkdir(parents=True, exist_ok=True)
    if len(list(base.iterdir())) >= 20:
        raise ValueError('Review retained Lua bridge runs before creating more than twenty')
    folder = base / str(uuid4())
    result = prepare(root, folder, target)
    result.update(schema_version=1, scope='Offline managed Lua54 fixture only, not native game evidence',
                  workspace_id=workspace_id, stage='ERROR', checks={})
    receipt = folder / 'receipt.json'
    try:
        for mode in ['boundaries', 'failures', 'gameplay', 'contracts']:
            observed = execute(folder, mode)
            (folder / (mode + '.log')).write_text(observed['output'], encoding='utf-8')
            result['checks'][mode] = {'exit_code': observed['exit_code'], 'log_sha256': digest(folder / (mode + '.log'))}
            if observed['exit_code']:
                raise ValueError('Managed Lua fixture failed: ' + mode)
            if mode == 'contracts':
                counts = [json.loads(s) for s in re.findall(r'SMELTER_ACCEPTANCE_CHECKS\|([^\r\n]+)', observed['output'])]
                expected = [acceptance.DEFINITIONS[identity]['checks'] for identity in SUBJECTS.values()]
                if [c['checks'] for c in counts] != expected or any(c['failures'] for c in counts):
                    raise ValueError('Frozen contract evidence missing or changed')
                result['checks'][mode]['counts'] = counts
        observed = execute(folder, 'contracts', mutant_snapshot(folder))
        (folder / 'mutant.log').write_text(observed['output'], encoding='utf-8')
        if observed['exit_code'] == 0 or '[ACCEPTANCE FAIL]' not in observed['output']:
            raise ValueError('Missing-attack mutant was not rejected by frozen acceptance')
        result['checks']['missing_attack_mutant'] = {'expected_failure': True, 'exit_code': observed['exit_code'], 'log_sha256': digest(folder / 'mutant.log')}
        result['stage'] = 'GREEN'
    finally:
        receipt.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return {**result, 'receipt': str(receipt)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace-id')
    args = parser.parse_args()
    print(json.dumps(check(ROOT, args.workspace_id), indent=2))
