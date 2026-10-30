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
    def test_native_reader_and_generic_registry_reuse_fixed_operator_fixtures(self):
        for name in ['gta_entity_reader','entity_identity_registry']:
            value=CATALOG[name]
            self.assertTrue(value['operator_only']);self.assertFalse(value['mcp_exposed'])
            self.assertFalse(value['game_runtime_verified']);self.assertEqual(value['dependencies'],[])
            for key in ['fixture','documentation']:
                self.assertTrue((CATALOG_PATH.parent/value[key]).is_file())
        registry=CATALOG['entity_identity_registry']
        self.assertIn('one_zero_failure_summary_matching_pass_lines',registry['checked_evidence'])
        self.assertTrue((CATALOG_PATH.parent/registry['checker']).is_file())
        self.assertEqual(CATALOG['gta_entity_reader']['bounds']['fixture_seconds'],10)

    def test_managed_lua_uses_pinned_native_runtime_and_operator_fixture_only(self):
        value=CATALOG['managed_lua_host']
        self.assertTrue(value['operator_only']);self.assertFalse(value['mcp_exposed'])
        self.assertFalse(value['game_runtime_verified']);self.assertEqual(value['dependencies'],[])
        self.assertEqual(value['sdk']['version'],'1.4.11')
        for key in ['module','check','tests','documentation']:
            self.assertTrue((CATALOG_PATH.parent/value[key]).is_file())
        pins=json.loads((CATALOG_PATH.parent/'tools/setup/managed-sdk-lock.json').read_text())
        self.assertFalse(pins['sdks']['keralua']['files']['lua54.dll']['reference'])
        self.assertTrue(pins['sdks']['keralua']['files']['KeraLua.dll']['reference'])

    def test_managed_development_is_operator_only_and_development_sdk_is_not_redistributed(self):
        value=CATALOG['managed_plugin_development']
        self.assertTrue(value['operator_only']);self.assertFalse(value['mcp_exposed'])
        self.assertFalse(value['executes_artifacts']);self.assertFalse(value['sdk']['redistribute'])
        self.assertTrue(value['sdk']['development_only']);self.assertEqual(value['dependencies'],[])
        for key in ['module','sdk_installer','sdk_lock']:self.assertTrue((CATALOG_PATH.parent/value[key]).is_file())
        for path in value['tests']:self.assertTrue((CATALOG_PATH.parent/path).is_file())
        for key in ['manifest','documentation']:self.assertTrue((CATALOG_PATH.parent/value['read_probe'][key]).is_file())
        self.assertFalse(value['read_probe']['runtime_installed'])

    def test_runtime_probe_verification_is_read_only_and_operator_only(self):
        value=CATALOG['runtime_probe_verification']
        self.assertTrue(value['operator_only']);self.assertFalse(value['mcp_exposed'])
        self.assertFalse(value['executes_artifacts']);self.assertFalse(value['extracts_archives'])
        self.assertFalse(value['game_runtime_verified']);self.assertEqual(value['dependencies'],[])
        for path in [value['verifier'],value['inventory'],value['documentation'],*value['tests'],*value['profiles']]:
            self.assertTrue((CATALOG_PATH.parent/path).is_file(),path)
        self.assertIn('deployed_plugin_sha256',value['checked_evidence'])
        self.assertIn('exact_loader_report_path',value['checked_evidence'])

    def test_file_is_at_repository_root(self):
        self.assertEqual(CATALOG_PATH.name, "system-requirements.json")
        self.assertTrue((CATALOG_PATH.parent / "REQUIREMENTS.md").is_file())

    def test_modules_read_the_file(self):
        self.assertEqual(set(check_requirements.TOOLS), set(CATALOG["tools"]))
        self.assertEqual(set(profiles.PROFILES), set(CATALOG["profiles"]))
        self.assertEqual(install_actions.WINGET_IDS,
                         {n: t["winget"] for n, t in CATALOG["tools"].items() if "winget" in t})

    def test_native_progress_uses_existing_runtime_and_a_read_only_source(self):
        value = CATALOG['native_progress']
        self.assertEqual(value['dependencies'], [])
        self.assertEqual(value['transport'], 'SSE')
        self.assertEqual(value['endpoint'], 'http://127.0.0.1:4096')
        self.assertTrue(value['read_only'])
        self.assertTrue((CATALOG_PATH.parent / value['module']).is_file())
        self.assertTrue((CATALOG_PATH.parent / value['activity_module']).is_file())
        self.assertIn('read-only', value['supplemental_transport'].lower())

    def test_task_trace_declares_websocket_and_existing_runtime_only(self):
        value = CATALOG['task_trace']
        self.assertEqual(value['dependencies'], [])
        self.assertEqual(value['transport'], 'WebSocket')
        self.assertTrue(value['read_only'])
        for key in ('module', 'socket_module', 'ui_module'):
            self.assertTrue((CATALOG_PATH.parent / value[key]).is_file())
        self.assertEqual(value['bounds']['quiet_warning_seconds'], 120)
        self.assertIn('never fabricated', value['identity'])

    def test_trace_workbench_declares_modules_and_no_new_dependencies(self):
        value = CATALOG['task_trace_workbench']
        self.assertEqual(value['dependencies'], [])
        for key in ('graph_module', 'ui_module', 'artifact_ui_module', 'history_module', 'artifact_module'):
            self.assertTrue((CATALOG_PATH.parent / value[key]).is_file())
        self.assertIn('not installed', value['optional_layers']['graphify'])

    def test_watchdog_declares_bounded_retries_and_no_new_dependencies(self):
        value=CATALOG['task_watchdog']
        self.assertEqual(value['dependencies'],[]);self.assertEqual(value['max_retries'],3)
        self.assertTrue(value['private_prompt'])
        for module in value['modules']+[value['setup']]:self.assertTrue((CATALOG_PATH.parent/module).is_file())

    def test_frozen_acceptance_is_controller_owned_and_uses_existing_sandbox(self):
        value=CATALOG['frozen_acceptance']
        self.assertEqual(value['dependencies'],[])
        self.assertFalse(value['model_editable'])
        self.assertEqual(value['bounds']['checks_entity_policy_v1'],30)
        self.assertEqual(value['bounds']['checks_predator_controller_v1'],52)
        self.assertEqual(value['bounds']['checks_provider_admission_v1'],26)
        self.assertEqual(value['bounds']['checks_predator_system_v1'],20)
        self.assertIn('tools/dashboard/acceptance/provider_admission_v1.lua',value['verifiers'])
        generated=value['test_scaffold']
        self.assertEqual(generated['dependencies'],[])
        self.assertTrue(generated['proposal_only'])
        self.assertTrue(generated['protected_acceptance_independent'])
        for path in [generated['module'],generated['setup']]:self.assertTrue((CATALOG_PATH.parent/path).is_file())
        self.assertIn('--migrate',value['migrate'])
        self.assertEqual(value['scaffold']['tool'],'scaffold_contract_subject');self.assertTrue((CATALOG_PATH.parent/value['scaffold']['module']).is_file())
        self.assertIn('predator-system-v1',value['scaffold']['contracts'])
        gate=CATALOG['coding_edit_safety']['lua_syntax_gate']
        self.assertIn('never executes',gate['parser']);self.assertEqual(gate['exempt'],['propose_coding_restore'])
        for module in [value['module'],value['register']]+value['verifiers']:self.assertTrue((CATALOG_PATH.parent/module).is_file())

    def test_recovery_guardrails_declares_local_runtime_and_bounded_retries(self):
        value=CATALOG['recovery_guardrails']
        self.assertEqual(value['dependencies'],[])
        self.assertEqual(value['mcp_work_window'],{'calls':128,'seconds':900})
        self.assertEqual(value['safe_retries']['writes'],0)
        for module in value['modules']+[value['configure']]:self.assertTrue((CATALOG_PATH.parent/module).is_file())

    def test_coding_edit_safety_uses_builtin_runtime_and_bounded_checkpoints(self):
        value=CATALOG['coding_edit_safety']
        self.assertEqual(value['dependencies'],[])
        self.assertIn('propose_coding_edits',value['tools'])
        self.assertEqual(value['limits']['edits_per_file'],16)
        self.assertTrue((CATALOG_PATH.parent/value['module']).is_file())

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

    def test_ecc_bridge_is_declared_and_uses_the_verified_bundle(self):
        from install_ecc_bridge import verified_bundle
        step = CATALOG['setup']['ecc_bridge']
        lock, _, files, _ = verified_bundle(CATALOG_PATH.parent)
        self.assertEqual(step['revision'], lock['revision'])
        self.assertEqual(step['kind'], 'python_script')
        self.assertTrue((CATALOG_PATH.parent / step['script']).is_file())
        self.assertIn('ecc_bridge', CATALOG['profiles']['qwen35b_agent']['setup'])
        self.assertEqual(CATALOG['profiles']['ecc_coding']['setup'], ['ecc_bridge'])
        self.assertEqual(len(lock['skills']), 13)
        self.assertTrue(all(path.name == 'LICENSE' or path.suffix == '.md' for path in files))

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
