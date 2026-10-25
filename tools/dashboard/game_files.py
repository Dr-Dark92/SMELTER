"""Read-only game file header inspection inside an approved inventory folder.

Reads only fixed header/footer bytes of archives and PE section samples: archive
format and encryption flags (RAGE RPF7, Unreal .pak, Unreal IoStore .utoc) and
executable section entropy (high entropy alone proves neither packing nor encryption). Never
extracts, decrypts, decompiles or executes anything.
"""
import collections
import math
import os
import stat
import struct
import time
from pathlib import Path

MAX_DEPTH = 8
MAX_VISITED = 20000
MAX_ARCHIVES = 400
MAX_EXECUTABLES = 6
SECTION_SAMPLE = 1024 * 1024
DEADLINE_SECONDS = 20
RPF_ENCRYPTION = {0x4E45504F: 'none (OPEN)', 0x0FFFFFF9: 'AES', 0x0FEFFFFF: 'NG'}


def rpf_header(path):
    with open(path, 'rb') as f:
        head = f.read(16)
    if len(head) < 16 or head[:4] != b'7FPR':
        return {'format': 'unknown', 'magic_found': False}
    _, entries, _, encryption = struct.unpack('<4I', head)
    return {'format': 'RPF7', 'magic_found': True, 'entries': entries,
            'encryption': RPF_ENCRYPTION.get(encryption, 'unknown 0x%08X' % encryption)}


def pak_footer(path):
    size = os.path.getsize(path)
    with open(path, 'rb') as f:
        f.seek(max(0, size - 512))
        tail = f.read()
    i = tail.rfind(struct.pack('<I', 0x5A6F12E1))
    if i < 17 or i + 8 > len(tail):
        return {'format': 'unknown', 'magic_found': False}
    return {'format': 'Unreal pak', 'magic_found': True, 'version': struct.unpack('<I', tail[i + 4:i + 8])[0],
            'encrypted_index': tail[i - 1] != 0, 'encryption_key_guid_set': any(tail[i - 17:i - 1])}


def utoc_header(path):
    with open(path, 'rb') as f:
        head = f.read(96)
    if head[:16] != b'-==--==--==--==-' or len(head) < 81:
        return {'format': 'unknown', 'magic_found': False}
    flags = head[80]
    return {'format': 'Unreal IoStore', 'magic_found': True, 'version': head[16],
            'compressed': bool(flags & 1), 'encrypted': bool(flags & 2), 'signed': bool(flags & 4),
            'indexed': bool(flags & 8), 'encryption_key_guid_set': any(head[64:80])}


def pe_sections(path, deadline=None):
    with open(path, 'rb') as f:
        head = f.read(4096)
        if head[:2] != b'MZ' or len(head) < 0x40:
            return {'format': 'not PE'}
        pe = struct.unpack_from('<I', head, 0x3C)[0]
        if pe + 24 > len(head) or head[pe:pe + 4] != b'PE\0\0':
            return {'format': 'not PE'}
        count, optional = struct.unpack_from('<H', head, pe + 6)[0], struct.unpack_from('<H', head, pe + 20)[0]
        base, sections = pe + 24 + optional, []
        for n in range(min(count, 32)):
            if deadline is not None and time.monotonic() > deadline:
                return {'format': 'PE', 'sections': sections, 'sample_incomplete': True}
            raw = head[base + 40 * n: base + 40 * n + 40]
            if len(raw) < 40:
                break
            size, offset = struct.unpack_from('<II', raw, 16)
            f.seek(offset)
            sample = f.read(min(size, SECTION_SAMPLE)) if size else b''
            counts = collections.Counter(sample)
            entropy = -sum(c / len(sample) * math.log2(c / len(sample)) for c in counts.values()) if sample else 0.0
            sections.append({'name': raw[:8].rstrip(b'\0').decode('latin1'), 'raw_bytes': size,
                             'entropy_sample': round(entropy, 2)})
    return {'format': 'PE', 'sections': sections,
            'note': 'High sample entropy is consistent with compression, encryption or other high-entropy data; it does not establish packing, encryption or a protector.'}


READERS = {'.rpf': rpf_header, '.pak': pak_footer, '.utoc': utoc_header}


