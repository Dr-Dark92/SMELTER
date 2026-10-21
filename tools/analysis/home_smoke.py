"""Operator smoke runner. Default is offline contracts; --live opts into Qwen.

Creates a new evidence folder. Never installs dependencies, starts services,
pulls images, kills existing processes, or reuses the production database.
"""
import argparse
from datetime import datetime, timezone
from importlib.metadata import version, PackageNotFoundError
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
from urllib.request import urlopen
from uuid import uuid4

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools/dashboard'))
from process_runner import run
from home_demo import create_fixtures, prepare_demo

IMAGE = re.compile(r'sha256:[a-f0-9]{64}')
PROFILE = {'context_tokens': 16384, 'max_output_tokens': 512, 'timeout_seconds': 120, 'thinking': False}


def redact(text):
    text = re.sub(r'(?i)((?:#|[?&])token=)[^\s&#"\']+', r'\1[REDACTED]', str(text))
    text = re.sub(r'(?im)(authorization\s*:\s*)[^\r\n]+', r'\1[REDACTED]', text)
    return re.sub(r'(?im)((?:authorization|api[_-]?key|password)\s*[:=]\s*)[^\s,}]+', r'\1[REDACTED]', text)


def failure_detail(exc):
    """Keep bounded, redacted native error output instead of only its exit code."""
    detail = redact(exc)
    error = getattr(exc, 'stderr', None)
    if error:
        if isinstance(error, bytes):
            error = error.decode('utf-8', 'replace')
        detail += '\nstderr: ' + redact(error).strip()
    return detail[:4096]


def read_local_json(path):
    with urlopen('http://127.0.0.1:11434' + path, timeout=5) as response:
        raw = response.read(4 * 1024 * 1024 + 1)
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError('Ollama metadata response exceeds limit')
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise ValueError('Invalid Ollama metadata')
    return result


def configured_images(root):
    from sandbox import config
    value = config(root)
    return {key: value[key] for key in ('python_image', 'node_image', 'opencode_image')}


