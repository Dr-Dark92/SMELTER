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
        self.assertEqual(set(profiles.PROFILES["opencode_agent"]["requires"]), {"ollama", "node", "wsl", "docker"})
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

    def test_msvc_installs_with_the_cpp_workload(self):
        msvc = CATALOG["tools"]["msvc"]
        self.assertEqual(msvc["winget"], "Microsoft.VisualStudio.2022.BuildTools")
        # Without the override, winget installs Build Tools with no compiler.
        self.assertIn("--add Microsoft.VisualStudio.Workload.VCTools", msvc["winget_override"])
        self.assertNotIn("--quiet", msvc["winget_override"])  # the installer stays visible
        self.assertIn("Microsoft.VisualStudio.Component.VC.Tools.x86.x64", msvc["check"])
        self.assertEqual(set(profiles.PROFILES["native_game_mods"]["requires"]), {"git", "docker"})
        self.assertIn("image_cpp", CATALOG["profiles"]["native_game_mods"]["setup"])

    def test_cli_toolchain_and_candidates_are_declared_separately(self):
        entries = CATALOG['modding_cli']['tools']
        self.assertEqual(entries['lua']['status'], 'provided_by_image_cpp')
        self.assertEqual(entries['repak']['status'], 'existing_adapter')
        self.assertEqual(entries['retoc']['adapter'], 'inspect_engine_archive')
        self.assertEqual(entries['unity_data_tool']['setup'], 'engine_cli')
        self.assertEqual(CATALOG['setup']['image_cpp']['image'], 'smelter-cpp:2')

    def test_cpp_test_image_is_built_and_selectable(self):
        step = CATALOG["setup"]["image_cpp"]
        self.assertEqual((step["kind"], step["dockerfile"]), ("docker_build", "tools/dashboard/Dockerfile.cpp"))
        self.assertTrue((CATALOG_PATH.parent / step["dockerfile"]).is_file())
        self.assertEqual(CATALOG["defaults"]["images"]["cpp_image"], "image_cpp")

    def test_winget_override_needs_a_winget_id(self):
        data = {"schema_version": 1, "profiles": {"vanilla": {"requires": []}},
                "tools": {"x": {"check": ["x"], "policy": "optional", "winget_override": "--add Y"}}}
        with self.assertRaisesRegex(ValueError, "winget_override"):
            self._load(data)

    def test_npm_package_must_be_pinned(self):
        data = {"schema_version": 1, "profiles": {"vanilla": {"requires": []}},
                "tools": {"x": {"check": ["x"], "policy": "optional", "npm": "opencode-ai"}}}
        with self.assertRaisesRegex(ValueError, "version-pinned"):
            self._load(data)

    def test_every_missing_tool_has_an_install_source(self):
        for name, tool in CATALOG["tools"].items():
            self.assertTrue("winget" in tool or "npm" in tool or "manual" in tool or name in ("npm", "powershell"), name)

    def test_documented_setup_steps_are_declared(self):
        steps = CATALOG["setup"]
        self.assertEqual(steps["mcp_sdk"]["version"], "1.30.0")
        self.assertEqual({steps[s]["image"] for s in ("image_python", "image_node", "image_opencode")},
                         {"python:3.12-alpine", "node:22-alpine", "smelter-opencode:1.19.3"})
        self.assertEqual(steps["glb_viewer"]["package"], "@google/model-viewer@4.1.0")
        self.assertEqual(steps["rea"]["package"], "rea-agents@6.7.0")
        self.assertEqual(steps["playwright"]["package"], "playwright@1.56.1")
        self.assertIn("image_node", steps["image_opencode"]["after"])
        self.assertEqual(steps["ghidra"]["script"], "tools/bootstraps/Setup-Smelter-Ghidra.ps1")
        self.assertTrue((CATALOG_PATH.parent / steps["ghidra"]["script"]).is_file())
        self.assertIn("ghidra", CATALOG["profiles"]["reverse_engineering"]["setup"])

    def test_ghidra_setup_accepts_the_catalog_jdk(self):
        # The catalog installs Microsoft OpenJDK 21; the Ghidra script must find it.
        self.assertEqual(CATALOG["tools"]["java"]["winget"], "Microsoft.OpenJDK.21")
        for script in (CATALOG_PATH.parent / "tools/bootstraps").glob("*.ps1"):
            text = script.read_text(encoding="utf-8-sig")
            if r"'C:\Program Files\Eclipse Adoptium'" in text:
                self.assertIn(r"'C:\Program Files\Microsoft'", text, script.name)

    def test_opencode_profile_includes_its_images(self):
        setup = CATALOG["profiles"]["opencode_agent"]["setup"]
        self.assertTrue({"mcp_sdk", "ollama_model", "image_opencode", "image_node"} <= set(setup))
        # Docker needs the Virtual Machine Platform active before any image step.
        self.assertLess(setup.index("wsl_platform"), setup.index("image_node"))

    def test_setup_step_kind_and_fields_validated(self):
        base = {"schema_version": 1, "tools": {}, "profiles": {"vanilla": {"requires": []}}}
        with self.assertRaisesRegex(ValueError, "unknown kind"):
            self._load({**base, "setup": {"x": {"kind": "curl"}}})
        with self.assertRaisesRegex(ValueError, "needs dockerfile"):
            self._load({**base, "setup": {"x": {"kind": "docker_build", "image": "a:1"}}})
        with self.assertRaisesRegex(ValueError, "version-pinned"):
            self._load({**base, "setup": {"x": {"kind": "npm_prefix", "prefix": "p", "package": "@google/model-viewer"}}})
        with self.assertRaisesRegex(ValueError, "unknown setup steps"):
            self._load({**base, "profiles": {"vanilla": {"requires": [], "setup": ["nope"]}}})

    def test_unknown_schema_rejected(self):
        with self.assertRaisesRegex(ValueError, "schema"):
            self._load({"schema_version": 2})


if __name__ == "__main__":
    unittest.main()
