"""Deployment defaults: hardware profile, model choice and the written file (no real probes)."""
import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import configure_defaults as cd
from requirements_catalog import CATALOG, load

LAPTOP_GPU = {"vendor": "nvidia", "name": "GTX 1050 Ti", "vram_mib": 4096, "driver": "582.78"}
DESKTOP_GPU = {"vendor": "nvidia", "name": "RTX 4070", "vram_mib": 12282, "driver": "582.78"}
WORKSTATION_GPU = {"vendor": "nvidia", "name": "RTX 4090", "vram_mib": 24564, "driver": "582.78", "ram_mib": 65536}
IMAGES = {"python_image": "sha256:" + "a" * 64, "node_image": "sha256:" + "b" * 64, "opencode_image": None}
STATUSES = {"ollama": {"status": "installed", "version": "ollama version is 0.40.10"},
            "blender": {"status": "installed"}, "7z": {"status": "missing"},
            "ffmpeg": {"status": "installed"}, "opencode": {"status": "detected_unverified"}}


class ProfileAndModelTests(unittest.TestCase):
    def test_hardware_picks_low_medium_high_or_extreme(self):
        self.assertEqual(cd.choose_profile({"vendor": None, "vram_mib": 0})["id"], "low")
        self.assertEqual(cd.choose_profile(LAPTOP_GPU)["id"], "medium")
        self.assertEqual(cd.choose_profile({"vram_mib": 6144})["id"], "medium")
        self.assertEqual(cd.choose_profile(DESKTOP_GPU)["id"], "high")
        self.assertEqual(cd.choose_profile({"vram_mib": 16384})["id"], "high")
        self.assertEqual(cd.choose_profile(WORKSTATION_GPU)["model"], "qwen3.5:35b-a3b")

    def test_extreme_needs_enough_system_ram(self):
        self.assertEqual(cd.choose_profile({**WORKSTATION_GPU, "ram_mib": 16384})["id"], "high")
        self.assertEqual(cd.choose_profile({**WORKSTATION_GPU, "ram_mib": None})["id"], "extreme")
        # Windows reports a "32 GB" machine as slightly under 32768 MiB.
        self.assertEqual(cd.choose_profile({**WORKSTATION_GPU, "ram_mib": 32498})["id"], "extreme")

    def test_named_profiles_and_custom(self):
        self.assertEqual(cd.profile_by_id("extreme")["runtime_profile"], "extreme")
        self.assertIsNone(cd.profile_by_id("custom"))
        with self.assertRaisesRegex(ValueError, "Known: low, medium, high, extreme, custom"):
            cd.profile_by_id("ultra")

    def test_model_must_be_installed_or_warned(self):
        medium = cd.choose_profile(LAPTOP_GPU)
        self.assertEqual(cd.choose_model(medium, ["qwen3.5:4b"]), ("qwen3.5:4b", []))
        model, warnings = cd.choose_model(medium, ["llama3:8b"])
        self.assertEqual(model, "qwen3.5:4b")
        self.assertIn("install_missing.ps1", warnings[0])
        self.assertIn("not running", cd.choose_model(medium, None)[1][0])

    def test_fallback_is_the_largest_installed_model_that_fits(self):
        extreme = cd.profile_by_id("extreme")
        model, warnings = cd.choose_model(extreme, ["qwen3.5:4b", "qwen3.5:9b"])
        self.assertEqual(model, "qwen3.5:9b")
        self.assertIn("not installed", warnings[0])
        # A weak GPU never falls back to a model larger than its profile.
        self.assertEqual(cd.choose_model(cd.profile_by_id("medium"), ["qwen3.5:35b-a3b"])[0], "qwen3.5:4b")


