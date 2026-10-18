"""Installation queue safety tests (never run winget)."""
import unittest
from unittest.mock import patch
from install_actions import build_actions
from setup_web import DependencyInstaller

PREVIEW = {"profiles": ["vanilla", "game_modding"],
           "dependencies": [{"name": "blender", "status": "missing"},
                            {"name": "ffmpeg", "status": "missing"},
                            {"name": "7z", "status": "missing"}]}

class InstallActionTests(unittest.TestCase):
    def test_allowlisted_exact_package(self):
        with patch("install_actions.sys.platform", "win32"), patch("install_actions.shutil.which", return_value="winget.exe"):
            plan = build_actions(PREVIEW, ["blender"])
        self.assertEqual(plan["actions"][0]["command"],
                         ["winget", "install", "--id", "BlenderFoundation.Blender", "--exact", "--source", "winget"])

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
