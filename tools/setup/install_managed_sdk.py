"""Cache an operator-pinned development SDK. No runtime installation or execution."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import sys
from urllib.request import urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/dashboard'))
from python_tools import _plain_path


def spec(root, identity):
    if not isinstance(identity,str) or not re.fullmatch(r'[a-z][a-z0-9_-]{0,30}',identity):
        raise ValueError('Invalid SDK identity')
    path = _plain_path(Path(root)/'tools/setup/managed-sdk-lock.json')
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('schema_version') != 1 or identity not in value.get('sdks',{}):
        raise ValueError('Unknown operator-pinned SDK')
    item = value['sdks'][identity]
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,80}',item.get('package','')) or not re.fullmatch(r'\d+\.\d+\.\d+(?:[-.][A-Za-z0-9]+)*',item.get('version','')):
        raise ValueError('Invalid SDK package/version')
    expected = 'https://api.nuget.org/v3-flatcontainer/{0}/{1}/{0}.{1}.nupkg'.format(item['package'].lower(),item['version'])
    if item['source'] != expected or not re.fullmatch(r'[0-9a-f]{64}',item['package_sha256']):
        raise ValueError('Invalid pinned package identity')
    if type(item['max_package_bytes']) is not int or not 0 < item['max_package_bytes'] <= 8*1024*1024:
        raise ValueError('SDK package exceeds allowed bound')
    if not isinstance(item['files'],dict) or not 1 <= len(item['files']) <= 16:
        raise ValueError('Invalid SDK file count')
    for name, member in item['files'].items():
        if 'reference' in member and type(member['reference']) is not bool:
            raise ValueError('SDK reference role must be boolean')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,90}',name) or name.endswith('.') or '..' in name:
            raise ValueError('Invalid SDK cache filename')
        if re.fullmatch(r'(?i:con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?',name):
            raise ValueError('Reserved SDK cache filename')
        if not re.fullmatch(r'[0-9a-f]{64}',member['sha256']) or not 0 < member['bytes'] <= 4*1024*1024:
            raise ValueError('Invalid SDK member pin')
    return item


def folder(root, identity, item):
    return _plain_path(Path(root)/'.smelter/tooling'/(identity+'-sdk')/item['version'])


def inspect(root, identity):
    item = spec(root,identity); base = folder(root,identity,item)
    files = {}
    for name, pin in item['files'].items():
        path = _plain_path(base/name)
        if not path.is_file() or path.stat().st_size != pin['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != pin['sha256']:
            raise ValueError('Pinned SDK member unavailable or changed: '+name)
        files[name] = str(path)
    return {'sdk':identity,'version':item['version'],'files':files,'package_sha256':item['package_sha256'],
            'development_only':item['development_only'],'redistribute':item['redistribute'],'runtime_installed':False}


def install(root, identity):
    item = spec(root,identity); base = folder(root,identity,item); base.mkdir(parents=True,exist_ok=True)
    package = _plain_path(base/(item['package'].lower()+'.'+item['version']+'.nupkg'))
    if package.exists():
        if package.stat().st_size > item['max_package_bytes']:raise ValueError('Oversized cached SDK package')
        raw = package.read_bytes()
    else:
        with urlopen(item['source'],timeout=30) as response:
            raw = response.read(item['max_package_bytes']+1)
    if len(raw) > item['max_package_bytes'] or hashlib.sha256(raw).hexdigest() != item['package_sha256']:
        raise ValueError('SDK package SHA-256 mismatch; nothing extracted')
    if not package.exists():package.write_bytes(raw)
    pending = {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for name,pin in item['files'].items():
            info = archive.getinfo(pin['member'])
            if info.file_size != pin['bytes']:raise ValueError('SDK member size mismatch')
            data = archive.read(pin['member'])
            if hashlib.sha256(data).hexdigest() != pin['sha256']:raise ValueError('SDK member SHA-256 mismatch')
            path = _plain_path(base/name)
            if path.exists() and path.read_bytes() != data:raise ValueError('Existing SDK member changed; not overwritten')
            pending[path] = data
    for path,data in pending.items():
        if not path.exists():path.write_bytes(data)
    result = inspect(root,identity)
    (base/'sdk.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--sdk',required=True)
    args=parser.parse_args();print(json.dumps(install(ROOT,args.sdk),indent=2))
