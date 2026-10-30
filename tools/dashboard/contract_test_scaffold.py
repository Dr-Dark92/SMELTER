"""Propose an editable conformance test from an operator-pinned Lua contract.

The protected verifier still runs independently. This copy removes the need for
a model to invent another interface or weaken expectations while writing tests.
It is never applied automatically and confers no access or runtime capability.
"""
import json
from pathlib import PurePosixPath

import acceptance_contracts as acceptance
import coding_workspace as cw


def propose(root, workspace_id, contract_id, destination):
    destination = cw.relative_path(destination, edit=True)
    test = PurePosixPath(destination)
    if test.parent.name != 'tests' or not test.name.startswith('test_') or test.suffix != '.lua':
        raise ValueError('Choose a test_*.lua file directly inside the subject project tests directory')
    with cw.locked(root):
        _, target = cw.load(root, workspace_id)
        contracts = acceptance.load(root, workspace_id, target)
        matches = [c for c in contracts if c['id'] == contract_id]
        if len(matches) != 1:
            raise ValueError('Choose an operator-registered contract in this workspace')
        contract = matches[0]
        subject = PurePosixPath(contract['subject_path'])
        project = test.parent.parent
        if not subject.is_relative_to(project) or subject.is_relative_to(test.parent):
            raise ValueError('Destination must be inside the same subject project, with source outside tests')
        relative_subject = subject.relative_to(project).as_posix()
        verifier = acceptance.verifier_path(contract_id).read_bytes()
        if cw.digest(verifier) != contract['verifier_sha256']:
            raise ValueError('Frozen verifier changed; operator review required')
        path = cw._file(target, destination, edit=True)
        expected = cw.digest(path.read_bytes()) if path.exists() else None
        header = ('-- Generated from operator-pinned ' + contract_id + '.\n'
                  '-- Verifier SHA256: ' + contract['verifier_sha256'] + '\n'
                  '-- This editable copy does not replace independent frozen acceptance.\n'
                  'local arg = {' + json.dumps(relative_subject, ensure_ascii=False) + '}\n')
        content = header + verifier.decode('utf-8')
    # propose rechecks current bytes and access under its own transaction and
    # parses Lua before recording a proposal. No model text is interpolated.
    result = cw.propose(root, {'workspace_id':workspace_id, 'allow_large_replacement':True,
        'changes':[{'relative_path':destination, 'expected_sha256':expected, 'content':content}]})
    return {**result, 'contract_id':contract_id, 'verifier_sha256':contract['verifier_sha256'],
            'checks':acceptance.DEFINITIONS[contract_id]['checks'], 'applied':False,
            'scope':'Editable conformance fixture only; protected acceptance remains independent'}
