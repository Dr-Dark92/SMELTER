"""Deployment defaults fill never-saved configuration; saved values always win."""
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from config_store import config_source, load_config, save_config
from database import select_database
from runtime_settings import PROFILES, load_runtime
from task_contract import configuration

PY = 'sha256:' + 'a' * 64
NODE = 'sha256:' + 'b' * 64
DEPLOYED = {'schema_version': 1, 'model': 'qwen3.5:4b', 'runtime_profile': 'medium',
            'extensions': ['ollama', 'opencode'], 'storage_directory': None,
            'images': {'python_image': PY, 'node_image': NODE, 'opencode_image': None}}


class DeploymentDefaultsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        self.root = self.temp / 'checkout'
        self.root.mkdir()

    def deploy(self, value=DEPLOYED):
        path = self.root / '.smelter' / 'deployment-defaults.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding='utf-8')

    def select(self):
        select_database(self.root, str(self.temp / 'data'))

    def test_without_a_file_built_in_defaults_apply(self):
        self.select()
        self.assertEqual(load_config(self.root, 'extensions.json')['enabled'], [])
        self.assertEqual(config_source(self.root, 'extensions.json'), 'default')
        self.assertEqual(configuration(self.root)['model'], 'qwen3.5:9b')

    def test_deployment_fills_every_unsaved_setting(self):
        self.select();self.deploy()
        self.assertEqual(load_config(self.root, 'extensions.json')['enabled'], ['ollama', 'opencode'])
        self.assertEqual(load_config(self.root, 'sandbox.json')['python_image'], PY)
        self.assertEqual(configuration(self.root)['model'], 'qwen3.5:4b')
        runtime = load_runtime(self.root)
        self.assertEqual(runtime['settings'], PROFILES['medium'])
        self.assertEqual(set(runtime['sources'].values()), {'deployment'})
        for name in ('extensions.json', 'model_preferences.json', 'runtime_settings.json', 'sandbox.json'):
            self.assertEqual(config_source(self.root, name), 'deployment', name)

    def test_saved_values_win_and_redeploying_cannot_override_them(self):
        self.select();self.deploy()
        save_config(self.root, 'model_preferences.json', {'schema_version': 1, 'models': {'reasoning': 'qwen3.5:9b'}})
        self.deploy({**DEPLOYED, 'model': 'other:1b'})
        self.assertEqual(configuration(self.root)['model'], 'qwen3.5:9b')
        self.assertEqual(config_source(self.root, 'model_preferences.json'), 'saved')
        self.assertEqual(config_source(self.root, 'extensions.json'), 'deployment')

    def test_invalid_deployment_values_are_ignored(self):
        self.select()
        self.deploy({**DEPLOYED, 'extensions': ['unknown'], 'runtime_profile': 'missing',
                     'images': {'python_image': 'python:latest'}})
        self.assertEqual(load_config(self.root, 'extensions.json')['enabled'], [])
        self.assertEqual(load_config(self.root, 'sandbox.json')['python_image'], None)
        self.assertEqual(load_runtime(self.root)['sources']['context_tokens'], 'default')
        self.deploy({'schema_version': 2, 'model': 'x'})
        self.assertEqual(config_source(self.root, 'model_preferences.json'), 'default')

    def test_environment_context_beats_deployment_but_not_saved(self):
        self.select();self.deploy()
        with patch.dict('os.environ', {'SMELTER_CONTEXT_LENGTH': '8192'}):
            runtime = load_runtime(self.root)
            self.assertEqual(runtime['settings']['context_tokens'], 8192)
            self.assertEqual(runtime['sources']['context_tokens'], 'environment')
            self.assertEqual(runtime['sources']['timeout_seconds'], 'deployment')
            from runtime_settings import save_runtime
            save_runtime(self.root, PROFILES['office'])
            self.assertEqual(load_runtime(self.root)['settings']['context_tokens'], 16384)

    def test_first_run_suggests_the_deployment_storage_folder(self):
        from startup import startup_report
        folder = str(self.temp / 'suggested-data')
        self.deploy({**DEPLOYED, 'storage_directory': folder})
        report = startup_report(self.root, lambda: {'tools': []}, lambda *a: {'status': 'disabled'})
        self.assertEqual((report['status'], report['suggested_directory']), ('setup_required', folder))
        self.deploy({**DEPLOYED, 'storage_directory': 'relative/path'})
        self.assertIsNone(startup_report(self.root, None, None)['suggested_directory'])

    def test_missing_model_names_where_to_fix_it(self):
        from ollama_turn import OllamaTurn
        from types import SimpleNamespace
        def opener(request, timeout):
            raise HTTPError(request.full_url, 404, 'Not Found', {}, io.BytesIO(b'{"error":"model not found"}'))
        turn = OllamaTurn('qwen3.5:9b', [{'role': 'system', 'content': 'x'}, {'role': 'user', 'content': 'hi'}],
                          SimpleNamespace(call_limit=4, events=[]), PROFILES['medium'], opener, None)
        with self.assertRaisesRegex(ValueError, r'qwen3\.5:9b is not installed.*Settings → Ollama models'):
            turn.infer(False)


if __name__ == '__main__':
    unittest.main()
