"""Graph resolution tests: avoid inventing calls or including nested bodies."""
import tempfile
import unittest
from pathlib import Path
from build_system_graph import build


class GraphTests(unittest.TestCase):
    def test_nested_ownership_aliases_and_shadowed_parameters(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'a.py').write_text('def helper(): pass\ndef outer():\n def inner(): helper()\n return inner\ndef shadow(helper): helper()\n')
            (root/'b.py').write_text('from a import helper as run\ndef caller(): run()\n')
            graph=build(root,['a.py','b.py'],'fixture')
            calls={(e['source'],e['target']) for e in graph['edges'] if e['type']=='calls'}
            self.assertIn(('a.py::outer.inner','a.py::helper'),calls)
            self.assertIn(('b.py::caller','a.py::helper'),calls)
            self.assertNotIn(('a.py::outer','a.py::helper'),calls)
            self.assertNotIn(('a.py::shadow','a.py::helper'),calls)
            self.assertIn({'source':'a.py::shadow','expression':'helper','line':5},graph['unresolved_calls'])

    def test_duplicate_module_names_prefer_importing_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for directory in ('one','two'):
                (root/directory).mkdir();(root/directory/'helper.py').write_text('def run(): pass\n')
            (root/'one/main.py').write_text('from helper import run\ndef go(): run()\n')
            graph=build(root,['one/helper.py','two/helper.py','one/main.py'],'fixture')
            self.assertTrue(any(e['source']=='one/main.py::go' and e['target']=='one/helper.py::run' for e in graph['edges']))

    def test_powershell_does_not_confuse_java_function_type_with_declaration(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'a.ps1').write_text('Function f; long size;\nFunction f=lookup();\nfunction Real-Helper { return 1 }\n')
            graph=build(root,['a.ps1'],'fixture')
            self.assertEqual([s['symbol'] for s in graph['symbols']],['Real-Helper'])

    def test_framework_hook_is_candidate_not_deleted(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'a.py').write_text('class Handler:\n def do_GET(self): return 1\n')
            graph=build(root,['a.py'],'fixture')
            self.assertTrue(graph['symbols'][0]['no_static_incoming'])
            self.assertIn('does not prove',graph['limitations'][2])


if __name__=='__main__':unittest.main()
