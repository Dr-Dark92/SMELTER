"""Judge a Lua host probe run: the read-probe gates plus the Lua host's own evidence.

Operator-only and read-only. verify_runtime_probe.judge checks the shared report
(identity, network checks, four valid samples, plugin hash, loader log). This adds
lua_host.json from the same run folder: Lua 5.4, the lua54.dll actually loaded in the
game process and KeraLua match the profile pins, every read went through the one
callback, all ticks ran on the host's own thread, and no command callback exists.
"""
import argparse
import json
from pathlib import Path
import sys

from verify_runtime_probe import ROOT, judge, latest_report, record, sha256

MAX_EVIDENCE = 64 * 1024


def judge_lua(report_path, profile, loader_log=None, executable=None):
    verdict, reasons, evidence = judge(report_path, profile, loader_log, executable)
    reasons = list(reasons); expect = lambda ok, reason: ok or reasons.append(reason)
    pins = profile['lua_host']; path = Path(report_path).parent / 'lua_host.json'
    lua = None
    if not path.is_file() or path.stat().st_size > MAX_EVIDENCE:
        reasons.append('lua_host_evidence_missing')
    else:
        try:
            lua = json.loads(path.read_bytes().decode('utf-8-sig'))
        except (ValueError, UnicodeError):
            reasons.append('lua_host_evidence_invalid')
        if not isinstance(lua, dict):
            if 'lua_host_evidence_invalid' not in reasons:
                reasons.append('lua_host_evidence_invalid')
            return 'rejected', reasons, evidence
        count = profile['sample_count']
        expect(type(lua.get('schema_version')) is int and lua['schema_version'] == 1, 'lua_host_schema_unsupported')
        expect(lua.get('lua_version') == pins['version'], 'lua_version_mismatch')
        expect(str(lua.get('lua54_sha256', '')).lower() == pins['lua54_sha256'], 'loaded_lua54_hash_mismatch')
        expect(str(lua.get('keralua_sha256', '')).lower() == pins['keralua_sha256'], 'keralua_hash_mismatch')
        loaded = Path(str(lua.get('lua54_module_path', '')))
        expect(loaded.is_file() and sha256(loaded) == pins['lua54_sha256'], 'lua54_on_disk_mismatch')
        binding = Path(str(lua.get('keralua_path', '')))
        expect(binding.is_file() and sha256(binding) == pins['keralua_sha256'], 'keralua_on_disk_mismatch')
        expect(type(lua.get('callback_calls')) is int and lua['callback_calls'] == pins['callback_calls'] == count, 'callback_calls_not_%d' % count)
        ticks = lua.get('tick_numbers')
        expect(isinstance(ticks, list) and all(type(n) is int for n in ticks) and ticks == list(range(1, count + 1)), 'ticks_not_sequential')
        owner = lua.get('host_thread_id'); threads = lua.get('tick_thread_ids')
        expect(type(owner) is int and owner > 0, 'host_thread_id_invalid')
        expect(isinstance(threads, list) and len(threads) == count and
               all(type(n) is int and n == owner for n in threads), 'ticks_left_host_thread')
        expect(type(lua.get('host_mutating_callbacks')) is int and lua['host_mutating_callbacks'] == pins['host_mutating_callbacks'], 'mutating_callbacks_reported')
        for flag in ('integer_division', 'integer_subtype', 'utf8_library', 'ambient_libraries_absent'):
            expect(lua.get(flag) is True, flag + '_failed')
        evidence['lua_host'] = {'path': str(path), 'sha256': sha256(path), **{k: lua.get(k) for k in
                                ('lua_version', 'lua54_module_path', 'lua54_sha256', 'keralua_path', 'keralua_sha256', 'callback_calls')}}
    return ('lua_host_verified' if not reasons else 'rejected'), reasons, evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--profile', default=str(ROOT / 'mods/gta-ark/gta/rph/lua_host_probe_expectations.json'))
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--report'); source.add_argument('--latest', action='store_true')
    parser.add_argument('--loader-log'); parser.add_argument('--executable'); parser.add_argument('--root', default=str(ROOT))
    args = parser.parse_args(argv)
    profile = json.loads(Path(args.profile).read_text(encoding='utf-8'))
    report = Path(args.report) if args.report else latest_report(profile['channel'])
    verdict, reasons, evidence = judge_lua(report, profile, args.loader_log, args.executable)
    path, _ = record(args.root, verdict, reasons, evidence, Path(args.profile))
    print(json.dumps({'verdict': verdict, 'reasons': reasons, 'receipt': str(path)}, indent=2))
    return 0 if verdict == 'lua_host_verified' else 1


if __name__ == '__main__':
    sys.exit(main())
