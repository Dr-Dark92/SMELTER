import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from database import select_database
from chats import create_chat
from chat_inference import ask
from runtime_settings import load_runtime, save_runtime, PROFILES


class RuntimeSettingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'checkout'
        self.root.mkdir()
        select_database(self.root, str(Path(self.temp.name) / 'data'))

    def test_saved_profile_persists_and_takes_precedence_over_environment(self):
        with patch.dict('os.environ', {'SMELTER_CONTEXT_LENGTH': '4096'}):
            self.assertEqual(load_runtime(self.root)['settings']['context_tokens'], 4096)
            result = save_runtime(self.root, PROFILES['office'])
            self.assertEqual(result['sources']['context_tokens'], 'saved')
            self.assertEqual(load_runtime(self.root)['settings'], PROFILES['office'])

    def test_invalid_values_do_not_replace_saved_configuration(self):
        save_runtime(self.root, PROFILES['office'])
        for key, value in [('context_tokens', True), ('timeout_seconds', 0), ('thinking', 'yes'), ('max_output_tokens', 9000), ('unknown', 123)]:
            settings = {**PROFILES['home'], key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                save_runtime(self.root, settings)
        with self.assertRaises(ValueError):
            save_runtime(self.root, {**PROFILES['office'], 'context_tokens': 2048, 'max_output_tokens': 4096})
        self.assertEqual(load_runtime(self.root)['settings'], PROFILES['office'])

    def test_inference_uses_saved_context_output_and_thinking(self):
        save_runtime(self.root, PROFILES['office'])
        cid = create_chat(self.root, 'Runtime fixture')['id']
        requests = []
        def opener(request, timeout):
            requests.append((json.loads(request.data), timeout))
            return io.BytesIO(b'{"message":{"content":"Fixture reply"}}')
        ask(self.root, cid, 'fixture', opener=opener)
        body, timeout = requests[0]
        self.assertEqual(body['options'], {'num_ctx': 16384, 'num_predict': 1024})
        self.assertFalse(body['think'])
        self.assertGreater(timeout, 890)

    def test_in_progress_turn_keeps_its_original_settings(self):
        save_runtime(self.root, PROFILES['office'])
        cid = create_chat(self.root, 'Stable settings')['id']
        bodies = []
        def opener(request, timeout):
            bodies.append(json.loads(request.data))
            if len(bodies) == 1:
                save_runtime(self.root, PROFILES['home'])
                return io.BytesIO(b'{"message":{"content":""}}')
            return io.BytesIO(b'{"message":{"content":"Fixture reply"}}')
        ask(self.root, cid, 'fixture', opener=opener)
        self.assertEqual(len(bodies), 2)
        self.assertTrue(all(body['options']['num_ctx'] == 16384 for body in bodies))
        self.assertEqual(load_runtime(self.root)['settings']['context_tokens'], 32768)

    def test_opencode_task_timeout_is_separate_and_optional_when_saving(self):
        self.assertEqual(load_runtime(self.root)['settings']['opencode_timeout_seconds'], 900)
        save_runtime(self.root, {**PROFILES['office'], 'opencode_timeout_seconds': 1500})
        # An older caller that sends only the original four settings keeps the saved task timeout.
        older = {k: v for k, v in PROFILES['home'].items() if k != 'opencode_timeout_seconds'}
        save_runtime(self.root, older)
        settings = load_runtime(self.root)['settings']
        self.assertEqual(settings['timeout_seconds'], 180)
        self.assertEqual(settings['opencode_timeout_seconds'], 1500)
        for bad in (30, 4000, True):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                save_runtime(self.root, {**older, 'opencode_timeout_seconds': bad})
        with self.assertRaisesRegex(ValueError, 'Provide all'):
            save_runtime(self.root, {'context_tokens': 8192})

    def test_opencode_task_deadline_uses_the_task_timeout(self):
        from opencode_runtime import ask as agent_ask
        source = Path(agent_ask.__code__.co_filename).read_text(encoding='utf-8')
        self.assertIn("runtime.get('opencode_timeout_seconds'", source)


class RuntimePresetUiTests(unittest.TestCase):
    def test_preset_shows_changes_and_keeps_unchanged_fields(self):
        shell = Path(__file__).with_name('dashboard_shell.js').read_text(encoding='utf-8')
        self.assertIn("'Preset changes: '", shell)
        self.assertIn("preset[key]!==undefined&&input.valueAsNumber!==preset[key]", shell)
        self.assertIn("['opencode_timeout_seconds','OpenCode task timeout (seconds)',60,3600]", shell)

    def test_direct_chat_is_the_default_engine(self):
        shell = Path(__file__).with_name('dashboard_shell.js').read_text(encoding='utf-8')
        self.assertIn("[['ollama','Ollama · direct chat'],['opencode',", shell)
