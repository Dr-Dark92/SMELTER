"""Bounded, read-only recovery evidence from the owned coding copy and receipts."""
import json
import re
from pathlib import Path


ACCEPTANCE_MARKER = '[CONTROLLER ACCEPTANCE]'


def diagnose(output):
    """Locate the cause before its callers; log text is evidence, never instructions.

    Frozen acceptance failures come first: an editable-suite syntax error must
    not hide that the operator's contract is failing, with observed values.
    """
    text = output.decode('utf-8', errors='replace') if isinstance(output, bytes) else output
    workspace, marker, frozen = text.partition(ACCEPTANCE_MARKER)
    failed = [line[:300] for line in frozen.splitlines() if line.startswith('[ACCEPTANCE FAIL]')] if marker else []
    if failed:
        return {'classification': 'acceptance_failure', 'failed_checks': failed[:8], 'failed_total': len(failed),
                'workspace_diagnostic': _first_failure(workspace),
                'guidance': 'The controller-owned frozen contract failed; fix the SUBJECT to the contract interface. '
                            '"observed:" shows what your code actually returned or raised. Fix the first failing check, '
                            'then rerun. Editable tests cannot override this contract; resolve any workspace_diagnostic too.'}
    return _first_failure(text)


def _first_failure(text):
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r'(?:lua[\d.]*:\s*)?([^\s:][^:]*\.lua):(\d+):\s*(.+)', line)
        if match:
            detail = match.group(3)
            kind = 'assertion_failure' if 'assertion failed' in detail.lower() else 'runtime_error'
            if '<eof>' in detail or 'syntax error' in detail or "expected near" in detail:
                kind = 'syntax_error'
            return {'classification': kind, 'path': match.group(1), 'line': int(match.group(2)),
                    'message': detail[:600], 'excerpt': '\n'.join(lines[max(0,index-1):index+9])[:2400],
                    'guidance': 'Read the first failing source frame and its actual inputs. Later stack frames are callers. Do not infer a syntax error from a runtime stack trace.'}
    # Preserve the first actual failure, rather than the tail's successful tests.
    for index, line in enumerate(lines):
        if re.search(r'(Traceback \(most recent call last\)|\[(?:ACCEPTANCE )?FAIL\]|^ERROR[: (]|^FAIL[: (]|\berror:)', line):
            acceptance='[ACCEPTANCE FAIL]' in line
            return {'classification': 'acceptance_failure' if acceptance else 'test_failure', 'excerpt': '\n'.join(lines[index:index+18])[:2400],
                    'guidance': ('The controller-owned frozen contract failed. Editable test comments and reason-code expectations cannot override it; preserve strict validation and fix the actual behavior.' if acceptance else 'Inspect this failure and distinguish assertion failures from import/runner errors before editing.')}
    return None


def anchor(root, workspace_id, target, diagnostic, acceptance):
    """Re-attach failing contracts' full text and interface; summaries drift after compaction."""
    if not isinstance(diagnostic, dict) or not isinstance(acceptance, dict):
        return diagnostic
    failing = {c.get('id') for c in acceptance.get('contracts', []) if isinstance(c, dict) and c.get('stage') != 'GREEN'}
    from acceptance_contracts import load, summary
    diagnostic['failing_contracts'] = [c for c in summary(load(root, workspace_id, target)) if c['id'] in failing]
    return diagnostic


