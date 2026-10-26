import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from skill_context import selected_context
from skill_router import route_skills
from skill_runtime import initialize

ROOT = Path(__file__).resolve().parents[2]


class CodingProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'SMELTER'
        for folder in (ROOT / 'skills').iterdir():
            if folder.is_dir() and (folder / 'SKILL.md').is_file():
                shutil.copytree(folder, self.root / 'skills' / folder.name)
        path = self.root / '.smelter/ecc-bridge.json'
        path.parent.mkdir()
        path.write_text(json.dumps({'schema_version': 1, 'enabled': True, 'automatic_coding': True}))

    def test_coding_defaults_are_loaded_and_hash_the_actual_text(self):
        result = selected_context(self.root, 'Implement a bounded helper', coding=True)
        self.assertEqual(result['selected'], ['ecc-tdd-workflow', 'ecc-verification-loop'])
        self.assertLess(len(result['text']), 6000)
        for snapshot in result['snapshots']:
            text = (self.root / 'skills' / snapshot['id'] / 'SKILL.md').read_text(encoding='utf-8')
            self.assertEqual(snapshot['sha256'], hashlib.sha256(text.encode()).hexdigest())
        self.assertNotIn('Test-Driven Development Workflow', result['text'])  # full upstream is not injected

    def test_profiles_match_concrete_task_types(self):
        expected = {
            'Debug Lua syntax and import paths': ['smelter-debugging', 'ecc-verification-loop'],
            'Implement Raptor NPC cooldown behavior': ['gameplay-testing', 'ecc-tdd-workflow'],
            'Implement a C++ ASI plugin': ['ecc-cpp-standards', 'ecc-cpp-testing'],
            'Review controller code and tests': ['ecc-code-review', 'ecc-test-review'],
            'Plan a native integration': ['ecc-planner', 'ecc-retrieval'],
        }
        for prompt, wanted in expected.items():
            with self.subTest(prompt=prompt):
                self.assertEqual(route_skills(self.root, prompt), wanted)

    def test_explicit_selection_takes_precedence(self):
        result = selected_context(self.root, 'Debug Lua syntax', selected=['ecc-code-review'], coding=True)
        self.assertEqual(result['selected'], ['ecc-code-review'])

    def test_real_direct_and_managed_bridges_receive_matching_instruction_snapshots(self):
        from database import select_database
        from chats import create_chat
        from python_tools import ToolSession
        from agent_bridge import AgentBridge
        from chat_inference import _messages
        select_database(self.root, str(self.base / 'data'))
        chat_id = create_chat(self.root, 'ECC bridge integration')['id']
        prompt = 'Debug Lua syntax in the controller'
        grants = {'coding_workspace': True}
        session = ToolSession(self.root, grants, chat_id)
        messages, selected = _messages(self.root, {'messages': []}, prompt, None, None, False, session)
        bridge = AgentBridge(self.root, chat_id, prompt, grants=grants)
        self.assertEqual(selected, ['smelter-debugging', 'ecc-verification-loop'])
        self.assertEqual(bridge.skills['selected'], selected)
        self.assertTrue(any(bridge.skills['text'] in item['content'] for item in messages))
        self.assertIn(bridge.skills['text'], bridge.instructions())
        self.assertEqual(bridge.summary()['skills'], selected_context(self.root, prompt, coding=True)['snapshots'])
        self.assertIn('smelter_run_coding_tests', bridge.summary()['tools'])
        self.assertNotIn('bash', bridge.summary()['tools'])

    def test_no_coding_grant_no_implicit_coding_instructions(self):
        self.assertEqual(selected_context(self.root, 'Implement a helper')['selected'], [])

    def test_unrelated_chat_does_not_load_coding_profiles_with_grant_available(self):
        self.assertEqual(selected_context(self.root, 'Hello there', coding=True)['selected'], [])

    def test_disabled_default_and_missing_activation_do_not_inject(self):
        path = self.root / '.smelter/ecc-bridge.json'
        path.write_text(json.dumps({'schema_version': 1, 'enabled': True, 'automatic_coding': False}))
        self.assertEqual(selected_context(self.root, 'Implement a helper', coding=True)['selected'], [])
        path.unlink()
        self.assertEqual(selected_context(self.root, 'Implement a helper', coding=True)['selected'], [])

    def test_disabled_skills_are_not_selected(self):
        (self.root / '.smelter/skill-state.json').write_text(json.dumps({'smelter-debugging': False}))
        self.assertNotIn('smelter-debugging', selected_context(self.root, 'Debug Lua syntax', coding=True)['selected'])

    def test_changed_skill_is_omitted_automatically_and_blocked_when_explicit(self):
        initialize(self.root)
        path = self.root / 'skills/ecc-tdd-workflow/SKILL.md'
        path.write_text(path.read_text() + '\nChanged instructions.\n')
        self.assertNotIn('ecc-tdd-workflow', selected_context(self.root, 'Implement a helper', coding=True)['selected'])
        with self.assertRaisesRegex(ValueError, 'restart'):
            selected_context(self.root, 'Implement a helper', selected=['ecc-tdd-workflow'], coding=True)


if __name__ == '__main__':
    unittest.main()
