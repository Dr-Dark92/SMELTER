"""Fixed cross-compiler driver, executed only inside the confined Linux container.

The controller validates the manifest, supplies a read-only /workspace, and
accepts only bounded artifacts from stdout. No built binary is executed.
"""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import time

FLAGS = ['-std=c++17', '-Wall', '-Wextra', '-Werror', '-DUNICODE', '-D_UNICODE']
COMPILER = 'x86_64-w64-mingw32-g++'
TOTAL_SECONDS = 180
MAX_ARTIFACT = 2 * 1024 * 1024
MAX_TOTAL = 4 * 1024 * 1024


def main(targets):
    deadline = time.monotonic() + TOTAL_SECONDS
    version = subprocess.run([COMPILER, '--version'], capture_output=True, text=True, timeout=5, check=True).stdout.splitlines()[0]
    output = Path('/build')
    results, total = [], 0
    for target in targets:
        folder = output / target['name']
        folder.mkdir()
        sources = ['/workspace/' + p for p in target['sources']]
        args = [COMPILER, *FLAGS, *('-I/workspace/' + d for d in target.get('include_dirs', [])),
                *('-D' + d for d in target.get('defines', []))]
        kind = target['kind']
        if kind == 'obj':
            commands = [args + ['-c', s, '-o', str(folder / (str(i) + '_' + Path(s).stem + '.obj'))]
                        for i, s in enumerate(sources)]
        else:
            commands = [args + (['-shared'] if kind == 'asi' else [])
                        + (['-municode'] if target.get('entry') == 'wmain' else [])
                        + ['-static-libgcc', '-static-libstdc++', '-s', '-Wl,--no-insert-timestamp', *sources,
                           '-o', str(folder / (target['name'] + '.' + kind))]
                        + ['-l' + lib for lib in target.get('libs', [])]]
        code, logs = 0, []
        for command in commands:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                code = None; logs.append('error: total build deadline exceeded'); break
            try:
                done = subprocess.run(command, cwd=folder, capture_output=True, text=True,
                                      timeout=min(45, remaining), env={**os.environ, 'LC_ALL': 'C'})
                logs.append((done.stdout + done.stderr)[-100000:])
                if done.returncode:
                    code = done.returncode; break
            except subprocess.TimeoutExpired:
                code = None; logs.append('error: compiler deadline exceeded'); break
        artifacts = []
        if code == 0:
            for path in sorted(folder.iterdir()):
                if path.suffix not in ('.asi', '.exe', '.obj') or not path.is_file() or path.is_symlink():
                    continue
                size = path.stat().st_size
                if size > MAX_ARTIFACT or total + size > MAX_TOTAL:
                    code = None; logs.append('error: compiled artifacts exceed the bounded output budget'); break
                raw = path.read_bytes(); total += len(raw)
                artifacts.append({'file': path.name, 'base64': base64.b64encode(raw).decode('ascii')})
        results.append({'name': target['name'], 'kind': kind, 'exit_code': code,
                        'output': '\n'.join(logs)[-100000:], 'artifacts': artifacts if code == 0 else []})
    print(json.dumps({'compiler': version, 'targets': results}), flush=True)


if __name__ == '__main__':
    main(json.loads(sys.argv[1]))
