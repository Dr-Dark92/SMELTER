"""Read-only game preflight and source-only staging. Never installs or launches.

inspect reads exact game executables and loader locations; stage copies only
the bundled ARK Lua source to a new application-owned package directory.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
from uuid import uuid4

MOD = Path(__file__).resolve().parents[1]
ROOT = MOD.parent.parent if MOD.parent.name == 'mods' else MOD
PAYLOAD = ('Scripts/main.lua', 'Scripts/gal_link.lua', 'enabled.txt')


def plain(path):
    path = Path(path).absolute()
    for part in (path, *path.parents):
        if part.exists() or part.is_symlink():
            info = part.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise ValueError('Linked/reparse paths are not supported: ' + str(part))
    return path


def sha256(path):
    path = plain(path)
    if not path.is_file() or path.stat().st_size > 2 * 1024**3:
        raise ValueError('Expected a bounded plain file: ' + str(path))
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): digest.update(chunk)
    return digest.hexdigest()


def file_version(path):
    """Read Windows version resources without executing the binary."""
    if os.name != 'nt': return None
    import ctypes
    from ctypes import wintypes
    version = ctypes.WinDLL('version', use_last_error=True)
    version.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    version.GetFileVersionInfoSizeW.restype = wintypes.DWORD
    version.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID]
    version.GetFileVersionInfoW.restype = wintypes.BOOL
    version.VerQueryValueW.argtypes = [wintypes.LPCVOID, wintypes.LPCWSTR, ctypes.POINTER(wintypes.LPVOID), ctypes.POINTER(wintypes.UINT)]
    version.VerQueryValueW.restype = wintypes.BOOL
    size = version.GetFileVersionInfoSizeW(str(path), None)
    if not size or size > 1024 * 1024: return None
    buffer = ctypes.create_string_buffer(size)
    if not version.GetFileVersionInfoW(str(path), 0, size, buffer): return None
    pointer, count = wintypes.LPVOID(), wintypes.UINT()
    if not version.VerQueryValueW(buffer, '\\', ctypes.byref(pointer), ctypes.byref(count)) or count.value < 52: return None
    words = ctypes.cast(pointer, ctypes.POINTER(wintypes.DWORD))
    if words[0] != 0xFEEF04BD: return None
    return '.'.join(str(n) for n in (words[2] >> 16, words[2] & 65535, words[3] >> 16, words[3] & 65535))


def fingerprint(path):
    path = plain(path)
    if not path.exists(): return {'path': str(path), 'present': False}
    return {'path': str(path), 'present': True, 'bytes': path.stat().st_size,
            'sha256': sha256(path), 'file_version': file_version(path)}


def requirements(mod=MOD):
    path = plain(Path(mod) / 'runtime_requirements.json')
    if path.stat().st_size > 16384: raise ValueError('Runtime requirements exceed size budget')
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('schema_version') != 1: raise ValueError('Unknown runtime requirements schema')
    return value


def inspect(gta_root, ark_root, *, mod=MOD):
    gta, ark = plain(gta_root), plain(ark_root)
    if not gta.is_dir() or not ark.is_dir(): raise ValueError('Choose the two existing game installation directories')
    lock = requirements(mod)
    target = fingerprint(gta / 'GTA5_Enhanced.exe')
    companion = fingerprint(ark / 'ShooterGame/Binaries/Win64/ArkAscended.exe')
    support = target.get('file_version') in lock['script_hook_v']['supported_enhanced'] if target.get('file_version') else None
    paths = {'gta': ['ScriptHookV.dll', 'dinput8.dll', 'dsound.dll', 'GtaArkLink.asi'],
             'ark': ['UE4SS.dll', 'dwmapi.dll', 'ue4ss/UE4SS.dll', 'ue4ss/Mods/GtaArkLink/Scripts/main.lua']}
    bases = {'gta': gta, 'ark': ark / 'ShooterGame/Binaries/Win64'}
    loaders = {game: [fingerprint(bases[game] / relative) for relative in names] for game, names in paths.items()}
    blockers = []
    if not target['present']: blockers.append('gta_executable_missing')
    elif support is None: blockers.append('gta_version_unknown')
    elif not support: blockers.append('gta_script_hook_version_mismatch')
    if not companion['present']: blockers.append('ark_executable_missing')
    if not loaders['gta'][0]['present']: blockers.append('script_hook_v_not_installed')
    if not any(row['present'] for row in loaders['ark'] if Path(row['path']).name == 'UE4SS.dll'):
        blockers.append('ue4ss_not_installed')
    blockers.append('ark_loader_and_game_thread_api_unverified')
    return {'schema_version': 1, 'status': 'runtime_unverified', 'observed_at': datetime.now(timezone.utc).isoformat(),
            'gta': target, 'ark': companion, 'loader_files': loaders, 'gta_version_supported_by_reviewed_shv': support,
            'requirements': lock, 'requirements_sha256': sha256(Path(mod) / 'runtime_requirements.json'),
            'blockers': blockers, 'game_runtime_verified': False, 'game_files_modified': False,
            'notes': ['File presence is not a successful loader probe.',
                      'Support uses the dated requirements snapshot, not an invented current release check.',
                      'No UE minor version is inferred from ARK file names or absent version resources.']}


def package(*, root=ROOT, mod=MOD, stage=False):
    root, mod = plain(root), plain(mod)
    source = plain(mod / 'ark/Mods/GtaArkLink')
    rows = []
    for relative in PAYLOAD:
        path = plain(source / relative)
        if path.stat().st_size > 128 * 1024: raise ValueError('Mod source exceeds package file budget')
        raw = path.read_bytes()
        rows.append({'path': 'ark/Mods/GtaArkLink/' + relative, 'bytes': len(raw),
                     'sha256': hashlib.sha256(raw).hexdigest()})
    report = {'schema_version': 1, 'kind': 'gta-ark-source-package', 'installable': False,
              'game_runtime_verified': False, 'game_files_modified': False, 'files': rows,
              'requirements_sha256': sha256(mod / 'runtime_requirements.json'),
              'blockers': ['gta_source_route_unavailable', 'ark_loader_and_game_thread_api_unverified'],
              'notes': ['ARK Lua source only. No loader DLL, GTA ASI, game asset or executable included.',
                        'This is a staging manifest, not an installation receipt.'], 'staged': False}
    if not stage: return report
    base = plain(root / '.smelter/mod-packages')
    if base.exists() and sum(1 for _ in base.iterdir()) >= 32:
        raise ValueError('Source package limit reached (32); review existing packages before staging again')
    destination = plain(base / ('gta-ark-' + str(uuid4())))
    destination.mkdir(parents=True, exist_ok=False)
    # Record intent first; partial packages remain labelled incomplete on error.
    manifest = destination / 'manifest.json'
    manifest.write_text(json.dumps({**report, 'status': 'staging'}, indent=2) + '\n', encoding='utf-8')
    for row in rows:
        relative = row['path'].removeprefix('ark/Mods/GtaArkLink/')
        raw = plain(source / relative).read_bytes()
        if hashlib.sha256(raw).hexdigest() != row['sha256']: raise ValueError('Mod source changed during staging')
        target = plain(destination / row['path']); target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream: stream.write(raw)
    report.update(staged=True, status='source_staged', path=str(destination))
    manifest.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    preflight = commands.add_parser('inspect'); preflight.add_argument('--gta', type=Path, required=True); preflight.add_argument('--ark', type=Path, required=True)
    staging = commands.add_parser('package'); staging.add_argument('--stage', action='store_true', help='Create a source-only package in .smelter/mod-packages; default prints the plan')
    args = parser.parse_args()
    try:
        value = inspect(args.gta, args.ark) if args.command == 'inspect' else package(stage=args.stage)
        print(json.dumps(value, indent=2)); return 0
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(json.dumps({'status': 'error', 'error': str(exc)})); return 2


if __name__ == '__main__': raise SystemExit(main())
