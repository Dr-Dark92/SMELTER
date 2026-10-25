"""First-run values written by tools/setup/configure_defaults.py.

The dashboard uses them only for configuration that was never saved; anything
saved in the dashboard always wins, so re-running deployment cannot override a
user's choice. A missing or invalid file simply means built-in defaults apply.
"""
from __future__ import annotations
import json
from pathlib import Path

PATH = '.smelter/deployment-defaults.json'


def load(root) -> dict | None:
    path = Path(root) / PATH
    if not path.is_file() or path.is_symlink():
        return None
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) and value.get('schema_version') == 1 else None


def config(root, name: str) -> dict | None:
    """Return the deployment value for one configuration name, unvalidated."""
    value = load(root)
    if value is None:
        return None
    if name == 'extensions.json' and isinstance(value.get('extensions'), list):
        return {'schema_version': 1, 'enabled': list(value['extensions'])}
    if name == 'model_preferences.json' and isinstance(value.get('model'), str) and value['model']:
        return {'schema_version': 1, 'models': {'reasoning': value['model'], 'lightweight': value['model']}}
    if name == 'runtime_settings.json':
        from runtime_settings import PROFILES
        profile = PROFILES.get(value.get('runtime_profile'))
        return {'schema_version': 1, 'settings': dict(profile)} if profile else None
    if name == 'sandbox.json' and isinstance(value.get('images'), dict):
        return {'schema_version': 1, **{key: value['images'].get(key) for key in ('python_image', 'node_image', 'opencode_image', 'cpp_image', 'engine_image') if key not in ('cpp_image', 'engine_image') or key in value['images']}}
    return None


def storage_directory(root) -> str | None:
    value = load(root)
    directory = value.get('storage_directory') if value else None
    return directory if isinstance(directory, str) and Path(directory).is_absolute() else None
