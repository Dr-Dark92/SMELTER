"""Install/start the digest-pinned private SearXNG provider; no API key or global PATH."""
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import sys
import time
from urllib.request import build_opener, ProxyHandler

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/dashboard'))


def install(root=ROOT,*,start=False,enable_docs=False):
    from python_tools import _plain_path
    from process_runner import run
    root=_plain_path(Path(root).resolve())
    lock_path=root/'tools/modding/requirements-web.json';lock=json.loads(lock_path.read_text(encoding='utf-8'))
    docker=shutil.which('docker')
    if not docker:raise ValueError('Local Docker is required')
    import os
    if os.environ.get('DOCKER_HOST') and not os.environ['DOCKER_HOST'].startswith(('unix://','npipe://')):raise ValueError('Only local Docker is supported')
    endpoint=run([docker,'context','inspect','--format','{{.Endpoints.docker.Host}}'],timeout=5,max_output=16384,text=True,check=True).stdout.strip()
    if not endpoint.startswith(('unix://','npipe://')):raise ValueError('Only local Docker is supported')
    if any(c in str(root) for c in ',\n\r\x00'):raise ValueError('Unsupported service mount path')
    base=_plain_path(root/'.smelter/tooling/web-search');config=base/'config';config.mkdir(parents=True,exist_ok=True)
    name='smelter-search-'+hashlib.sha256(str(root).encode()).hexdigest()[:12]
    image=lock['image']
    observed=run([docker,'image','inspect',image,'--format','{{.Id}}'],timeout=10,max_output=16384,text=True)
    if observed.returncode:
        run([docker,'pull','--platform',lock['platform'],image],timeout=300,max_output=1024*1024,text=True,check=True)
        observed=run([docker,'image','inspect',image,'--format','{{.Id}}'],timeout=10,max_output=16384,text=True,check=True)
    image_id=observed.stdout.strip()
    settings=_plain_path(config/'settings.yml')
    if not settings.exists():
        value={'use_default_settings':{'engines':{'keep_only':['duckduckgo','brave','bing']}},
               'general':{'instance_name':'SMELTER private search','debug':False},
               'search':{'formats':['html','json'],'safe_search':1},
               'server':{'secret_key':secrets.token_hex(32),'limiter':False,'image_proxy':False,'public_instance':False,'base_url':'http://127.0.0.1:8842/'},
               'outgoing':{'request_timeout':6.0,'max_request_timeout':10.0},'enabled_plugins':[],
               'engines':[{'name':'duckduckgo','disabled':False},{'name':'brave','disabled':False},{'name':'bing','disabled':False}]}
        settings.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    receipt={'schema_version':1,'container':name,'image':image,'image_id':image_id,'bind':'127.0.0.1:8842',
             'version':lock['version'],'revision':lock['revision'],
             'lock_sha256':hashlib.sha256(lock_path.read_bytes()).hexdigest(),'settings_sha256':hashlib.sha256(settings.read_bytes()).hexdigest()}
    if start:
        existing=run([docker,'container','inspect',name],timeout=10,max_output=65536,text=True)
        if existing.returncode==0:
            row=json.loads(existing.stdout)[0]
            if row.get('Config',{}).get('Labels',{}).get('smelter.service')!='web-search-v1' or row.get('Image')!=image_id:
                raise ValueError('The existing search container has a different owner/image; preserved for review')
            if not row.get('State',{}).get('Running'):
                raise ValueError('The owned search container is stopped. Inspect its logs before restarting; it was preserved.')
        else:
            run([docker,'run','--detach','--pull','never','--name',name,'--label','smelter.service=web-search-v1',
                 '--restart','unless-stopped','--read-only','--user','65534:65534','--cap-drop','ALL',
                 '--security-opt','no-new-privileges=true','--pids-limit','128','--memory','512m','--memory-swap','512m','--cpus','2',
                 '--log-driver','local','--log-opt','max-size=1m','--log-opt','max-file=2',
                 '--publish','127.0.0.1:8842:8080',
                 '--mount','type=bind,source='+str(config)+',target=/etc/searxng,readonly',
                 '--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=64m,mode=1777',
                 '--tmpfs','/var/cache/searxng:rw,noexec,nosuid,nodev,size=64m,uid=65534,gid=65534,mode=0700',
                 '--env','SEARXNG_SETTINGS_PATH=/etc/searxng/settings.yml','--env','GRANIAN_WORKERS=1',
                 '--entrypoint','/usr/local/searxng/.venv/bin/granian',image,'searx.webapp:app'],
                timeout=30,max_output=65536,text=True,check=True)
        opener=build_opener(ProxyHandler({}));end=time.monotonic()+45
        while time.monotonic()<end:
            try:
                with opener.open('http://127.0.0.1:8842/healthz',timeout=2) as response:
                    if response.status==200:break
            except OSError:time.sleep(.5)
        else:raise ValueError('Owned search service did not become healthy; inspect docker logs '+name)
    (base/'installation.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    if enable_docs:
        from web_access import settings as web_settings
        from config_store import save_config
        value=web_settings(root);value['mode']='docs';save_config(root,'web_access.json',value)
    return {**receipt,'started':start,'documentation_mode_enabled':enable_docs}


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--start',action='store_true');parser.add_argument('--enable-docs',action='store_true');args=parser.parse_args()
    print(json.dumps(install(args.root,start=args.start,enable_docs=args.enable_docs),indent=2))
