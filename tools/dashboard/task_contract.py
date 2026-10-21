"""One immutable admission configuration and terminal outcome for both engines."""
import copy
import hashlib
import json


def configuration(root):
    from config_store import load_config
    from runtime_settings import load_runtime
    value={'model':load_config(root,'model_preferences.json')['models'].get('reasoning','qwen3.5:9b'),
            'runtime':copy.deepcopy(load_runtime(root)['settings'])}
    value['revision']=hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
    return value


OUTPUT_LIMIT_ERROR = 'Model output limit reached; response is partial'


def generation_limited(reason):
    return reason == 'length'


def outcome(cancelled=False, error=None, partial=False):
    state='cancelled' if cancelled else 'partial' if error and partial else 'error' if error else 'completed'
    return {'status':state,'error':str(error)[:1000] if error else None,'cancelled':bool(cancelled)}


def job_state(result):
    state=result.get('status','completed') if isinstance(result,dict) else 'completed'
    return {'completed':'done','partial':'partial','error':'error','cancelled':'cancelled'}.get(state,'error')
