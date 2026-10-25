"""Pinned standalone Universal Modder CLI, without replacing Melty's um.

Usage: python tools/modding/um.py scan "C:/Games/Foo" --json
       python tools/modding/um.py kb search "unreal" --json
"""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/dashboard'))


if __name__ == '__main__':
    from universal_modder import verified_installation, cli_command
    installed = verified_installation(ROOT)
    # Explicit standalone invocation retains the operator's normal host permissions.
    # The separate MCP adapter exposes only fixed read-only operations.
    raise SystemExit(subprocess.call(cli_command(installed, sys.argv[1:])))
