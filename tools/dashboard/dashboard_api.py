"""Resource-sized HTTP handlers with one auth, schema and error boundary.

Context resolves the dashboard's injected services dynamically, preserving fixture
patches without importing a second dashboard instance under __main__.
"""
import json
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

class Context:
    def __init__(self,namespace):self.namespace=namespace
    def __getattr__(self,name):return self.namespace[name]

class ApiRoutes:
    GET_ROUTES={'/': '_get_page', '/api/access-policy': '_get_api_access_policy', '/api/opencode/agent': '_get_api_opencode_agent', '/api/mcp/status': '_get_api_mcp_status', '/api/models/status': '_get_api_models_status', '/api/skills': '_get_api_skills', '/api/skills/status': '_get_api_skills_status', '/api/rea/status': '_get_api_rea_status', '/api/runtime': '_get_api_runtime', '/api/system/status': '_get_api_system_status', '/api/chats': '_get_api_chats', '/api/startup': '_get_api_startup', '/api/opencode/validate': '_get_api_opencode_validate', '/api/opencode/provider-preview': '_get_api_opencode_provider_preview', '/api/opencode/status': '_get_api_opencode_status', '/api/ollama/preferences': '_get_api_ollama_preferences', '/api/ollama/models': '_get_api_ollama_models', '/api/workflows/reports': '_get_api_workflows_reports', '/api/workflows': '_get_api_workflows', '/api/extensions': '_get_api_extensions'}
    GET_PREFIXES=[('/api/models/', '_get_api_models_item'), ('/api/chat-jobs/', '_get_api_chat_jobs_item'), ('/api/skills/review/', '_get_api_skills_review_item'), ('/api/chats/', '_get_api_chats_item')]
    POST_ROUTES={'/api/access-policy': '_post_api_access_policy', '/api/mcp': '_post_api_mcp', '/api/models': '_post_api_models', '/api/skills/collection-preview': '_post_api_skills_collection_preview', '/api/skills/discover-repository': '_post_api_skills_discover_repository', '/api/skills/discover': '_post_api_skills_discover', '/api/skills/manage': '_post_api_skills_manage', '/api/aero/classify': '_post_api_aero_classify', '/api/chats': '_post_api_chats', '/api/database/select': '_post_api_database_select', '/api/opencode/deploy': '_post_api_opencode_deploy', '/api/ollama/preferences': '_post_api_ollama_preferences', '/api/blender/inspect': '_post_api_blender_inspect', '/api/media/inspect': '_post_api_media_inspect', '/api/archive/inspect': '_post_api_archive_inspect', '/api/workflows/plan': '_post_api_workflows_plan', '/api/extensions': '_post_api_extensions'}
    ASSETS={
        '/assets/session-auth.js':'session_auth.js','/assets/file-activity.js':'file_activity.js',
        '/assets/chat-renderer.js':'chat_renderer.js','/assets/mcp-ui.js':'mcp_ui.js',
        '/assets/turntable.js':'turntable.js','/assets/model-animations.js':'model_animations.js',
        '/assets/model-preview.js':'model_preview.js','/assets/opencode-agent-ui.js':'opencode_agent_ui.js',
        '/assets/skills-ui.js':'skills_ui.js','/assets/attachments-ui.js':'attachments_ui.js','/assets/settings-ui.js':'settings_ui.js','/assets/access-ui.js':'access_ui.js',
        '/assets/operations-ui.js':'operations_ui.js','/assets/dashboard-shell.js':'dashboard_shell.js'}

    def do_GET(self):
        try:
            route=urlsplit(self.path).path
            if route in self.ASSETS:
                source=Path(self.app.__file__).with_name(self.ASSETS[route])
                return self.reply(200,source.read_text(encoding='utf-8'),'application/javascript')
            if route=='/assets/model-viewer.min.js':
                try:return self.reply(200,self.app.viewer_bundle(self.app.ROOT).read_bytes(),'application/javascript')
                except (ValueError,OSError) as error:return self.reply(404,{'error':str(error)})
            if route!='/' and not self.authorized():return self.reply(403,{'error':'Unauthorized'})
            name=self.GET_ROUTES.get(route)
            if not name:name=next((name for prefix,name in self.GET_PREFIXES if route.startswith(prefix)),None)
            return getattr(self,name)(route) if name else self.reply(404,{'error':'Not found'})
        except (ValueError,OSError,TypeError,KeyError) as error:return self.reply(400,{'error':str(error)})
        except sqlite3.Error:return self.reply(503,{'error':'Database operation failed; inspect local diagnostics'})

    def do_POST(self):
        if not self.authorized():return self.reply(403,{'error':'Unauthorized'})
        route=urlsplit(self.path).path;name=self.POST_ROUTES.get(route)
        if not name:return self.reply(404,{'error':'Not found'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            limit=36*1024*1024 if route=='/api/models' else 3*1024*1024 if route=='/api/chats' else 65536
            if not 0<length<=limit:raise ValueError('Invalid request size')
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict):raise ValueError('Request must be a JSON object')
            with self.app.STATE_LOCK:return getattr(self,name)(route,data)
        except (ValueError,OSError,TypeError,KeyError) as error:return self.reply(400,{'error':str(error)})
        except sqlite3.Error:return self.reply(503,{'error':'Database operation failed; inspect local diagnostics'})

    def _get_page(self, route, data=None):
        return self.reply(200, self.app.HTML, 'text/html')

    def _get_api_access_policy(self, route, data=None):
        from access_policy import current
        from task_contract import configuration
        effective = configuration(self.app.ROOT)
        return self.reply(200, {**current(self.app.ROOT).report(), 'model': effective['model'], 'configuration': effective})

    def _get_api_opencode_agent(self, route, data=None):
        from opencode_runtime import status as opencode_agent_status
        try:
            with self.app.STATE_LOCK:return self.reply(200, opencode_agent_status(self.app.ROOT))
        except (ValueError, OSError, TypeError, KeyError) as e:
            return self.reply(400, {'error': str(e)})

    def _get_api_mcp_status(self, route, data=None):
        try:
            return self.reply(200, self.app.mcp_status(self.app.ROOT))
        except (OSError, ValueError) as e:
            return self.reply(400, {'error': str(e)})

    def _get_api_models_status(self, route, data=None):
        return self.reply(200, self.app.viewer_status(self.app.ROOT))

    def _get_api_models_item(self, route, data=None):
        try:
            return self.reply(200, self.app.model_path(self.app.ROOT, route.removeprefix('/api/models/')).read_bytes(), 'model/gltf-binary')
        except (OSError, ValueError) as e:
            return self.reply(400, {'error': str(e)})

    def _get_api_chat_jobs_item(self, route, data=None):
        try:
            return self.reply(200, self.app.JOBS.status(route.removeprefix('/api/chat-jobs/'), root=self.app.ROOT))
        except ValueError as e:
            return self.reply(400, {'error': str(e)})

    def _get_api_skills(self, route, data=None):
        try:
            return self.reply(200, self.app.skill_monitor(self.app.ROOT).status())
        except (OSError, ValueError) as e:
            return self.reply(400, {'error': str(e)})

    def _get_api_skills_status(self, route, data=None):
        try:
            return self.reply(200, {**self.app.skill_monitor(self.app.ROOT).status(), 'tools': self.app.tools_status(self.app.ROOT)})
        except (OSError, ValueError) as e:
            return self.reply(400, {'error': str(e)})

    def _get_api_skills_review_item(self, route, data=None):
        try:
            return self.reply(200, self.app.skill_monitor(self.app.ROOT).review(self.app.unquote(route.removeprefix('/api/skills/review/'))))
        except (OSError, ValueError) as e:
            return self.reply(400, {'error': str(e)})

    def _get_api_rea_status(self, route, data=None):
        return self.reply(200, self.app.rea_package_status(self.app.ROOT))

    def _get_api_runtime(self, route, data=None):
        try:
            return self.reply(200, self.app.load_runtime(self.app.ROOT))
        except (OSError, ValueError) as e:
            return self.reply(400, {'error': str(e)})

    def _get_api_system_status(self, route, data=None):
        try:
            return self.reply(200, self.app.system_status(self.app.ROOT))
        except (ValueError, OSError) as e:
            return self.reply(400, {'error': str(e)})

    def _get_api_chats(self, route, data=None):
        try:
            return self.reply(200, self.app.list_chats(self.app.ROOT))
        except (ValueError, OSError) as e:
            return self.reply(400, {'error': str(e)})

    def _get_api_chats_item(self, route, data=None):
        try:
            return self.reply(200, self.app.read_chat(self.app.ROOT, route.removeprefix('/api/chats/'), before=self.app.parse_qs(self.app.urlsplit(self.path).query).get('before', [None])[0]))
        except (ValueError, OSError) as e:
            return self.reply(400, {'error': str(e)})

    def _get_api_startup(self, route, data=None):
        try:
            return self.reply(200, self.app.startup_report(self.app.ROOT, self.app.scan, self.app.list_models))
        except (ValueError, OSError, TypeError, KeyError, self.app.json.JSONDecodeError) as e:
            return self.reply(400, {'error': str(e)})

    def _get_api_opencode_validate(self, route, data=None):
        try:
            with self.app.STATE_LOCK:
                current_state = self.app.load_config(self.app.ROOT, 'extensions.json')
                preferences = self.app.load_config(self.app.ROOT, 'model_preferences.json')
            status = {item['name']: item for item in self.app.scan()['tools']}
            self.app.inspect_opencode(current_state, status)
            discovery = self.app.list_models(current_state, {name: item['status'] for name, item in status.items()})
            return self.reply(200, self.app.validate_staged_config(self.app.ROOT / '.smelter' / 'opencode-isolated', preferences, discovery))
        except (ValueError, OSError, self.app.json.JSONDecodeError, AttributeError) as e:
            return self.reply(400, {'error': str(e)})

    def _get_api_opencode_provider_preview(self, route, data=None):
        try:
            with self.app.STATE_LOCK:
                current_state = self.app.load_config(self.app.ROOT, 'extensions.json')
                preferences = self.app.load_config(self.app.ROOT, 'model_preferences.json')
            status = {item['name']: item for item in self.app.scan()['tools']}
            discovery = self.app.list_models(current_state, {name: item['status'] for name, item in status.items()})
            agent = self.app.inspect_opencode(current_state, status)
            return self.reply(200, self.app.provider_preview(preferences, discovery, agent))
        except (ValueError, OSError, TypeError, KeyError, self.app.json.JSONDecodeError) as e:
            return self.reply(400, {'error': str(e)})

    def _get_api_opencode_status(self, route, data=None):
        try:
            with self.app.STATE_LOCK:
                current_state = self.app.load_config(self.app.ROOT, 'extensions.json')
            status = {item['name']: item for item in self.app.scan()['tools']}
            return self.reply(200, self.app.inspect_opencode(current_state, status))
        except (ValueError, OSError, TypeError, KeyError, self.app.json.JSONDecodeError) as e:
            return self.reply(400, {'error': str(e)})

    def _get_api_ollama_preferences(self, route, data=None):
        try:
            with self.app.STATE_LOCK:
                preferences = self.app.load_config(self.app.ROOT, 'model_preferences.json')
                current_state = self.app.load_config(self.app.ROOT, 'extensions.json')
            status = {item['name']: item['status'] for item in self.app.scan()['tools']}
            return self.reply(200, self.app.configured_status(preferences, self.app.list_models(current_state, status)))
        except (ValueError, OSError, TypeError, KeyError, self.app.json.JSONDecodeError) as e:
            return self.reply(400, {'error': str(e)})

    def _get_api_ollama_models(self, route, data=None):
        try:
            with self.app.STATE_LOCK:
                current_state = self.app.load_config(self.app.ROOT, 'extensions.json')
            status = {item['name']: item['status'] for item in self.app.scan()['tools']}
            return self.reply(200, self.app.list_models(current_state, status))
        except (ValueError, OSError, TypeError, KeyError, self.app.json.JSONDecodeError) as e:
            return self.reply(400, {'error': str(e)})

    def _get_api_workflows_reports(self, route, data=None):
        return self.reply(200, {'reports': self.app.list_reports(self.app.REPORTS)})

    def _get_api_workflows(self, route, data=None):
        return self.reply(200, {'workflows': self.app.definitions()})

    def _get_api_extensions(self, route, data=None):
        try:
            return self.reply(200, {'extensions': self.app.catalog(self.app.scan(refresh=True) if self.app.parse_qs(self.app.urlsplit(self.path).query).get('refresh')==['1'] else self.app.scan(), self.app.load_config(self.app.ROOT, 'extensions.json'))})
        except (ValueError, OSError, TypeError, KeyError, self.app.json.JSONDecodeError) as e:
            return self.reply(500, {'error': str(e)})

    def _post_api_access_policy(self, route, data=None):
        from access_policy import save
        with self.app.STATE_LOCK:
            return self.reply(200, save(self.app.ROOT, data.get('policy')))

    def _post_api_mcp(self, route, data=None):
        if data.get('action') == 'save':
            with self.app.STATE_LOCK:
                return self.reply(200, self.app.save_mcp_config(self.app.ROOT, data.get('config')))
        if data.get('action') == 'probe':
            sid = data.get('server')
            if not isinstance(sid, str):
                raise ValueError('Choose an MCP server')
            if sid != 'smelter':
                raise ValueError('External MCP servers require a confined runner; no process was started')
            from access_policy import current, check_grants, using
            policy = current(self.app.ROOT)
            grants = self.app.validate_tool_permissions(self.app.ROOT, data.get('permissions'))
            check_grants(self.app.ROOT, grants, policy)
            with using(policy):
                return self.reply(200, self.app.mcp_exchange(self.app.ROOT, sid, grants, timeout=20))
        raise ValueError('Unknown MCP action')

    def _post_api_models(self, route, data=None):
        return self.reply(200, self.app.rename_animation(self.app.ROOT, data) if data.get('action') == 'rename_animation' else self.app.attach_model(self.app.ROOT, data))

    def _post_api_skills_collection_preview(self, route, data=None):
        urls = data.get('urls')
        if not isinstance(urls, list) or not 1 <= len(urls) <= 40:
            raise ValueError('Select 1-40 skills')
        results = [self.app.discover_github_skill(url) for url in urls]
        return self.reply(200, {'skills': results})

    def _post_api_skills_discover_repository(self, route, data=None):
        return self.reply(200, self.app.discover_github_repository(data.get('url')))

    def _post_api_skills_discover(self, route, data=None):
        return self.reply(200, self.app.discover_github_skill(data.get('url')))

    def _post_api_skills_manage(self, route, data=None):
        with self.app.STATE_LOCK:
            action = data.get('action')
            if action == 'add':
                raise ValueError('Use GitHub discovery before installation')
            elif action == 'bulk':
                from skill_manager import manage_many
                result=manage_many(self.app.ROOT,data.get('ids'),data.get('operation'),data.get('approval'))
            elif action == 'install_collection':
                result = self.app.install_collection(self.app.ROOT, data.get('repository_url'), data.get('selected'), data.get('approval'))
            elif action == 'install_github':
                result = self.app.install_discovered_skill(self.app.ROOT, data.get('id'), data.get('url'), data.get('sha256'), data.get('approval'))
            elif action == 'enable':
                result = self.app.set_skill_enabled(self.app.ROOT, data.get('id'), data.get('enabled'), data.get('approval'))
            elif action == 'remove':
                result = self.app.remove_skill(self.app.ROOT, data.get('id'), data.get('approval'))
            else:
                raise ValueError('Unknown skill action')
        return self.reply(200, result)

    def _post_api_aero_classify(self, route, data=None):
        return self.reply(200, self.app.classify_task(data.get('task')))

    def _post_api_chats(self, route, data=None):
        if data.get('action') == 'runtime_settings':
            return self.reply(200, self.app.save_runtime(self.app.ROOT, data.get('settings')))
        if data.get('action') in ('start', 'ask'):
            return self.reply(202, self.app.JOBS.start(self.app.ROOT, data))
        if data.get('action') == 'stop':
            return self.reply(200, self.app.JOBS.cancel(data.get('job_id')))
        with self.app.STATE_LOCK:
            action = data.get('action')
            if action == 'create':
                result = self.app.create_chat(self.app.ROOT, data.get('title'))
            elif action == 'note':
                result = self.app.add_note(self.app.ROOT, data.get('id'), data.get('content'))
            elif action == 'rename':
                result = self.app.rename_chat(self.app.ROOT, data.get('id'), data.get('title'))
            elif action == 'delete':
                result = self.app.delete_chat(self.app.ROOT, data.get('id'))
            else:
                raise ValueError('Unknown chat action')
        return self.reply(200, result)

    def _post_api_database_select(self, route, data=None):
        with self.app.STATE_LOCK:
            return self.reply(200, self.app.select_database(self.app.ROOT, data.get('directory')))

    def _post_api_opencode_deploy(self, route, data=None):
        with self.app.STATE_LOCK:
            current_state = self.app.load_config(self.app.ROOT, 'extensions.json')
            preferences = self.app.load_config(self.app.ROOT, 'model_preferences.json')
        status = {item['name']: item for item in self.app.scan()['tools']}
        discovery = self.app.list_models(current_state, {name: item['status'] for name, item in status.items()})
        agent = self.app.inspect_opencode(current_state, status)
        preview = self.app.provider_preview(preferences, discovery, agent)
        with self.app.STATE_LOCK:
            result = self.app.deploy_isolated_config(self.app.ROOT / '.smelter' / 'opencode-isolated', preview, data.get('approval'))
        return self.reply(200, result)

    def _post_api_ollama_preferences(self, route, data=None):
        with self.app.STATE_LOCK:
            current_state = self.app.load_config(self.app.ROOT, 'extensions.json')
        status = {item['name']: item['status'] for item in self.app.scan()['tools']}
        discovery = self.app.list_models(current_state, status)
        with self.app.STATE_LOCK:
            role, model = (data.get('role'), data.get('model'))
            if role not in ('reasoning', 'lightweight') or not isinstance(model, str) or model not in {item['name'] for item in discovery.get('models', [])} or (discovery.get('status') != 'connected'):
                raise ValueError('Model must be installed in connected Ollama and role must be valid')
            preferences = self.app.load_config(self.app.ROOT, 'model_preferences.json')
            preferences['models'][role] = model
            self.app.save_config(self.app.ROOT, 'model_preferences.json', preferences)
        return self.reply(200, self.app.configured_status(preferences, discovery))

    def _post_api_blender_inspect(self, route, data=None):
        with self.app.STATE_LOCK:
            current_state = self.app.load_config(self.app.ROOT, 'extensions.json')
        status = {item['name']: item['status'] for item in self.app.scan()['tools']}
        from access_policy import current
        policy = current(self.app.ROOT)
        policy.authorize(self.app.ROOT, 'execute', 'blender')
        report = self.app.inspect_blender(data.get('approval'), current_state, status)
        with self.app.STATE_LOCK:
            self.app.save_report(self.app.REPORTS, report)
        return self.reply(200, report)

    def _post_api_media_inspect(self, route, data=None):
        with self.app.STATE_LOCK:
            current_state = self.app.load_config(self.app.ROOT, 'extensions.json')
        status = {item['name']: item['status'] for item in self.app.scan()['tools']}
        from access_policy import current
        policy = current(self.app.ROOT)
        policy.authorize(self.app.ROOT, 'execute', 'media')
        policy.authorize(data.get('path'), 'read')
        report = self.app.inspect_media(data.get('path'), data.get('approval'), current_state, status)
        with self.app.STATE_LOCK:
            self.app.save_report(self.app.REPORTS, report)
        return self.reply(200, report)

    def _post_api_archive_inspect(self, route, data=None):
        with self.app.STATE_LOCK:
            current_state = self.app.load_config(self.app.ROOT, 'extensions.json')
        status = {item['name']: item['status'] for item in self.app.scan()['tools']}
        from access_policy import current
        policy = current(self.app.ROOT)
        policy.authorize(self.app.ROOT, 'execute', 'archive')
        policy.authorize(data.get('path'), 'read')
        report = self.app.inspect_archive(data.get('path'), data.get('approval'), current_state, status)
        with self.app.STATE_LOCK:
            self.app.save_report(self.app.REPORTS, report)
        return self.reply(200, report)

    def _post_api_workflows_plan(self, route, data=None):
        report = self.app.attach_inputs(self.app.plan(data.get('workflow_id'), self.app.scan(), self.app.load_config(self.app.ROOT, 'extensions.json')), data.get('inputs'))
        with self.app.STATE_LOCK:
            self.app.save_report(self.app.REPORTS, report)
        return self.reply(200, report)

    def _post_api_extensions(self, route, data=None):
        with self.app.STATE_LOCK:
            state = self.app.set_enabled(self.app.load_config(self.app.ROOT, 'extensions.json'), data.get('id'), data.get('enabled'), self.app.scan())
            self.app.save_config(self.app.ROOT, 'extensions.json', state)
        return self.reply(200, {'enabled': state['enabled']})

    def _get_capabilities(self,route,data=None):
        from capability_catalog import catalog
        return self.reply(200,catalog(self.app.ROOT))

    def _get_maintenance(self,route,data=None):
        from maintenance import status
        return self.reply(200,status(self.app.ROOT))

    def _post_maintenance(self,route,data):
        from maintenance import status,plan,prune,backup
        action=data.get('action')
        if action=='status':result=status(self.app.ROOT)
        elif action=='plan':result=plan(self.app.ROOT,data.get('days',30))
        elif action=='prune':result=prune(self.app.ROOT,data.get('plan_id'),data.get('approval'))
        elif action=='backup':result=backup(self.app.ROOT,data.get('directory'),data.get('approval'))
        elif action=='reconcile_containers':
            from sandbox import reconcile
            result=reconcile(self.app.ROOT,data.get('approval'))
        elif action=='integrity':
            from database import inspect_database
            result=inspect_database(self.app.ROOT,integrity=True)
        else:raise ValueError('Unknown maintenance action')
        return self.reply(200,result)

    def _get_sandbox(self,route,data=None):
        from sandbox import status
        return self.reply(200,status(self.app.ROOT))

    def _post_sandbox(self,route,data):
        if data.get('action')=='save':
            from config_store import save_config
            save_config(self.app.ROOT,'sandbox.json',data.get('configuration'))
            return self.reply(200,{'saved':True,'started':False})
        if data.get('action')=='stop_preview':
            from sandbox_preview import stop
            return self.reply(200,stop())
        raise ValueError('Unknown sandbox action')

    def _post_project_contract(self,route,data):
        from project_contract import inspect_project
        from access_policy import current,using
        policy=current(self.app.ROOT)
        target=policy.authorize(data.get('path'),'read')
        with using(policy):result=inspect_project(target)
        return self.reply(200,result)


ApiRoutes.GET_ROUTES.update({'/api/capabilities':'_get_capabilities','/api/maintenance':'_get_maintenance','/api/sandbox':'_get_sandbox'})
ApiRoutes.POST_ROUTES.update({'/api/project-contract':'_post_project_contract','/api/maintenance':'_post_maintenance','/api/sandbox':'_post_sandbox'})
