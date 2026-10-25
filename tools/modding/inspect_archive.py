"""CLI for the same fixed, read-only engine archive adapter exposed over MCP."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/dashboard'))

if __name__=='__main__':
    from access_policy import current, using, check_grants
    from engine_archive import inspect
    from python_tools import permissions
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',required=True,help='Registered read-only inventory scope')
    parser.add_argument('--format',required=True,choices=['pak','iostore','unity'])
    parser.add_argument('--action',required=True,choices=['info','list','header','metadata','objects'])
    parser.add_argument('--relative-path',required=True)
    parser.add_argument('--entry')
    parser.add_argument('--contains')
    parser.add_argument('--offset',type=int,default=0)
    parser.add_argument('--limit',type=int,default=100)
    args=vars(parser.parse_args())
    grants=permissions(ROOT,{'inventory_root':args.pop('folder')})
    policy=current(ROOT);check_grants(ROOT,grants,policy)
    with using(policy):result=inspect(ROOT,grants,{k:v for k,v in args.items() if v is not None})
    print(json.dumps(result,indent=2))
    sys.exit(0 if result['status']=='engine_archive_completed' else 1)
