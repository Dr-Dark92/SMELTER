"""Actual CSS/MCP/test/preview smoke, with disposable code/DB and existing images."""
import argparse
import hashlib
from http.client import HTTPConnection
import json
from pathlib import Path
import shutil
import sys
import tempfile
from urllib.parse import urlsplit, parse_qs

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools/dashboard'))


def smoke(directory, python_image, node_image):
    from frontend_workspace import _source_files, DASHBOARD
    from database import select_database
    from config_store import save_config
    from python_tools import ToolSession
    from sandbox_preview import stop
    from sandbox import owned_runs
    from smoke_agent_bridge import port_free
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    report = {'status': 'FAIL', 'live_qwen': False, 'mode': 'actual MCP, container tests and loopback preview'}
    with tempfile.TemporaryDirectory(prefix='smelter-css-smoke-') as temporary:
        root = Path(temporary) / 'SMELTER'
        root.mkdir()
        for name, source in _source_files(REPO).items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
        select_database(root, str(Path(temporary) / 'data'))
        save_config(root, 'sandbox.json', {'schema_version': 1, 'python_image': python_image,
                                         'node_image': node_image, 'opencode_image': None})
        skill = root / 'skills/smoke-design/SKILL.md'
        skill.parent.mkdir(parents=True)
        skill.write_text('# Smoke Design\n\n## Purpose\nUse the exact CSS tool and verify saved bytes.\n', encoding='utf-8')
        original = (root / DASHBOARD).read_bytes()
        session = ToolSession(root, {'frontend_workspace': True, 'transport': 'mcp'})
        def call(name, arguments):
            result = session.execute({'function': {'name': name, 'arguments': arguments}})
            if result.get('status') in ('error', 'workspace_validation_failed'):
                raise ValueError(name + ': ' + json.dumps(result))
            return result
        try:
            port_free(8770)
            info = call('frontend_workspace_info', {})
            if 'smoke-design' not in {s['id'] for s in info['skills']}:raise ValueError('Enabled design fixture is missing')
            reference = call('read_enabled_design_skill', {'skill_id': 'smoke-design'})
            if 'verify saved bytes' not in reference['text']:raise ValueError('Actual skill reference was not read')
            call('prepare_frontend_workspace', {})
            css = call('read_frontend_file', {})
            old = css['text'][:80]
            call('replace_frontend_css', {'expected_sha256': css['sha256'], 'old_text': old,
                                         'new_text': ':root{--smelter-smoke:1}\n' + old})
            validation = call('validate_frontend_workspace', {})
            preview = call('launch_frontend_preview', {})
            url = urlsplit(preview['url'])
            token = parse_qs(url.fragment)['token'][0]
            connection = HTTPConnection('127.0.0.1', url.port, timeout=20)
            try:
                connection.request('GET', '/')
                response = connection.getresponse()
                html = response.read().decode('utf-8')
                if response.status != 200 or '--smelter-smoke:1' not in html:raise ValueError('Preview does not contain the saved CSS')
                connection.request('GET', '/api/chats', headers={'X-Smelter-Token': token})
                response = connection.getresponse()
                if response.status != 200 or json.loads(response.read()).get('conversations') != []:
                    raise ValueError('Isolated preview database is not empty/authenticated')
            finally:connection.close()
            # Editing after a successful launch must not replay a cached URL.
            css = call('read_frontend_file', {})
            call('replace_frontend_css', {'expected_sha256': css['sha256'], 'old_text': '--smelter-smoke:1',
                                         'new_text': '--smelter-smoke:2'})
            stale = session.execute({'function': {'name': 'launch_frontend_preview', 'arguments': {}}})
            if stale.get('status') != 'error' or 'validation' not in stale.get('error', ''):
                raise ValueError('A stale preview launch was not rejected')
            if (root / DASHBOARD).read_bytes() != original:raise ValueError('Source dashboard changed')
            cleaned = stop()
            if cleaned.get('cleanup_pending') or owned_runs(root):raise ValueError('Owned CSS test/preview cleanup remains pending')
            report.update(status='PASS', tests=validation['checks'], preview_css_verified=True,
                          authenticated_empty_preview_db=True, stale_launch_rejected=True,
                          source_unchanged=True, source_sha256=hashlib.sha256(original).hexdigest(),
                          file_cards=len(session.file_activity.snapshot()), cleanup_confirmed=True)
        except Exception as exc:report['error'] = str(exc)[:3000]
        finally:
            cleanup = stop()
            if cleanup.get('cleanup_pending'):
                report.update(status='FAIL', cleanup_confirmed=False, cleanup_pending=cleanup['cleanup_pending'])
            for name in ('tool-runs',):
                source = root / '.smelter' / name
                if source.is_dir():shutil.copytree(source, directory / name)
            validation_logs = root.with_name('SMELTERV2') / '.smelter/frontend-validation'
            if validation_logs.is_dir():shutil.copytree(validation_logs, directory / 'validation')
    (directory / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--python-image', required=True)
    parser.add_argument('--node-image', required=True)
    args = parser.parse_args()
    result = smoke(args.output, args.python_image, args.node_image)
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
