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


def smoke(directory):
    from database import select_database
    from config_store import save_config
    from chat_jobs import Control
    from chat_inference import ask
    from chats import create_chat, read_chat
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    report = {'status': 'FAIL', 'live_qwen': True, 'engine': 'direct Ollama', 'model': 'qwen3.5:9b'}
    with tempfile.TemporaryDirectory(prefix='smelter-direct-live-') as temporary:
        root = Path(temporary) / 'SMELTER'
        root.mkdir()
        select_database(root, str(Path(temporary) / 'data'))
        save_config(root, 'runtime_settings.json', {'schema_version': 1, 'settings': {
            'context_tokens': 16384, 'max_output_tokens': 512, 'timeout_seconds': 120, 'thinking': False}})
        cid = create_chat(root, 'Live direct tool smoke')['id']
        content = '# DIRECT_QWEN_SMOKE_OK\n'
        prompt = ('Call write_diagnostic_markdown exactly once. filename=direct-smoke.md. '
                  'content must be exactly this JSON string: ' + json.dumps(content) +
                  '. Then give a brief final answer based on the actual receipt.')
        try:
            result = ask(root, cid, prompt, control=Control(),
                         tool_permissions={'write_diagnostics': True, 'transport': 'mcp'})
            transcript = read_chat(root, cid)
            (directory / 'chat-evidence.json').write_text(json.dumps(transcript, indent=2), encoding='utf-8')
            events = transcript['messages'][-1]['execution']['events']
            path = root / 'diagnostics/direct-smoke.md'
            if result['status'] != 'completed' or len(events) != 1 or not path.is_file():
                raise ValueError('Live direct model did not complete exactly one approved write')
            raw = path.read_bytes()
            if raw != content.encode() or events[0]['result'].get('sha256') != hashlib.sha256(raw).hexdigest():
                raise ValueError('Direct model/controller saved bytes differ from the requested marker')
            shutil.copyfile(path, directory / path.name)
            report.update(status='PASS', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                          controller_calls=1, saved_bytes_verified=True)
        except Exception as exc:report['error'] = str(exc)[:1500]
        finally:
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
