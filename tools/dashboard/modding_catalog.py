"""Read-only CLI inventory. Never execute candidates, install tools or grant shell."""
import argparse
import json
from pathlib import Path
import shutil


def catalog(root, arguments=None):
    arguments = arguments or {}
    if set(arguments) - {'engine'}:
        raise ValueError('Choose an engine only; tool commands are not accepted')
    from python_tools import _plain_path
    path = _plain_path(Path(root).resolve() / 'system-requirements.json')
    if path.stat().st_size > 512 * 1024:
        raise ValueError('Requirements catalog exceeds its size limit')
    section = json.loads(path.read_text(encoding='utf-8'))['modding_cli']
    known = sorted({e for tool in section['tools'].values() for e in tool['engines']})
    engine = arguments.get('engine')
    if engine is not None and (not isinstance(engine, str) or engine not in known):
        raise ValueError('Unknown engine; choose from: ' + ', '.join(known))
    tools = [{'id': identity, **item, 'found_on_host_path': bool(shutil.which(item['executable'])),
              'installed_version_verified': False}
             for identity, item in section['tools'].items()
             if not engine or engine in item['engines'] or 'universal' in item['engines']]
    return {'status': 'modding_catalog_read', 'reviewed_on': section['reviewed_on'], 'tools': tools,
            'engines': known, 'read_only': True, 'executes_tools': False, 'policy': section['policy'],
            'message': 'Candidates need a pinned install and execution adapter. PATH presence is not compatibility verification.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--engine')
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    print(json.dumps(catalog(args.root, {'engine': args.engine} if args.engine else {}), indent=2))
