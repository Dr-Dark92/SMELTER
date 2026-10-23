import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from opencode_runtime import status, ask, RULES, session_rules, _progress, _session_contract, Client
from chat_jobs import Control, Jobs
from chats import create_chat, read_chat
from database import select_database


SPEC = {'paths':{'/session':{'post':{'requestBody':{'content':{'application/json':{'schema':{
    'properties':{'permission':{'type':'array','items':{'type':'object','properties':{
        'permission':{'type':'string'},'pattern':{'type':'string'},'action':{'enum':['allow','deny','ask']}}}}}}}}}}}}}


class Fixture:
    def __init__(self, directory):
        self.directory = str(directory)
        self.calls = []
        self.policy = session_rules(directory)
        self.model_endpoint = 'http://127.0.0.1:11434/v1'
        self.health = {'healthy':True, 'version':'1.19.3'}
        self.spec = SPEC
        self.frames = [[{'info':{'role':'assistant','finish':'stop','time':{'completed':1}},
                        'parts':[{'type':'text','text':'Observed tools/dashboard/dashboard.py.'}]}]]
        self.last = self.frames[-1]

    def request(self, path, method='GET', body=None, timeout=3):
        self.calls.append((path, method, copy.deepcopy(body)))
        if path == '/global/health':return self.health
        if path == '/path':return {'directory':self.directory,'worktree':'/'}
        if path == '/doc':return self.spec
        if path == '/config':return {'provider':{'local':{'options':{'baseURL':self.model_endpoint,'apiKey':'NEVER_EXPOSE'},'models':{'qwen3.5:9b':{}}}}}
        if path == '/provider':return {'connected':['local'],'all':[{'id':'local','models':{'qwen3.5:9b':{}}}]}
        if path == '/session' and method == 'POST':return {'id':'ses_fixture'}
        if path == '/session/ses_fixture':return {'id':'ses_fixture','directory':self.directory,'permission':self.policy}
        if path.endswith('/prompt_async') or path.endswith('/abort'):return None
        if path.endswith('/message?limit=50'):
            return self.frames.pop(0) if self.frames else self.last
        raise AssertionError('Unexpected API call '+path)


class OpenCodeRuntimeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        self.root = base / 'SMELTER'
        self.root.mkdir()
        self.target = base / 'SMELTERV2'
        self.target.mkdir()
        select_database(self.root, str(base / 'data'))
        self.cid = create_chat(self.root, 'OpenCode pilot')['id']
        self.client = Fixture(self.target)

    def run_task(self, **kwargs):
        return ask(self.root, self.cid, 'List source files without modifying anything.',
                   model_key='local/qwen3.5:9b', approval=True, client=self.client, **kwargs)

    def test_connection_check_is_read_only_and_redacts_provider_credentials(self):
        report = status(self.root, self.client)
        self.assertTrue(report['read_only_ready'])
        self.assertEqual(report['models'][0]['key'], 'local/qwen3.5:9b')
        self.assertNotIn('NEVER_EXPOSE', json.dumps(report))
        self.assertTrue(all(method=='GET' for _,method,_ in self.client.calls))

    def test_wrong_directory_and_version_block_without_session_creation(self):
        self.client.directory = str(self.root)
        self.assertFalse(status(self.root, self.client)['read_only_ready'])
        self.client.directory = str(self.target)
        self.client.health['version'] = 'other'
        self.assertFalse(status(self.root, self.client)['read_only_ready'])
        self.assertFalse(any(path=='/session' for path,_,_ in self.client.calls))

    def test_missing_session_permission_contract_blocks_tasks(self):
        self.client.spec = {'paths':{}}
        with self.assertRaisesRegex(ValueError, 'session permission'):
            self.run_task()
        self.assertFalse(any(method=='POST' for _,method,_ in self.client.calls))

    def test_cloud_model_endpoint_is_not_accepted(self):
        self.client.model_endpoint = 'https://example.com/v1'
        with self.assertRaisesRegex(ValueError, 'local Ollama'):
            self.run_task()
        self.assertFalse(any(method=='POST' for _,method,_ in self.client.calls))

    def test_real_chat_persistence_and_exact_read_only_permissions(self):
        control = Control()
        result = self.run_task(control=control)
        self.assertEqual(result['session_id'], 'ses_fixture')
        creates = [body for path,method,body in self.client.calls if path=='/session' and method=='POST']
        self.assertEqual(creates[0]['permission'], session_rules(self.target))
        self.assertEqual(RULES[0], {'permission':'*','pattern':'*','action':'deny'})
        message = read_chat(self.root, self.cid)['messages'][-1]
        self.assertEqual(message['execution']['engine'], 'opencode')
        self.assertIn('Observed tools', message['content'])
        self.assertTrue(Path(message['execution']['audit_path']).is_file())
        self.assertTrue(control.completed)
        self.assertEqual([b for p,m,b in self.client.calls if p.endswith('/prompt_async')][0]['model'], {'providerID':'local','modelID':'qwen3.5:9b'})

    def test_unconfirmed_permissions_block_prompt_and_abort_session(self):
        self.client.policy = []
        result = self.run_task()
        self.assertIn('did not confirm', result['reply'])
        self.assertFalse(any(path.endswith('/prompt_async') for path,_,_ in self.client.calls))
        self.assertTrue(any(path.endswith('/abort') for path,_,_ in self.client.calls))

    def test_missing_approval_and_attachment_cannot_start_session(self):
        for kwargs in ({'approval':False}, {'approval':True,'image':{}}):
            with self.assertRaises(ValueError):
                ask(self.root,self.cid,'fixture',model_key='local/qwen3.5:9b',client=self.client,**kwargs)
        self.assertEqual(self.client.calls, [])

    def test_tool_step_is_not_final_completion(self):
        tool = {'info':{'role':'assistant','finish':'tool-calls','time':{'completed':1}},
                'parts':[{'type':'tool','tool':'read','state':{'status':'completed','input':{'filePath':'tools/dashboard/dashboard.py'}}}]}
        self.assertFalse(_progress([tool])[2])
        self.client.frames.insert(0, [tool])
        with patch('opencode_runtime.time.sleep'):
            result = self.run_task()
        self.assertIn('Observed', result['reply'])
        self.assertEqual(len([p for p,_,_ in self.client.calls if '/message?' in p]),2)
        events = read_chat(self.root,self.cid)['messages'][-1]['execution']['events']
        self.assertEqual(len(events),1)
        self.assertEqual(events[0]['tool'], 'opencode/read')

    def test_stop_aborts_only_the_owned_session(self):
        control = Control()
        original = self.client.request
        def request(path, *args, **kwargs):
            result = original(path, *args, **kwargs)
            if path.endswith('/prompt_async'):control.cancel()
            return result
        self.client.request = request
        result = self.run_task(control=control)
        self.assertIn('stopped', result['reply'])
        self.assertEqual([p for p,m,b in self.client.calls if p.endswith('/abort')], ['/session/ses_fixture/abort'])
        self.assertTrue(read_chat(self.root,self.cid)['messages'][-1]['execution']['cancelled'])

    def test_schema_reference_resolution(self):
        spec = copy.deepcopy(SPEC)
        body = spec['paths']['/session']['post']['requestBody']
        spec['components'] = {'requestBodies':{'Create':body}}
        spec['paths']['/session']['post']['requestBody'] = {'$ref':'#/components/requestBodies/Create'}
        self.assertTrue(_session_contract(spec))

    def test_gui_job_requires_explicit_opencode_approval(self):
        with self.assertRaisesRegex(ValueError, 'Approve'):
            Jobs().start(self.root, {'id':self.cid,'content':'fixture','engine':'opencode_readonly'})

    def test_client_uses_loopback_no_redirects_and_scoped_directory(self):
        import io
        client = Client()
        client.directory = str(self.target)
        with patch.object(client.opener, 'open', return_value=io.BytesIO(b'{"healthy":true}')) as opener:
            client.request('/global/health')
        request = opener.call_args.args[0]
        self.assertEqual(request.full_url, 'http://127.0.0.1:4096/global/health')
        self.assertIn('X-opencode-directory', dict(request.header_items()))
        with self.assertRaises(ValueError):client.request('//example.com')


