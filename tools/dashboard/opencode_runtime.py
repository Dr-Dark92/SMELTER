"""First OpenCode GUI bridge: explicit, bounded, read-only V2 sessions.

Connects to an existing loopback server; never launches a CLI or patches its
configuration. Session rules are application permissions, not an OS sandbox.
"""
import base64
import hashlib
import json
import os
import re
import sqlite3
import time
from contextlib import closing, nullcontext
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, build_opener, ProxyHandler, HTTPRedirectHandler
from uuid import uuid4
from datetime import datetime, timezone

BASE = 'http://127.0.0.1:4096'
VERSION = '1.19.3'
LIMIT = 4 * 1024 * 1024
RULES = [
    {'permission':'*', 'pattern':'*', 'action':'deny'},
    {'permission':'read', 'pattern':'*.env*', 'action':'deny'},
    {'permission':'read', 'pattern':'**/.env*', 'action':'deny'},
    {'permission':'read', 'pattern':'**/.smelter/**', 'action':'deny'},
    {'permission':'read', 'pattern':'**/.git/**', 'action':'deny'},
    {'permission':'external_directory', 'pattern':'*', 'action':'deny'},
]


def session_rules(directory):
    # Limit source content reads independently of the server's VCS worktree.
    # A non-Git project can report worktree '/', which is not a useful scope.
    bases = {str(Path(directory)), Path(directory).as_posix()}
    patterns = {'README.md', 'tools/**', 'skills/**'}
    for base in bases:
        for suffix in ('README.md','tools/**','skills/**'):
            patterns.add(base.rstrip('/\\') + '/' + suffix)
            if '\\' in base:
                patterns.add(base.rstrip('/\\') + '\\' + suffix.replace('/','\\'))
    return [RULES[0]] + [{'permission':'read','pattern':p,'action':'allow'} for p in sorted(patterns)] + RULES[1:]


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self):
        self.directory = None
        self.opener = build_opener(ProxyHandler({}), _NoRedirect())

    def request(self, path, method='GET', body=None, timeout=3):
        if not path.startswith('/') or path.startswith('//'):
            raise ValueError('Invalid OpenCode API path')
        headers = {'Accept':'application/json'}
        if self.directory:
            headers['x-opencode-directory'] = quote(self.directory, safe='')
        password = os.environ.get('SMELTER_OPENCODE_PASSWORD', os.environ.get('OPENCODE_SERVER_PASSWORD'))
        if password:
            user = os.environ.get('OPENCODE_SERVER_USERNAME', 'opencode')
            headers['Authorization'] = 'Basic ' + base64.b64encode((user + ':' + password).encode()).decode()
        data = None if body is None else json.dumps(body).encode()
        if data is not None:
            headers['Content-Type'] = 'application/json'
        try:
            with self.opener.open(Request(BASE + path, data=data, headers=headers, method=method), timeout=timeout) as response:
                raw = response.read(LIMIT + 1)
        except HTTPError as exc:
            raise ValueError('OpenCode HTTP ' + str(exc.code) + ' at ' + path.split('?')[0]) from exc
        if len(raw) > LIMIT:
            raise ValueError('OpenCode API response exceeds 4 MiB')
        return json.loads(raw) if raw.strip() else None


def _resolve(spec, value):
    for _ in range(12):
        if not isinstance(value, dict) or '$ref' not in value:
            return value
        ref = value['$ref']
        if not isinstance(ref, str) or not ref.startswith('#/'):
            return {}
        value = spec
        for key in ref[2:].split('/'):
            value = value.get(key.replace('~1','/').replace('~0','~'), {}) if isinstance(value, dict) else {}
    return {}


def _session_contract(spec):
    if not isinstance(spec, dict):
        return False
    route = spec.get('paths', {}).get('/session', {}).get('post', {})
    body = _resolve(spec, route.get('requestBody', {}))
    schema = _resolve(spec, body.get('content', {}).get('application/json', {}).get('schema', {}))
    permission = _resolve(spec, schema.get('properties', {}).get('permission', {}))
    rule = _resolve(spec, permission.get('items', {}))
    keys = rule.get('properties', {})
    action = _resolve(spec, keys.get('action', {}))
    return permission.get('type') == 'array' and {'permission','pattern','action'}.issubset(keys) and {'allow','deny'}.issubset(action.get('enum', []))


