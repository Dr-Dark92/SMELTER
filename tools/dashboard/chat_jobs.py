"""Bounded in-memory chat jobs and cancellable local inference transport."""
import http.client
import io
import json
import socket
import threading
import time
from uuid import uuid4


class ChatCancelled(ValueError):
    pass


class _CancellableReader(io.RawIOBase):
    """Retry raw socket timeouts without poisoning a buffered HTTP reader."""
    def __init__(self, sock, control, deadline):
        super().__init__()
        self.sock, self.control, self.deadline = sock, control, deadline

    def readable(self):
        return True

    def readinto(self, buffer):
        while True:
            self.control.check()
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise ValueError('Chat turn time limit reached')
            self.sock.settimeout(min(0.2, remaining))
            try:
                count = self.sock.recv_into(buffer)
            except socket.timeout:
                continue
            except OSError:
                self.control.check()
                raise
            self.control.check()
            return count


class _ResponseSocket:
    def __init__(self, sock, control, deadline):
        self.sock, self.control, self.deadline = sock, control, deadline

    def makefile(self, mode):
        if mode != 'rb':
            raise ValueError('Only binary HTTP response reads are supported')
        return io.BufferedReader(_CancellableReader(self.sock, self.control, self.deadline))


class Control:
    def __init__(self):
        self.lock = threading.RLock()
        self.cancelled = threading.Event()
        self.sock = None
        self.phase = 'Waiting for model'
        self.completed = False
        self.file_activity = None
        self.tool_call_limit = 4

    def check(self):
        if self.cancelled.is_set():
            raise ChatCancelled('Request stopped')

    def update(self, phase):
        with self.lock:
            self.check()
            self.phase = phase

    def cancel(self):
        with self.lock:
            if self.completed:
                return False
            self.cancelled.set()
            self.phase = 'Stopping; waiting for any active tool to finish'
            if self.sock:
                try:
                    self.sock.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
            return True

    def infer(self, body, timeout, maximum):
        """Read native Ollama NDJSON; close its request socket on Stop."""
        self.update('Waiting for model')
        deadline = time.monotonic() + timeout
        connection = http.client.HTTPConnection('127.0.0.1', 11434, timeout=timeout)
        response = None
        cancel_socket = None
        body = {**body, 'stream': True}
        try:
            connection.connect()
            with self.lock:
                self.check()
                # HTTPConnection can close its socket object after handing a
                # connection-close response to HTTPResponse. Keep an independently
                # owned handle for shutdown while the response reader is active.
                cancel_socket = connection.sock.dup()
                self.sock = cancel_socket
            connection.request('POST', '/api/chat', json.dumps(body), {'Content-Type': 'application/json'})
            # HTTPResponse retains its normal header, chunked-transfer and line
            # parsing, but every raw read checks Stop at most 200 ms apart.
            connection.response_class = lambda sock, **kwargs: http.client.HTTPResponse(
                _ResponseSocket(cancel_socket, self, deadline), **kwargs)
            response = connection.getresponse()
            if response.status != 200:
                raise ValueError('Local Ollama HTTP error: ' + str(response.status))
            content, thinking, calls, size = [], [], [], 0
            while True:
                self.check()
                if time.monotonic() >= deadline:
                    raise ValueError('Chat turn time limit reached')
                line = response.readline(maximum + 1)
                self.check()
                if not line:
                    raise ValueError('Ollama stream ended without completion')
                size += len(line)
                if size > maximum:
                    raise ValueError('Model stream too large')
                part = json.loads(line)
                if part.get('error'):
                    raise ValueError('Local Ollama: ' + str(part['error'])[:300])
                message = part.get('message', {})
                if not isinstance(message, dict):
                    raise ValueError('Invalid Ollama stream message')
                for key, output in (('content', content), ('thinking', thinking)):
                    value = message.get(key, '')
                    if not isinstance(value, str):
                        raise ValueError('Invalid Ollama stream content')
                    if value:
                        output.append(value)
                        self.update('Generating response' if key == 'content' else 'Model thinking')
                new_calls = message.get('tool_calls', [])
                if not isinstance(new_calls, list):
                    raise ValueError('Invalid Ollama tool calls')
                calls.extend(new_calls)
                if self.file_activity is not None:
                    for call in new_calls:
                        self.file_activity.propose(call)
                if len(calls) > self.tool_call_limit:
                    raise ValueError('Excessive Ollama tool calls')
                if part.get('done'):
                    return json.dumps({'message': {'role': 'assistant', 'content': ''.join(content),
                                      'tool_calls': calls}, 'done_reason': part.get('done_reason', 'stop')}).encode()
        except http.client.HTTPException as exc:
            self.check()
            raise ValueError('Ollama connection ended unexpectedly') from exc
        finally:
            with self.lock:
                self.sock = None
            if cancel_socket is not None:
                cancel_socket.close()
            if response is not None:
                response.close()
            connection.close()


class Jobs:
    def __init__(self):
        self.lock = threading.Lock()
        self.jobs = {}

    def start(self, root, data, worker=None):
        from chats import read_chat
        read_chat(root, data.get('id'))
        prompt = data.get('content')
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 1800:
            raise ValueError('Prompt must be 1–1800 characters')
        with self.lock:
            if any(j['state'] == 'running' for j in self.jobs.values()):
                raise ValueError('A chat request is already running; finish or stop it first')
            if len(self.jobs) >= 50:
                del self.jobs[next(iter(self.jobs))]
            job = {'id': str(uuid4()), 'conversation_id': data['id'], 'state': 'running',
                   'started': time.monotonic(), 'control': Control(), 'error': None}
            self.jobs[job['id']] = job
        threading.Thread(target=self._run, args=(root, data, job, worker), daemon=True).start()
        return self.status(job['id'])

    def _run(self, root, data, job, worker):
        from chat_inference import ask
        control = job['control']
        try:
            (worker or ask)(root, data['id'], data['content'], image=data.get('image'),
                skills=data.get('skills'), auto_skills=data.get('auto_skills', False),
                tool_permissions=data.get('tool_permissions'), control=control)
            state, error = ('cancelled', None) if control.cancelled.is_set() else ('done', None)
        except ChatCancelled:
            state, error = 'cancelled', None
        except Exception as exc:
            state, error = ('cancelled', None) if control.cancelled.is_set() else ('error', str(exc)[:1000])
        if control.file_activity is not None:
            control.file_activity.settle(state == 'cancelled')
        with self.lock:
            job.update(state=state, error=error, ended=time.monotonic())

    def status(self, jid):
        with self.lock:
            if jid not in self.jobs:
                raise ValueError('Chat request not found; the server may have restarted')
            job = self.jobs[jid]
            return {k: job[k] for k in ('id', 'conversation_id', 'state', 'error')} | {
                'phase': job['control'].phase,
                'files': job['control'].file_activity.snapshot() if job['control'].file_activity is not None else [],
                'elapsed_seconds': round(job.get('ended', time.monotonic()) - job['started'], 1)}

    def cancel(self, jid):
        with self.lock:
            if jid not in self.jobs:
                raise ValueError('Chat request not found')
            job = self.jobs[jid]
            if job['state'] == 'running':
                job['control'].cancel()
        return self.status(jid)


JOBS = Jobs()
