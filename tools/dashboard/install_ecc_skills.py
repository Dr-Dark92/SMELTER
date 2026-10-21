"""Preview or import a small, commit-pinned ECC instruction pack.

No ECC installer, package, hook, script, tool or plugin is executed.
"""
import argparse
import json
from pathlib import Path

from github_skill_discovery import discover_github_skill
from skill_collections import install_collection

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = 'https://github.com/affaan-m/ECC'
REVISION = '90606c8315ee09cafc303515c5f33024db6b9882'
SKILLS = {
    'coding-standards': 'e80544c3d1eac5b14f22022146bd91a6b0ecc30e099cf5181894853aeb81dee1',
    'security-review': 'b9eb6416eebc8dda046674f0a2dbb3be88aff526d182b60a0f55998d3d6d0d8d',
    'verification-loop': '5b06be54d4852f60e6cf1b04c6e9a4748554334eb3e41af6c0959b544e6464ae',
}
CODING_SKILLS = {**SKILLS, 'tdd-workflow': '8887afa786ef30de834e7567115d3df71934b343c3d9d849714f8ea43f979ee0'}


def preview(discover=discover_github_skill, *, pack='core'):
    if pack not in ('core', 'coding'):
        raise ValueError('Choose the core or coding ECC instruction pack')
    manifests = []
    for name, expected in (SKILLS if pack == 'core' else CODING_SKILLS).items():
        url = f'{REPOSITORY}/blob/{REVISION}/skills/{name}/SKILL.md'
        result = discover(url)
        if result['sha256'] != expected:
            raise ValueError('ECC pinned manifest integrity mismatch: ' + name)
        manifests.append({**result, 'id': name})
    return manifests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', action='store_true', help='Import reviewed manifests disabled; never overwrite')
    parser.add_argument('--pack', choices=('core','coding'), default='core', help='Coding adds the pinned TDD workflow')
    args = parser.parse_args()
    try:
        manifests = preview(pack=args.pack)
        for manifest in manifests:
            print(json.dumps({k: manifest[k] for k in ('id', 'url', 'sha256', 'bytes', 'warnings')}, indent=2))
        print('Reviewed instructions only. Explicit coding permission adds scoped patch/test tools. ECC hooks, agents, shell, memory and plugin tools are not connected.')
        if args.install:
            selected = [{k: item[k] for k in ('id', 'url', 'sha256')} for item in manifests]
            cache = {item['url']: item for item in manifests}
            result = install_collection(ROOT, REPOSITORY, selected, approval=True, discover=cache.__getitem__)
            print(json.dumps(result, indent=2))
            print('Imported disabled. Review, enable, restart the dashboard, then select Use in next task.')
        else:
            print('Preview complete; nothing installed. Review the linked source before using --install.')
        return 0
    except Exception as exc:
        print('ECC preview/import failed: ' + str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
