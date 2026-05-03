# VFR AiEngine Training

This folder keeps training workflows separate from the default runtime path. The current production target provider is still `heuristic`; the measurement regressor is experimental until its reports beat the current `anthropometry.py` targets.

## Measurement Regressor

Train a small tabular model:

```bash
python -m vfr_ai_engine.non_runtime.training.measurement_regressor train \
  --dataset data/anthropometry.csv \
  --mapping data/column-mapping.json \
  --output-dir training-artifacts/measurement-regressor-smoke \
  --epochs 5
```

Evaluate a checkpoint against the same canonical labels and the current heuristic:

```bash
python -m vfr_ai_engine.non_runtime.training.measurement_regressor evaluate \
  --model training-artifacts/measurement-regressor-smoke/measurement-regressor-best.pt \
  --dataset data/anthropometry.csv \
  --mapping data/column-mapping.json \
  --output-dir training-artifacts/measurement-regressor-eval
```

Predict measurements for profiles without labels:

```bash
python -m vfr_ai_engine.non_runtime.training.measurement_regressor predict \
  --model training-artifacts/measurement-regressor-smoke/measurement-regressor-best.pt \
  --input data/profiles.jsonl \
  --output training-artifacts/predictions.jsonl
```

## Dataset Mapping

The mapping file is JSON. A direct string reads a source column as-is. An object can scale values, for example millimeters to centimeters.

```json
{
  "columns": {
    "gender": "sex",
    "height_cm": { "column": "stature_mm", "scale": 0.1 },
    "weight_kg": "weight_kg",
    "chest_cm": { "column": "chest_mm", "scale": 0.1 },
    "waist_cm": { "column": "waist_mm", "scale": 0.1 }
  }
}
```

Canonical inputs are `gender`, `height_cm`, `weight_kg`, `bmi`, `body_type`, `muscularity`, and `body_fat_percentage`. Canonical outputs are `chest_cm`, `waist_cm`, `hips_cm`, `left_bicep_cm`, `left_thigh_cm`, `arm_length_cm`, `leg_length_cm`, `shoulder_cm`, `calf_cm`, and `torso_length_cm`.

Keep raw dataset files under `data/` or another ignored local directory. Do not commit ANSUR/NHANES/CAESAR-derived raw data.

## Optional Runtime Use

The avatar runtime remains heuristic by default. To explicitly test a trained checkpoint through the runtime path:

```bash
MEASUREMENT_TARGET_PROVIDER=regressor
MEASUREMENT_REGRESSOR_MODEL_PATH=training-artifacts/measurement-regressor-smoke/measurement-regressor-best.pt
```

If the provider is set to `regressor` without a valid checkpoint, generation fails loudly instead of silently falling back.
