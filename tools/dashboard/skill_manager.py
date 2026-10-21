"""Persistent SMELTER skill management.

Bundled skills remain immutable; managed skills live under .smelter/managed-skills.
Only SKILL.md text is accepted. No code, archives, or remote installation.
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path
from skill_manifest import parse_skill_manifest

ID = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
MAX_CONTENT = 48 * 1024


def _paths(root):
    root = Path(root)
    from python_tools import _plain_path
    _plain_path(root / '.smelter' / 'skill-state.json')
    _plain_path(root / '.smelter' / 'managed-skills')
    return root / ".smelter" / "skill-state.json", root / ".smelter" / "managed-skills"


def _state(root):
    path, _ = _paths(root)
    from python_tools import _plain_path
    _plain_path(path)
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or any(not isinstance(k, str) or not isinstance(v, bool) for k, v in data.items()):
        raise ValueError("Invalid skill state")
    return data


def enabled_map(root):
    return _state(root)


def _write_state(root, data):
    path, _ = _paths(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("Unsafe state path")
    temp = path.with_suffix(".tmp")
    if temp.is_symlink():
        raise ValueError("Unsafe temporary state path")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(temp, path)


def _safe_id(name):
    if not isinstance(name, str) or not ID.fullmatch(name):
        raise ValueError("Invalid skill ID")


def add_skill(root, name, content, approval=False):
    _safe_id(name)
    if approval is not True:
        raise ValueError("Explicit approval required")
    if not isinstance(content, str) or not content.strip() or len(content.encode("utf-8")) > MAX_CONTENT:
        raise ValueError("Invalid skill content or size")
    if not parse_skill_manifest(content)["valid"]:
        raise ValueError("SKILL.md requires recognizable name and description")
    state_path, base = _paths(root)
    bundled = Path(root) / "skills" / name
    if bundled.exists() or bundled.is_symlink():
        raise ValueError("Bundled skill ID is reserved")
    if base.is_symlink():
        raise ValueError("Unsafe managed skills directory")
    base.mkdir(parents=True, exist_ok=True)
    folder = base / name
    if folder.exists() or folder.is_symlink():
        raise ValueError("Skill already exists")
    folder.mkdir()
    (folder / "SKILL.md").write_text(content, encoding="utf-8")
    return {"id": name, "added": True, "enabled": True}


def set_skill_enabled(root, name, enabled, approval=False):
    if isinstance(name, str) and "/" in name:
        parts = name.split("/")
        if len(parts) != 2:
            raise ValueError("Invalid collection skill ID")
        for part in parts:
            _safe_id(part)
    else:
        _safe_id(name)
    if not isinstance(enabled, bool) or approval is not True:
        raise ValueError("Explicit approval and boolean enabled value required")
    from skills_catalog import catalog_skills
    known = {s["id"]: s for s in catalog_skills(root)["skills"]}
    if name not in known:
        raise ValueError("Skill not found")
    if enabled and known[name]["status"] != "ready":
        raise ValueError("Skill is not ready")
    state = _state(root)
    state[name] = enabled
    _write_state(root, state)
    return {"id": name, "enabled": enabled}


def _removal(root,name):
    from skills_catalog import catalog_skills
    from skill_runtime import skill_folder
    from python_tools import _plain_path
    skill=next((s for s in catalog_skills(root)['skills'] if s['id']==name),None)
    if not skill or not skill['removable'] or skill['status']=='identity_conflict':raise ValueError('Only unambiguous user-imported skills can be removed')
    folder=_plain_path(skill_folder(Path(root),skill));contents=list(folder.iterdir())
    if len(contents)!=1 or contents[0].name!='SKILL.md' or not _plain_path(contents[0]).is_file():raise ValueError('Managed skill contains unexpected files; removal blocked')
    return folder


def remove_skill(root,name,approval=False):
    if approval is not True:raise ValueError('Explicit approval required')
    folder=_removal(root,name);(folder/'SKILL.md').unlink();folder.rmdir()
    state=_state(root);state.pop(name,None);_write_state(root,state)
    return {'id':name,'removed':True}


def manage_many(root,ids,operation,approval=False):
    if approval is not True:raise ValueError('Explicit approval required')
    if not isinstance(ids,list) or not ids or len(ids)>256 or any(not isinstance(i,str) for i in ids) or len(set(ids))!=len(ids):raise ValueError('Select 1–256 distinct skill IDs')
    if operation not in ('enable','disable','remove'):raise ValueError('Unknown bulk skill operation')
    from skills_catalog import catalog_skills
    known={s['id']:s for s in catalog_skills(root)['skills']}
    if any(i not in known for i in ids):raise ValueError('A selected skill no longer exists; refresh the table')
    if operation=='enable' and any(known[i]['status']!='ready' for i in ids):raise ValueError('All selected skills must be ready before enabling')
    if operation!='remove':
        state=_state(root)
        for sid in ids:state[sid]=operation=='enable'
        _write_state(root,state)
        return {'operation':operation,'changed':ids,'errors':[]}
    # Validate every selected folder before destructive work; report partial IO failures.
    folders=[(sid,_removal(root,sid)) for sid in ids];changed=[];errors=[]
    for sid,folder in folders:
        try:(folder/'SKILL.md').unlink();folder.rmdir();changed.append(sid)
        except OSError as exc:errors.append({'id':sid,'error':str(exc)[:300]})
    state=_state(root)
    for sid in changed:state.pop(sid,None)
    try:_write_state(root,state)
    except OSError as exc:errors.append({'id':'skill-state','error':str(exc)[:300]})
    return {'operation':operation,'changed':changed,'errors':errors}
