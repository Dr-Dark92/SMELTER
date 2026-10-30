"""Propose, never apply, a Lua test from a reviewed registered contract."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/dashboard'))

if __name__ == '__main__':
    from contract_test_scaffold import propose
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--workspace-id', required=True)
    parser.add_argument('--contract', required=True)
    parser.add_argument('--destination', required=True)
    args = parser.parse_args()
    print(json.dumps(propose(args.root, args.workspace_id, args.contract, args.destination), indent=2))
