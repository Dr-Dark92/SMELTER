"""Read-only duplicate identity/content checks for instruction imports."""
import hashlib
from pathlib import Path


def digest(content):
    return hashlib.sha256(content.replace('\r\n','\n').replace('\r','\n').encode('utf-8')).hexdigest()


def installed(root):
    from skills_catalog import catalog_skills
    from skill_runtime import skill_folder
    from python_tools import _plain_path
    identities=set();contents={}
    for skill in catalog_skills(root)['skills']:
        identities.add(skill['id'])
        try:
            manifest=_plain_path(skill_folder(Path(root),skill)/'SKILL.md')
            if manifest.stat().st_size<=65536:contents.setdefault(digest(manifest.read_text(encoding='utf-8')),skill['id'])
        except (ValueError,OSError,UnicodeError):continue
    return identities,contents
