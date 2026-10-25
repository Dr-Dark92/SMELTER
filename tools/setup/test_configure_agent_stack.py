"""An existing measured Qwen runtime must survive repeat engine setup."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import configure_agent_stack


class AgentRuntimePreservationTests(unittest.TestCase):
    def test_repeat_setup_preserves_saved_128k_profile(self):
        from database import select_database
        from runtime_settings import load_runtime, save_runtime
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); root = base / 'project'; root.mkdir()
            (root / '.smelter/tooling/rea').mkdir(parents=True)
            ghidra = base / 'ghidra'; ghidra.mkdir()
            select_database(root, str(base / 'data'))
            with patch('ghidra_connection.status', return_value={'status':'installed','home':str(ghidra)}):
                first = configure_agent_stack.configure(root, apply=True)
                self.assertEqual(first['runtime']['context_tokens'], 16384)
                measured = {**load_runtime(root)['settings'], 'context_tokens':131072, 'max_output_tokens':8192}
                save_runtime(root, measured)
                second = configure_agent_stack.configure(root, apply=True)
                self.assertEqual(second['runtime'], measured)
                self.assertEqual(load_runtime(root)['settings'], measured)