def recover(root, arguments):
    if set(arguments) - {'workspace_id', 'relative_paths'} or 'workspace_id' not in arguments:
        raise ValueError('Recovery requires workspace_id and optional relative_paths')
    paths = arguments.get('relative_paths', [])
    if not isinstance(paths, list) or len(paths) > 6 or any(not isinstance(p,str) for p in paths):
        raise ValueError('Choose at most six exact project-relative recovery paths')
    import coding_workspace as cw
    from python_tools import _plain_path
    with cw.locked(root):
        metadata, target = cw.load(root, arguments['workspace_id'])
        files = cw._scan(target)
        tree = cw.tree_digest(files)
        entries = []
        for relative in paths:
            relative = cw.relative_path(relative)
            path = cw._file(target, relative)
            entry = {'relative_path': relative, 'physical_path': str(path), 'exists': path.is_file(),
                     'sha256': files.get(relative)}
            if path.is_file() and path.stat().st_size <= cw.MAX_FILE:
                raw = path.read_bytes()
                entry.update(sha256=cw.digest(raw), bytes=len(raw), newline_style=cw.newline_style(raw.decode('utf-8')))
            entries.append(entry)
        tests = []
        folder = cw.base_path(root) / arguments['workspace_id'] / 'test-runs'
        for profile, saved in list(metadata.get('tests', {}).items())[:5]:
            path = _plain_path(Path(saved['path']))
            # Metadata cannot point recovery reads at arbitrary host files.
            if path.parent.resolve() != folder.resolve() or path.suffix != '.json':
                raise ValueError('Recovery receipt is outside its owned test directory')
            current = saved.get('tree_sha256') == tree
            from acceptance_contracts import fresh
            current = current and fresh(root,arguments['workspace_id'],target,profile,saved)
            if profile == 'lua':
                from sandbox import lua_runner_sha256
                current = current and saved.get('runner_sha256') == lua_runner_sha256()
            receipt = {'profile': profile, 'stage': saved.get('stage'),
                       'current': current, 'receipt_path': str(path)}
            if path.is_file() and path.stat().st_size <= 3*1024*1024:
                evidence = json.loads(path.read_text(encoding='utf-8'))
                log = _plain_path(path.with_suffix('.log'))
                if log.is_file() and log.stat().st_size <= 3*1024*1024:
                    raw = log.read_bytes()
                    if cw.digest(raw) != evidence.get('log_sha256'):
                        raise ValueError('Recovery test log no longer matches its receipt')
                    receipt.update(log_path=str(log), log_sha256=cw.digest(raw), diagnostic=diagnose(raw))
                receipt['test_programs'] = [
                    {'test': str(program.get('test',''))[:500],
                     'working_directory': str(program.get('working_directory',''))[:500],
                     'exit_code': program.get('exit_code') if type(program.get('exit_code')) is int else None}
                    for program in evidence.get('test_programs', [])[:16] if isinstance(program,dict)]
                detail = receipt.get('diagnostic')
                if detail and detail.get('classification') == 'acceptance_failure':
                    anchor(root, arguments['workspace_id'], target, detail, evidence.get('acceptance'))
                    detail = detail.get('workspace_diagnostic')
                if detail and detail.get('path'):
                    # A stack path is relative to the test CWD, not to Melty or
                    # the checkout. Never guess when multiple failing programs
                    # resolve it differently. Recheck file scope before reading.
                    candidates = set()
                    for program in receipt['test_programs']:
                        if not program.get('exit_code'):continue
                        candidate = program.get('working_directory','') + '/' + detail['path']
                        if candidate in files:candidates.add(candidate)
                    detail['candidate_relative_paths'] = sorted(candidates)
                    if len(candidates) == 1:
                        relative = candidates.pop(); source = cw._file(target,relative)
                        if source.is_file() and source.stat().st_size <= cw.MAX_FILE:
                            raw = source.read_bytes(); lines = raw.decode('utf-8').splitlines(); number = detail['line']
                            detail.update(relative_path=relative, physical_path=str(source), current_sha256=cw.digest(raw),
                                source_excerpt='\n'.join(str(i+1)+': '+lines[i] for i in range(max(0,number-4),min(len(lines),number+3)))[:2400])
            tests.append(receipt)
        tests.sort(key=lambda item:(item.get('stage')=='GREEN',not item['current'],item['profile']))
        checkpoints = []
        for item in metadata.get('checkpoints', [])[-12:]:
            if paths and item['relative_path'] not in paths:
                continue
            cw._file(target, item['relative_path'])  # Recheck current read access.
            checkpoints.append(item)
        from acceptance_contracts import load as load_contracts, summary
        return {'status': 'coding_recovery_context', 'workspace_id': arguments['workspace_id'],
                'acceptance_contracts': summary(load_contracts(root,arguments['workspace_id'],target)),
                'workspace_root': str(target), 'source_root': str(Path(root).resolve()),
                'tree_sha256': tree, 'files': entries, 'tests': tests, 'checkpoints': checkpoints,
                'next_steps': ['Use this workspace ID and canonical HOST paths; Docker executes immutable snapshots.',
                    'Read the first failing source frame once. Compare function arguments/returns with the actual interface.',
                    'Prefer propose_coding_edit with five flat strings: workspace_id, relative_path, expected_sha256, old_text, new_text. CRLF/LF matching is handled by the controller.',
                    'After a rejected edit change the context or hypothesis. Do not repeat an identical failing call.',
                    'Recover corrupted files only from a verified checkpoint proposal, preserving acceptance criteria and fixtures.',
                    'Run the relevant tests after a meaningful fix; report current failure evidence if recovery cannot proceed.'],
                'mutations_performed': False,
                'acceptance': 'A GREEN receipt applies only to its tested tree and assertions; it does not prove frozen requirements or in-game behavior.'}