def opencode_allows(rules, permission, pattern):
    """Mirror OpenCode 1.19's rule evaluation: backslashes become '/', '*' matches
    anything, matching ignores case, and the last matching rule wins."""
    import re
    def match(value, glob):
        value, glob = value.replace('\\', '/'), glob.replace('\\', '/')
        regex = re.sub(r'[.+^${}()|[\]\\]', lambda m: '\\' + m.group(0), glob).replace('*', '.*').replace('?', '.')
        return re.fullmatch(regex, value, re.S | re.I) is not None
    hit = [r for r in rules if match(permission, r['permission']) and match(pattern, r['pattern'])]
    return bool(hit) and hit[-1]['action'] == 'allow'


class WorktreeRelativeReadTests(unittest.TestCase):
    # The container snapshot at /workspace is not a Git repository, so OpenCode
    # reports worktree '/' and checks reads as path.relative('/', file).
    def test_snapshot_reads_allowed_with_root_worktree(self):
        rules = session_rules('/workspace')
        for path in ('workspace/skills/taste/SKILL.md', 'workspace/skills', 'workspace/tools/dashboard/dashboard.py',
                     'workspace/README.md', 'skills/taste/SKILL.md', 'skills'):
            self.assertTrue(opencode_allows(rules, 'read', path), path)

    def test_outside_scope_and_secrets_stay_denied(self):
        rules = session_rules('/workspace')
        for path in ('etc/passwd', 'workspace', 'workspace/projects/x.txt', 'workspace/skills/.env',
                     'workspace/tools/.smelter/state.json', 'workspace/tools/.git/config', 'home/app/.ssh/id_rsa'):
            self.assertFalse(opencode_allows(rules, 'read', path), path)
        self.assertFalse(opencode_allows(rules, 'bash', 'ls'))

    def test_location_exclusions_apply_to_root_worktree_paths(self):
        class Policy:
            value = {'locations': [{'path': str(Path('/host/SMELTER/tools/vendor')), 'enabled': True,
                                    'read': False, 'exclusions': []}]}
        rules = session_rules('/workspace', Policy(), host_directory=str(Path('/host/SMELTER')))
        self.assertFalse(opencode_allows(rules, 'read', 'workspace/tools/vendor/lib.js'))
        self.assertFalse(opencode_allows(rules, 'read', 'tools/vendor/lib.js'))
        self.assertTrue(opencode_allows(rules, 'read', 'workspace/tools/dashboard/dashboard.py'))
