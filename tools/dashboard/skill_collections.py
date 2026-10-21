"""GitHub collection installation: preview all selected manifests, then approve batch.

Only SKILL.md is fetched and stored. No scripts or dependencies are executed.
"""
from __future__ import annotations
import re
from github_skill_discovery import discover_github_skill, parse_github_skill
from skill_manager import _paths, _state, _write_state
from skill_manifest import parse_skill_manifest

ID = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
MAX_BATCH = 40


def _validate(repo_url, selected):
    owner, repo, _, path = parse_github_skill(repo_url)
    if "/blob/" in repo_url or path != "SKILL.md":
        raise ValueError("Use repository root URL")
    if not isinstance(selected, list) or not 1 <= len(selected) <= MAX_BATCH:
        raise ValueError("Select 1-40 skills")
    if any(not isinstance(item, dict) or not isinstance(item.get("url"), str)
           or not isinstance(item.get("sha256"), str) or not isinstance(item.get("id"), str)
           for item in selected):
        raise ValueError("Invalid skill selection")
    ids = [x["id"] for x in selected]
    if any(not ID.fullmatch(x) for x in ids) or any(not re.fullmatch(r"[a-f0-9]{64}",x["sha256"]) for x in selected):
        raise ValueError("Invalid skill IDs or discovery digests")
    for item in selected:
        selected_owner, selected_repo, _, selected_path = parse_github_skill(item["url"])
        if (selected_owner, selected_repo) != (owner, repo) or not selected_path.endswith("SKILL.md"):
            raise ValueError("Skill source differs from collection repository")
    return owner, repo


def install_collection(root, repo_url, selected, approval=False, discover=discover_github_skill):
    if approval is not True:
        raise ValueError("Explicit approval required")
    owner, repo = _validate(repo_url, selected)
    collection = re.sub(r"[^a-z0-9_-]", "-", (owner + "-" + repo).lower())[:64].strip("-")
    if not ID.fullmatch(collection):
        raise ValueError("Invalid collection identifier")
    from python_tools import _plain_path
    from skill_duplicates import installed,digest
    _,base=_paths(root);collections=_plain_path(base/'collections');folder=_plain_path(collections/collection)
    if folder.exists() and not folder.is_dir():raise ValueError('Collection path is not a directory')
    identities,contents=installed(root);checked=[];skipped=[];seen=set()
    for item in selected:
        identity=collection+'/'+item['id']
        if identity in identities or item['id'] in seen or (folder/item['id']).exists():
            skipped.append({'id':item['id'],'reason':'identity_exists','existing_id':identity});continue
        seen.add(item['id']);manifest=discover(item['url'])
        if manifest['sha256']!=item['sha256']:raise ValueError('Skill changed since preview: '+item['id'])
        if not parse_skill_manifest(manifest['content'])['valid']:raise ValueError('Invalid manifest: '+item['id'])
        fingerprint=digest(manifest['content'])
        if fingerprint in contents:
            skipped.append({'id':item['id'],'reason':'duplicate_content','existing_id':contents[fingerprint]});continue
        contents[fingerprint]=identity;checked.append((item['id'],manifest['content']))
    if checked:
        from skills_catalog import catalog_skills
        catalog=catalog_skills(root)
        if catalog['capacity_used']+len(checked)>catalog['capacity']:
            raise ValueError('Collection would exceed the 256-manifest installed catalogue; select a smaller batch. Nothing was imported.')
        collections.mkdir(parents=True,exist_ok=True);created_group=not folder.exists();folder.mkdir(exist_ok=True);created=[]
        try:
            for name,content in checked:
                child=_plain_path(folder/name);child.mkdir();created.append(child)
                with (child/'SKILL.md').open('x',encoding='utf-8',newline='') as stream:stream.write(content)
            state=_state(root)
            for name,_ in checked:state[collection+'/'+name]=False
            _write_state(root,state)
        except Exception:
            for child in reversed(created):
                (child/'SKILL.md').unlink(missing_ok=True);child.rmdir()
            if created_group:folder.rmdir()
            raise
    return {'collection':collection,'count':len(checked),'installed':[name for name,_ in checked],
            'skipped':skipped,'skipped_count':len(skipped),'enabled':False,'source':repo_url,
            'status':'installed' if checked else 'unchanged'}
