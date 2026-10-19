import unittest
from aero_classifier import classify_task


class AeroClassifierTests(unittest.TestCase):
    def test_coding(self):
        self.assertEqual(classify_task("Refactor Python function")["primary_domain"], "coding")

    def test_3d(self):
        self.assertEqual(classify_task("Fix Blender armature and bone weights")["primary_domain"], "3d_modeling")

    def test_modding(self):
        self.assertEqual(classify_task("Build a GTA game mod")["primary_domain"], "game_modding")

    def test_reverse_engineering(self):
        self.assertEqual(classify_task("Use Ghidra to disassemble firmware")["primary_domain"], "reverse_engineering")

    def test_automation(self):
        self.assertEqual(classify_task("Automate scheduled job workflow")["primary_domain"], "automation")

    def test_unknown(self):
        self.assertEqual(classify_task("Hello")["classification"], "unknown")

    def test_tie_not_forced(self):
        result = classify_task("Python Blender")
        self.assertEqual(result["classification"], "ambiguous")
        self.assertIsNone(result["primary_domain"])

    def test_complexity(self):
        self.assertEqual(classify_task("Refactor a distributed system")["complexity_hint"], "high")

    def test_no_execution(self):
        result = classify_task("Automate a pipeline")
        self.assertFalse(result["tools_executed"])
        self.assertFalse(result["model_switch_performed"])

    def test_invalid_input(self):
        for value in (None, "", " " * 3, "x" * 4001):
            with self.subTest(value=str(value)[:10]):
                with self.assertRaises(ValueError):
                    classify_task(value)


if __name__ == "__main__":
    unittest.main()
