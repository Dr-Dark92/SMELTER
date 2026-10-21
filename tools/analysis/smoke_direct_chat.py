"""Explicit live direct-Ollama tool smoke in disposable state. Never starts services."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tools/dashboard'))
CONTENT = '# DIRECT_QWEN_SMOKE_OK\n'
FILENAME = 'direct-smoke.md'


def acceptance(outcome, events, raw):
    """Keep model completion, actual execution, bytes and receipt checks distinct."""
    event = events[0] if len(events) == 1 else {}
    receipt = event.get('result', {})
    digest = hashlib.sha256(raw).hexdigest() if raw is not None else None
    checks = {
        'model_completed': outcome == 'completed',
        'one_approved_mcp_write': (len(events) == 1 and event.get('executed') is True and
            event.get('tool') == 'write_diagnostic_markdown' and event.get('transport') == 'mcp' and
            receipt.get('status') == 'written'),
        'file_present': raw is not None,
        'exact_content': raw == CONTENT.encode('utf-8'),
        'receipt_hash': raw is not None and receipt.get('sha256') == digest,
        'receipt_bytes': raw is not None and receipt.get('bytes') == len(raw),
    }
    return checks


def retain_saved(path, directory):
    if not path.is_file():
        return None, {'exists': False}
    raw = path.read_bytes()
    with (directory / FILENAME).open('xb') as stream:
        stream.write(raw)
    return raw, {'exists': True, 'artifact': FILENAME, 'bytes': len(raw),
                 'sha256': hashlib.sha256(raw).hexdigest(),
                 'utf8_preview': raw.decode('utf-8', errors='backslashreplace')[:256]}


def smoke(directory, *, control=None):
    from database import select_database
    from config_store import save_config
    from chat_jobs import Control
    from chat_inference import ask
    from chats import create_chat, read_chat
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    fixture = control is not None
    report = {'status': 'FAIL', 'live_qwen': not fixture, 'engine': 'direct Ollama',
              'model': 'synthetic contract fixture' if fixture else 'qwen3.5:9b',
              'inference_attempted': False,
              'expected': {'content': CONTENT, 'bytes': len(CONTENT.encode('utf-8')),
                           'sha256': hashlib.sha256(CONTENT.encode('utf-8')).hexdigest()}}
    with tempfile.TemporaryDirectory(prefix='smelter-direct-live-') as temporary:
        root = Path(temporary) / 'SMELTER'
        root.mkdir()
        select_database(root, str(Path(temporary) / 'data'))
        save_config(root, 'runtime_settings.json', {'schema_version': 1, 'settings': {
            'context_tokens': 16384, 'max_output_tokens': 512, 'timeout_seconds': 120, 'thinking': False}})
        cid = create_chat(root, 'Live direct tool smoke')['id']
        prompt = ('Call write_diagnostic_markdown exactly once. filename=direct-smoke.md. '
                  'content must be exactly this JSON string: ' + json.dumps(CONTENT) +
                  '. Then give a brief final answer based on the actual receipt.')
        path = root / 'diagnostics' / FILENAME
        captured = False
        try:
            report['inference_attempted'] = not fixture
            result = ask(root, cid, prompt, control=control if fixture else Control(),
                         tool_permissions={'write_diagnostics': True, 'transport': 'mcp'})
            transcript = read_chat(root, cid)
            (directory / 'chat-evidence.json').write_text(json.dumps(transcript, indent=2), encoding='utf-8')
            events = transcript['messages'][-1]['execution']['events']
            raw, observed = retain_saved(path, directory)
            captured = True
            report.update(model_outcome=result['status'], controller_calls=len(events), observed=observed)
            report['checks'] = acceptance(result['status'], events, raw)
            report['receipt'] = events[0].get('result', {}) if len(events) == 1 else None
            failed = [name for name, passed in report['checks'].items() if not passed]
            if failed:
                report['failed_checks'] = failed
                raise ValueError('Direct acceptance failed: ' + ', '.join(failed))
            report.update(status='PASS', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                          controller_calls=1, saved_bytes_verified=True)
        except Exception as exc:report['error'] = str(exc)[:1500]
        finally:
            if not captured:
                _, report['observed'] = retain_saved(path, directory)
            if not (directory / 'chat-evidence.json').exists():
                (directory / 'chat-evidence.json').write_text(json.dumps(read_chat(root, cid), indent=2), encoding='utf-8')
            audits = root / '.smelter/tool-runs'
            if audits.is_dir():shutil.copytree(audits, directory / 'tool-runs')
    (directory / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true', required=True, help='Explicitly authorize actual local Qwen inference')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = smoke(args.output)
    print(json.dumps(result, indent=2))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
