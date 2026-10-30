"""Plan, apply and remove the supervised RPH read-probe deployment.

extract copies only the top-level files of an author archive (the runtime the
       author's readme says goes into the game folder) into .smelter, never subfolders.
plan   inventories an extracted author runtime folder (read-only) and writes a plan.
apply  copies exactly the planned files into the game folder: never overwrites an
       existing file, re-hashes every source first, and records an install manifest.
remove deletes only files whose bytes still match that manifest.

All files at the runtime folder's top level are selected by default (RPH's
readme: everything except its SDK and Licenses folders) and RAGEPluginHook.exe
must be among them. Anything in a subfolder (for example a bundled LSPDFR's
plugins/ and lspdfr/) is listed as excluded and needs an explicit --file. The tool never launches the game, loads a plugin,
patches executables or changes security settings.
"""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]
EXPECTATIONS=ROOT/'mods/gta-ark/gta/rph/read_probe_expectations.json'
PACKAGE=ROOT/'.smelter/mod-packages/gta-native-read-probe-20261028'
GAME=Path(r'D:\SteamLibrary\steamapps\common\Grand Theft Auto V Enhanced')
STATE=ROOT/'.smelter/native-read-gate'
MAX_FILES=256


def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def profile(path=EXPECTATIONS):
    """Executable and plugin pins from the same reviewed profile verify_runtime_probe.py judges against."""
    value=json.loads(Path(path).read_text(encoding='utf-8'))
    return {'executable':value['executable']['name'],'version':value['executable']['file_version'],
            'sha256':value['executable']['sha256'],'plugin':value['plugin']['name'],'plugin_sha256':value['plugin']['sha256']}


def _relative(base,path):
    value=Path(path)
    if value.is_absolute() or '..' in value.parts:raise ValueError('Paths must stay inside their folder: '+str(path))
    return (base/value).resolve().relative_to(base.resolve()).as_posix()


def extract(archive,state=STATE):
    """Copy the archive's top-level files (only) into a folder named after its hash."""
    import zipfile
    digest=sha256(archive);target=Path(state)/'runtime'/digest[:16]
    with zipfile.ZipFile(archive) as z:
        top=[i for i in z.infolist() if not i.is_dir() and '/' not in i.filename.strip('/') and chr(92) not in i.filename]
        if not top or len(top)>MAX_FILES:raise ValueError('Archive top level has no files or more than 256')
        if sum(i.file_size for i in top)>512*1024*1024:raise ValueError('Archive top-level files exceed 512 MiB')
        target.mkdir(parents=True,exist_ok=False)
        for info in top:
            name=Path(info.filename).name
            if name in ('','.','..'):raise ValueError('Unsafe archive member: '+info.filename)
            with z.open(info) as src,open(target/name,'xb') as out:shutil.copyfileobj(src,out)
    (target.parent/(digest[:16]+'.source.json')).write_text(json.dumps({'archive':str(Path(archive).resolve()),'sha256':digest,
        'files':sorted(i.filename for i in top),'subfolders_skipped':True}),encoding='utf-8')
    return target


def plan(runtime_dir,game_dir=GAME,extra=(),package=PACKAGE,pins=None):
    """runtime_dir None deploys only a package onto an existing runtime (e.g. a second probe)."""
    runtime=Path(runtime_dir).resolve() if runtime_dir else None;game=Path(game_dir).resolve();pins=pins or profile();package=Path(package)
    exe=game/pins['executable']
    if not exe.is_file() or sha256(exe)!=pins['sha256']:raise ValueError('Installed executable does not match the probe profile')
    selected,excluded=[],[]
    if runtime is not None:
        if not runtime.is_dir():raise ValueError('Runtime folder not found: '+str(runtime))
        files=[p for p in runtime.rglob('*') if p.is_file()]
        if len(files)>MAX_FILES:raise ValueError('Runtime folder has more than 256 files; extract only the author runtime')
        chosen={_relative(runtime,x) for x in extra}
        for path in sorted(files):
            rel=path.relative_to(runtime).as_posix()
            (selected if rel in chosen or '/' not in rel else excluded).append(rel)
        missing=chosen-set(selected)
        if missing:raise ValueError('Requested files are not in the runtime folder: '+', '.join(sorted(missing)))
        if not any(rel.lower()=='ragepluginhook.exe' for rel in selected):raise ValueError('No RAGEPluginHook.exe at the runtime folder top level')
    elif extra:raise ValueError('--file needs --runtime-dir')
    manifest=json.loads((package/'manifest.json').read_text(encoding='utf-8'));plugin='Plugins/'+pins['plugin']
    if not sha256(package/plugin)==manifest['plugin_sha256']==pins['plugin_sha256']:
        raise ValueError('Staged plugin does not match its manifest and the probe profile')
    copies=[{'source':str(runtime/rel),'target':rel,'sha256':sha256(runtime/rel),'bytes':(runtime/rel).stat().st_size} for rel in selected]
    copies.append({'source':str(package/plugin),'target':plugin,'sha256':pins['plugin_sha256'],'bytes':(package/plugin).stat().st_size})
    # Package files the plugin needs beside the game executable (for example a Lua binding), each pinned by the manifest.
    for name,digest in sorted(manifest.get('root_files',{}).items()):
        source=package/'root'/_relative(package/'root',name)
        if '/' in name or sha256(source)!=digest:raise ValueError('Package root file missing or changed: '+name)
        copies.append({'source':str(source),'target':name,'sha256':digest,'bytes':source.stat().st_size})
    clashes=[c['target'] for c in copies if (game/c['target']).exists()]
    return {'schema_version':1,'kind':'native_read_probe_deployment_plan','game_dir':str(game),'runtime_dir':str(runtime) if runtime else None,
            'package':str(package),'executable':{'name':pins['executable'],'version':pins['version'],'sha256':pins['sha256']},
            'copies':copies,'excluded':excluded,'existing_targets':clashes,'applicable':not clashes,
            'planned_at':datetime.now().astimezone().isoformat()}


