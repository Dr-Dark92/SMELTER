"""Inventory a downloaded loader/runtime folder or zip before any deployment.

Operator-only and read-only: members are hashed in place (zip members are read,
never extracted) and nothing is executed. PE file versions are read from the
VS_FIXEDFILEINFO block, so the record identifies exactly what a person chose.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import struct
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
MAX_MEMBERS = 2000
MAX_TOTAL = 512 * 1024 * 1024
PE_SUFFIXES = ('.exe', '.dll', '.asi')
FIXED_SIGNATURE = struct.pack('<I', 0xFEEF04BD)


def pe_version(data):
    """Return 'a.b.c.d' from VS_FIXEDFILEINFO, or None when the file has no version resource."""
    if data[:2] != b'MZ':
        return None
    at = data.find(FIXED_SIGNATURE)
    if at < 0 or at + 16 > len(data):
        return None
    _sig, _struct, ms, ls = struct.unpack_from('<IIII', data, at)
    return '%d.%d.%d.%d' % (ms >> 16, ms & 0xFFFF, ls >> 16, ls & 0xFFFF)


def _entry(name, data):
    entry = {'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    if name.lower().endswith(PE_SUFFIXES):
        entry['file_version'] = pe_version(data)
    return entry


def inventory(source):
    source = Path(source)
    entries, total = [], 0
    if source.is_file() and zipfile.is_zipfile(source):
        with zipfile.ZipFile(source) as archive:
            members = [m for m in archive.infolist() if not m.is_dir()]
            if len(members) > MAX_MEMBERS:
                raise ValueError('Archive has more than %d members' % MAX_MEMBERS)
            for member in members:
                total += member.file_size
                if total > MAX_TOTAL:
                    raise ValueError('Archive content exceeds 512 MiB')
                entries.append(_entry(str(PurePosixPath(member.filename)), archive.read(member)))
        kind = 'zip'
    elif source.is_dir():
        files = sorted(p for p in source.rglob('*') if p.is_file())
        if len(files) > MAX_MEMBERS:
            raise ValueError('Folder has more than %d files' % MAX_MEMBERS)
        for path in files:
            total += path.stat().st_size
            if total > MAX_TOTAL:
                raise ValueError('Folder content exceeds 512 MiB')
            entries.append(_entry(path.relative_to(source).as_posix(), path.read_bytes()))
        kind = 'folder'
    else:
        raise ValueError('Expected a folder or a zip archive: ' + str(source))
    container = hashlib.sha256(source.read_bytes()).hexdigest() if kind == 'zip' else None
    return {'schema_version': 1, 'inspected_at': datetime.now(timezone.utc).isoformat(), 'source': str(source),
            'kind': kind, 'archive_sha256': container, 'files': entries, 'executed': False, 'extracted': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', help='Downloaded runtime folder or zip')
    parser.add_argument('--label', default='runtime', help='Short name for the saved inventory')
    parser.add_argument('--root', default=str(ROOT))
    args = parser.parse_args(argv)
    if not args.label.replace('-', '').replace('_', '').isalnum():
        raise SystemExit('Label must be letters, digits, - or _')
    value = inventory(args.source)
    folder = Path(args.root) / '.smelter' / 'runtime-inventories'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (args.label + '-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    with open(path, 'x', encoding='utf-8') as out:
        json.dump(value, out, indent=2)
    executables = [e for e in value['files'] if 'file_version' in e]
    print(json.dumps({'inventory': str(path), 'files': len(value['files']), 'executables': executables}, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
