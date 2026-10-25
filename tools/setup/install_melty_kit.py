"""Install a verified Melty kit as data inside this checkout; never execute it."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
URL = 'https://melty.gg/api/kit/modding-kit'
CDN_HOST = 'ekvzctwehmwidsengayc.storage.supabase.co'
CDN_PATH = '/storage/v1/s3/melty-mods/mods/kit/modding-kit/739f3496657b87ef8247b867affb289e1874e50580bd3db4e76cbcf23dab26e4.tar.gz'
PIN = {
    'name': "Melty's modding kit",
    'version': '2026.10.18-739f3496',
    'hash': '739f3496657b87ef8247b867affb289e1874e50580bd3db4e76cbcf23dab26e4',
    'archive_sha256': '907ea7f3ed2d4c3443c9f3190f5070db0e77a9c910c50eeaaedf6cd1694f9935',
    'files': 555,
    'bytes': 23282319,
}
MAX_ARCHIVE = 32 * 1024 * 1024
MAX_EXPANDED = 40 * 1024 * 1024
MAX_MEMBER = 16 * 1024 * 1024
MAX_MEMBERS = 2048
MAX_MANIFEST = 256 * 1024
METADATA = {'MELTY-KIT.json', 'MELTY.md'}
RECEIPT = '.smelter-melty-install.json'
RESERVED = re.compile(r'(?i)^(?:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?$')


def _plain(path):
    """Do not follow symlinks or Windows junction/reparse points in any ancestor."""
    import stat
    path = Path(path)
    for part in (path, *path.parents):
        if part.exists() or part.is_symlink():
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                raise ValueError('Links and reparse points are not allowed in the kit install path')
    return path


def destination(root=ROOT):
    root = Path(root)
    if not root.is_absolute() or '..' in root.parts or str(root).startswith(('\\\\', '//')):
        raise ValueError('Checkout must be an absolute local path without traversal')
    return _plain(root / '.smelter/tooling/melty')


def _relative(name):
    if not isinstance(name, str) or not name or len(name) > 500 or '\\' in name or ':' in name or any(ord(c) < 32 for c in name):
        raise ValueError('Unsafe archive member path')
    path = PurePosixPath(name)
    if path.is_absolute() or name.startswith('/') or any(p in ('', '.', '..') or p.endswith(('.', ' ')) or RESERVED.fullmatch(p) for p in name.split('/')):
        raise ValueError('Unsafe archive member path')
    return path.as_posix()


def _digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk := stream.read(65536):
            result.update(chunk)
    return result.hexdigest()


def _allowed_download_url(value):
    parts = urlsplit(value)
    return value == URL or (parts.scheme == 'https' and parts.netloc == CDN_HOST
                            and parts.path == CDN_PATH and not parts.fragment)


class _OfficialRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # The public Melty endpoint issues one signed URL for this exact pinned
        # archive. Never forward credentials, follow another host/path, or chain.
        if req.full_url != URL or not _allowed_download_url(newurl):
            return None
        return Request(newurl, headers={'User-Agent': 'SMELTER-Melty-kit-installer'})


def _download(path, *, opener=None):
    opener = opener or build_opener(ProxyHandler({}), _OfficialRedirect()).open
    request = Request(URL, headers={'User-Agent': 'SMELTER-Melty-kit-installer'})
    total = 0
    with opener(request, timeout=30) as response, Path(path).open('xb') as output:
        if not _allowed_download_url(getattr(response, 'geturl', lambda: URL)()):
            raise ValueError('Melty kit redirect destination is not approved')
        while chunk := response.read(65536):
            total += len(chunk)
            if total > MAX_ARCHIVE:
                raise ValueError('Melty compressed archive exceeds 32 MiB')
            output.write(chunk)
    return total


def _manifest(raw):
    if len(raw) > MAX_MANIFEST:
        raise ValueError('Melty kit manifest exceeds 256 KiB')
    value = json.loads(raw)
    if not isinstance(value, dict) or any(value.get(key) != PIN[key] for key in ('name', 'version', 'hash', 'files', 'bytes')) or any(type(value.get(key)) is not int for key in ('files', 'bytes')):
        raise ValueError('Melty kit manifest differs from the requirements pin')
    hashes = value.get('fileHashes')
    if not isinstance(hashes, dict) or len(hashes) != PIN['files']:
        raise ValueError('Melty kit file hash inventory is incomplete')
    keys = set()
    for name, digest in hashes.items():
        _relative(name)
        if name.casefold() in keys or name in METADATA or name == RECEIPT or not isinstance(digest, str) or not re.fullmatch(r'[a-f0-9]{64}', digest):
            raise ValueError('Invalid Melty file hash inventory')
        keys.add(name.casefold())
    return value


def _extract(archive, staging):
    files = {}
    seen = set()
    total = 0
    with tarfile.open(archive, mode='r:gz') as source:
        for index, member in enumerate(source):
            if index >= MAX_MEMBERS:
                raise ValueError('Melty archive has too many members')
            name = _relative(member.name.rstrip('/') if member.isdir() else member.name)
            if name.casefold() in seen:
                raise ValueError('Melty archive contains duplicate/colliding paths')
            seen.add(name.casefold())
            if not member.isdir() and not member.isfile():
                raise ValueError('Melty archive links and special files are forbidden')
            if member.size < 0 or member.size > MAX_MEMBER:
                raise ValueError('Melty archive member exceeds the size limit')
            total += member.size
            if total > MAX_EXPANDED:
                raise ValueError('Melty expanded archive exceeds 40 MiB')
            if member.isfile():
                files[name] = member
        info = files.get('MELTY-KIT.json')
        if info is None or info.size > MAX_MANIFEST:
            raise ValueError('Melty archive has no bounded root manifest')
        data = _manifest(source.extractfile(info).read(MAX_MANIFEST + 1))
        hashes = data['fileHashes']
        if set(files) != set(hashes) | METADATA:
            raise ValueError('Melty archive contents differ from the declared file inventory')
        if sum(files[name].size for name in hashes) != PIN['bytes']:
            raise ValueError('Melty archive declared byte count differs')
        metadata_hashes = {}
        for name, member in files.items():
            path = staging / name
            path.parent.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha256()
            count = 0
            with source.extractfile(member) as input_stream, path.open('xb') as output:
                while chunk := input_stream.read(65536):
                    count += len(chunk)
                    if count > member.size:
                        raise ValueError('Melty member exceeds its declared size')
                    output.write(chunk)
                    digest.update(chunk)
            if count != member.size or name in hashes and digest.hexdigest() != hashes[name]:
                raise ValueError('Melty kit content checksum mismatch: ' + name)
            if name in METADATA:
                metadata_hashes[name] = digest.hexdigest()
            path.chmod(0o644)
    return metadata_hashes


def check(root=ROOT):
    target = destination(root)
    if not target.exists():
        return {'status': 'missing', 'directory': str(target), 'installed': False, 'executed': False}
    if not target.is_dir():
        raise ValueError('Melty kit destination is not a directory')
    path = _plain(target / 'MELTY-KIT.json')
    if not path.is_file() or path.stat().st_size > MAX_MANIFEST:
        raise ValueError('Existing Melty kit has no bounded manifest; refusing overwrite')
    value = _manifest(path.read_bytes())
    receipt_path = _plain(target / RECEIPT)
    if not receipt_path.is_file() or receipt_path.stat().st_size > 8192:
        raise ValueError('Existing Melty kit has no installation receipt; refusing overwrite')
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    if not isinstance(receipt, dict) or receipt.get('archive_sha256') != PIN['archive_sha256'] or not isinstance(receipt.get('metadata_sha256'), dict) or set(receipt['metadata_sha256']) != METADATA:
        raise ValueError('Existing Melty kit receipt differs from the pin')
    expected = {**value['fileHashes'], **receipt['metadata_sha256']}
    found = set()
    for item in target.rglob('*'):
        _plain(item)
        if item.is_dir():
            continue
        relative = item.relative_to(target).as_posix()
        found.add(relative)
        if relative == RECEIPT:
            continue
        if relative not in expected or not item.is_file() or item.stat().st_size > MAX_MEMBER or _digest(item) != expected[relative]:
            raise ValueError('Existing Melty kit is divergent; refusing overwrite: ' + relative)
    if found != set(expected) | {RECEIPT}:
        raise ValueError('Existing Melty kit is incomplete; refusing overwrite')
    return {'status': 'installed', 'directory': str(target), 'installed': True,
            'version': PIN['version'], 'content_hash': PIN['hash'],
            'archive_sha256': PIN['archive_sha256'], 'verified_files': len(expected),
            'connected': False, 'executed': False}


def install(root=ROOT, *, archive=None, downloader=_download):
    target = destination(root)
    if target.exists():
        return {**check(root), 'status': 'already_installed'}
    target.parent.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(target.parent).free < MAX_EXPANDED + MAX_ARCHIVE + 16 * 1024 * 1024:
        raise ValueError('Insufficient disk space for verified Melty kit staging')
    with tempfile.TemporaryDirectory(prefix='melty-stage-', dir=target.parent) as temporary:
        stage = Path(temporary)
        archive_path = Path(archive) if archive is not None else stage / 'kit.tar.gz'
        if archive is None:
            downloader(archive_path)
        if not archive_path.is_file() or archive_path.stat().st_size > MAX_ARCHIVE:
            raise ValueError('Melty compressed archive is missing or oversized')
        digest = _digest(archive_path)
        if digest != PIN['archive_sha256']:
            raise ValueError('Melty archive SHA-256 differs from the requirements pin; nothing installed')
        output = stage / 'kit'
        output.mkdir()
        metadata = _extract(archive_path, output)
        receipt = {'schema_version': 1, 'source': URL, 'version': PIN['version'],
                   'content_hash': PIN['hash'], 'archive_sha256': digest,
                   'archive_bytes': archive_path.stat().st_size, 'metadata_sha256': metadata,
                   'executed': False}
        (output / RECEIPT).write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
        if target.exists():
            raise ValueError('Melty destination appeared during staging; refusing overwrite')
        output.rename(target)
    return {**check(root), 'status': 'installed'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--check', action='store_true', help='Verify an existing checkout-local install without network')
    parser.add_argument('--archive', type=Path, help='Use an existing archive only if its SHA-256 matches the official pin')
    args = parser.parse_args()
    if args.check and args.archive is not None:
        parser.error('--check and --archive cannot be combined')
    try:
        result = check(args.root) if args.check else install(args.root, archive=args.archive)
    except (OSError, ValueError, tarfile.TarError) as exc:
        print(json.dumps({'status': 'failed', 'error': str(exc)[:1000], 'executed': False}))
        return 1
    print(json.dumps(result, indent=2))
    return 0 if result['installed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