def apply(plan_value,state=STATE):
    if not plan_value.get('applicable') or plan_value.get('existing_targets'):raise ValueError('Plan would overwrite existing game files; nothing was copied')
    game=Path(plan_value['game_dir']);exe=game/plan_value['executable']['name']
    if sha256(exe)!=plan_value['executable']['sha256']:raise ValueError('Executable changed since planning')
    for c in plan_value['copies']:
        if sha256(c['source'])!=c['sha256']:raise ValueError('Source changed since planning: '+c['source'])
        if (game/c['target']).exists():raise ValueError('Target appeared since planning: '+c['target'])
    install={'schema_version':1,'kind':'native_read_probe_install','id':uuid4().hex,'game_dir':str(game),'files':[],'directories':[]}
    record=Path(state)/'installs'/(install['id']+'.json');record.parent.mkdir(parents=True,exist_ok=True)
    save=lambda:record.write_text(json.dumps(install,indent=2),encoding='utf-8')
    save()  # Written first, so an interrupted copy still lists what may need removal.
    for c in plan_value['copies']:
        target=game/c['target']
        for parent in reversed(target.relative_to(game).parents[:-1]):
            if not (game/parent).exists():(game/parent).mkdir();install['directories'].append(parent.as_posix())
        with open(c['source'],'rb') as src,open(target,'xb') as out:shutil.copyfileobj(src,out)
        if sha256(target)!=c['sha256']:raise ValueError('Copied file does not match: '+c['target'])
        install['files'].append({'target':c['target'],'sha256':c['sha256']});save()
    install['installed_at']=datetime.now().astimezone().isoformat();save()
    return record


def remove(install_path):
    install=json.loads(Path(install_path).read_text(encoding='utf-8'));game=Path(install['game_dir'])
    removed,kept=[],[]
    for f in install['files']:
        target=game/_relative(game,f['target'])
        if target.is_file() and sha256(target)==f['sha256']:target.unlink();removed.append(f['target'])
        elif target.exists():kept.append(f['target'])
    for d in reversed(install['directories']):
        folder=game/_relative(game,d)
        if folder.is_dir() and not any(folder.iterdir()):folder.rmdir()
    return {'removed':removed,'kept_changed':kept}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    sub=parser.add_subparsers(dest='command',required=True)
    e=sub.add_parser('extract');e.add_argument('--archive',required=True)
    p=sub.add_parser('plan');p.add_argument('--runtime-dir',help='extracted author runtime; omit to deploy only a package onto an existing runtime')
    p.add_argument('--game-dir',default=str(GAME));p.add_argument('--profile',default=str(EXPECTATIONS),help='probe expectations profile')
    p.add_argument('--package',default=str(PACKAGE),help='staged package with manifest.json, Plugins/ and optional root/')
    p.add_argument('--file',action='append',default=[],help='extra runtime file to copy, relative to --runtime-dir')
    a=sub.add_parser('apply');a.add_argument('--plan',required=True)
    r=sub.add_parser('remove');r.add_argument('--install',required=True)
    args=parser.parse_args(argv)
    if args.command=='extract':
        print(json.dumps({'runtime_dir':str(extract(Path(args.archive)))}));return 0
    if args.command=='plan':
        value=plan(args.runtime_dir,args.game_dir,args.file,args.package,profile(args.profile));path=STATE/'plans'/(uuid4().hex+'.json')
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2),encoding='utf-8')
        print(json.dumps({'plan':str(path),'applicable':value['applicable'],'copies':[c['target'] for c in value['copies']],
                          'excluded':value['excluded'],'existing_targets':value['existing_targets']},indent=2))
        return 0 if value['applicable'] else 1
    if args.command=='apply':
        print(json.dumps({'install':str(apply(json.loads(Path(args.plan).read_text(encoding='utf-8'))))}));return 0
    print(json.dumps(remove(args.install),indent=2));return 0


if __name__=='__main__':
    sys.exit(main())
