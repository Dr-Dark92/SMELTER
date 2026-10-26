"""Freeze prototype sources and run Python/Lua checks without network or games."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]


def smoke():
    docker = shutil.which('docker')
    if not docker: raise ValueError('Existing Docker CLI/toolchain required')
    image = subprocess.run([docker, 'image', 'inspect', 'smelter-cpp:2', '--format', '{{.Id}}'], capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    output = ROOT / '.smelter/mod-runtime-runs' / str(uuid4())
    source = output / 'source/mods/gta-ark'
    source.mkdir(parents=True, exist_ok=False)
    original = ROOT / 'mods/gta-ark'
    suffixes = {'.py', '.lua', '.json', '.hex', '.txt', '.md', '.cpp', '.h', '.bat'}
    hashes = {}
    for path in original.rglob('*'):
        relative = path.relative_to(original)
        if {'build', '__pycache__'} & set(relative.parts) or path.suffix not in suffixes: continue
        if path.is_symlink(): raise ValueError('Linked prototype sources are unsupported')
        if not path.is_file(): continue
        raw = path.read_bytes()
        if len(raw) > 128 * 1024: raise ValueError('Oversized prototype source')
        destination = source / relative; destination.parent.mkdir(parents=True, exist_ok=True); destination.write_bytes(raw)
        hashes[relative.as_posix()] = hashlib.sha256(raw).hexdigest()
    report = {'status': 'failed', 'image': image, 'source_hashes': hashes, 'checks': [],
              'game_runtime_verified': False, 'game_files_modified': False, 'sandbox': 'docker-no-network', 'path': str(output)}
    commands = [['python', '-I', '-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'],
                ['lua5.4', 'tests/test_gal_link.lua'], ['lua5.4', 'tests/test_ark_runtime.lua']]
    for index, command in enumerate(commands):
        name = 'smelter-mod-smoke-' + uuid4().hex
        args = [docker, 'run', '--rm', '--name', name, '--label', 'smelter.purpose=gta-ark-offline-smoke', '--pull', 'never', '--network', 'none', '--read-only', '--cap-drop', 'ALL',
                '--security-opt', 'no-new-privileges', '--pids-limit', '64', '--memory', '256m', '--cpus', '1',
                '--user', '65534:65534', '--mount', 'type=bind,source='+str(source)+',target=/work,readonly',
                '--tmpfs', '/tmp:rw,noexec,nosuid,nodev,size=32m,mode=1777', '--workdir', '/work', image, *command]
        try:
            done = subprocess.run(args, capture_output=True, timeout=60)
            raw, exit_code = done.stdout + done.stderr, done.returncode
        except subprocess.TimeoutExpired as exc:
            raw, exit_code = (exc.stdout or b'') + (exc.stderr or b'') + b'\nSmoke deadline reached\n', 124
        finally:
            # Only this invocation's exact generated container is removed.
            subprocess.run([docker, 'rm', '--force', name], capture_output=True, timeout=10)
        log = output / ('check-'+str(index)+'.log'); log.write_bytes(raw)
        report['checks'].append({'command': command, 'exit_code': exit_code, 'log': str(log), 'log_sha256': hashlib.sha256(raw).hexdigest()})
    report['source_unchanged'] = all(hashlib.sha256((original / name).read_bytes()).hexdigest() == digest for name, digest in hashes.items())
    if report['source_unchanged'] and all(row['exit_code'] == 0 for row in report['checks']): report['status'] = 'passed'
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    result = smoke(); print(json.dumps({key: value for key, value in result.items() if key != 'source_hashes'}, indent=2))
    raise SystemExit(0 if result['status'] == 'passed' else 1)
