"""Profile resolver tests; no subprocesses or downloads."""
import unittest
from profiles import catalog, resolve

SCAN = {"tools": [
    {"name": "git", "status": "installed", "version": "2.55"},
    {"name": "node", "status": "installed", "version": "24"},
    {"name": "npm", "status": "detected_unverified", "version": None},
    {"name": "gh", "status": "installed", "version": "2"},
    {"name": "ollama", "status": "installed", "version": "0.40"},
    {"name": "blender", "status": "missing", "version": None},
    {"name": "ffmpeg", "status": "missing", "version": None},
    {"name": "7z", "status": "missing", "version": None},
]}

class ProfilesTests(unittest.TestCase):
    def test_catalog_has_vanilla(self):
        self.assertIn("vanilla", [p["id"] for p in catalog()])

    def test_empty_selection_means_vanilla(self):
        result = resolve([], SCAN)
        self.assertEqual(result["profiles"], ["vanilla"])
        self.assertEqual(result["dependencies"], [])

    def test_deferred_tools_never_auto_install(self):
        result = resolve(["game_modding"], SCAN)
        self.assertEqual([d["name"] for d in result["dependencies"]], ["7z", "blender", "ffmpeg"])
        self.assertEqual(result["install_actions"], [])
        self.assertTrue(all(d["action"] == "review_manually" for d in result["dependencies"]))

    def test_deduplicates_profiles(self):
        self.assertEqual(resolve(["developer", "developer"], SCAN)["profiles"], ["vanilla", "developer"])

    def test_reject_unknown(self):
        with self.assertRaises(ValueError):
            resolve(["arbitrary"], SCAN)

    def test_reject_wrong_type(self):
        with self.assertRaises(ValueError):
            resolve("developer", SCAN)

if __name__ == "__main__":
    unittest.main()
