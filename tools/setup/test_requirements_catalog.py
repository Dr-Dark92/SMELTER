"""system-requirements.json drives the scanner, profiles and winget queue."""
import json
import tempfile
import unittest
from pathlib import Path
from requirements_catalog import CATALOG, CATALOG_PATH, load
import check_requirements
import install_actions
import profiles


class RequirementsCatalogTests(unittest.TestCase):
    def test_file_is_at_repository_root(self):
        self.assertEqual(CATALOG_PATH.name, "system-requirements.json")
        self.assertTrue((CATALOG_PATH.parent / "REQUIREMENTS.md").is_file())

    def test_modules_read_the_file(self):
        self.assertEqual(set(check_requirements.TOOLS), set(CATALOG["tools"]))
        self.assertEqual(set(profiles.PROFILES), set(CATALOG["profiles"]))
        self.assertEqual(install_actions.WINGET_IDS,
                         {n: t["winget"] for n, t in CATALOG["tools"].items() if "winget" in t})

    def test_opencode_agent_profile_needs_wsl_and_docker(self):
        self.assertEqual(set(profiles.PROFILES["opencode_agent"]["requires"]), {"ollama", "wsl", "docker"})
        self.assertEqual(install_actions.WINGET_IDS["docker"], "Docker.DockerDesktop")
        self.assertEqual(install_actions.WINGET_IDS["wsl"], "Microsoft.WSL")

    def _load(self, data):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "system-requirements.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return load(path)

    def test_profile_with_unknown_tool_rejected(self):
        data = {"schema_version": 1, "tools": {}, "profiles": {"vanilla": {"requires": ["nope"]}}}
        with self.assertRaisesRegex(ValueError, "unknown tools"):
            self._load(data)

    def test_tool_without_check_rejected(self):
        data = {"schema_version": 1, "tools": {"x": {"policy": "optional"}}, "profiles": {"vanilla": {"requires": []}}}
        with self.assertRaisesRegex(ValueError, "check command"):
            self._load(data)

    def test_unknown_schema_rejected(self):
        with self.assertRaisesRegex(ValueError, "schema"):
            self._load({"schema_version": 2})


if __name__ == "__main__":
    unittest.main()
