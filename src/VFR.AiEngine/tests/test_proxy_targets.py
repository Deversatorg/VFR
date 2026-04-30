from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import torch


if Path("/app/vfr_ai_engine").exists():
    AI_ENGINE_DIR = Path("/app")
else:
    REPO_ROOT = Path(__file__).resolve().parents[3]
    AI_ENGINE_DIR = REPO_ROOT / "src" / "VFR.AiEngine"


def _load_module(module_name: str):
    sys.path.insert(0, str(AI_ENGINE_DIR))
    return importlib.import_module(module_name)


class ProxyTargetRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ml_pipeline = _load_module("vfr_ai_engine.measurements.proxy_targets")
        cls.measurement_optimizer = _load_module("vfr_ai_engine.measurements.optimizer")

    def test_normalize_proxy_slider_handles_percent_and_unit_inputs(self):
        normalize = self.ml_pipeline.normalize_proxy_slider

        self.assertEqual(normalize(72), 0.72)
        self.assertEqual(normalize(0.72), 0.72)
        self.assertEqual(normalize(-5), 0.0)
        self.assertEqual(normalize(140), 1.0)
        self.assertEqual(normalize(None), 0.0)

    def test_calculate_proxy_targets_is_deterministic_for_gender_profiles(self):
        exact_measurements = {
            "chest_cm": 100.0,
            "hips_cm": 96.0,
        }

        male_targets = self.ml_pipeline.calculate_proxy_targets(
            exact_measurements=exact_measurements,
            muscle_slider=72,
            fat_slider=14,
            gender="male",
        )
        female_targets = self.ml_pipeline.calculate_proxy_targets(
            exact_measurements=exact_measurements,
            muscle_slider=72,
            fat_slider=14,
            gender="female",
        )
        neutral_targets = self.ml_pipeline.calculate_proxy_targets(
            exact_measurements=exact_measurements,
            muscle_slider=72,
            fat_slider=14,
            gender="neutral",
        )

        for measured, expected in (
            (male_targets, {"shoulder_circumference_cm": 122.62, "bicep_circumference_cm": 31.04, "thigh_circumference_cm": 56.3712}),
            (female_targets, {"shoulder_circumference_cm": 115.60, "bicep_circumference_cm": 24.88, "thigh_circumference_cm": 59.0976}),
            (neutral_targets, {"shoulder_circumference_cm": 119.11, "bicep_circumference_cm": 27.96, "thigh_circumference_cm": 57.7344}),
        ):
            self.assertEqual(set(measured), set(expected))
            for measurement_name, expected_value in expected.items():
                self.assertAlmostEqual(measured[measurement_name], expected_value, places=5)

    def test_calculate_proxy_targets_changes_with_composition_mix(self):
        exact_measurements = {
            "chest_cm": 105.0,
            "hips_cm": 101.0,
        }

        muscle_heavy = self.ml_pipeline.calculate_proxy_targets(
            exact_measurements=exact_measurements,
            muscle_slider=0.9,
            fat_slider=0.1,
            gender="male",
        )
        fat_heavy = self.ml_pipeline.calculate_proxy_targets(
            exact_measurements=exact_measurements,
            muscle_slider=0.1,
            fat_slider=0.9,
            gender="male",
        )

        self.assertGreater(
            muscle_heavy["bicep_circumference_cm"],
            fat_heavy["bicep_circumference_cm"],
        )
        self.assertGreater(
            fat_heavy["thigh_circumference_cm"],
            muscle_heavy["thigh_circumference_cm"],
        )

    def test_build_profile_optimizer_targets_elevates_explicit_manual_weights(self):
        targets, weights, explicit_keys = self.ml_pipeline.build_profile_optimizer_targets(
            target_measurements={
                "chest_cm": 101.0,
                "waist_cm": 50.0,
                "hips_cm": 96.0,
                "shoulder_circumference_cm": 118.0,
                "arm_length_cm": 63.0,
            },
            measurement_weights={
                "chest_cm": 1.3,
                "waist_cm": 3.0,
                "hips_cm": 1.2,
                "shoulder_circumference_cm": 0.3,
                "arm_length_cm": 0.9,
            },
            measurement_sources={
                "chest_cm": "inferred",
                "waist_cm": "user",
                "hips_cm": "inferred",
                "shoulder_circumference_cm": "proxy_targets(muscle=0.720,fat=0.140)",
                "arm_length_cm": "user",
            },
            manual_hint_values={
                "torso_length_cm": 100.0,
                "shoulder_cm": 0.0,
            },
        )

        self.assertEqual(targets["waist_cm"], 50.0)
        self.assertEqual(weights["chest_cm"], 1.0)
        self.assertEqual(weights["waist_cm"], self.ml_pipeline.STRICT_EXPLICIT_MEASUREMENT_WEIGHT)
        self.assertEqual(weights["shoulder_circumference_cm"], 0.3)
        self.assertIn("waist_cm", explicit_keys)
        self.assertIn("arm_length_cm", explicit_keys)
        self.assertIn("torso_length_cm", explicit_keys)

    def test_convert_shoulder_width_to_circumference_cm_uses_stable_ratio(self):
        convert = self.ml_pipeline.convert_shoulder_width_to_circumference_cm

        self.assertEqual(convert(46.0), 119.6)
        self.assertEqual(convert(0.0), 0.0)
        self.assertEqual(convert(None), 0.0)

    def test_measurement_optimizer_metadata_includes_proxy_measurements(self):
        optimizer = self.measurement_optimizer

        self.assertIn("shoulder_circumference_cm", optimizer.SUPPORTED_MEASUREMENTS)
        self.assertIn("bicep_circumference_cm", optimizer.SUPPORTED_MEASUREMENTS)
        self.assertIn("thigh_circumference_cm", optimizer.SUPPORTED_MEASUREMENTS)
        self.assertEqual(optimizer.DEFAULT_MEASUREMENT_WEIGHTS["chest_cm"], 1.0)
        self.assertEqual(optimizer.DEFAULT_MEASUREMENT_WEIGHTS["waist_cm"], 1.0)
        self.assertEqual(optimizer.DEFAULT_MEASUREMENT_WEIGHTS["hips_cm"], 1.0)
        self.assertEqual(optimizer.DEFAULT_MEASUREMENT_WEIGHTS["shoulder_circumference_cm"], 0.3)
        self.assertEqual(optimizer.DEFAULT_MEASUREMENT_WEIGHTS["bicep_circumference_cm"], 0.5)
        self.assertEqual(optimizer.DEFAULT_MEASUREMENT_WEIGHTS["thigh_circumference_cm"], 0.5)
        self.assertEqual(
            optimizer.LOOP_MEASUREMENT_MAP["shoulder_circumference_cm"],
            "shoulder_circumference",
        )

    def test_constraint_weights_loosen_for_explicit_manual_targets(self):
        optimizer = self.measurement_optimizer

        shape_weight, regularization_weight, active_explicit = optimizer._resolve_constraint_weights(
            active_targets={
                "waist_cm": 50.0,
                "hips_cm": 96.0,
            },
            explicit_keys=["waist_cm", "torso_length_cm"],
            shape_preservation_weight=0.05,
            regularization_weight=0.003,
        )

        self.assertAlmostEqual(shape_weight, 0.002, places=6)
        self.assertAlmostEqual(regularization_weight, 0.0001, places=6)
        self.assertEqual(active_explicit, ["waist_cm"])

    def test_apply_proportion_warp_applies_strict_circumference_warps(self):
        optimizer = self.measurement_optimizer
        dummy_vertices = torch.zeros((1, 8, 3), dtype=torch.float32)
        dummy_joints = torch.zeros((1, 4, 3), dtype=torch.float32)
        parents = torch.tensor([-1, 0, 1, 2], dtype=torch.long)
        weights = torch.zeros((8, 4), dtype=torch.float32)

        with (
            patch.object(optimizer, "normalize_to_target_height", return_value=(dummy_vertices[0], dummy_joints[0], torch.tensor(1.0), torch.tensor(175.0))),
            patch.object(optimizer, "_prepare_parent_tensor", return_value=parents),
            patch.object(optimizer, "_prepare_weights_tensor", return_value=weights),
            patch.object(optimizer, "_warp_circumference_band", return_value=(dummy_vertices[0], 2.0)) as circumference_warp,
        ):
            _, _, applied_scales = optimizer.apply_proportion_warp(
                vertices=dummy_vertices,
                joints=dummy_joints,
                parents=parents,
                weights=weights,
                target_measurements={"waist_cm": 160.0},
                target_height_cm=175.0,
                strict_circumference_keys=["waist_cm"],
            )

        circumference_warp.assert_called_once()
        self.assertEqual(applied_scales["waist_cm"], 2.0)

    def test_calculate_measurements_exposes_proxy_loop_outputs(self):
        optimizer = self.measurement_optimizer
        dummy_vertices = torch.zeros((8, 3), dtype=torch.float32)

        proxy_values = {
            "shoulder_circumference": torch.tensor(118.0),
            "bicep_circumference": torch.tensor(33.0),
            "thigh_circumference": torch.tensor(61.0),
        }

        with (
            patch.object(optimizer, "_has_valid_loop", side_effect=lambda name: name in proxy_values),
            patch.object(optimizer, "_loop_circumference_cm", side_effect=lambda vertices, name: proxy_values[name]),
        ):
            measured = optimizer.calculate_measurements(
                vertices=dummy_vertices,
                joints=None,
                target_height_cm=None,
            )

        self.assertEqual(float(measured["shoulder_circumference_cm"]), 118.0)
        self.assertEqual(float(measured["bicep_circumference_cm"]), 33.0)
        self.assertEqual(float(measured["thigh_circumference_cm"]), 61.0)


if __name__ == "__main__":
    unittest.main()
