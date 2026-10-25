"""Fixed Linux container driver. Read-only metadata commands, bounded streamed output."""
import json
import os
import selectors
import subprocess
import sys
import time

COMMANDS = {
    ('pak', 'info'): ['/opt/engine-cli/repak/repak', 'info', '/input/archive.pak'],
    ('pak', 'list'): ['/opt/engine-cli/repak/repak', 'list', '/input/archive.pak'],
    ('iostore', 'info'): ['/opt/engine-cli/retoc/retoc', 'info', '/input/archive.utoc'],
    ('iostore', 'list'): ['/opt/engine-cli/retoc/retoc', 'list', '/input/archive.utoc', '--size', '--path'],
    ('unity', 'list'): ['/opt/engine-cli/unity/UnityDataTool', 'archive', 'list', '/input/archive'],
    ('unity', 'header'): ['/opt/engine-cli/unity/UnityDataTool', 'sf', 'header', '/input/archive'],
    ('unity', 'metadata'): ['/opt/engine-cli/unity/UnityDataTool', 'sf', 'metadata', '/input/archive'],
    ('unity', 'objects'): ['/opt/engine-cli/unity/UnityDataTool', 'sf', 'objectlist', '/input/archive'],
}
MAX_BYTES = 32 * 1024 * 1024
MAX_LINE = 4096
MAX_LINES = 500000
MAX_RETURN = 48000
SECONDS = 55


def inspect(request):
    command = list(COMMANDS[(request['format'], request['action'])])
    if request.get('entry'):
        command += ['--entry', request['entry']]
    offset, limit = request['offset'], request['limit']
    query = request.get('contains', '').casefold()
    lines, matching, observed, returned = [], 0, 0, 0
    stdout_bytes = stderr_bytes = 0
    errors = bytearray()
    pending = b''
    shortened = False
    return_limited = False
    stopped = None

    def line(raw):
        nonlocal matching, observed, returned, shortened, return_limited
        observed += 1
        shortened |= len(raw) > MAX_LINE
        value = raw[:MAX_LINE].decode('utf-8', 'replace').rstrip('\r')
        if query and query not in value.casefold():
            return
        if matching >= offset and len(lines) < limit and not return_limited:
            length = len(value.encode('utf-8'))
            if returned + length <= MAX_RETURN:
                lines.append(value)
                returned += length
            else:
                return_limited = True
        matching += 1

    start = time.monotonic()
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          stdin=subprocess.DEVNULL, env={**os.environ, 'NO_COLOR': '1', 'TERM': 'dumb', 'RAYON_NUM_THREADS': '2'}) as process:
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ, 'stdout')
        selector.register(process.stderr, selectors.EVENT_READ, 'stderr')
        try:
            while selector.get_map():
                if time.monotonic() - start > SECONDS:
                    stopped = 'time_limit'
                    break
                for key, _ in selector.select(timeout=0.1):
                    chunk = os.read(key.fileobj.fileno(), 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    if key.data == 'stderr':
                        stderr_bytes += len(chunk)
                        errors.extend(chunk)
                        del errors[:-16384]
                    else:
                        stdout_bytes += len(chunk)
                        pending += chunk
                        while b'\n' in pending:
                            raw, pending = pending.split(b'\n', 1)
                            line(raw)
                        # Do not retain a pathological line. Its suffix cannot be searched.
                        if len(pending) > MAX_LINE:
                            shortened = True
                            pending = pending[:MAX_LINE]
                    if stdout_bytes + stderr_bytes > MAX_BYTES or observed > MAX_LINES:
                        stopped = 'output_limit'
                        break
                if stopped:
                    break
            if pending:
                line(pending)
        finally:
            selector.close()
            if process.poll() is None:
                process.kill()
            process.wait(timeout=3)
    more = matching > offset + len(lines)
    complete = stopped is None and process.returncode == 0 and not shortened
    return {'exit_code': process.returncode, 'lines': lines, 'offset': offset,
            'next_offset': offset + len(lines) if more and lines else None,
            'matching_lines_observed': matching, 'lines_observed': observed,
            'scan_complete': complete, 'page_truncated': more or not complete or return_limited,
            'line_shortened': shortened, 'return_byte_limit': return_limited, 'stopped': stopped,
            'stdout_bytes': stdout_bytes, 'stderr_bytes': stderr_bytes,
            'stderr_tail': errors.decode('utf-8', 'replace'),
            'duration_seconds': round(time.monotonic() - start, 3)}


if __name__ == '__main__':
    try:
        print(json.dumps(inspect(json.loads(sys.argv[1]))))
    except Exception as exc:
        print(json.dumps({'worker_error': str(exc)[:1000]}))
        sys.exit(1)
