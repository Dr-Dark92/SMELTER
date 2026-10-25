"""Real pinned CLI and stdio MCP knowledge smoke; optional read-only game recon.

Never installs into or launches a game. Saves observations in application-owned
storage. Field-note matches remain reference data, not current-build guarantees.
"""
import argparse
import json
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/dashboard'))


def smoke(game_folders=()):
    from universal_modder import verified_installation, cli_command
    from mcp_connections import exchange
    from process_runner import run
    installed = verified_installation(ROOT)
    output = ROOT / '.smelter/universal-modder-runs' / uuid4().hex
    output.mkdir(parents=True)
    results = {'version':installed['version'],'revision':installed['revision'],'mcp':{},'scans':[]}
    grants = {'coding_workspace':True}
    for args in ({'action':'status'}, {'action':'search_notes','query':'grand theft auto'}):
        result = exchange(ROOT, grants=grants, name='universal_modder', arguments=args, timeout=60)
        tool = result.get('structuredContent', {}).get('tool_result', {})
        if result.get('isError') or tool.get('status') != 'universal_modder_completed':
            raise AssertionError('Universal Modder MCP operation failed: ' + json.dumps(tool))
        results['mcp'][args['action']] = tool
    notes = results['mcp']['search_notes']['notes']
    if not notes:
        raise AssertionError('Pinned GTA knowledge fixture was not found')
    note = notes[0]['path']
    result = exchange(ROOT, grants=grants, name='universal_modder',
                      arguments={'action':'read_note','note':note,'limit':3000}, timeout=60)
    tool = result.get('structuredContent', {}).get('tool_result', {})
    if result.get('isError') or not tool.get('text') or tool.get('note') != note:
        raise AssertionError('Pinned field-note read did not complete')
    results['mcp']['read_note'] = tool
    for index, folder in enumerate(game_folders):
        path = Path(folder).resolve(strict=True)
        if not path.is_dir():
            raise ValueError('Game recon needs an existing directory')
        done = run(cli_command(installed, ['scan',str(path),'--json']), timeout=90, max_output=512*1024, text=True, encoding='utf-8',check=True)
        report = json.loads(done.stdout)
        (output / ('scan-' + str(index) + '.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
        results['scans'].append({'input':str(path),'name':report.get('name'),'engine':report.get('engine'),
                                 'engine_detail':report.get('engine_detail'),'route_count':len(report.get('routes',[]))})
    evidence = output / 'smoke.json'
    evidence.write_text(json.dumps(results,indent=2),encoding='utf-8')
    return {'status':'passed','revision':installed['revision'],'mcp_operations':['status','search_notes','read_note'],
            'matched_note':note,'scans':results['scans'],'evidence':str(evidence),'game_execution':False}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scan-game',action='append',default=[])
    args=parser.parse_args()
    print(json.dumps(smoke(args.scan_game),indent=2))
