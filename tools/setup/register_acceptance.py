"""Register a reviewed frozen contract outside a model's editable coding copy."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/dashboard'))

if __name__=='__main__':
    from acceptance_contracts import register, DEFINITIONS
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--workspace-id',required=True)
    parser.add_argument('--contract',choices=list(DEFINITIONS),required=True)
    parser.add_argument('--subject',required=True,help='Existing project-relative Lua module path')
    args=parser.parse_args();print(json.dumps(register(args.root,args.workspace_id,args.contract,args.subject),indent=2))
