import unittest
from opencode_provider import provider_preview

PREFS = {"models": {"reasoning": "qwen3.5:9b", "lightweight": "qwen3.5:4b"}}
DISCOVERY = {"status": "connected", "models": [{"name": "qwen3.5:9b"}, {"name": "qwen3.5:4b"}]}
AGENT = {"status": "detected_unverified", "detected": True}

class ProviderPreviewTests(unittest.TestCase):
    def test_preview_only(self):
        result = provider_preview(PREFS, DISCOVERY, AGENT)
        self.assertEqual(result["status"], "preview_ready")
        self.assertFalse(result["written"])
        self.assertFalse(result["executed"])
        self.assertEqual(result["config"]["provider"]["smelter_ollama"]["options"]["baseURL"], "http://127.0.0.1:11434/v1")
        self.assertEqual(result["role_models"]["reasoning"], "smelter_ollama/qwen3.5:9b")
    def test_same_model_for_both_roles(self):
        result = provider_preview({"models": {"reasoning": "qwen3.5:9b", "lightweight": "qwen3.5:9b"}}, DISCOVERY, AGENT)
        self.assertEqual(len(result["config"]["provider"]["smelter_ollama"]["models"]), 1)
    def test_agent_missing(self):
        with self.assertRaisesRegex(ValueError, "OpenCode"):
            provider_preview(PREFS, DISCOVERY, {"status": "missing", "detected": False})
    def test_ollama_offline(self):
        with self.assertRaisesRegex(ValueError, "Ollama"):
            provider_preview(PREFS, {"status": "unavailable", "models": []}, AGENT)
    def test_model_not_installed(self):
        with self.assertRaisesRegex(ValueError, "installed"):
            provider_preview({"models": {"reasoning": "missing"}}, DISCOVERY, AGENT)
    def test_no_models_selected(self):
        with self.assertRaisesRegex(ValueError, "Configure"):
            provider_preview({"models": {}}, DISCOVERY, AGENT)

if __name__ == "__main__":
    unittest.main()
