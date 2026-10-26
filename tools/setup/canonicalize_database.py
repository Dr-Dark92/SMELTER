"""Back up and canonicalize an existing database pointer; never move its data.

Preview by default. Run from the app environment that can see the selected
database (for example Codex when Windows redirected its LocalAppData).
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/dashboard'))


def canonicalize(root=ROOT, *, apply=False):
    from database import chosen_database, inspect_database, marker_path
    from python_tools import _plain_path
    root = _plain_path(Path(root).resolve())
    marker = _plain_path(marker_path(root))
    if marker.stat().st_size > 16384: raise ValueError('Database marker exceeds its size budget')
    before = marker.read_bytes(); value = json.loads(before)
    status = inspect_database(root, integrity=True)
    if not status['ready']: raise ValueError('Selected database is not readable/ready: ' + status['status'])
    database = _plain_path(chosen_database(root))
    canonical = _plain_path(database.resolve(strict=True))
    if not database.samefile(canonical): raise ValueError('Canonical path does not identify the selected database')
    result = {'mode': 'apply' if apply else 'preview', 'old_path': str(database), 'canonical_path': str(canonical),
              'changed': value['path'] != str(canonical), 'data_moved': False, 'backup': None}
    if not apply or not result['changed']: return result
    from maintenance import _idle
    _idle(root)
    destination = _plain_path(root / '.smelter/database-pointer-backups' /
        (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid4().hex[:8]))
    destination.mkdir(parents=True, exist_ok=False)
    marker_backup = destination / 'database-location.json'
    with marker_backup.open('xb') as stream: stream.write(before)
    snapshot = destination / 'smelter.sqlite3'
    with snapshot.open('xb'): pass
    # SQLite online backup also captures committed WAL data consistently.
    with closing(sqlite3.connect(canonical.as_uri() + '?mode=ro', uri=True, timeout=5)) as source:
        with closing(sqlite3.connect(snapshot)) as target:
            source.backup(target)
            if target.execute('PRAGMA quick_check').fetchone() != ('ok',): raise ValueError('Database backup failed its integrity check')
    if marker.read_bytes() != before: raise ValueError('Database pointer changed during backup; preserved without applying')
    value['path'] = str(canonical)
    pending = _plain_path(marker.with_name(marker.name + '.' + uuid4().hex + '.pending'))
    with pending.open('xb') as stream: stream.write((json.dumps(value) + '\n').encode('utf-8'))
    try:
        if marker.read_bytes() != before: raise ValueError('Database pointer changed before apply')
        pending.replace(marker)
    finally: pending.unlink(missing_ok=True)
    if not inspect_database(root, integrity=True)['ready']: raise ValueError('Canonical database failed final verification; inspect the preserved backup')
    result['backup'] = str(destination)
    result['backup_sha256'] = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    (destination / 'receipt.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT); parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(); print(json.dumps(canonicalize(args.root, apply=args.apply), indent=2))
