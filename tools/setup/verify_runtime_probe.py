"""Judge a native read-probe report against a reviewed expectation profile.

Operator-only and read-only: it never launches a game, installs a loader or edits
the report. The report is self-reported by the plugin, so the verdict re-hashes
the executable on disk and records every input hash; it is still not an
authenticated proof of a live session.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import ntpath
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
MAX_REPORT = 1024 * 1024
MAX_LOG = 16 * 1024 * 1024
MAX_LOG_LINES = 20


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def probe_root():
    local = os.environ.get('LOCALAPPDATA')
    if not local:
        raise ValueError('LOCALAPPDATA is unavailable')
    return Path(local) / 'SMELTER' / 'runtime-probes'


def latest_report(channel, root=None):
    folder = Path(root or probe_root()) / channel
    reports = sorted(folder.glob('*/probe.json'), key=lambda p: p.stat().st_mtime) if folder.is_dir() else []
    if not reports:
        raise ValueError('No probe.json under ' + str(folder))
    return reports[-1]


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def judge(report_path, profile, loader_log=None, executable=None):
    """Return (verdict, reasons, evidence). Every failed check adds a reason; none is skipped silently."""
    report_path = Path(report_path)
    if report_path.stat().st_size > MAX_REPORT:
        raise ValueError('Probe report exceeds 1 MiB')
    raw = report_path.read_bytes()
    report = json.loads(raw.decode('utf-8-sig'))
    reasons = []
    expect = lambda ok, reason: ok or reasons.append(reason)
    count = profile['sample_count']
    expect(report.get('schema_version') == 1, 'report_schema_unsupported')
    expect(report.get('stage') == profile['stage'], 'stage_not_' + profile['stage'])
    expect(report.get('scope') == profile['scope'], 'scope_mismatch')
    expect(report.get('native_reads_completed') is True, 'native_reads_not_completed')
    expect(not report.get('error'), 'report_error:' + str(report.get('error'))[:200])
    expect(report_path.parent.name == report.get('run_id'), 'run_id_folder_mismatch')
    # Claim boundaries: a read probe must never claim gameplay or report a mutating call.
    expect(report.get('game_runtime_verified') is False, 'report_overclaims_game_runtime')
    expect(report.get('probe_mutating_calls') == 0, 'mutating_calls_reported')
    expect(report.get('network_session_checks') == count, 'network_checks_not_%d' % count)
    samples = report.get('samples') or []
    expect(len(samples) == count, 'samples_not_%d' % count)
    times = []
    for i, sample in enumerate(samples):
        ok = (isinstance(sample, dict) and sample.get('valid') is True and bool(sample.get('handle'))
              and all(_finite(sample.get(axis)) for axis in 'xyz') and bool(sample.get('utc')))
        expect(ok, 'sample_%d_invalid' % i)
        if ok:
            times.append(sample['utc'])
    expect(times == sorted(times), 'sample_times_not_ordered')
    pinned = profile['executable']
    expect(Path(str(report.get('executable', ''))).name.lower() == pinned['name'].lower(), 'executable_name_mismatch')
    expect(report.get('file_version') == pinned['file_version'], 'executable_version_mismatch')
    expect(str(report.get('executable_sha256', '')).lower() == pinned['sha256'], 'reported_executable_hash_mismatch')
    expect(str(report.get('plugin_sha256', '')).lower() == profile['plugin']['sha256'], 'plugin_hash_mismatch')
    # Independent check: the file on disk must still be the pinned build.
    on_disk = Path(executable or report.get('executable') or '')
    disk_hash = sha256(on_disk) if on_disk.is_file() else None
    expect(disk_hash == pinned['sha256'], 'executable_on_disk_mismatch' if disk_hash else 'executable_on_disk_unavailable')
    evidence = {'report': str(report_path), 'report_sha256': hashlib.sha256(raw).hexdigest(), 'run_id': report.get('run_id'),
                'runtime_assembly': report.get('runtime_assembly'), 'executable_on_disk_sha256': disk_hash, 'loader_log': None}
    # Match the deployed binary, not merely the hash a report claims it ran.
    relative = profile['plugin'].get('deployed_relative_path')
    if relative is not None:
        if (not isinstance(relative, str) or not relative or ntpath.isabs(relative)
                or ':' in relative or '..' in relative.replace('\\', '/').split('/')):
            raise ValueError('Deployed plugin path must stay under the executable folder')
        deployed = on_disk.parent / Path(relative.replace('\\', '/'))
        deployed_hash = sha256(deployed) if deployed.is_file() else None
        expect(deployed_hash == profile['plugin']['sha256'],
               'deployed_plugin_hash_mismatch' if deployed_hash else 'deployed_plugin_unavailable')
        evidence['deployed_plugin'] = {'path': str(deployed), 'sha256': deployed_hash}
    rule = profile.get('loader_log')
    if loader_log is not None:
        log = Path(loader_log)
        if not log.is_file() or log.stat().st_size > MAX_LOG:
            reasons.append('loader_log_unavailable_or_oversized')
        else:
            text = log.read_bytes().decode('utf-8', errors='replace')
            needles = [n.lower() for n in rule['must_mention']]
            lines = [line.strip() for line in text.splitlines() if any(n in line.lower() for n in needles)]
            expect(bool(lines), 'loader_log_never_mentions_plugin')
            expect(not any('exception' in line.lower() for line in lines), 'loader_log_plugin_exception')
            evidence['loader_log'] = {'path': str(log), 'sha256': sha256(log), 'plugin_lines': lines[:MAX_LOG_LINES]}
            prefix = rule.get('receipt_prefix')
            if prefix:
                # RPH prepends timestamps and the plugin's friendly name. Compare
                # the entire path after our fixed marker, including the run ID.
                linked = [line.strip() for line in text.splitlines() if prefix in line]
                # realpath also expands Windows 8.3 aliases used by some Temp
                # folders; they identify the same file as its long path.
                normalize = lambda p: ntpath.normcase(ntpath.normpath(os.path.realpath(p.strip().strip('"'))))
                exact = [line for line in linked
                         if normalize(line.split(prefix, 1)[1]) == normalize(str(report_path.resolve()))]
                expect(bool(exact), 'loader_log_report_path_mismatch')
                evidence['loader_log']['report_link_lines'] = exact[:MAX_LOG_LINES]
    elif rule and rule.get('required'):
        reasons.append('loader_log_required')
    verdict = 'native_reads_verified' if not reasons else 'rejected'
    return verdict, reasons, evidence


def record(root, verdict, reasons, evidence, profile_path):
    folder = Path(root) / '.smelter' / 'runtime-probe-verdicts'
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    receipt = {'schema_version': 1, 'judged_at': datetime.now(timezone.utc).isoformat(), 'verdict': verdict,
               'reasons': reasons, 'profile': str(profile_path), 'profile_sha256': sha256(profile_path),
               'claims': {'self_reported_report': True, 'game_runtime_verified': False, 'gameplay_verified': False},
               **evidence}
    run = evidence.get('run_id')
    if not isinstance(run, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', run):
        # A rejected report's untrusted ID must not choose the receipt path.
        run = 'invalid-run-' + hashlib.sha256(repr(run).encode('utf-8')).hexdigest()[:16]
    path = folder / (run + '-' + stamp + '.json')
    with open(path, 'x', encoding='utf-8') as out:
        json.dump(receipt, out, indent=2)
    return path, receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True, help='Reviewed expectation profile JSON')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--report', help='probe.json to judge')
    source.add_argument('--latest', action='store_true', help="Newest report in the profile's channel")
    parser.add_argument('--loader-log', help="The loader's own log from the same run")
    parser.add_argument('--executable', help='Executable to re-hash (default: the path the report names)')
    parser.add_argument('--root', default=str(ROOT))
    args = parser.parse_args(argv)
    profile = json.loads(Path(args.profile).read_text(encoding='utf-8'))
    report = Path(args.report) if args.report else latest_report(profile['channel'])
    verdict, reasons, evidence = judge(report, profile, args.loader_log, args.executable)
    path, _ = record(args.root, verdict, reasons, evidence, Path(args.profile))
    print(json.dumps({'verdict': verdict, 'reasons': reasons, 'receipt': str(path)}, indent=2))
    return 0 if verdict == 'native_reads_verified' else 1


if __name__ == '__main__':
    sys.exit(main())
