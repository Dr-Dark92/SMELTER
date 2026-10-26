"""Preview/apply the existing Melty OpenCode profile's CLI modding integration.

Keeps other providers, credentials and permissions untouched. Optional compact
REA wraps its existing command without changing its environment or backend.
Changes the existing Qwen model output ceiling, grants SMELTER's fixed isolated
coding/build tools, and installs matching modding instruction files. No downloads.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/dashboard'))


def configure(root=ROOT, *, config=None, apply=False, align_dashboard=False, inventory_root=None, enable_knowledge=False, compact_rea=False, native_tool_mode=False):
    from python_tools import _plain_path
    root = _plain_path(Path(root).resolve())
    config = _plain_path(Path(config) if config else Path.home() / '.config/opencode/opencode.json')
    raw = config.read_bytes()
    value = json.loads(raw.decode('utf-8-sig'))
    model = value['provider']['ollama']['models']['qwen3.5:35b-a3b-128k']
    if model.get('limit', {}).get('context') != 131072:
        raise ValueError('The existing native Qwen 128K profile was not found; no configuration was changed')
    server = value.get('mcp', {}).get('smelter')
    if not isinstance(server, dict) or server.get('type') != 'local':
        raise ValueError('The existing local SMELTER MCP registration is required')
    grants = json.loads(server.get('environment', {}).get('SMELTER_MCP_GRANTS', '{}'))
    if not isinstance(grants, dict):
        raise ValueError('Invalid existing SMELTER grants')
    model['limit']['output'] = 8192
    if native_tool_mode:
        options = model.setdefault('options', {})
        variants = model.setdefault('variants', {})
        if not isinstance(options, dict) or not isinstance(variants, dict):
            raise ValueError('Native Qwen options and variants must be objects')
        selected = {'smelter-tools': {'reasoningEffort': 'none'},
                    'smelter-thinking': {'reasoningEffort': 'medium'}}
        for name, setting in selected.items():
            if name in variants and variants[name] != setting:
                raise ValueError('Existing native Qwen variant differs; preserved for review: ' + name)
        model['reasoning'] = True
        options['reasoningEffort'] = 'none'
        variants.update(selected)
    grants.update(melty_read=True, coding_workspace=True, native_build=True)
    if enable_knowledge:grants.update(web_read=True,project_memory=True)
    if inventory_root is not None:
        from python_tools import permissions
        from access_policy import current
        scope=permissions(root,{'inventory_root':str(inventory_root)})['inventory_root']
        current(root).authorize(scope,'read')
        grants['inventory_root']=scope
    server.setdefault('environment', {})['SMELTER_MCP_GRANTS'] = json.dumps(grants, sort_keys=True)
    rea_summary = None
    if compact_rea:
        rea = value.get('mcp', {}).get('rea')
        if not isinstance(rea, dict) or rea.get('type') != 'local':
            raise ValueError('Compact REA requires the existing local REA registration')
        command = rea.get('command')
        if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
            raise ValueError('Existing REA command must be a nonempty string array')
        # Collapsing operation names would bypass per-operation OpenCode rules.
        permissions = [value.get('permission', {})] + [a.get('permission', {}) for a in value.get('agent', {}).values() if isinstance(a, dict)]
        for rules in permissions:
            if not isinstance(rules, dict) or any(k.startswith('rea_') and k != 'rea_*' for k in rules):
                raise ValueError('Review per-operation REA permissions before enabling the gateway')
        gateway = _plain_path(root / 'tools/dashboard/rea_mcp_gateway.py')
        if not gateway.is_file():
            raise ValueError('Compact REA gateway source is missing')
        already = len(command) >= 4 and command[1] == str(gateway) and command[2] == '--'
        if not already:
            rea['command'] = [str(_plain_path(Path(sys.executable))), str(gateway), '--', *command]
        rea_summary = {'gateway': str(gateway), 'tool_count': 3, 'upstream_command_preserved': True,
                       'already_configured': already, 'environment_preserved': True}
    skills = []
    for name in ('game-modding', 'mod-validation', 'universal-modder', 'engine-archive', 'project-knowledge'):
        source = _plain_path(root / 'skills' / name / 'SKILL.md')
        destination = _plain_path(config.parent / 'skills' / name / 'SKILL.md')
        data = source.read_bytes()
        if destination.exists() and destination.read_bytes() != data:
            raise ValueError('Existing native skill differs; preserved for review: ' + str(destination))
        skills.append((destination, data))
    updated = (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    changed = json.loads(raw.decode('utf-8-sig')) != value
    result = {'mode':'apply' if apply else 'preview', 'config':str(config), 'config_changed':changed,
              'output_tokens':8192, 'mcp_grants':grants,
              'skills':[str(p) for p, _ in skills], 'backup':None, 'downloads':False,
              'scope':'Fixed SMELTER coding-copy/build operations; no game installation or artifact execution. Native OpenCode retains its existing host permissions.'}
    if rea_summary is not None:
        result['rea_gateway'] = rea_summary
    if native_tool_mode:
        result['native_qwen_mode'] = {'default': 'direct answers for tool work',
                                     'reasoning_effort': 'none', 'thinking_variant': 'smelter-thinking',
                                     'context_tokens': 131072, 'output_tokens': 8192}
    if align_dashboard:
        from runtime_settings import load_runtime
        dashboard_before = load_runtime(root)['settings']
        dashboard_after = {**dashboard_before, 'context_tokens':131072, 'max_output_tokens':8192}
        result['dashboard_runtime'] = {'before':dashboard_before, 'after':dashboard_after, 'backup':None}
    if apply:
        if align_dashboard:
            from maintenance import _idle
            _idle(root)
        if config.read_bytes() != raw:
            raise ValueError('OpenCode configuration changed during preview')
        for path, data in skills:
            if not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('xb') as stream:
                    stream.write(data)
        if changed:
            backup = config.with_name(config.name + '.bak-smelter-cli-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
            _plain_path(backup)
            with backup.open('xb') as stream:
                stream.write(raw)
            pending = _plain_path(config.with_name(config.name + '.smelter-cli.pending'))
            with pending.open('xb') as stream:
                stream.write(updated)
            pending.replace(config)
            result['backup'] = str(backup)
        if align_dashboard and dashboard_before != dashboard_after:
            from runtime_settings import save_runtime
            folder = _plain_path(root / '.smelter'); folder.mkdir(exist_ok=True)
            backup = folder / ('runtime-before-cli-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
            with backup.open('x', encoding='utf-8') as stream:
                json.dump(dashboard_before, stream, indent=2)
            save_runtime(root, dashboard_after)
            result['dashboard_runtime']['backup'] = str(backup)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--align-dashboard', action='store_true', help='Explicitly select the user-chosen 128K/8K limits in this dashboard too')
    parser.add_argument('--inventory-root', type=Path, help='Persist one already-registered read-only inventory scope for native MCP tools')
    parser.add_argument('--enable-knowledge',action='store_true',help='Enable controlled web and project-memory tools; project settings still govern access')
    parser.add_argument('--compact-rea', action='store_true', help='Expose the existing native REA catalog through on-demand discovery/schema/call tools to preserve model context')
    parser.add_argument('--native-tool-mode', action='store_true', help='Use direct answers for native Qwen tool work; retain a named thinking variant and the 128K/8K limits')
    args = parser.parse_args()
    print(json.dumps(configure(args.root, config=args.config, apply=args.apply, align_dashboard=args.align_dashboard, inventory_root=args.inventory_root, enable_knowledge=args.enable_knowledge, compact_rea=args.compact_rea, native_tool_mode=args.native_tool_mode), indent=2))
