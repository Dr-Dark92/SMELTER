"""Verify portable engine CLIs and build their private Linux container. No global install.

Only --select writes the selected immutable engine_image after an idle check.
Does not register game folders, change model settings or grant game write access.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/dashboard'))
MAX_ARCHIVE = 80 * 1024 * 1024
MAX_EXPANDED = 256 * 1024 * 1024


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract(archive, destination, prefix=''):
    """Validate the entire archive before creating any output; never extract links."""
    destination = Path(destination)
    if destination.exists():
        raise ValueError('Release destination already exists')
    is_zip = zipfile.is_zipfile(archive)
    with zipfile.ZipFile(archive) if is_zip else tarfile.open(archive) as source:
        members = source.infolist() if is_zip else source.getmembers()
        if len(members) > 2000:
            raise ValueError('Too many release members')
        seen, files, size = set(), [], 0
        for member in members:
            name = member.orig_filename if is_zip else member.name
            p = PurePosixPath(name)
            mode = member.external_attr >> 16 if is_zip else member.mode
            if not name or '\\' in name or any(ord(c) < 32 for c in name) or p.is_absolute() or any(
                    part in ('.', '..') or ':' in part or part.endswith((' ', '.')) or
                    part.split('.')[0].upper() in {'CON','PRN','AUX','NUL',*[f'COM{i}' for i in range(10)],*[f'LPT{i}' for i in range(10)]}
                    for part in name.rstrip('/').split('/')):
                raise ValueError('Unsafe release member')
            if (is_zip and stat.S_ISLNK(mode)) or (not is_zip and not (member.isfile() or member.isdir())):
                raise ValueError('Release links/special files are not allowed')
            directory = member.is_dir() if is_zip else member.isdir()
            if directory:
                continue
            if prefix and not name.startswith(prefix):
                raise ValueError('Unexpected release prefix')
            relative = name[len(prefix):]
            if not relative or relative.casefold() in seen:
                raise ValueError('Duplicate release member')
            seen.add(relative.casefold())
            length = member.file_size if is_zip else member.size
            size += length
            if size > MAX_EXPANDED or length > MAX_EXPANDED:
                raise ValueError('Release exceeds expansion budget')
            files.append((member, relative))
        if any(any(str(parent).casefold() in seen for parent in PurePosixPath(name).parents if str(parent) != '.') for _, name in files):
            raise ValueError('Release file/directory collision')
        for member, relative in files:
            path = destination / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with source.open(member) if is_zip else source.extractfile(member) as stream:
                path.write_bytes(stream.read(MAX_EXPANDED + 1))


def install(root=ROOT, *, select=False):
    from python_tools import _plain_path
    from process_runner import run
    root = _plain_path(Path(root).resolve())
    lock_path = root / 'tools/modding/requirements-engine-cli.json'
    lock = json.loads(lock_path.read_text(encoding='utf-8'))
    base = _plain_path(root / '.smelter/tooling/engine-cli')
    base.mkdir(parents=True, exist_ok=True)
    downloads = _plain_path(root / '.smelter/downloads/engine-cli')
    downloads.mkdir(parents=True, exist_ok=True)
    docker = shutil.which('docker')
    if not docker:
        raise ValueError('Local Docker Linux containers are required')
    with tempfile.TemporaryDirectory(prefix='build-', dir=base) as stage:
        context = Path(stage)
        shutil.copyfile(lock_path, context / 'requirements-engine-cli.json')
        for name, item in lock['tools'].items():
            archive = _plain_path(downloads / item['url'].rsplit('/', 1)[1])
            if not archive.exists():
                with urllib.request.urlopen(item['url'], timeout=120) as stream:
                    raw = stream.read(MAX_ARCHIVE + 1)
                if len(raw) > MAX_ARCHIVE or hashlib.sha256(raw).hexdigest() != item['sha256']:
                    raise ValueError('Release download checksum/size mismatch: ' + name)
                archive.write_bytes(raw)
            if archive.stat().st_size > MAX_ARCHIVE or sha(archive) != item['sha256']:
                raise ValueError('Release checksum mismatch: ' + name)
            extract(archive, context / 'runtime' / name, item['prefix'])
        result = run([docker, 'build', '--platform', lock['platform'], '--network', 'none',
                      '--label', 'smelter.engine-lock-sha256=' + sha(lock_path),
                      '-f', str(root / 'tools/dashboard/Dockerfile.engine-cli'), '-t', lock['image'], str(context)],
                     timeout=300, max_output=1024*1024, text=True)
        (base / 'build.log').write_text(result.stdout + result.stderr, encoding='utf-8')
        if result.returncode:
            raise ValueError('Engine image build failed; see .smelter/tooling/engine-cli/build.log')
    image = run([docker, 'image', 'inspect', '--format', '{{.Id}}', lock['image']], timeout=10, text=True, check=True).stdout.strip()
    versions = {}
    for name, item in lock['tools'].items():
        result = run([docker, 'run', '--rm', '--pull', 'never', '--network', 'none', '--read-only',
                      '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--memory', '512m', '--pids-limit', '64',
                      '--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=128m', image,
                      '/opt/engine-cli/' + name + '/' + item['executable'], '--version'], timeout=30, max_output=16384, text=True)
        if result.returncode or item['version'] not in result.stdout:
            raise ValueError('CLI version probe failed for ' + name + ': ' + result.stderr[-500:])
        versions[name] = result.stdout.strip()
    receipt = {'schema_version': 1, 'image_id': image, 'lock_sha256': sha(lock_path),
               'dockerfile_sha256': sha(root / 'tools/dashboard/Dockerfile.engine-cli'), 'versions': versions}
    (base / 'installation.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    if select:
        from maintenance import _idle
        _idle(root)
        # Keep existing GUI rows readable by an already-running older backend.
        selected=_plain_path(base/'selection.json')
        pending=_plain_path(base/'selection.pending')
        pending.write_text(json.dumps({'schema_version':1,'image_id':image,'lock_sha256':sha(lock_path)},indent=2)+'\n',encoding='utf-8')
        pending.replace(selected)
        from sandbox import config
        if config(root)['engine_image']!=image:
            # An explicit GUI value (including null) takes priority over fallback.
            from config_store import save_config
            save_config(root,'sandbox.json',{**config(root),'engine_image':image})
    return {**receipt, 'selected': select}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--select', action='store_true')
    args = parser.parse_args()
    print(json.dumps(install(args.root, select=args.select), indent=2))
