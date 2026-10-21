"""Bounded in-memory chat jobs and cancellable local inference transport."""
import http.client
import io
import json
import socket
import sqlite3
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
        self.output_text = ''
        self.tool_activity = []
        self.access_policy = None
        self.context_budget = None
        self.configuration = None
        self.terminal_result = None
        self.job_id = None
        self.admitted_at = None
        self.journal_committed = False

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
        with self.lock:
            self.output_text = ''
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
                if not isinstance(part, dict):
                    raise ValueError('Invalid Ollama stream packet: expected an object')
                if type(part.get('done', False)) is not bool:
                    raise ValueError('Invalid Ollama completion flag')
                if part.get('done') and not isinstance(part.get('done_reason', 'stop'), str):
                    raise ValueError('Invalid Ollama completion reason')
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
                        if key == 'content':
                            with self.lock:
                                self.output_text = ''.join(content)[-64000:]
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
        self.lock = threading.RLock()
        self.jobs = {}

    def start(self, root, data, worker=None):
        from chats import read_chat
        read_chat(root, data.get('id'))
        from job_store import recover,active
        self.retry_persistence(root)
        recover(root)
        if active(root):raise ValueError('A recorded task is still owned by a live process; inspect it before starting another')
        prompt = data.get('content')
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 1800:
            raise ValueError('Prompt must be 1–1800 characters')
        from access_policy import current, check_grants
        policy = current(root)
        supplied = data.get('tool_permissions') or {}
        if not isinstance(supplied, dict):raise ValueError('Invalid tool permissions')
        check_grants(root, supplied, policy)
        if supplied.get('mcp_tools'):
            raise ValueError('External MCP execution requires a confined runner; no process was started')
        engine = data.get('engine', 'ollama')
        if engine not in ('ollama', 'opencode_readonly'):
            raise ValueError('Unknown execution engine')
        if engine == 'opencode_readonly':
            if data.get('opencode_approval') is not True:
                raise ValueError('Approve this read-only OpenCode session before sending')
            from functools import partial
            from opencode_runtime import ask as opencode_ask
            worker = partial(opencode_ask, model_key=data.get('opencode_model'), approval=True)
        from task_contract import configuration
        effective=configuration(root)
        if data.get('configuration_revision') and data['configuration_revision']!=effective['revision']:
            raise ValueError('Task configuration changed; refresh task access before sending')
        if data.get('policy_revision') and data['policy_revision']!=policy.revision:
            raise ValueError('Access policy changed; refresh task access before sending')
        with self.lock:
            if any(j['state'] == 'running' for j in self.jobs.values()):
                raise ValueError('A chat request is already running; finish or stop it first')
            if len(self.jobs) >= 50:
                removable=next((jid for jid,old in self.jobs.items() if old['state']!='running' and not old.get('persistence_pending')),None)
                if removable is None:raise ValueError('Unpersisted task outcomes must be saved before admitting more work')
                del self.jobs[removable]
            job = {'id': str(uuid4()), 'conversation_id': data['id'], 'state': 'running',
                   'started': time.monotonic(), 'control': Control(), 'error': None, 'engine':engine, 'root':root,'prompt':data['content']}
            job['control'].job_id=job['id']
            job['control'].admitted_at=job['started']
            job['control'].access_policy = policy
            job['control'].configuration = effective
            from job_store import admit
            admit(root,{'id':job['id'],'conversation_id':job['conversation_id'],'engine':engine,'state':'running','error':None,'phase':'Admitted','policy_revision':policy.revision,'configuration':effective,'elapsed_seconds':0,'prompt':data['content']})
            self.jobs[job['id']] = job
        try:threading.Thread(target=self._run, args=(root, data, job, worker), daemon=True).start()
        except RuntimeError as exc:
            self._finish(root,job,'error','Task worker could not start: '+str(exc)[:500])
            raise ValueError('Task worker could not start; no action was executed') from exc
        return self.status(job['id'])

    def _run(self, root, data, job, worker):
        from chat_inference import ask
        control = job['control']
        try:
            result = (worker or ask)(root, data['id'], data['content'], image=data.get('image'),
                skills=data.get('skills'), auto_skills=data.get('auto_skills', False),
                tool_permissions=data.get('tool_permissions'), control=control)
            from task_contract import job_state
            with control.lock:
                terminal = control.terminal_result or result or {}
                state = job_state(terminal)
                error = terminal.get('error')
                if not control.completed and control.cancelled.is_set():state='cancelled'
                control.completed=True
        except ChatCancelled:
            state, error = 'cancelled', None
        except Exception as exc:
            state, error = ('cancelled', None) if control.cancelled.is_set() else ('error', str(exc)[:1000])
        if control.file_activity is not None:
            control.file_activity.settle(state == 'cancelled')
        self._finish(root,job,state,error)

    def _finish(self,root,job,state,error):
        with self.lock:
            control=job['control']
            with control.lock:
                if control.terminal_result is not None:
                    from task_contract import job_state
                    state,error=job_state(control.terminal_result),control.terminal_result.get('error')
                elif not control.completed and control.cancelled.is_set():state,error='cancelled',None
                control.completed=True
                control.phase={'done':'Completed','cancelled':'Stopped','partial':'Partially completed','error':'Failed'}[state]
            job.update(state=state,error=error,ended=time.monotonic(),persistence_pending=False,persistence_error=None)
            if not job['control'].journal_committed:self._persist(root,job)

    def _persist(self,root,job):
        from job_store import save
        try:
            save(root,self._snapshot(job))
            job.update(persistence_pending=False,persistence_error=None)
        except (ValueError,OSError,TypeError,sqlite3.Error) as exc:
            job.update(persistence_pending=True,persistence_error='Task ended but its job record is not saved: '+str(exc)[:500])

    def retry_persistence(self,root):
        """Retry metadata only; never rerun a worker, model request or tool action."""
        from pathlib import Path
        with self.lock:
            for job in self.jobs.values():
                if job.get('persistence_pending') and Path(job['root']).resolve()==Path(root).resolve():self._persist(root,job)

    def _snapshot(self,job):
        return {k:job[k] for k in ('id','conversation_id','state','error','prompt')} | {
            'engine':job['engine'],
            'policy_revision':job['control'].access_policy.revision if job['control'].access_policy else None,
            'context_budget':job['control'].context_budget,'configuration':job['control'].configuration,
            'phase':job['control'].phase,'output_text':job['control'].output_text,
            'tool_activity':job['control'].tool_activity,
            'files':job['control'].file_activity.snapshot() if job['control'].file_activity is not None else [],
            'persistence_pending':job.get('persistence_pending',False),'persistence_error':job.get('persistence_error'),
            'elapsed_seconds':round(job.get('ended',time.monotonic())-job['started'],1)}

    def status(self,jid,root=None):
        with self.lock:
            if jid not in self.jobs:
                if root is not None:
                    from job_store import read
                    return read(root,jid)
                raise ValueError('Chat request not found; the server may have restarted')
            job=self.jobs[jid]
            if job.get('persistence_pending'):self._persist(job['root'],job)
            return self._snapshot(job)

    def cancel(self, jid):
        with self.lock:
            if jid not in self.jobs:
                raise ValueError('Chat request not found')
            job = self.jobs[jid]
            if job['state'] == 'running':
                job['control'].cancel()
        return self.status(jid)


JOBS = Jobs()
