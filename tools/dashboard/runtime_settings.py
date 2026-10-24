"""Local chat runtime settings. Saving does not load or execute a model."""
import os
from config_store import load_config, save_config

# timeout_seconds bounds one model turn (a direct reply or one OpenCode relay
# request); opencode_timeout_seconds bounds a whole multi-turn OpenCode task.
DEFAULTS = {'context_tokens': 32768, 'max_output_tokens': 2048, 'timeout_seconds': 180,
            'opencode_timeout_seconds': 900, 'thinking': True}
LIMITS = {'context_tokens': (2048, 131072), 'max_output_tokens': (128, 8192), 'timeout_seconds': (30, 1800),
          'opencode_timeout_seconds': (60, 3600)}
# Added after the original four settings; older callers may omit it when saving.
OPTIONAL = {'opencode_timeout_seconds'}
# office/home/frontend remain for existing saved settings and scripts; the
# dashboard offers low/medium/high plus Custom (the user's own values).
PROFILES = {
    'office': {'context_tokens': 16384, 'max_output_tokens': 1024, 'timeout_seconds': 900,
               'opencode_timeout_seconds': 900, 'thinking': False},
    'home': dict(DEFAULTS),
    # Hardware profiles chosen by deployment (system-requirements.json defaults).
    # low: no NVIDIA GPU, CPU inference is slow, so smaller context and longer bounds.
    'low': {'context_tokens': 16384, 'max_output_tokens': 1024, 'timeout_seconds': 600,
            'opencode_timeout_seconds': 1800, 'thinking': False},
    # medium: GPU up to 6 GB; verified on a 4 GB GTX 1050 Ti with qwen3.5:4b (2026-10-24).
    'medium': {'context_tokens': 32768, 'max_output_tokens': 1024, 'timeout_seconds': 300,
               'opencode_timeout_seconds': 900, 'thinking': False},
    # high: GPU over 6 GB up to 16 GB running qwen3.5:9b.
    'high': {'context_tokens': 32768, 'max_output_tokens': 2048, 'timeout_seconds': 180,
             'opencode_timeout_seconds': 900, 'thinking': True},
    # extreme: GPU over 16 GB and 32 GB+ RAM running qwen3.5:35b-a3b (not yet measured on a rig).
    'extreme': {'context_tokens': 65536, 'max_output_tokens': 4096, 'timeout_seconds': 300,
                'opencode_timeout_seconds': 1800, 'thinking': True},
    'frontend': {**DEFAULTS, 'max_output_tokens':4096,'timeout_seconds':900},
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
    # Precedence: saved in the dashboard > SMELTER_CONTEXT_LENGTH > deployment defaults > built in.
    from config_store import config_source
    stored = load_config(root, 'runtime_settings.json')['settings']
    source = config_source(root, 'runtime_settings.json') if stored else 'default'
    settings = dict(DEFAULTS)
    sources = {key: 'default' for key in settings}
    settings.update(stored)
    sources.update({key: source for key in stored})
    if source != 'saved' and os.environ.get('SMELTER_CONTEXT_LENGTH'):
        try:
            settings['context_tokens'] = int(os.environ['SMELTER_CONTEXT_LENGTH'])
        except ValueError as exc:
            raise ValueError('SMELTER_CONTEXT_LENGTH must be an integer') from exc
        sources['context_tokens'] = 'environment'
    validate(settings)
    if settings['max_output_tokens'] >= settings['context_tokens']:
        raise ValueError('Response limit must be smaller than the context length')
    return {'settings': settings, 'sources': sources, 'profiles': PROFILES,
            'applies_to': 'New direct and managed OpenCode tasks; active tasks keep their admitted settings'}


def save_runtime(root, value):
    validate(value)
    if not (set(DEFAULTS) - OPTIONAL) <= set(value):
        raise ValueError('Provide all runtime settings')
    if set(DEFAULTS) - set(value):
        # Keep the saved (or default) value of settings an older caller omitted.
        value = {**{key: load_runtime(root)['settings'][key] for key in set(DEFAULTS) - set(value)}, **value}
    if value['max_output_tokens'] >= value['context_tokens']:
        raise ValueError('Response limit must be smaller than the context length')
    save_config(root, 'runtime_settings.json', {'schema_version': 1, 'settings': value})
    return load_runtime(root)
