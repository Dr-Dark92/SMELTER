import json
from pathlib import Path
import tempfile
import shutil
import unittest
from unittest.mock import patch
from configure_melty_cli import configure, ROOT


class NativeCliProfileTests(unittest.TestCase):
    def test_native_tool_mode_is_explicit_backed_up_and_keeps_thinking_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'opencode.json'
            original = {'provider': {'ollama': {'models': {'qwen3.5:35b-a3b-128k': {
                'limit': {'context': 131072, 'output': 8192}, 'options': {'fixture': 'keep'},
                'variants': {'existing': {'fixture': 'keep'}}}}}, 'other': {'options': {'apiKey': 'fixture-secret'}}},
                'mcp': {'smelter': {'type': 'local'}, 'rea': {'type': 'local', 'command': ['keep-rea']}},
                'permission': {'melty_*': 'allow'}}
            path.write_text(json.dumps(original)); before = path.read_bytes()
            preview = configure(ROOT, config=path, native_tool_mode=True)
            self.assertEqual(path.read_bytes(), before)
            self.assertNotIn('fixture-secret', json.dumps(preview))
            applied = configure(ROOT, config=path, native_tool_mode=True, apply=True)
            self.assertEqual(Path(applied['backup']).read_bytes(), before)
            saved = json.loads(path.read_text()); model = saved['provider']['ollama']['models']['qwen3.5:35b-a3b-128k']
            self.assertEqual(model['options'], {'fixture': 'keep', 'reasoningEffort': 'none'})
            self.assertTrue(model['reasoning'])
            self.assertEqual(model['variants']['smelter-thinking']['reasoningEffort'], 'medium')
            self.assertEqual(model['variants']['existing'], {'fixture': 'keep'})
            self.assertEqual(model['limit'], {'context': 131072, 'output': 8192})
            self.assertEqual(saved['provider']['other'], original['provider']['other'])
            self.assertEqual(saved['permission'], original['permission'])
            self.assertEqual(saved['mcp']['rea'], original['mcp']['rea'])
            self.assertFalse(configure(ROOT, config=path, native_tool_mode=True, apply=True)['config_changed'])
            self.assertFalse(configure(ROOT, config=path, apply=True)['config_changed'])

    def test_native_tool_mode_preserves_conflicting_user_variant(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'opencode.json'
            value = {'provider': {'ollama': {'models': {'qwen3.5:35b-a3b-128k': {
                'limit': {'context': 131072}, 'variants': {'smelter-thinking': {'user': True}}}}}},
                'mcp': {'smelter': {'type': 'local'}}}
            path.write_text(json.dumps(value)); before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'variant differs'):
                configure(ROOT, config=path, native_tool_mode=True, apply=True)
            self.assertEqual(path.read_bytes(), before)

    def test_compact_rea_preview_apply_and_repeat_preserve_backend_and_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'opencode.json'
            command = ['node', '/existing/rea.mjs', 'mcp']
            rea = {'type': 'local', 'command': command, 'environment': {'REA_ANALYSIS_PROVIDER': 'ghidra'}, 'timeout': 900000, 'enabled': True}
            original = {'provider': {'ollama': {'models': {'qwen3.5:35b-a3b-128k': {'limit': {'context': 131072, 'output': 8192}}}}},
                        'mcp': {'smelter': {'type': 'local'}, 'rea': rea}, 'permission': {'melty_*': 'allow'}}
            path.write_text(json.dumps(original)); before = path.read_bytes()
            preview = configure(ROOT, config=path, compact_rea=True)
            self.assertEqual(path.read_bytes(), before); self.assertEqual(preview['rea_gateway']['tool_count'], 3)
            applied = configure(ROOT, config=path, compact_rea=True, apply=True)
            self.assertEqual(Path(applied['backup']).read_bytes(), before)
            saved = json.loads(path.read_text()); actual = saved['mcp']['rea']
            self.assertEqual(actual['command'][3:], command)
            self.assertEqual({k: v for k, v in actual.items() if k != 'command'}, {k: v for k, v in rea.items() if k != 'command'})
            self.assertEqual(saved['permission'], original['permission'])
            self.assertEqual(saved['provider'], original['provider'])
            repeat = configure(ROOT, config=path, compact_rea=True, apply=True)
            self.assertFalse(repeat['config_changed']); self.assertIsNone(repeat['backup'])

    def test_compact_rea_refuses_to_bypass_per_operation_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'opencode.json'
            value = {'provider': {'ollama': {'models': {'qwen3.5:35b-a3b-128k': {'limit': {'context': 131072}}}}},
                     'mcp': {'smelter': {'type': 'local'}, 'rea': {'type': 'local', 'command': ['existing-rea']}},
                     'permission': {'rea_open_binary': 'deny'}}
            path.write_text(json.dumps(value)); before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, 'per-operation'):
                configure(ROOT, config=path, compact_rea=True, apply=True)
            self.assertEqual(path.read_bytes(), before)

    def test_inventory_scope_requires_registered_read_policy_and_is_previewable(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'game';folder.mkdir();path=Path(tmp)/'opencode.json'
            original={'provider':{'ollama':{'models':{'qwen3.5:35b-a3b-128k':{'limit':{'context':131072}}}}},'mcp':{'smelter':{'type':'local'}}}
            path.write_text(json.dumps(original));before=path.read_bytes()
            with patch('access_policy.current') as policy:
                policy.return_value.authorize.side_effect=ValueError('not registered')
                with self.assertRaisesRegex(ValueError,'not registered'):configure(ROOT,config=path,inventory_root=folder,apply=True)
            self.assertEqual(path.read_bytes(),before)
            with patch('access_policy.current') as policy:
                preview=configure(ROOT,config=path,inventory_root=folder)
                policy.return_value.authorize.assert_called_once_with(str(folder.resolve()),'read')
                self.assertEqual(path.read_bytes(),before)
                self.assertEqual(preview['mcp_grants']['inventory_root'],str(folder.resolve()))
                configure(ROOT,config=path,inventory_root=folder,apply=True)
            saved=json.loads(path.read_text());grants=json.loads(saved['mcp']['smelter']['environment']['SMELTER_MCP_GRANTS'])
            self.assertEqual(grants['inventory_root'],str(folder.resolve()))

    def test_dashboard_alignment_is_explicit_backed_up_and_preserves_other_settings(self):
        from database import select_database
        from runtime_settings import load_runtime, save_runtime
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); root = base / 'project'; root.mkdir()
            for name in ('game-modding', 'mod-validation', 'universal-modder', 'engine-archive', 'project-knowledge'):
                destination = root / 'skills' / name / 'SKILL.md'
                destination.parent.mkdir(parents=True)
                shutil.copyfile(ROOT / 'skills' / name / 'SKILL.md', destination)
            select_database(root, str(base / 'data'))
            before = {**load_runtime(root)['settings'], 'context_tokens':16384, 'timeout_seconds':300}
            save_runtime(root, before)
            path = base / 'opencode.json'
            path.write_text(json.dumps({'provider':{'ollama':{'models':{'qwen3.5:35b-a3b-128k':{'limit':{'context':131072}}}}},'mcp':{'smelter':{'type':'local'}}}))
            configure(root, config=path)
            self.assertEqual(load_runtime(root)['settings'], before)
            result = configure(root, config=path, apply=True, align_dashboard=True)
            after = load_runtime(root)['settings']
            self.assertEqual((after['context_tokens'], after['max_output_tokens']), (131072, 8192))
            self.assertEqual(after['timeout_seconds'], 300)
            self.assertEqual(json.loads(Path(result['dashboard_runtime']['backup']).read_text()), before)

    def test_preview_apply_and_repeat_preserve_unrelated_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'opencode.json'
            data = {'provider':{'ollama':{'models':{'qwen3.5:35b-a3b-128k':{'limit':{'context':131072,'output':2048}}}},
                                'other':{'options':{'apiKey':'fixture-private'}}},
                    'mcp':{'smelter':{'type':'local','environment':{'SMELTER_MCP_GRANTS':'{"melty_read":true}'}},
                           'rea':{'command':['existing-rea']}}, 'permission':{'bash':'ask'}}
            path.write_text(json.dumps(data))
            original = path.read_bytes()
            preview = configure(ROOT, config=path)
            self.assertEqual(path.read_bytes(), original)
            self.assertNotIn('fixture-private', json.dumps(preview))
            done = configure(ROOT, config=path, apply=True)
            result = json.loads(path.read_text())
            self.assertEqual(Path(done['backup']).read_bytes(), original)
            self.assertEqual(result['mcp']['rea'], data['mcp']['rea'])
            self.assertEqual(result['provider']['other'], data['provider']['other'])
            self.assertEqual(result['permission'], data['permission'])
            self.assertEqual(result['provider']['ollama']['models']['qwen3.5:35b-a3b-128k']['limit']['output'], 8192)
            self.assertEqual(result['provider']['ollama']['models']['qwen3.5:35b-a3b-128k']['limit']['context'], 131072)
            repeat = configure(ROOT, config=path, apply=True)
            self.assertIsNone(repeat['backup'])
            self.assertFalse(repeat['config_changed'])

    def test_existing_different_skill_blocks_all_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'opencode.json'
            path.write_text(json.dumps({'provider':{'ollama':{'models':{'qwen3.5:35b-a3b-128k':{'limit':{'context':131072}}}}},'mcp':{'smelter':{'type':'local'}}}))
            destination = path.parent / 'skills/game-modding/SKILL.md'
            destination.parent.mkdir(parents=True)
            destination.write_text('existing user instruction')
            before = path.read_bytes()
            with self.assertRaises(ValueError):configure(ROOT, config=path, apply=True)
            self.assertEqual(path.read_bytes(), before)
