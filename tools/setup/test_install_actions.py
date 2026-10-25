"""Installation queue safety tests (never run winget)."""
import subprocess
import unittest
from unittest.mock import patch
from install_actions import build_actions
from setup_web import DependencyInstaller, winget_list_state, WINGET_NO_APPLICATIONS_FOUND

PREVIEW = {"profiles": ["vanilla", "game_modding"],
           "dependencies": [{"name": "blender", "status": "missing"},
                            {"name": "ffmpeg", "status": "missing"},
                            {"name": "7z", "status": "missing"}]}

class InstallActionTests(unittest.TestCase):
    def test_winget_not_found_is_safe_to_install(self):
        result = subprocess.CompletedProcess(["winget", "list"], WINGET_NO_APPLICATIONS_FOUND, "", "")
        self.assertEqual(winget_list_state(result, "BlenderFoundation.Blender"), "absent")

    def test_winget_signed_not_found(self):
        result = subprocess.CompletedProcess(["winget", "list"], WINGET_NO_APPLICATIONS_FOUND - (1 << 32), "", "")
        self.assertEqual(winget_list_state(result, "BlenderFoundation.Blender"), "absent")

    def test_winget_existing_package_skips_install(self):
        result = subprocess.CompletedProcess(["winget", "list"], 0, "BlenderFoundation.Blender 4.0", "")
        self.assertEqual(winget_list_state(result, "BlenderFoundation.Blender"), "installed")

    def test_winget_unexpected_failure_blocks(self):
        result = subprocess.CompletedProcess(["winget", "list"], 1, "", "network failure")
        with self.assertRaisesRegex(RuntimeError, "refusing potential upgrade"):
            winget_list_state(result, "BlenderFoundation.Blender")

    def test_winget_unrecognized_success_blocks(self):
        result = subprocess.CompletedProcess(["winget", "list"], 0, "unexpected output", "")
        with self.assertRaisesRegex(RuntimeError, "manual review"):
            winget_list_state(result, "BlenderFoundation.Blender")

    def test_allowlisted_exact_package(self):
        with patch("install_actions.sys.platform", "win32"), patch("install_actions.shutil.which", return_value="winget.exe"):
            plan = build_actions(PREVIEW, ["blender"])
        self.assertEqual(plan["actions"][0]["command"],
                         ["winget", "install", "--id", "BlenderFoundation.Blender", "--exact", "--source", "winget"])

    def test_catalog_override_is_one_argument(self):
        preview = {"profiles": ["vanilla", "native_game_mods"], "dependencies": [{"name": "msvc", "status": "missing"}]}
        with patch("install_actions.sys.platform", "win32"), patch("install_actions.shutil.which", return_value="winget.exe"):
            command = build_actions(preview, ["msvc"])["actions"][0]["command"]
        self.assertEqual(command[:7], ["winget", "install", "--id", "Microsoft.VisualStudio.2022.BuildTools", "--exact", "--source", "winget"])
        self.assertEqual(command[7], "--override")
        self.assertEqual(len(command), 9)
        self.assertIn("Microsoft.VisualStudio.Workload.VCTools", command[8])

    def test_unselected_dependency_rejected(self):
        with self.assertRaisesRegex(ValueError, "not part"):
            build_actions(PREVIEW, ["git"])

    def test_duplicates_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            build_actions(PREVIEW, ["blender", "blender"])

    def test_no_auto_install_without_winget(self):
        with patch("install_actions.sys.platform", "win32"), patch("install_actions.shutil.which", return_value=None):
            with self.assertRaisesRegex(ValueError, "winget"):
                build_actions(PREVIEW, ["blender"])

    def test_already_installed_rejected(self):
        with self.assertRaisesRegex(ValueError, "Already installed"):
            build_actions({"dependencies": [{"name": "git", "status": "installed"}]}, ["git"])

    def test_empty_queue_safe(self):
        self.assertEqual(build_actions(PREVIEW, [])["actions"], [])

    def test_apply_requires_exact_approval(self):
        installer = DependencyInstaller()
        with self.assertRaisesRegex(ValueError, "approval"):
            installer.apply("invalid", True)
        with self.assertRaisesRegex(ValueError, "approval"):
            installer.apply("invalid", False)

if __name__ == "__main__":
    unittest.main()
