"""Controller-owned loop limits, renewable MCP budgets and safe read retries."""
import errno
import hashlib
import json
import time

READ_ONLY = frozenset({'read_coding_file', 'list_coding_files', 'coding_workspace_context',
                       'coding_recovery_context', 'review_coding_workspace'})


def retryable_read(name, error):
    # Never retry writes, tests/builds, access denials or missing paths.
    return name in READ_ONLY and isinstance(error, OSError) and (
        error.errno in {errno.EAGAIN, errno.EBUSY, errno.EINTR, errno.ECONNRESET, errno.ETIMEDOUT}
        or getattr(error, 'winerror', None) in {32, 33})


class PersistentBudget:
    """Rate window for persistent stdio, renewed only by the monotonic clock.

    A connection outlives a turn; exhausting 32 lifetime calls must not disable
    every subsequent user turn. Renewal never changes grants or permissions.
    """
    def __init__(self, clock=time.monotonic, limit=128, seconds=900):
        self.clock, self.limit, self.seconds = clock, limit, seconds
        self.start, self.used = clock(), 0

    def consume(self):
        now = self.clock()
        if now - self.start >= self.seconds:
            self.start, self.used = now, 0
        if self.used >= self.limit:
            return {'status': 'error', 'code': 'call_budget_window',
                    'error': 'MCP work-window call budget reached; preserve task state and wait for renewal.',
                    'retry_after_seconds': max(1, int(self.seconds - (now-self.start)) + 1),
                    'limit': self.limit, 'window_seconds': self.seconds}
        self.used += 1
        return None


class RecoveryGuard:
    def __init__(self):
        self.failures, self.reads = {}, {}

    def key(self, name, arguments):
        raw = json.dumps([name, arguments], sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(raw.encode()).hexdigest()

    def before(self, name, arguments):
        key = self.key(name, arguments)
        failed, reads = self.failures.get(key, 0), self.reads.get(key, (None, 0))[1]
        if failed >= 2 or (name == 'read_coding_file' and reads >= 4):
            return {'status': 'error', 'code': 'recovery_required',
                    'error': 'Repeated unchanged read or identical failed call blocked before execution.',
                    'next_action': 'Use coding_recovery_context, inspect the actual failure once, then change the inputs or hypothesis. Do not switch to native edit/bash to bypass this guard.',
                    'repeated_failures': failed, 'unchanged_reads': reads}
        return None

    def after(self, name, arguments, result):
        key = self.key(name, arguments)
        if result.get('status') in ('error','coding_tests_failed') and result.get('code') != 'recovery_required':
            self.failures[key] = self.failures.get(key, 0) + 1
        elif result.get('status') != 'error':
            self.failures.pop(key, None)
        if name == 'read_coding_file' and result.get('status') == 'coding_file_read':
            previous, count = self.reads.get(key, (None, 0))
            sha = result.get('sha256')
            self.reads[key] = (sha, count+1 if sha == previous else 1)
        if result.get('status') == 'coding_patch_applied' and not result.get('reused'):
            self.reads.clear(); self.failures.clear()
        for values in (self.failures, self.reads):
            while len(values) > 128:values.pop(next(iter(values)))


def evidence(root, arguments):
    from coding_recovery import recover
    if not isinstance(arguments, dict) or not arguments.get('workspace_id'):
        return {'next_action': 'Use coding_workspace_context to recover the existing workspace ID.'}
    request = {'workspace_id': arguments['workspace_id']}
    path = arguments.get('relative_path')
    if isinstance(path, str):request['relative_paths'] = [path]
    try:
        return recover(root, request)
    except (ValueError, OSError, UnicodeError, KeyError, TypeError):
        return {'next_action': 'Use coding_workspace_context with the existing workspace ID; recovery evidence is unavailable under current access.'}