def preflight(root, *, runtime=False, live=False, image=None, command=run, lookup=shutil.which):
    checks = []
    def record(name, status, detail):
        checks.append({'name': name, 'status': status, 'detail': detail})
    record('Python', 'PASS' if sys.version_info >= (3, 11) else 'BLOCKED', sys.version.split()[0])
    try:
        sdk = version('mcp')
    except PackageNotFoundError:
        sdk = 'missing'
    record('MCP SDK', 'PASS' if sdk == '1.30.0' else 'BLOCKED', sdk + '; required 1.30.0')
    node = lookup('node')
    try:
        if not node:
            raise ValueError('Node is not on PATH')
        node_version = command([node, '--version'], timeout=10, text=True, check=True).stdout.strip()
        if int(node_version.lstrip('v').split('.')[0]) < 20:
            raise ValueError('Node 20 or newer is required for the host checks')
        record('Node', 'PASS', node_version)
    except Exception as exc:
        record('Node', 'BLOCKED', failure_detail(exc))
    try:
        images = configured_images(root)
    except Exception as exc:
        images = {key: None for key in ('python_image', 'node_image', 'opencode_image')}
        record('Saved image configuration', 'BLOCKED', failure_detail(exc))
    if image:
        if not IMAGE.fullmatch(image):
            record('OpenCode image argument', 'BLOCKED', 'Use an immutable sha256 image ID')
        else:
            images['opencode_image'] = image
    if runtime:
        docker = lookup('docker')
        try:
            if not docker:
                raise ValueError('Docker is not installed; no host-process fallback')
            if os.environ.get('DOCKER_HOST') and not os.environ['DOCKER_HOST'].startswith(('unix://', 'npipe://')):
                raise ValueError('Remote Docker hosts are unsupported')
            context = command([docker, 'context', 'inspect', '--format', '{{.Endpoints.docker.Host}}'],
                              timeout=8, text=True, check=True).stdout.strip()
            if not context.startswith(('unix://', 'npipe://')):
                raise ValueError('Select a local Docker engine')
            fields = {'server': 'ServerVersion', 'os': 'OSType', 'memory': 'MemoryLimit',
                      'swap': 'SwapLimit', 'cpu': 'CpuCfsQuota', 'pids': 'PidsLimit', 'security': 'SecurityOptions'}
            packet = json.loads(command([docker, 'info', '--format', '{{json .}}'],
                                        timeout=8, text=True, check=True).stdout)
            if not isinstance(packet, dict):
                raise ValueError('Docker info must return a JSON object')
            info = {key: packet.get(value) for key, value in fields.items()}
            if info['os'] != 'linux' or int(info['server'].split('.')[0]) < 28:
                raise ValueError('Docker Engine 28+ with Linux containers is required')
            if not all(info[key] is True for key in ('memory', 'swap', 'cpu', 'pids')):
                raise ValueError('Docker cannot enforce the required resource limits')
            if not any('seccomp' in value for value in info['security']):
                raise ValueError('Docker seccomp support is required')
            record('Docker confinement prerequisites', 'PASS', info)
            for key, tag in [('opencode_image', 'smelter-opencode:1.19.3'),
                             ('python_image', 'python:3.12-alpine'), ('node_image', 'node:22-alpine')]:
                wanted = images[key] or tag
                try:
                    actual = command([docker, 'image', 'inspect', '--format', '{{.Id}}', wanted],
                                     timeout=8, text=True, check=True).stdout.strip()
                    if not IMAGE.fullmatch(actual) or images[key] and images[key] != actual:
                        raise ValueError('Image identity mismatch')
                    images[key] = actual
                    record(key, 'PASS', actual)
                except Exception as exc:
                    record(key, 'BLOCKED' if key == 'opencode_image' else 'NOT_RUN',
                           'Image not installed/valid: ' + wanted +
                           ('; required for optional CSS validation' if key != 'opencode_image' else '') +
                           '\n' + failure_detail(exc))
        except Exception as exc:
            record('Docker confinement prerequisites', 'BLOCKED', failure_detail(exc))
    if live:
        try:
            ollama = read_local_json('/api/version')
            tags = read_local_json('/api/tags')
            names = [item.get('name') for item in tags.get('models', [])]
            if 'qwen3.5:9b' not in names:
                raise ValueError('qwen3.5:9b is not installed; no model was downloaded')
            record('Ollama + installed Qwen', 'PASS', {'version': ollama.get('version'), 'model': 'qwen3.5:9b',
                                                      'loaded_models': read_local_json('/api/ps').get('models', [])})
        except Exception as exc:
            record('Ollama + installed Qwen', 'BLOCKED', failure_detail(exc))
    return checks, images


def contracts(root, node):
    return [(name, [sys.executable, '-m', 'unittest', 'discover', '-s', 'tools/' + name, '-p', 'test_*.py'])
            for name in ('dashboard', 'setup', 'analysis')] + [
            ('javascript', [node, '--test', *[str(path.relative_to(root)) for path in sorted((root / 'tools/dashboard').glob('test_*.js'))]])]


def phase(directory, name, argv, *, root=REPO, timeout=900, command=run, extra_env=None):
    start = time.monotonic()
    environment = dict(os.environ, SMELTER_VISION_LIVE='0', SMELTER_TEST_DOCKER='0', PYTHONUTF8='1')
    environment.update(extra_env or {})
    print('RUN ' + name, flush=True)
    try:
        result = command(argv, cwd=root, env=environment, timeout=timeout, max_output=8 * 1024 * 1024, text=True)
        output = result.stdout + '\n' + result.stderr
        status = 'PASS' if result.returncode == 0 else 'FAIL'
        code = result.returncode
    except Exception as exc:
        output, status, code = failure_detail(exc), 'FAIL', None
    log = directory / (name + '.log')
    with log.open('x', encoding='utf-8') as stream:
        stream.write(redact(output))
    item = {'name': name, 'status': status, 'exit_code': code,
            'seconds': round(time.monotonic() - start, 2), 'log': str(log)}
    print(status + ' ' + name + ' (' + str(item['seconds']) + 's)', flush=True)
    return item


