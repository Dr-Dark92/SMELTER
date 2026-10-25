"""Install a verified Universal Modder source revision and private CLI environment.

No plugin hooks, agent configuration, game modifications or paid services are
enabled. The existing Melty kit remains untouched. The catalog is the pin source.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import urllib.request
import venv
import zipfile
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/dashboard'))
from python_tools import _plain_path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_files(source):
    result = {}
    for path in source.rglob('*'):
        relative = path.relative_to(source)
        if any(part in ('__pycache__', '.pytest_cache') for part in relative.parts):
            continue
        _plain_path(path)
        if path.is_file():
            result[relative.as_posix()] = sha(path)
    return result


def extract(archive, destination, revision):
    """Validate the complete ZIP before creating files; no overwrite or links."""
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        if len(members) > 5000 or sum(m.file_size for m in members) > 128 * 1024 * 1024:
            raise ValueError('Universal Modder source archive exceeds its budget')
        prefix = 'universal-modder-' + revision
        seen, planned = set(), []
        for member in members:
            name = member.filename
            parts = PurePosixPath(name).parts
            if not parts or parts[0] != prefix or '\\' in name or ':' in name or any(p in ('.', '..') for p in parts):
                raise ValueError('Unsafe Universal Modder archive path')
            mode = member.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise ValueError('Source archive links are not supported')
            relative = Path(*parts[1:])
            if not relative.parts:
                continue
            if any(p.endswith(('.', ' ')) or re.fullmatch(r'(?i:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?', p) for p in relative.parts):
                raise ValueError('Unsafe Windows source path')
            identity = relative.as_posix().casefold()
            if identity in seen:
                raise ValueError('Duplicate source path')
            seen.add(identity)
            if not member.is_dir():
                planned.append((member, relative))
        if destination.exists():
            raise ValueError('Source destination already exists; existing files were preserved')
        destination.mkdir(parents=True)
        for member, relative in planned:
            path = destination / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as src, path.open('xb') as out:
                shutil.copyfileobj(src, out)


def enable_runtime(root):
    """One-time registration for this fixed controller operation, preserving denials."""
    from access_policy import current, save
    policy = current(root)
    value = json.loads(json.dumps(policy.value))
    path = Path(root).resolve() / '.smelter/tooling/universal-modder'
    if any(Path(row['path']).resolve() == path for row in value['locations']):
        return 'Existing Universal Modder location policy preserved'
    if any(row['id'] == 'universal_modder_runtime' for row in value['locations']):
        raise ValueError('Universal Modder location ID conflicts with an existing policy')
    value['locations'].append({'id':'universal_modder_runtime','name':'Pinned Universal Modder CLI', 'path':str(path),
                              'read':False,'write':False,'execute':True,'operations':['modding'],
                              'exclusions':[],'enabled':True})
    save(root, value, policy.revision)
    return 'Registered fixed modding execution only; no target-folder grants added'


def install(root=ROOT, archive=None, enable=False):
    if sys.version_info < (3, 12):
        raise ValueError('The pinned Universal Modder environment requires Python 3.12+')
    root = _plain_path(Path(root).resolve())
    catalog = json.loads((root / 'system-requirements.json').read_text(encoding='utf-8'))
    pin = catalog['setup']['universal_modder']
    base = _plain_path(root / '.smelter/tooling/universal-modder')
    base.mkdir(parents=True, exist_ok=True)
    source = _plain_path(base / 'source')
    manifest = _plain_path(base / 'source-manifest.json')
    if source.exists():
        if not manifest.is_file():
            raise ValueError('Unmanaged existing Universal Modder source; preserve and review it')
        saved = json.loads(manifest.read_text())
        if saved.get('revision') != pin['revision'] or saved.get('files') != source_files(source):
            raise ValueError('Universal Modder source drift detected; no files were replaced')
    else:
        downloads = _plain_path(root / '.smelter/downloads'); downloads.mkdir(parents=True, exist_ok=True)
        archive = _plain_path(Path(archive).resolve()) if archive else downloads / ('universal-modder-' + pin['revision'] + '.zip')
        if not archive.exists():
            with urllib.request.urlopen(pin['url'], timeout=60) as response:
                raw = response.read(80 * 1024 * 1024 + 1)
            if len(raw) > 80 * 1024 * 1024:
                raise ValueError('Universal Modder download exceeds 80 MiB')
            with archive.open('xb') as stream:
                stream.write(raw)
        if sha(archive) != pin['sha256']:
            raise ValueError('Universal Modder archive checksum differs from the reviewed pin')
        stage = _plain_path(base / ('source-' + uuid4().hex))
        extract(archive, stage, pin['revision'])
        stage.rename(source)
        saved = {'revision':pin['revision'], 'archive_sha256':pin['sha256'], 'files':source_files(source)}
        manifest.write_text(json.dumps(saved, indent=2) + '\n', encoding='utf-8')
    environment = _plain_path(base / 'venv')
    python = environment / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
    if not python.is_file():
        venv.EnvBuilder(with_pip=True).create(environment)
    requirements = _plain_path(root / pin['requirements'])
    report = _plain_path(base / 'pip-report.json')
    done = subprocess.run([str(python), '-m', 'pip', 'install', '--only-binary=:all:', '--disable-pip-version-check',
                           '--report', str(report), '-r', str(requirements)], capture_output=True, text=True, timeout=240)
    if done.returncode:
        raise ValueError('Universal Modder dependency installation failed: ' + done.stderr[-2000:])
    dependencies = subprocess.run([str(python), '-m', 'pip', 'freeze', '--all'], capture_output=True, text=True, check=True, timeout=30).stdout
    (base / 'resolved-requirements.txt').write_text(dependencies, encoding='utf-8')
    code = 'import sys;sys.path.insert(0,' + repr(str(source)) + ');from um.cli import main;main()'
    checked = subprocess.run([str(python), '-I', '-B', '-c', code, '--version'], capture_output=True, text=True, timeout=20, check=True)
    if checked.stdout.strip() != 'universal-modder ' + pin['version']:
        raise ValueError('Installed Universal Modder CLI version differs from its pin')
    receipt = {'version':pin['version'], 'revision':pin['revision'], 'archive_sha256':pin['sha256'],
               'requirements_sha256':sha(requirements), 'manifest_sha256':sha(manifest),
               'source':str(source), 'python':str(python), 'cli_version':checked.stdout.strip(),
               'scope':'Private source/runtime; no global PATH, plugin, game or paid-service changes'}
    _plain_path(base / 'installation.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    if enable:
        receipt['policy'] = enable_runtime(root)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--enable', action='store_true', help='Register execution of the fixed local knowledge adapter')
    args = parser.parse_args()
    print(json.dumps(install(args.root, args.archive, args.enable), indent=2))
