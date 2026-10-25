import unittest
from pathlib import Path
from unittest.mock import patch
from modding_catalog import catalog
from tool_registry import schemas, execute_builtin
from python_tools import permissions


class ModdingCatalogTests(unittest.TestCase):
    root = Path(__file__).resolve().parents[2]

    def test_unreal_filter_includes_universal_but_not_unity_tools(self):
        with patch('subprocess.Popen', side_effect=AssertionError('catalog must not launch processes')):
            result = catalog(self.root, {'engine':'ue5'})
        names = {t['id'] for t in result['tools']}
        self.assertTrue({'repak', 'retoc', 'ghidra'} <= names)
        self.assertNotIn('unity_data_tool', names)
        self.assertFalse(result['executes_tools'])

    def test_unknown_engine_and_commands_are_rejected(self):
        for arguments in ({'engine':'unknown'}, {'command':'cmd.exe'}):
            with self.assertRaises(ValueError):catalog(self.root, arguments)

    def test_catalog_does_not_expand_grants(self):
        with self.assertRaises(ValueError):execute_builtin(self.root, {}, 'modding_tool_catalog', {})
        base = permissions(self.root, {})
        self.assertNotIn('modding_tool_catalog', {t['function']['name'] for t in schemas(base)})
        self.assertIn('modding_tool_catalog', {t['function']['name'] for t in schemas({**base, 'coding_workspace':True})})
