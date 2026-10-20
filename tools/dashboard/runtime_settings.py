"""Local chat runtime settings. Saving does not load or execute a model."""
import os
from config_store import load_config, save_config

DEFAULTS = {'context_tokens': 32768, 'max_output_tokens': 2048, 'timeout_seconds': 180, 'thinking': True}
LIMITS = {'context_tokens': (2048, 131072), 'max_output_tokens': (128, 8192), 'timeout_seconds': (30, 1800)}
PROFILES = {
    'office': {'context_tokens': 16384, 'max_output_tokens': 1024, 'timeout_seconds': 900, 'thinking': False},
    'home': dict(DEFAULTS),
}


def validate(value):
    if not isinstance(value, dict) or set(value) - set(DEFAULTS):
        raise ValueError('Unknown runtime setting')
    for key, item in value.items():
        if key == 'thinking':
            if type(item) is not bool:
                raise ValueError('Thinking must be boolean')
        elif type(item) is not int or not LIMITS[key][0] <= item <= LIMITS[key][1]:
            raise ValueError(key + ' must be an integer between ' + str(LIMITS[key][0]) + ' and ' + str(LIMITS[key][1]))


def load_runtime(root):
    stored = load_config(root, 'runtime_settings.json')['settings']
    settings = dict(DEFAULTS)
    sources = {key: 'default' for key in settings}
    if 'context_tokens' not in stored and os.environ.get('SMELTER_CONTEXT_LENGTH'):
        try:
            settings['context_tokens'] = int(os.environ['SMELTER_CONTEXT_LENGTH'])
        except ValueError as exc:
            raise ValueError('SMELTER_CONTEXT_LENGTH must be an integer') from exc
        sources['context_tokens'] = 'environment'
    settings.update(stored)
    sources.update({key: 'saved' for key in stored})
    validate(settings)
    if settings['max_output_tokens'] >= settings['context_tokens']:
        raise ValueError('Response limit must be smaller than the context length')
    return {'settings': settings, 'sources': sources, 'profiles': PROFILES,
            'applies_to': 'New SMELTER chat requests only; active jobs and OpenCode are unchanged'}


def save_runtime(root, value):
    validate(value)
    if set(value) != set(DEFAULTS):
        raise ValueError('Provide all runtime settings')
    if value['max_output_tokens'] >= value['context_tokens']:
        raise ValueError('Response limit must be smaller than the context length')
    save_config(root, 'runtime_settings.json', {'schema_version': 1, 'settings': value})
    return load_runtime(root)
