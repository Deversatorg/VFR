from __future__ import annotations

import json
import shutil
import sys
import types
import unittest
import uuid
from pathlib import Path

import torch

CURRENT_FILE = Path(__file__).resolve()
if str(CURRENT_FILE).startswith("/app/"):
    AI_ENGINE_DIR = Path("/app")
    TEST_TEMP_ROOT = Path("/workspace-tmp") / "aiengine-tests"
else:
    REPO_ROOT = CURRENT_FILE.parents[3]
    AI_ENGINE_DIR = REPO_ROOT / "src" / "VFR.AiEngine"
    TEST_TEMP_ROOT = REPO_ROOT / "tmp" / "aiengine-tests"
sys.path.insert(0, str(AI_ENGINE_DIR))

from vfr_ai_engine.runtime.measurements.regressor import infer_measurement_targets as infer_regressor_targets
from vfr_ai_engine.non_runtime.training.data import load_regressor_dataset
from vfr_ai_engine.non_runtime.training.measurement_regressor import evaluate, train
from vfr_ai_engine.runtime.measurements.regressor_model import MeasurementRegressorPredictor, masked_mse_loss
from vfr_ai_engine.runtime.measurements.regressor_schema import OUTPUT_MEASUREMENTS


class MeasurementRegressorTests(unittest.TestCase):
    def setUp(self):
        TEST_TEMP_ROOT.mkdir(parents=True, exist_ok=True)
        self.tempdir = TEST_TEMP_ROOT / f"regressor-{uuid.uuid4().hex}"
        self.tempdir.mkdir()
        self.dataset_path = self.tempdir / "anthropometry.csv"
        self.mapping_path = self.tempdir / "mapping.json"
        self.output_dir = self.tempdir / "run"
        self.eval_dir = self.tempdir / "eval"
        self._write_fixture_dataset()

    def tearDown(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_dataset_mapping_normalizes_canonical_records(self):
        dataset = load_regressor_dataset(self.dataset_path, mapping_path=self.mapping_path)

        first = dataset.records[0]
        self.assertEqual(first.profile["gender"], "male")
        self.assertEqual(first.profile["height_cm"], 165.0)
        self.assertEqual(first.profile["body_type"], "slim")
        self.assertAlmostEqual(first.targets["chest_cm"], 86.84)
        self.assertAlmostEqual(first.targets["shoulder_cm"], 39.6)
        self.assertEqual(dataset.inputs.shape[1], 12)
        self.assertEqual(dataset.targets.shape[1], len(OUTPUT_MEASUREMENTS))

    def test_masked_loss_ignores_missing_labels(self):
        predictions = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
        targets = torch.tensor([[1.0, 99.0], [99.0, 6.0]])
        mask = torch.tensor([[1.0, 0.0], [0.0, 1.0]])

        loss = masked_mse_loss(predictions, targets, mask)

        self.assertAlmostEqual(float(loss.detach().cpu().item()), 2.0)

    def test_training_checkpoint_prediction_and_evaluation_artifacts(self):
        args = self._train_args()

        summary = train(args)

        checkpoint_path = self.output_dir / "measurement-regressor-best.pt"
        self.assertTrue(checkpoint_path.exists())
        self.assertTrue((self.output_dir / "metadata.json").exists())
        self.assertTrue((self.output_dir / "predictions.csv").exists())
        self.assertTrue((self.output_dir / "measurement-regressor-report.md").exists())
        self.assertIn("by_measurement", summary)

        predictor = MeasurementRegressorPredictor.from_checkpoint(checkpoint_path)
        prediction = predictor.predict_profile(
            {
                "gender": "female",
                "height_cm": 170.0,
                "weight_kg": 64.0,
                "body_type": "regular",
                "muscularity": 50.0,
                "body_fat_percentage": 28.0,
            }
        )
        for measurement_name in OUTPUT_MEASUREMENTS:
            self.assertIn(measurement_name, prediction)
            self.assertGreater(prediction[measurement_name], 0)

        runtime_targets, runtime_weights, runtime_sources = infer_regressor_targets(
            height_cm=170.0,
            weight_kg=64.0,
            body_type="regular",
            gender="female",
            muscularity=50.0,
            body_fat_percentage=28.0,
            overrides={"waist_cm": 72.0},
            hints={"shoulder_cm": 41.0},
            model_path=str(checkpoint_path),
        )
        self.assertEqual(runtime_targets["waist_cm"], 72.0)
        self.assertEqual(runtime_sources["waist_cm"], "user")
        self.assertEqual(runtime_targets["shoulder_cm"], 41.0)
        self.assertEqual(runtime_sources["shoulder_cm"], "user_hint")
        self.assertIn("bicep_circumference_cm", runtime_targets)
        self.assertIn("thigh_circumference_cm", runtime_targets)
        self.assertEqual(runtime_targets["shoulder_circumference_cm"], 106.6)
        self.assertGreater(runtime_weights["chest_cm"], 0)

        evaluate(
            types.SimpleNamespace(
                dataset=str(self.dataset_path),
                mapping=str(self.mapping_path),
                model=str(checkpoint_path),
                output_dir=str(self.eval_dir),
            )
        )
        self.assertTrue((self.eval_dir / "summary.json").exists())
        report = (self.eval_dir / "measurement-regressor-report.md").read_text(encoding="utf-8")
        self.assertIn("heuristic", report.lower())

    def _train_args(self):
        return types.SimpleNamespace(
            dataset=str(self.dataset_path),
            mapping=str(self.mapping_path),
            output_dir=str(self.output_dir),
            epochs=4,
            batch_size=4,
            learning_rate=0.005,
            weight_decay=0.0,
            hidden_size=24,
            seed=20260430,
            validation_fraction=0.2,
            test_fraction=0.2,
            max_hours=0.0,
            checkpoint_interval=2,
            early_stopping_patience=0,
            resume=False,
        )

    def _write_fixture_dataset(self):
        self.mapping_path.write_text(
            json.dumps(
                {
                    "columns": {
                        "gender": "sex",
                        "height_cm": {"column": "stature_mm", "scale": 0.1},
                        "weight_kg": "mass_kg",
                        "body_type": "build",
                        "muscularity": "muscle",
                        "body_fat_percentage": "fat",
                        "chest_cm": {"column": "chest_mm", "scale": 0.1},
                        "waist_cm": {"column": "waist_mm", "scale": 0.1},
                        "hips_cm": {"column": "hips_mm", "scale": 0.1},
                        "left_bicep_cm": {"column": "upper_arm_mm", "scale": 0.1},
                        "left_thigh_cm": {"column": "thigh_mm", "scale": 0.1},
                        "arm_length_cm": {"column": "arm_length_mm", "scale": 0.1},
                        "leg_length_cm": {"column": "leg_length_mm", "scale": 0.1},
                        "shoulder_cm": {"column": "shoulder_mm", "scale": 0.1},
                        "calf_cm": {"column": "calf_mm", "scale": 0.1},
                        "torso_length_cm": {"column": "torso_mm", "scale": 0.1},
                    }
                }
            ),
            encoding="utf-8",
        )

        rows = [
            ("M", 165, 56, "slim", 35, 14),
            ("M", 172, 76, "regular", 50, 18),
            ("M", 182, 84, "athletic", 74, 14),
            ("M", 188, 104, "curvy", 42, 27),
            ("F", 158, 50, "slim", 34, 22),
            ("F", 166, 60, "regular", 48, 28),
            ("F", 170, 64, "athletic", 68, 23),
            ("F", 168, 76, "curvy", 44, 35),
            ("M", 178, 88, "regular", 48, 23),
            ("F", 176, 68, "slim", 38, 24),
        ]
        header = [
            "sex",
            "stature_mm",
            "mass_kg",
            "build",
            "muscle",
            "fat",
            "chest_mm",
            "waist_mm",
            "hips_mm",
            "upper_arm_mm",
            "thigh_mm",
            "arm_length_mm",
            "leg_length_mm",
            "shoulder_mm",
            "calf_mm",
            "torso_mm",
        ]
        lines = [",".join(header)]
        for gender, height_cm, weight_kg, body_type, muscle, fat in rows:
            bmi = weight_kg / ((height_cm / 100.0) ** 2)
            is_male = gender == "M"
            chest = height_cm * (0.535 if is_male else 0.525) + (bmi - 22.0) * 1.0
            waist = height_cm * (0.43 if is_male else 0.405) + (bmi - 22.0) * 1.7
            hips = height_cm * (0.53 if is_male else 0.575) + (bmi - 22.0) * 1.2
            bicep = height_cm * (0.155 if is_male else 0.142) + (muscle - 50.0) * 0.07
            thigh = height_cm * (0.32 if is_male else 0.335) + (fat - 25.0) * 0.08
            arm = height_cm * 0.37
            leg = height_cm * 0.50
            shoulder = height_cm * (0.24 if is_male else 0.235)
            calf = height_cm * 0.21
            torso = height_cm * 0.315
            values = [
                gender,
                int(height_cm * 10),
                weight_kg,
                body_type,
                muscle,
                fat,
                round(chest * 10, 1),
                round(waist * 10, 1),
                round(hips * 10, 1),
                round(bicep * 10, 1),
                round(thigh * 10, 1),
                round(arm * 10, 1),
                round(leg * 10, 1),
                round(shoulder * 10, 1),
                round(calf * 10, 1),
                round(torso * 10, 1),
            ]
            lines.append(",".join(str(value) for value in values))

        self.dataset_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