def status(root, client=None):
    from frontend_workspace import target_path
    client = client or Client()
    expected = target_path(root)
    health = client.request('/global/health')
    paths = client.request('/path')
    if not isinstance(health, dict) or health.get('healthy') is not True or not isinstance(paths, dict):
        raise ValueError('Invalid OpenCode health/path response')
    directory = paths.get('directory')
    matches = isinstance(directory, str) and Path(directory).resolve() == expected.resolve()
    result = {'endpoint':BASE, 'version':health.get('version'), 'expected_version':VERSION,
        'directory':directory, 'expected_directory':str(expected), 'directory_matches':matches,
        'worktree':paths.get('worktree'), 'models':[], 'read_only_ready':False,
        'status':'connected', 'note':'Connection only; no model task was submitted. Working directory is not an OS sandbox.'}
    if not matches:
        result['reason'] = 'Restart OpenCode from the expected V2 directory'
        return result
    client.directory = directory
    if health.get('version') != VERSION:
        result['reason'] = 'OpenCode version has not been validated for this adapter'
        return result
    spec = client.request('/doc')
    result['session_permissions_supported'] = _session_contract(spec)
    if not result['session_permissions_supported']:
        result['reason'] = 'Live API does not expose the expected session permission rules; task submission blocked'
        return result
    config = client.request('/config')
    providers = client.request('/provider')
    if not isinstance(config, dict) or not isinstance(providers, dict):
        raise ValueError('Invalid OpenCode provider response')
    connected = providers.get('connected', [])
    all_providers = providers.get('all', [])
    configured_providers = config.get('provider', {})
    if not isinstance(connected, list) or not isinstance(all_providers, list) or not isinstance(configured_providers, dict):
        raise ValueError('Invalid OpenCode provider list')
    for provider in all_providers:
        if not isinstance(provider, dict):
            continue
        pid = provider.get('id')
        configured = configured_providers.get(pid, {}) if isinstance(pid, str) else {}
        if not isinstance(configured, dict) or not isinstance(configured.get('options', {}), dict) or not isinstance(configured.get('models', {}), dict) or not isinstance(provider.get('models', {}), dict):
            raise ValueError('Invalid OpenCode provider configuration')
        endpoint = configured.get('options', {}).get('baseURL')
        if pid not in connected or not isinstance(endpoint, str) or endpoint.rstrip('/') != 'http://127.0.0.1:11434/v1':
            continue
        for mid in configured.get('models', {}):
            if isinstance(mid, str) and mid in provider.get('models', {}) and len(mid) <= 200:
                result['models'].append({'key':pid + '/' + mid, 'providerID':pid, 'modelID':mid})
    result['models'] = result['models'][:50]
    result['read_only_ready'] = bool(result['models'])
    result['reason'] = 'Ready for an explicitly approved read-only session' if result['models'] else 'No connected model with an explicit local Ollama baseURL was found'
    return result


def _sid(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,160}', value):
        raise ValueError('Invalid OpenCode session ID')
    return value


def _progress(messages):
    if not isinstance(messages, list):
        raise ValueError('Invalid OpenCode messages response')
    text, events, finished, failure = [], [], False, None
    for message in messages[-50:]:
        if not isinstance(message, dict) or not isinstance(message.get('info'), dict) or not isinstance(message.get('parts', []), list):
            raise ValueError('Invalid OpenCode message')
        info = message.get('info', {})
        if info.get('role') != 'assistant':
            continue
        if info.get('error'):
            failure = 'OpenCode reported a model/session error; inspect its server log'
        # Intermediate assistant messages can finish a tool-call step. Only
        # the latest assistant's final stop establishes task completion.
        finished = bool(info.get('time', {}).get('completed')) and info.get('finish') == 'stop'
        for part in message.get('parts', []):
            if not isinstance(part, dict):
                raise ValueError('Invalid OpenCode message part')
            if part.get('type') == 'text' and isinstance(part.get('text'), str):
                text.append(part['text'])
            elif part.get('type') == 'tool':
                state = part.get('state', {})
                name = str(part.get('tool', 'unknown'))[:100]
                state_name = str(state.get('status', 'unknown'))[:50]
                arguments = state.get('input', {})
                path = arguments.get('filePath', arguments.get('path')) if isinstance(arguments, dict) else None
                fallback = hashlib.sha256(json.dumps([name,arguments],sort_keys=True).encode()).hexdigest()
                event_id = str(part.get('id', part.get('callID', fallback)))[:200]
                events.append({'external_id':event_id, 'tool':'opencode/' + name, 'transport':'opencode',
                    'executed':state_name == 'completed', 'reused':False,
                    'result':{'status':state_name, 'path':str(path)[:1024] if path else None,
                              'error':str(state.get('error',''))[:500],
                              'verification_scope':'Tool activity reported by OpenCode; no independent filesystem verification'}})
    return '\n\n'.join(text)[-64000:], events[-100:], finished, failure


