"""Move native binding archives into a dated, hash-verified folder so rebinding can continue."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/dashboard'))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',default=str(ROOT))
    args=parser.parse_args(argv)
    from native_progress import export_archives
    result=export_archives(Path(args.root))
    print(json.dumps(result or {'count':0,'folder':None}))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
