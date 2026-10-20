import io
import json
import unittest
from unittest.mock import patch
import resource_metrics as metrics


class ResourceMetricsTests(unittest.TestCase):
    def test_cpu_uses_counter_differences(self):
        with patch.object(metrics, '_previous', None), patch.object(metrics, '_cpu_times', side_effect=[(100, 200), (120, 300)]):
            self.assertEqual(metrics.cpu_status()['status'], 'sampling')
            self.assertEqual(metrics.cpu_status()['percent'], 80)

    def test_memory_available_is_used_instead_of_free(self):
        with patch.object(metrics.os, 'name', 'posix'), patch('resource_metrics.Path') as path:
            path.return_value.read_text.return_value = 'MemTotal: 1000 kB\nMemAvailable: 600 kB\nMemFree: 100 kB\n'
            result = metrics.memory_status()
        self.assertEqual(result['percent'], 40)
        self.assertEqual(result['available_bytes'], 600 * 1024)

    def test_ollama_allocations_are_not_utilization(self):
        opener = lambda *a, **kw: io.BytesIO(json.dumps({'models': [{'name': 'fixture', 'size': 100, 'size_vram': 80}]}).encode())
        self.assertEqual(metrics.model_status(opener)['gpu_allocated_bytes'], 80)

    def test_missing_ollama_and_invalid_counters(self):
        def missing(*a, **kw):
            raise OSError('not listening')
        self.assertEqual(metrics.model_status(missing)['status'], 'unavailable')
        invalid = lambda *a, **kw: io.BytesIO(b'{"models":[{"size":-1}]}')
        self.assertEqual(metrics.model_status(invalid)['status'], 'unavailable')