def inspect(grants, arguments):
    from python_tools import _plain_path
    from access_policy import require, allowed
    if not grants.get('inventory_root'):
        raise ValueError('Folder inspection was not approved for this message')
    if set(arguments) - {'relative_path', 'max_depth'}:
        raise ValueError('Unknown inspection argument')
    relative, depth_limit = arguments.get('relative_path'), arguments.get('max_depth', 4)
    if type(depth_limit) is not int or not 0 <= depth_limit <= MAX_DEPTH:
        raise ValueError('Invalid inspection depth')
    if not isinstance(relative, str) or not relative or len(relative) > 500 or '\\' in relative or ':' in relative:
        raise ValueError('Use a relative path with forward slashes')
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('Path escapes approved folder')
    approved = Path(grants['inventory_root'])
    target = _plain_path(approved / relative).resolve(strict=True)
    require(target, 'read')
    if not target.is_relative_to(approved) or not target.is_dir():
        raise ValueError('Inspection target must be a directory inside approved folder')
    deadline = time.monotonic() + DEADLINE_SECONDS
    pending, visited, reasons = [(target, 0)], 0, set()
    archives, executables, totals = [], [], collections.Counter()
    while pending:
        if visited >= MAX_VISITED or time.monotonic() > deadline:
            reasons.add('entry_scan_limit' if visited >= MAX_VISITED else 'time_limit')
            break
        folder, depth = pending.pop()
        try:
            with os.scandir(folder) as entries:
                for entry in entries:
                    if visited >= MAX_VISITED or time.monotonic() > deadline:
                        reasons.add('entry_scan_limit' if visited >= MAX_VISITED else 'time_limit')
                        break
                    visited += 1
                    info = entry.stat(follow_symlinks=False)
                    path = Path(entry.path)
                    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                        reasons.add('links_skipped')
                        continue
                    if not allowed(path, 'read'):
                        reasons.add('policy_exclusion')
                        continue
                    if stat.S_ISDIR(info.st_mode):
                        if depth < depth_limit:
                            pending.append((path, depth + 1))
                        else:
                            reasons.add('depth_limit')
                        continue
                    suffix = path.suffix.lower()
                    if suffix in READERS:
                        totals[suffix] += 1
                        if len(archives) < MAX_ARCHIVES:
                            archives.append((path, info.st_size, suffix))
                        else:
                            reasons.add('archive_header_limit')
                    elif suffix == '.exe':
                        executables.append((info.st_size, path))
        except OSError:
            reasons.add('filesystem_error')
    summary, samples = collections.Counter(), []
    for path, size, suffix in archives:
        if time.monotonic() > deadline:
            reasons.add('time_limit')
            break
        try:
            _plain_path(path)
            require(path, 'read')
            header = READERS[suffix](path)
        except (OSError, ValueError, struct.error):
            header = {'format': 'unreadable'}
        key = ' '.join('%s=%s' % (k, header[k]) for k in sorted(header) if k not in ('entries',))
        summary[suffix + ' ' + key] += 1
        if len(samples) < 6:
            samples.append({'path': path.relative_to(approved).as_posix(), 'bytes': size, **header})
    exe_reports = []
    for size, path in sorted(executables, reverse=True)[:MAX_EXECUTABLES]:
        if time.monotonic() > deadline:
            reasons.add('time_limit')
            break
        try:
            _plain_path(path)
            require(path, 'read')
            report = pe_sections(path, deadline=deadline)
        except OSError:
            report = {'format': 'unreadable'}
        exe_reports.append({'path': path.relative_to(approved).as_posix(), 'bytes': size, **report})
        if report.get('sample_incomplete'):
            reasons.add('time_limit')
    return {'status': 'game_files_inspected', 'approved_root': str(approved), 'relative_path': relative,
            'archive_counts': dict(totals), 'archive_header_summary': [{'kind': k, 'count': c} for k, c in summary.most_common(20)],
            'archive_samples': samples, 'largest_executables': exe_reports,
            'scan_complete': not reasons, 'scan_stop_reasons': sorted(reasons),
            'scope': 'Header bytes and section samples only; no extraction, decryption, decompilation or execution. '
                     'Encryption flags describe container metadata, not whether individual assets can be converted.'}
