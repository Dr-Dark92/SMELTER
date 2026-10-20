"""Read host counters and Ollama allocation without launching programs/models."""
import ctypes
import json
import os
import threading
from pathlib import Path
from urllib.request import urlopen

_lock = threading.Lock()
_previous = None


def _cpu_times():
    if os.name == "nt":
        idle, kernel, user = (ctypes.c_ulonglong() for _ in range(3))
        if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
            raise OSError("GetSystemTimes failed")
        return idle.value, kernel.value + user.value
    values = list(map(int, Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
    return values[3] + values[4], sum(values)


def cpu_status():
    global _previous
    try:
        current = _cpu_times()
        with _lock:
            previous, _previous = _previous, current
        if previous is None or current[1] <= previous[1]:
            return {"status": "sampling", "logical_cpus": os.cpu_count()}
        usage = 100 * (1 - (current[0] - previous[0]) / (current[1] - previous[1]))
        return {"status": "ready", "percent": round(max(0, min(100, usage)), 1), "logical_cpus": os.cpu_count()}
    except (OSError, ValueError, IndexError, AttributeError):
        return {"status": "unavailable"}


def memory_status():
    try:
        if os.name == 'nt':
            class Memory(ctypes.Structure):
                _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong)] + [
                    (name, ctypes.c_ulonglong) for name in ('total', 'available', 'page_total', 'page_available', 'virtual_total', 'virtual_available', 'extended')]
            data = Memory()
            data.length = ctypes.sizeof(data)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(data)):
                raise OSError('Memory counters unavailable')
            total, available = data.total, data.available
        else:
            counters = {line.split(':')[0]: int(line.split()[1]) * 1024
                        for line in Path('/proc/meminfo').read_text().splitlines() if ':' in line}
            total, available = counters['MemTotal'], counters['MemAvailable']
        used = total - available
        return {'status': 'ready', 'total_bytes': total, 'available_bytes': available,
                'used_bytes': used, 'percent': round(100 * used / total, 1)}
    except (OSError, ValueError, KeyError, AttributeError, ZeroDivisionError):
        return {'status': 'unavailable'}


def model_status(opener=urlopen):
    try:
        with opener('http://127.0.0.1:11434/api/ps', timeout=1) as response:
            raw = response.read(256 * 1024 + 1)
        if len(raw) > 256 * 1024:
            raise ValueError('Model status response too large')
        models = json.loads(raw)['models']
        if not isinstance(models, list):
            raise ValueError('Invalid model status')
        loaded = []
        for model in models:
            size, gpu = model.get('size', 0), model.get('size_vram', 0)
            if type(size) is not int or type(gpu) is not int or min(size, gpu) < 0:
                raise ValueError('Invalid allocation counters')
            loaded.append({'name': str(model.get('name', 'Unknown'))[:160],
                           'allocated_bytes': size, 'gpu_allocated_bytes': gpu})
        return {'status': 'ready', 'models': loaded,
                'gpu_allocated_bytes': sum(x['gpu_allocated_bytes'] for x in loaded)}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {'status': 'unavailable', 'models': []}


def resource_status():
    models = model_status()
    return {'cpu': cpu_status(), 'memory': memory_status(), 'models': models,
            'gpu': {'status': models['status'], 'metric': 'ollama_model_allocation',
                    'allocated_bytes': models.get('gpu_allocated_bytes'),
                    'utilization_percent': None,
                    'note': 'Ollama-reported model allocation, not GPU utilization; integrated GPUs share system RAM.'}}
