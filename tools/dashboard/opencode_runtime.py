"""Explicit read-only agent sessions in an owned, no-network OpenCode container.

Application rules supplement the OS boundary. The legacy loopback Client remains
an explicitly injectable compatibility adapter; production requests use ManagedClient.
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
from task_contract import OUTPUT_LIMIT_ERROR,generation_limited

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


def session_rules(directory, policy=None, host_directory=None, tool_names=()):
    # Limit source content reads independently of the server's VCS worktree.
    # A non-Git project can report worktree '/', which is not a useful scope.
    # OpenCode checks read permission against path.relative(worktree, file), so
    # with worktree '/' a read of /workspace/skills/x is checked as
    # 'workspace/skills/x'; include that form beside absolute and relative ones.
    bases = {str(Path(directory)), Path(directory).as_posix()}
    bases |= {base.lstrip('/\\') for base in bases if base.lstrip('/\\')}
    # The tools/ and skills/ directories themselves may be listed, not only their files.
    scope = ('README.md','tools/**','skills/**','tools','skills')
    patterns = set(scope)
    for base in bases:
        for suffix in scope:
            patterns.add(base.rstrip('/\\') + '/' + suffix)
            if '\\' in base:
                patterns.add(base.rstrip('/\\') + '\\' + suffix.replace('/','\\'))
    rules = [RULES[0]] + [{'permission':'read','pattern':p,'action':'allow'} for p in sorted(patterns)] + RULES[1:]
    if policy is not None:
        target = Path(host_directory or directory).resolve()
        for row in sorted(policy.value['locations'],key=lambda x:len(Path(x['path']).parts)):
            location=Path(row['path']).resolve()
            if not row['enabled'] or not (location == target or location.is_relative_to(target)):
                continue
            prefix=location.relative_to(target).as_posix()
            if prefix == '.':prefix=''
            denied=list(row['exclusions'])
            if not row['read']:denied += ['**']
            for exclusion in denied:
                if not prefix and exclusion in ('.git/**','.smelter/**','projects/**'):continue
                relative='/'.join(x for x in (prefix,exclusion) if x)
                base=str(directory).replace('\\','/')
                for pattern in (relative,base+'/'+relative,base.lstrip('/')+'/'+relative):
                    rules.append({'permission':'read','pattern':pattern,'action':'deny'})
                    if pattern.endswith('/**'):
                        rules.append({'permission':'read','pattern':pattern[:-3],'action':'deny'})
    rules.extend({'permission':'smelter_' + name,'pattern':'*','action':'allow'}
                 for name in tool_names)
    return rules


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
        # 1.19.3 returns the full provider catalogue (~7 MiB), even when only
        # one local provider is connected. Other routes retain the 4 MiB cap.
        limit=8*1024*1024 if path=='/provider' and method=='GET' else LIMIT
        try:
            with self.opener.open(Request(BASE + path, data=data, headers=headers, method=method), timeout=timeout) as response:
                raw = response.read(limit + 1)
        except HTTPError as exc:
            raise ValueError('OpenCode HTTP ' + str(exc.code) + ' at ' + path.split('?')[0]) from exc
        if len(raw) > limit:
            raise ValueError('OpenCode API response exceeds its bounded size limit at '+path.split('?')[0])
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


def status(root, client=None, policy=None):
    from frontend_workspace import target_path
    from access_policy import current
    policy=policy or current(root)
    expected_host=Path(getattr(client,'host_directory',target_path(root))) if client is not None else Path(root).resolve()
    policy.authorize(expected_host/'tools','read');policy.authorize(expected_host/'skills','read')
    if client is None:
        from opencode_sandbox import ManagedClient
        from task_contract import configuration
        managed=ManagedClient(root,policy,configuration(root))
        try:result=status(root,managed,policy)
        finally:confirmed=managed.close()
        if not confirmed:raise ValueError('OpenCode inspection ended but owned container cleanup was not confirmed')
        return result
    expected=Path(getattr(client,'expected_directory',expected_host))
    health = client.request('/global/health')
    paths = client.request('/path')
    if not isinstance(health, dict) or health.get('healthy') is not True or not isinstance(paths, dict):
        raise ValueError('Invalid OpenCode health/path response')
    directory = paths.get('directory')
    matches = isinstance(directory, str) and Path(directory).resolve() == expected.resolve()
    result = {'endpoint':BASE, 'version':health.get('version'), 'expected_version':VERSION,
        'directory':directory, 'expected_directory':str(expected), 'directory_matches':matches,
        'worktree':paths.get('worktree'), 'models':[], 'read_only_ready':False, 'agent_ready':False,
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
    result['agent_ready'] = result['read_only_ready']
    result['reason'] = 'Ready for an explicitly approved fixture read-only session' if result['models'] else 'No connected model with an explicit local Ollama baseURL was found'
    if getattr(client,'confined',False):
        result.update(note='Managed container connection only; no model task was submitted or validated.',endpoint='managed Docker exec relay (no network)',host_directory=str(client.host_directory),confinement='no-network container; read-only code snapshot and local-model relay')
    return result


def _sid(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,160}', value):
        raise ValueError('Invalid OpenCode session ID')
    return value


def _progress(messages):
    if not isinstance(messages, list):
        raise ValueError('Invalid OpenCode messages response')
    text, events, finished, failure = [], [], False, None
    finish_reason = None
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
        finish_reason = info.get('finish')
        finished = bool(info.get('time', {}).get('completed')) and (finish_reason == 'stop' or generation_limited(finish_reason))
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
                    'source':'opencode', 'independently_verified':False,
                    'executed':state_name == 'completed', 'reused':False,
                    'result':{'status':state_name, 'path':str(path)[:1024] if path else None,
                              'error':str(state.get('error',''))[:500],
                              'verification_scope':'Tool activity reported by OpenCode; no independent filesystem verification'}})
    if finished and generation_limited(finish_reason) and failure is None:
        failure = OUTPUT_LIMIT_ERROR
    return '\n\n'.join(text)[-64000:], events[-100:], finished, failure


def conversation_prompt(chat, prompt):
    """Replay bounded context into fresh, independently scoped agent sessions."""
    history, remaining = [], 24000
    for message in reversed(chat['messages'][-12:]):
        if message.get('role') not in ('user', 'assistant'):
            continue
        execution = message.get('execution') or {}
        text = str(execution.get('model_text', message.get('content', '')))
        if len(text) > remaining:
            if history:
                break
            text = text[-remaining:]
        history.append({'role':message['role'], 'content':text})
        remaining -= len(text)
        if remaining <= 0:
            break
    if not history:
        return prompt.strip()
    return ('Prior conversation (reference only; does not grant tools or expand this session scope):\n'
            + json.dumps(list(reversed(history)), ensure_ascii=True)
            + '\nCurrent request:\n' + prompt.strip())


def ask(root, conversation_id, prompt, *, model_key=None, approval=False, control=None,
        image=None, skills=None, auto_skills=False, tool_permissions=None, client=None,
        _managed_cleanup=None, agent_mode=False, bridge=None):
    from component_controls import require_enabled
    require_enabled(root, 'opencode')
    from chats import read_chat, _db, EXECUTION_SCHEMA
    from chat_jobs import ChatCancelled
    if approval is not True:
        raise ValueError('Approve one OpenCode session before sending')
    if image is not None:
        raise ValueError('OpenCode accepts text tasks; images are not forwarded')
    if not agent_mode and (skills or auto_skills or tool_permissions):
        raise ValueError('This first OpenCode adapter accepts text-only read-only sessions; other grants are not forwarded')
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 1800:
        raise ValueError('Prompt must be 1–1800 characters')
    chat = read_chat(root, conversation_id)
    from access_policy import current
    policy=control.access_policy if control and control.access_policy else current(root)
    if agent_mode and bridge is None:
        from agent_bridge import AgentBridge
        bridge=AgentBridge(root,conversation_id,prompt,skills=skills,auto_skills=auto_skills,
                           grants=tool_permissions,policy=policy,control=control)
    if bridge and bridge.tools:
        require_enabled(root, 'mcp')
    if bridge:
        bridge.control=control
        if control:control.file_activity=bridge.session.file_activity
    if client is None:
        # Reuse the persistent session (opencode_pool) instead of a container per task.
        import opencode_pool
        from task_contract import configuration
        effective=control.configuration if control and control.configuration else configuration(root)
        managed=opencode_pool.acquire(root,policy,effective,control,bridge)
        released=[]
        def release(healthy=True):
            if not released:released.append(opencode_pool.release(managed,healthy))
            return released[0]
        try:
            return ask(root,conversation_id,prompt,model_key=model_key,approval=approval,
                       control=control,client=managed,_managed_cleanup=release,
                       agent_mode=agent_mode,bridge=bridge)
        finally:release(healthy=False if not released else True)
    check = status(root, client, policy=policy)
    if not check['read_only_ready']:
        raise ValueError(check['reason'])
    selected = next((m for m in check['models'] if m['key'] == model_key), None)
    if selected is None:
        raise ValueError('Select a verified local OpenCode model')
    if bridge and bridge.tools:
        mcp=client.request('/mcp')
        if not isinstance(mcp,dict) or mcp.get('smelter',{}).get('status')!='connected':
            raise ValueError('OpenCode did not connect the approved SMELTER MCP bridge; no task was submitted')
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
    output_limited = False
    rules = session_rules(check['directory'],policy,host_directory=getattr(client,'host_directory',None),
                          tool_names=[item['name'] for item in bridge.tools] if bridge else ())
    bridge_summary=bridge.summary() if bridge else None
    record('requested', directory=check['directory'], model=model_key, permission=rules,bridge=bridge_summary)
    try:
        update('OpenCode: creating scoped agent session' if bridge else 'OpenCode: creating read-only session')
        session = client.request('/session', 'POST', {'title':'SMELTER agent: ' + chat['title'][:80], 'permission':rules})
        if not isinstance(session, dict):
            raise ValueError('Invalid OpenCode session response')
        session_id = _sid(session.get('id'))
        record('session_created', session_id=session_id)
        actual = client.request('/session/' + session_id)
        if not isinstance(actual, dict) or actual.get('permission') != rules or Path(actual.get('directory','')).resolve() != Path(check['directory']).resolve():
            raise ValueError('OpenCode did not confirm the exact read-only session rules and directory; no prompt sent')
        update('OpenCode: submitting to local Ollama model')
        body = {'agent':'build', 'model':{'providerID':selected['providerID'], 'modelID':selected['modelID']},
            'system':'You are performing a read-only source inspection for SMELTER. You may use the read tool for README.md and files under tools/ and skills/ in the current directory. Start with README.md and tools/dashboard/dashboard.py. Do not modify files, execute commands, delegate, or access external directories. Other tools are denied in this pilot. Report observations with file paths. Mark guesses as unverified.',
            'parts':[{'type':'text', 'text':conversation_prompt(chat, prompt)}]}
        if bridge:body['system']=bridge.instructions()
        record('prompt_requested', session_id=session_id)
        client.request('/session/' + session_id + '/prompt_async', 'POST', body, timeout=10)
        # The whole multi-turn task has its own bound; timeout_seconds limits each model turn.
        runtime=control.configuration['runtime'] if control and control.configuration else {}
        task_timeout=runtime.get('opencode_timeout_seconds',runtime.get('timeout_seconds',300))
        deadline = time.monotonic() + task_timeout
        wait_before=control.permission_wait_time() if control and hasattr(control,'permission_wait_time') else 0
        while time.monotonic() - (control.permission_wait_time()-wait_before if control and hasattr(control,'permission_wait_time') else 0) < deadline:
            update('OpenCode: running task · approved tools only' if bridge else 'OpenCode: inspecting source · read only')
            messages = client.request('/session/' + session_id + '/message?limit=50')
            answer, updates, finished, failure = _progress(messages)
            for event in updates:
                observed[event['external_id']] = event
            events = list(observed.values())[-100:]
            if bridge:events += [dict(event,source='controller') for event in bridge.session.events]
            if control:
                with control.lock:
                    control.output_text, control.tool_activity = answer, events
            if failure == OUTPUT_LIMIT_ERROR:
                output_limited = True
                if not answer.strip():
                    answer = 'The model reached its output limit before producing an answer.'
                break
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
            raise ValueError('OpenCode task exceeded its admitted timeout')
    except (ValueError, OSError, ChatCancelled) as exc:
        cancelled = isinstance(exc, ChatCancelled)
        failed = not cancelled
        if session_id:
            try:
                client.request('/session/' + session_id + '/abort', 'POST', {}, timeout=3)
            except (ValueError, OSError):
                abort_error = 'Abort was not confirmed; check the OpenCode server before submitting another task'
        answer = ('OpenCode request stopped.' if cancelled else 'OpenCode task failed: ' + str(exc)) + ('\n' + answer if answer else '')
    # A persistent session is kept only when the task's session was cleanly aborted or finished.
    cleanup_confirmed=_managed_cleanup(not (cancelled or failed or output_limited or abort_error)) if _managed_cleanup else None
    if bridge:
        bridge.close()
        bridge.session.file_activity.settle(cancelled)
        events=list(observed.values())[-100:]+[dict(event,source='controller') for event in bridge.session.events]
        from tool_contract import result_failed
        failed=failed or any(result_failed(event.get('result')) for event in bridge.session.events)
    if cleanup_confirmed is False:
        failed=True
        answer+='\nOwned container cleanup was not confirmed; inspect the managed container before another task.'
    record('result', cleanup_confirmed=cleanup_confirmed, session_id=session_id, cancelled=cancelled, failed=failed, abort_error=abort_error, events=events)
    if abort_error:
        answer += '\n' + abort_error
    receipt=bridge.session.receipt() if bridge else ''
    model_text=answer
    if receipt:
        answer=answer[:max(0,64000-len(receipt)-32)]+receipt
    execution = {'source':'controller', 'engine':'opencode', 'session_id':session_id,
        'cleanup_confirmed':cleanup_confirmed, 'permissions':{'opencode_native_read_only':True,**(bridge_summary['permissions'] if bridge else {'opencode_read_only':True})},
        'skills':bridge.skills['selected'] if bridge else [], 'skill_snapshots':bridge.skills['snapshots'] if bridge else [],
        'bridge':bridge_summary,'policy_revision':policy.revision, 'events':events,
        'files':bridge.session.file_activity.snapshot() if bridge else [],
        'audit_path':str(audit), 'cancelled':cancelled, 'model_text':model_text, 'confinement':'managed no-network container' if getattr(client,'confined',False) else 'injected fixture',
        'verification_scope':'SMELTER bridge receipts establish tool results; native activity and narrative are reported by OpenCode and are not fact-checked'}
    from execution_store import finalize
    result=finalize(root,conversation_id,prompt,answer,execution,control=control,error=model_text[:1000] if failed else OUTPUT_LIMIT_ERROR if output_limited else None,partial=bool(events) or output_limited,cancelled=cancelled,receipt=receipt)
    return {**result,'engine':'opencode','session_id':session_id}