def write_report(directory, report):
    with (directory / 'summary.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
    lines = ['# SMELTER home smoke', '', 'Automated result: **' + report['status'] + '**',
             '', 'GUI demo: **MANUAL_PENDING**. Live Qwen: **' + report['live_qwen'] + '**.', '',
             '| Check | Result |', '|---|---|']
    lines += ['| ' + row['name'] + ' | ' + row['status'] + ' |' for row in report['checks'] + report['phases']]
    lines += ['', 'Read `summary.json` for details and phase logs for errors.',
              'The report status covers requested automated checks only. Optional CSS validation needs Python and Node images.',
              'Use docs/HOME_SMOKE_TEST.md for exact prompts, expected outcomes and manual acceptance.', '']
    (directory / 'SUMMARY.md').write_text('\n'.join(lines), encoding='utf-8')
    (directory / 'MANUAL_RESULTS.md').write_text(
        '# Manual demo results\n\nAll items are pending until checked by the operator.\n\n' +
        '\n'.join('- [ ] ' + item for item in ['Dashboard opens; title required; resource footer populated',
        'Selected skill snapshot recorded', 'MCP report exists with matching bytes/hash',
        'Inventory is 3 files / 1 directory / 26 bytes', 'Out-of-scope operation denied by controller',
        'Next-Send grants reset', 'Stop and refresh settle with retained receipts',
        'GLB renders; clips are 1s and 2s; rename survives refresh; PNG/WebM export',
        'Optional CSS edit displays old/new bytes; validation and preview verified',
        'ECC instruction selection works; unsupported plugin features remain explicit']) + '\n', encoding='utf-8')


def execute(args, *, root=REPO, command=run):
    full = getattr(args, 'full', False)
    coding = getattr(args, 'coding', False) or full and (args.live or args.fixture)
    directory = Path(args.output).resolve() if args.output else root / 'diagnostics' / (
        'home-smoke-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid4().hex[:8])
    directory.mkdir(parents=True, exist_ok=False)
    print('Evidence: ' + str(directory), flush=True)
    report = {'status': 'FAIL', 'mode': 'live' if args.live else 'fixture' if args.fixture else 'preflight' if args.preflight_only else 'offline',
              'live_qwen': 'NOT_RUN', 'gui': 'MANUAL_PENDING', 'checks': [], 'phases': [],
              'smoke_profile': PROFILE, 'evidence_directory': str(directory), 'services_started_automatically': False,
              'scope': 'full automated layer smoke' if full else 'baseline contracts and requested runtime',
              'manual_acceptance': 'PENDING', 'live_direct_ollama': 'NOT_RUN', 'coding_profiles': 'NOT_RUN',
              'browser': 'NOT_RUN'}
    try:
        fixtures = create_fixtures(directory / 'inputs')
        report['inputs'] = fixtures
        checks, images = preflight(root, runtime=args.live or args.fixture or args.preflight_only,
                                   live=args.live or args.preflight_only, image=args.opencode_image, command=command)
        report['checks'] = checks
        browser_module = os.environ.get('SMELTER_TEST_PLAYWRIGHT') or str(root / '.smelter/tooling/browser/node_modules/playwright')
        if full:
            try:
                command([shutil.which('node'), '-e', "const fs=require('node:fs');const p=require(process.argv[1]);if(!fs.existsSync(p.chromium.executablePath()))process.exit(2);", browser_module],
                        timeout=10, text=True, check=True)
                from model_assets import viewer_bundle
                viewer_bundle(root)
                checks.append({'name': 'Browser + local GLB viewer', 'status': 'PASS', 'detail': 'Existing Playwright Chromium and model-viewer 4.1.0'})
            except Exception as exc:
                checks.append({'name': 'Browser + local GLB viewer', 'status': 'BLOCKED',
                               'detail': 'Full GUI smoke needs reviewed local browser/viewer dependencies; no installation was attempted. ' + failure_detail(exc)})
            if args.live or args.fixture or args.preflight_only:
                for key in ('python_image', 'node_image'):
                    checks.append({'name': 'Full smoke ' + key, 'status': 'PASS' if images.get(key) else 'BLOCKED',
                                   'detail': images.get(key) or 'Both fixed coding profiles require their local immutable images'})
        if coding:
            checks.append({'name': 'Python coding image', 'status': 'PASS' if images.get('python_image') else 'BLOCKED',
                           'detail': images.get('python_image') or 'Install/configure the local Python test image'})
        manifests = []
        if args.ecc or coding:
            from install_ecc_skills import preview, REVISION
            manifests = preview(pack='coding' if coding else 'core')
            for manifest in manifests:
                folder = directory / 'ecc-manifests' / manifest['id']
                folder.mkdir(parents=True)
                (folder / 'SKILL.md').write_bytes(manifest['content'].encode('utf-8'))
            report['ecc'] = {'revision': REVISION, 'mode': 'instructions_only',
                             'manifests': [{key: m[key] for key in ('id', 'url', 'sha256')} for m in manifests]}
        if args.prepare_demo:
            report['demo'] = prepare_demo(root, directory, images, fixtures, manifests)
            print('Demo prepared; not started. PowerShell launch command:', flush=True)
            argv = report['demo']['launch_argv']
            print('& ' + ' '.join("'" + value.replace("'", "''") + "'" for value in argv), flush=True)
        blocked = any(item['status'] == 'BLOCKED' for item in checks)
        if not args.preflight_only and not blocked:
            for name, argv in contracts(root, shutil.which('node')):
                result = phase(directory, name, argv, root=root, command=command)
                report['phases'].append(result)
                if result['status'] != 'PASS':
                    break
            if full and all(item['status'] == 'PASS' for item in report['phases']):
                report['phases'].append(phase(directory, 'workflow-http-mcp', [sys.executable,
                    str(root / 'tools/analysis/smoke_workflows.py'), '--output', str(directory / 'workflow-evidence')],
                    root=root, timeout=90, command=command))
                if report['phases'][-1]['status'] == 'PASS':
                    result = phase(directory, 'browser-ui-glb', [shutil.which('node'),
                        str(root / 'tools/analysis/check_workbench_browser.mjs'), '--output', str(directory / 'browser-evidence')],
                        root=root, timeout=300, command=command,
                        extra_env={'SMELTER_TEST_PLAYWRIGHT': browser_module, 'SMELTER_TEST_PYTHON': sys.executable})
                    report['phases'].append(result)
                    report['browser'] = result['status']
            if full and (args.live or args.fixture) and all(item['status'] == 'PASS' for item in report['phases']):
                result = phase(directory, 'python-node-confined-profiles', [sys.executable,
                    str(root / 'tools/analysis/smoke_coding_profiles.py'), '--output', str(directory / 'profile-evidence'),
                    '--python-image', images['python_image'], '--node-image', images['node_image']],
                    root=root, timeout=600, command=command)
                report['phases'].append(result)
                report['coding_profiles'] = result['status']
                if result['status'] == 'PASS':
                    report['phases'].append(phase(directory, 'frontend-css-tests-preview', [sys.executable,
                        str(root / 'tools/analysis/smoke_frontend_workspace.py'), '--output', str(directory / 'frontend-evidence'),
                        '--python-image', images['python_image'], '--node-image', images['node_image']],
                        root=root, timeout=600, command=command))
            if full and args.live and all(item['status'] == 'PASS' for item in report['phases']):
                result = phase(directory, 'direct-ollama-live', [sys.executable,
                    str(root / 'tools/analysis/smoke_direct_chat.py'), '--live', '--output', str(directory / 'direct-live-evidence')],
                    root=root, timeout=180, command=command)
                report['phases'].append(result)
                report['live_direct_ollama'] = result['status']
            if all(item['status'] == 'PASS' for item in report['phases']) and (args.live or args.fixture):
                argv = [sys.executable, str(root / 'tools/analysis/smoke_agent_bridge.py'), '--image', images['opencode_image'],
                        '--evidence-dir', str(directory / 'runtime-evidence')]
                if args.live:
                    argv.append('--live')
                else:
                    argv += ['--fixture-delay', '12']
                if manifests:
                    argv += ['--skill-manifest', str(directory / 'ecc-manifests/verification-loop/SKILL.md'),
                             '--skill-id', 'ecc-verification-loop']
                result = phase(directory, 'agent-runtime', argv, root=root, timeout=300, command=command)
                report['phases'].append(result)
                if args.live:
                    report['live_qwen'] = result['status']
                    try:
                        report['ollama_after_test'] = read_local_json('/api/ps')
                    except Exception as exc:
                        report['ollama_after_test'] = {'observation_error': redact(exc)}
                if coding and result['status'] == 'PASS':
                    argv = [sys.executable, str(root / 'tools/analysis/smoke_ecc_coding.py'),
                            '--image', images['opencode_image'], '--python-image', images['python_image'],
                            '--skill-manifest', str(directory / 'ecc-manifests/tdd-workflow/SKILL.md'),
                            '--evidence-dir', str(directory / 'coding-runtime-evidence')]
                    if args.live:argv.append('--live')
                    report['phases'].append(phase(directory, 'ecc-coding-runtime', argv, root=root,
                                                  timeout=420, command=command))
                    report['coding_test_profile'] = {'context_tokens': 32768, 'max_output_tokens': 1024,
                                                    'timeout_seconds': 300, 'thinking': False}
        report['status'] = ('BLOCKED' if blocked else 'FAIL' if any(item['status'] == 'FAIL' for item in report['phases']) else 'PASS')
    except Exception as exc:
        report['error'] = failure_detail(exc)
        report['status'] = 'FAIL'
    write_report(directory, report)
    print(report['status'] + ': ' + str(directory / 'SUMMARY.md'), flush=True)
    return {'PASS': 0, 'FAIL': 1, 'BLOCKED': 2}[report['status']]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--live', action='store_true', help='Opt into real existing Ollama/Qwen through managed OpenCode')
    mode.add_argument('--fixture', action='store_true', help='Real Docker/OpenCode/MCP with synthetic model; port 11434 must be free')
    mode.add_argument('--preflight-only', action='store_true', help='Read-only prerequisite checks; no tests or inference')
    parser.add_argument('--prepare-demo', action='store_true', help='Create fresh GUI source/V2 and separate databases; do not launch')
    parser.add_argument('--ecc', action='store_true', help='Fetch three pinned ECC manifests; test verification-loop if runtime is requested')
    parser.add_argument('--coding', action='store_true', help='Also test ECC RED/fix/GREEN; requires --live or --fixture and a Python image')
    parser.add_argument('--full', action='store_true', help='Also exercise real HTTP/MCP workflows and Chromium/GLB; with runtime, add both confined coding profiles; with --live, add direct Qwen')
    parser.add_argument('--opencode-image', help='Override with existing immutable sha256 ID; never pull/build')
    parser.add_argument('--output', help='New evidence directory; existing paths are rejected')
    args = parser.parse_args()
    if args.coding and not (args.live or args.fixture):
        parser.error('--coding requires the explicit --live or --fixture runtime mode')
    try:
        return execute(args)
    except (OSError, ValueError) as exc:
        print('Smoke setup failed: ' + redact(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