class DetectionTests(unittest.TestCase):
    def test_largest_gpu_is_used(self):
        output = "Intel Arc, 2048, 31.0\nNVIDIA RTX 4070, 12282, 582.78\n"
        run = lambda argv, timeout=20: subprocess.CompletedProcess(argv, 0, output, "")
        with patch.object(cd, "_find", return_value="nvidia-smi"):
            gpu = cd.detect_gpu(run)
        self.assertEqual((gpu["name"], gpu["vram_mib"], gpu["driver"]), ("NVIDIA RTX 4070", 12282, "582.78"))

    def test_missing_or_failing_nvidia_smi(self):
        with patch.object(cd, "_find", return_value=None):
            self.assertEqual(cd.detect_gpu()["vram_mib"], 0)
        with patch.object(cd, "_find", return_value="nvidia-smi"):
            self.assertEqual(cd.detect_gpu(lambda argv, timeout=20: None)["vram_mib"], 0)

    def test_extensions_follow_installed_tools(self):
        self.assertEqual(cd.enabled_extensions(STATUSES), ["blender", "ffmpeg", "ollama", "opencode"])


class BuildTests(unittest.TestCase):
    def build(self, gpu=LAPTOP_GPU, installed=("qwen3.5:4b",)):
        return cd.build(gpu=gpu, installed=list(installed), images=IMAGES, statuses=STATUSES)

    def test_report_matches_what_the_dashboard_reads(self):
        report = self.build()
        self.assertEqual((report["schema_version"], report["model"], report["runtime_profile"]), (1, "qwen3.5:4b", "medium"))
        self.assertEqual(report["profile_source"], "detected")
        self.assertEqual(report["images"], IMAGES)
        self.assertEqual(report["extensions"], ["blender", "ffmpeg", "ollama", "opencode"])
        self.assertTrue(all(row["matches"] for row in report["versions"]))

    def test_old_driver_and_version_drift_are_warned(self):
        report = cd.build(gpu={**LAPTOP_GPU, "driver": "528.79"}, installed=["qwen3.5:4b"], images=IMAGES,
                          statuses={**STATUSES, "ollama": {"status": "installed", "version": "ollama version is 0.39.0"}})
        self.assertTrue(any("528.79" in w for w in report["warnings"]))
        self.assertTrue(any("0.39.0" in w for w in report["warnings"]))

    def test_desktop_gets_9b_and_high_profile(self):
        report = self.build(DESKTOP_GPU, ("qwen3.5:9b", "qwen3.5:4b"))
        self.assertEqual((report["model"], report["runtime_profile"]), ("qwen3.5:9b", "high"))

    def test_custom_leaves_model_and_runtime_to_the_user(self):
        report = cd.build(gpu=LAPTOP_GPU, installed=["qwen3.5:4b"], images=IMAGES, statuses=STATUSES, profile_id="custom")
        self.assertEqual((report["hardware_profile"], report["model"], report["runtime_profile"]), ("custom", None, "custom"))
        self.assertEqual(report["profile_source"], "chosen")
        self.assertEqual(report["images"], IMAGES)

    def test_write_replaces_the_file_atomically(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".smelter" / "deployment-defaults.json"
            cd.write(self.build(), path)
            cd.write(self.build(DESKTOP_GPU, ("qwen3.5:9b",)), path)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["model"], "qwen3.5:9b")
            self.assertEqual([p.name for p in path.parent.iterdir()], ["deployment-defaults.json"])


class CatalogDefaultsTests(unittest.TestCase):
    def _load(self, data):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "system-requirements.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            return load(path)

    def test_last_hardware_profile_must_be_unlimited(self):
        data = copy.deepcopy(CATALOG)
        data["defaults"]["hardware_profiles"][-1]["max_vram_mib"] = 99999
        with self.assertRaisesRegex(ValueError, "no VRAM limit"):
            self._load(data)

    def test_default_images_must_name_docker_steps(self):
        data = copy.deepcopy(CATALOG)
        data["defaults"]["images"]["python_image"] = "mcp_sdk"
        with self.assertRaisesRegex(ValueError, "Docker setup step"):
            self._load(data)

    def test_model_step_is_chosen_from_hardware(self):
        self.assertEqual(CATALOG["setup"]["ollama_model"]["model"], "hardware")


if __name__ == "__main__":
    unittest.main()
