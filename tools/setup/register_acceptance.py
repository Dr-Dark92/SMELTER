"""Register a reviewed frozen contract outside a model's editable coding copy."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/dashboard'))

if __name__=='__main__':
    from acceptance_contracts import register, migrate, DEFINITIONS
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--workspace-id',required=True)
    parser.add_argument('--contract',choices=list(DEFINITIONS),required=True)
    action=parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--subject',help='Existing project-relative Lua module path')
    action.add_argument('--migrate',metavar='REASON',help='Re-pin an already registered contract to its reviewed current verifier; REASON is logged')
    args=parser.parse_args()
    result=(migrate(args.root,args.workspace_id,args.contract,args.migrate) if args.migrate is not None
            else register(args.root,args.workspace_id,args.contract,args.subject))
    print(json.dumps(result,indent=2))
