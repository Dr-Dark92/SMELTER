"""Temporary GUI fixture: synthetic replies, no Ollama/OpenCode/Docker service use.

Run from any directory with Python; open the printed launch URL. Ctrl+C removes
fixture chats/reports/state. Application source remains unchanged. This is a
manual development harness, not an alternate production execution engine.
"""
import argparse
import base64
import hashlib
import io
from contextlib import ExitStack
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import signal
import sys
import tempfile
import time
from unittest.mock import patch
from uuid import uuid4


def serve(port=18771,viewer_root=None):
    repo=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(repo/'tools/dashboard'))
    import dashboard
    from chat_jobs import Control,Jobs
    from database import select_database,inspect_database
    from skill_runtime import initialize
    from check_requirements import TOOLS
    with tempfile.TemporaryDirectory(prefix='smelter-offline-') as temporary,ExitStack() as patches:
        base=Path(temporary);root=base/'SMELTER';root.mkdir();root.with_name('SMELTERV2').mkdir()
        select_database(root,str(base/'data'))
        (root/'README.md').write_text('Offline synthetic GUI fixture.\n')
        for name in ('Characters','Environments'):(root/'Assets'/name).mkdir(parents=True)
        (root/'Assets/notes.txt').write_text('This file is not listed or read by the folder browser.')
        skill=root/'skills/fixture';skill.mkdir(parents=True)
        (skill/'SKILL.md').write_text('# Fixture\n\n## Purpose\nInspect synthetic work only.\n')
        demo={name:'# '+name.title()+'\n\n## Purpose\nReview '+name+' in the offline fixture.\n' for name in ('layout','spacing','contrast')}
        for name,text in demo.items():
            folder=root/'.smelter/managed-skills/collections/demo-design'/name;folder.mkdir(parents=True);(folder/'SKILL.md').write_text(text)
        (root/'.smelter/skill-state.json').write_text(json.dumps({'demo-design/layout':True,'demo-design/spacing':False,'demo-design/contrast':True}))
        imported={'layout':demo['layout'],'rhythm':'# Rhythm\n\n## Purpose\nImprove rhythm in this fixture.\n','rhythm-copy':'# Rhythm\n\n## Purpose\nImprove rhythm in this fixture.\n'}
        def discovery(url):
            from github_skill_discovery import parse_github_skill
            owner,repository,ref,path=parse_github_skill(url)
            if (owner,repository)!=('offline','design'):raise ValueError('Offline import demo uses https://github.com/offline/design')
            name=path.split('/')[-2] if '/' in path else 'layout';text=imported[name]
            return {'url':url,'owner':owner,'repository':repository,'ref':ref,'path':path,'content':text,'sha256':hashlib.sha256(text.encode()).hexdigest(),'warnings':[]}
        def discovery_repository(url):
            if url!='https://github.com/offline/design':raise ValueError('Offline import demo uses https://github.com/offline/design')
            rows=[{'path':'skills/'+name+'/SKILL.md','url':url+'/blob/main/skills/'+name+'/SKILL.md'} for name in imported]
            return {'owner':'offline','repository':'design','ref':'main','skills':rows,'count':len(rows)}
        def fixture_opener(request,timeout):
            name=request.full_url.split('/skills/')[1].split('/')[0]
            return io.BytesIO(json.dumps({'type':'file','encoding':'base64','content':base64.b64encode(imported[name].encode()).decode()}).encode())
        reports=root/'.smelter/reports';reports.mkdir()
        old=reports/(str(uuid4())+'.json');old.write_text('{"fixture":true}')
        import os
        os.utime(old,(time.time()-40*86400,)*2)
        unavailable={'status':'offline_fixture','models':[],'reason':'Service disabled in offline fixture'}
        def scan():return {'tools':[{'name':name,'status':'missing','version':None,'path':None} for name in TOOLS],'fixture':True}
        def system(_):return {'timestamp':time.time(),'database':{'status':inspect_database(root)['status']},'cpu':{'status':'unavailable'},'memory':{'status':'unavailable'},'models':unavailable,'gpu':{'status':'unavailable'},'storage':{'free_bytes':0},'fixture':True}
        def infer(control,body,timeout,maximum):
            control.check();messages=body['messages'];prompt=next((m['content'] for m in reversed(messages) if m['role']=='user'),'')
            if 'slow' in prompt.lower():
                control.update('Offline fixture waiting for Stop')
                for _ in range(200):
                    if control.cancelled.wait(.05):control.check()
            if 'report' in prompt.lower() and body.get('tools') and not any(m['role']=='tool' for m in messages):
                message={'content':'','tool_calls':[{'function':{'name':'write_diagnostic_markdown','arguments':{'filename':'offline-fixture.md','content':'# Offline fixture\n'}}}]}
            else:message={'content':'Offline fixture response. No model was called.'}
            return json.dumps({'message':message}).encode()
        patches.enter_context(patch.object(dashboard,'ROOT',root));patches.enter_context(patch.object(dashboard,'REPORTS',reports));patches.enter_context(patch.object(dashboard,'JOBS',Jobs()))
        patches.enter_context(patch.object(dashboard,'scan',scan));patches.enter_context(patch.object(dashboard,'system_status',system))
        patches.enter_context(patch.object(dashboard,'list_models',lambda *a,**k:unavailable))
        patches.enter_context(patch.object(dashboard,'inspect_opencode',lambda *a,**k:unavailable))
        patches.enter_context(patch.object(dashboard,'rea_package_status',lambda *a,**k:unavailable))
        patches.enter_context(patch('opencode_runtime.status',return_value=unavailable))
        patches.enter_context(patch('sandbox.status',return_value={'configured':{'schema_version':1,'python_image':None,'node_image':None,'opencode_image':None},'ready':False,'reason':'Execution blocked in offline fixture','boundary':'Synthetic fixture; no container service','host_fallback':False}))
        from skill_collections import install_collection
        from github_skill_discovery import install_discovered_skill
        patches.enter_context(patch.object(dashboard,'discover_github_skill',discovery))
        patches.enter_context(patch.object(dashboard,'discover_github_repository',discovery_repository))
        patches.enter_context(patch.object(dashboard,'install_collection',lambda *a,**k:install_collection(*a,**k,discover=discovery)))
        patches.enter_context(patch.object(dashboard,'install_discovered_skill',lambda *a,**k:install_discovered_skill(*a,**k,opener=fixture_opener)))
        patches.enter_context(patch.object(Control,'infer',infer))
        initialize(root)
        changed=root/'.smelter/managed-skills/collections/demo-design/contrast/SKILL.md';changed.write_text(demo['contrast']+'\nChanged fixture instructions.\n')
        if viewer_root is not None:
            # Explicit test dependency: reuse a validated local viewer bundle.
            # No package installation or asset fetching occurs in this fixture.
            import model_assets
            bundle=model_assets.viewer_bundle(Path(viewer_root).resolve())
            patches.enter_context(patch.object(dashboard,'viewer_bundle',lambda _:bundle))
            patches.enter_context(patch.object(dashboard,'viewer_status',lambda _:{'status':'installed','version':model_assets.VIEWER_VERSION}))
        token=secrets.token_urlsafe(32)
        handler=dashboard.handler(token)
        class FixtureHandler(handler):
            def _get_page(self,*args,**kwargs):
                html=dashboard.HTML.replace('V1.7 · Scoped local workbench','OFFLINE FIXTURE · Temporary data · Synthetic responses')
                return self.reply(200,html,'text/html')
        server=ThreadingHTTPServer(('127.0.0.1',port),FixtureHandler)
        print('OFFLINE GUI FIXTURE — no real model calls; temporary data.',flush=True)
        print(f'http://127.0.0.1:{server.server_port}/#token={token}',flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:
            for job in list(dashboard.JOBS.jobs.values()):
                if job['state']=='running':job['control'].cancel()
            deadline=time.monotonic()+5
            while any(j['state']=='running' for j in dashboard.JOBS.jobs.values()) and time.monotonic()<deadline:time.sleep(.05)
            server.shutdown();server.server_close()
            from skill_runtime import _monitors
            _monitors.pop(str(root.resolve()),None)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--port',type=int,default=18771);parser.add_argument('--viewer-root',type=Path)
    def stop(*_):raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,stop)
    args=parser.parse_args()
    serve(args.port,args.viewer_root)
