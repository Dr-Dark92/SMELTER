"""Explicit coding-task completion backed by current controller test receipts."""
import json
from pathlib import Path

PROFILES = {'lua', 'mods', 'python', 'node', 'cpp'}


def verify_receipts(root, workspace_id, records, profiles=()):
    """Verify evidence, without interpreting a test result as task completion."""
    import coding_workspace as cw
    from acceptance_contracts import load as contracts, fresh
    from sandbox import lua_runner_sha256
    from python_tools import _plain_path
    with cw.locked(root):
        _, target = cw.load(root, workspace_id)
        registered = contracts(root, workspace_id, target)
        selected = {}
        for updated, workspace, profile, path in records:
            if workspace == workspace_id and profile in PROFILES and profile not in selected:
                selected[profile] = path
        wanted = {c['profile'] for c in registered} | set(profiles) | set(selected)
        if not wanted or not wanted <= set(selected):
            return None
        tree = cw.tree_digest(cw._scan(target))
        receipts = []
        for profile in sorted(wanted):
            if not selected[profile]:
                return None
            path = _plain_path(Path(selected[profile]))
            base = cw.base_path(root) / workspace_id / 'test-runs'
            if path.parent.resolve() != base.resolve() or path.suffix != '.json' or not path.is_file() or path.stat().st_size > 3*1024*1024:
                return None
            raw = path.read_bytes()
            value = json.loads(raw)
            if (value.get('workspace_id') != workspace_id or value.get('profile') != profile
                    or value.get('tree_sha256') != tree or not value.get('current_tree_matches')
                    or value.get('stage') not in ('RED', 'GREEN')):
                return None
            saved = {'acceptance_revision': value.get('acceptance', {}).get('contracts_revision')}
            if not fresh(root, workspace_id, target, profile, saved):
                return None
            if any(c['profile'] == profile for c in registered) and value['stage'] == 'GREEN' and (
                    value.get('workspace_tests_stage') != 'GREEN' or value.get('acceptance', {}).get('stage') != 'GREEN'):
                return None
            if profile == 'lua' and (value.get('runner_sha256') != lua_runner_sha256()
                    or not value.get('source_snapshot', {}).get('bytes_match')):
                return None
            log = _plain_path(path.with_suffix('.log'))
            if not log.is_file() or log.stat().st_size > 3*1024*1024 or cw.digest(log.read_bytes()) != value.get('log_sha256'):
                return None
            receipts.append({'profile': profile, 'id': path.stem, 'sha256': cw.digest(raw), 'stage': value['stage']})
        red = next((r for r in receipts if r['stage'] == 'RED'), None)
        return {'flag': 'RED' if red else 'GREEN', 'receipt': (red or receipts[0])['id'],
                'tree_sha256': tree, 'profiles': sorted(wanted), 'receipts': receipts}


def finish(root, arguments):
    """The caller explicitly ends its task; a RED test alone never does this."""
    import coding_workspace as cw
    if set(arguments) != {'workspace_id', 'outcome', 'profiles'}:
        raise ValueError('Task completion requires workspace_id, outcome and profiles')
    profiles = arguments['profiles']
    if (arguments['outcome'] not in ('RED', 'GREEN') or not isinstance(profiles, list)
            or not profiles or len(profiles) > 5 or any(not isinstance(p, str) or p not in PROFILES for p in profiles)
            or len(set(profiles)) != len(profiles)):
        raise ValueError('Use RED/GREEN and one to five unique supported test profiles')
    with cw.locked(root):
        metadata, _ = cw.load(root, arguments['workspace_id'])
        records = [(0, arguments['workspace_id'], p, metadata['tests'].get(p, {}).get('path')) for p in profiles]
    proof = verify_receipts(root, arguments['workspace_id'], records, profiles)
    if not proof or proof['flag'] != arguments['outcome']:
        raise ValueError('End flag rejected: run the relevant tests on the current tree; outcome must match local and frozen evidence')
    return {'status': 'coding_task_end_flag', 'workspace_id': arguments['workspace_id'],
            'outcome': arguments['outcome'], **proof,
            'message': 'Explicit task end recorded for these test scopes. This does not prove in-game behavior.'}