def ask(root, conversation_id, prompt, *, model_key=None, approval=False, control=None,
        image=None, skills=None, auto_skills=False, tool_permissions=None, client=None):
    from chats import read_chat, _db, EXECUTION_SCHEMA
    from chat_jobs import ChatCancelled
    if approval is not True:
        raise ValueError('Approve one read-only OpenCode session before sending')
    if image is not None or skills or auto_skills or tool_permissions:
        raise ValueError('This first OpenCode adapter accepts text-only read-only sessions; other grants are not forwarded')
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 1800:
        raise ValueError('Prompt must be 1–1800 characters')
    chat = read_chat(root, conversation_id)
    client = client or Client()
    check = status(root, client)
    if not check['read_only_ready']:
        raise ValueError(check['reason'])
    selected = next((m for m in check['models'] if m['key'] == model_key), None)
    if selected is None:
        raise ValueError('Select a verified local OpenCode model')
    from python_tools import _plain_path
    folder = _plain_path(Path(root) / '.smelter/tool-runs')
    folder.mkdir(parents=True, exist_ok=True)
    audit = _plain_path(folder / (str(uuid4()) + '.jsonl'))
    def record(phase, **data):
        with audit.open('a', encoding='utf-8') as out:
            out.write(json.dumps({'timestamp_utc':datetime.now(timezone.utc).isoformat(),
                'conversation_id':conversation_id, 'engine':'opencode', 'phase':phase, **data}) + '\n')
    def update(phase):
        if control:
            control.update(phase)
    session_id, answer, events, cancelled, abort_error, failed = None, '', [], False, None, False
    observed = {}
    policy = session_rules(check['directory'])
    record('requested', directory=check['directory'], model=model_key, permission=policy)
    try:
        update('OpenCode: creating read-only session')
        session = client.request('/session', 'POST', {'title':'SMELTER read-only: ' + chat['title'][:80], 'permission':policy})
        if not isinstance(session, dict):
            raise ValueError('Invalid OpenCode session response')
        session_id = _sid(session.get('id'))
        record('session_created', session_id=session_id)
        actual = client.request('/session/' + session_id)
        if not isinstance(actual, dict) or actual.get('permission') != policy or Path(actual.get('directory','')).resolve() != Path(check['directory']).resolve():
            raise ValueError('OpenCode did not confirm the exact read-only session rules and directory; no prompt sent')
        update('OpenCode: submitting to local Ollama model')
        body = {'agent':'build', 'model':{'providerID':selected['providerID'], 'modelID':selected['modelID']},
            'system':'You are performing a read-only source inspection for SMELTER. You may use the read tool for README.md and files under tools/ and skills/ in the current directory. Start with README.md and tools/dashboard/dashboard.py. Do not modify files, execute commands, delegate, or access external directories. Other tools are denied in this pilot. Report observations with file paths. Mark guesses as unverified.',
            'parts':[{'type':'text', 'text':prompt.strip()}]}
        record('prompt_requested', session_id=session_id)
        client.request('/session/' + session_id + '/prompt_async', 'POST', body, timeout=10)
        deadline = time.monotonic() + 300
        while time.monotonic() < deadline:
            update('OpenCode: inspecting source · read only')
            messages = client.request('/session/' + session_id + '/message?limit=50')
            answer, updates, finished, failure = _progress(messages)
            for event in updates:
                observed[event['external_id']] = event
            events = list(observed.values())[-100:]
            if control:
                with control.lock:
                    control.output_text, control.tool_activity = answer, events
            if failure:
                raise ValueError(failure)
            if finished:
                if not answer.strip():
                    raise ValueError('OpenCode completed without a text answer')
                break
            if control:
                control.cancelled.wait(0.5)
                control.check()
            else:
                time.sleep(0.5)
        else:
            raise ValueError('OpenCode task exceeded five minutes')
    except (ValueError, OSError, ChatCancelled) as exc:
        cancelled = isinstance(exc, ChatCancelled)
        failed = not cancelled
        if session_id:
            try:
                client.request('/session/' + session_id + '/abort', 'POST', {}, timeout=3)
            except (ValueError, OSError):
                abort_error = 'Abort was not confirmed; check the OpenCode server before submitting another task'
        answer = ('OpenCode request stopped.' if cancelled else 'OpenCode task failed: ' + str(exc)) + ('\n' + answer if answer else '')
    record('result', session_id=session_id, cancelled=cancelled, failed=failed, abort_error=abort_error, events=events)
    if abort_error:
        answer += '\n' + abort_error
    execution = {'source':'controller', 'engine':'opencode', 'session_id':session_id,
        'permissions':{'opencode_read_only':True}, 'events':events, 'files':[],
        'audit_path':str(audit), 'cancelled':cancelled, 'model_text':answer,
        'verification_scope':'Model narrative and tool activity are reported by OpenCode; not independently fact-checked'}
    lock = control.lock if control else nullcontext()
    with lock:
        with closing(sqlite3.connect(_db(root), timeout=5)) as conn, conn:
            conn.execute('PRAGMA foreign_keys=ON')
            conn.execute('INSERT INTO messages(conversation_id,role,content) VALUES(?,?,?)', (conversation_id,'user',prompt.strip()))
            mid = conn.execute('INSERT INTO messages(conversation_id,role,content) VALUES(?,?,?)', (conversation_id,'assistant',answer)).lastrowid
            conn.execute(EXECUTION_SCHEMA)
            conn.execute('INSERT INTO message_execution(message_id,payload) VALUES(?,?)', (mid,json.dumps(execution)))
        if control:
            control.completed = True
    return {'reply':answer, 'stored':True, 'engine':'opencode', 'session_id':session_id,
            'status':'error' if failed else 'cancelled' if cancelled else 'completed',
            'error':answer[:1000] if failed else None}
