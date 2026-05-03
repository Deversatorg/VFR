# VFR AI Engine Validation

This folder includes a baseline anthropometry validation loop for tuning
`height + weight + body_type + gender -> plausible avatar shape`.

## Files

- `vfr_ai_engine/non_runtime/validation/measurements.py`
  Runs heuristic, auto-inferred, exact-fit validation, and the reachability/calibration assay against a case set.
- `validation_cases.baseline.json`
  Starter archetype dataset for daily tuning.
- `vfr_ai_engine/runtime/measurements/anthropometry.py`
  Main place to tune body priors and body-type adjustments.
- `vfr_ai_engine/non_runtime/training/measurement_regressor.py`
  Experimental tabular model for learning profile-to-measurement targets from local anthropometric datasets.

## Run

```bash
python -m vfr_ai_engine.non_runtime.validation.measurements --cases validation_cases.baseline.json
```

Optional flags:

```bash
python -m vfr_ai_engine.non_runtime.validation.measurements \
  --cases validation_cases.baseline.json \
  --model-path models \
  --device cpu \
  --iterations 140 \
  --output measurement_validation_report.json
```

Reachability/calibration assay for plateau diagnosis:

```bash
python -m vfr_ai_engine.non_runtime.validation.measurements \
  --cases validation_cases.baseline.json \
  --assay reachability \
  --random-starts 3 \
  --output measurement_reachability_assay.json
```

Measurement loop audit for generated batch artifacts:

```bash
python -m vfr_ai_engine.non_runtime.validation.measurement_loop_audit \
  --batch-dir ../../tests/artifacts/studio-avatar-batch/synthetic-150-both-20260430 \
  --case synthetic_034_male_curvy_tall_plus_mlow_fmid__profile_only \
  --output ../../tests/artifacts/measurement-loop-audit/bicep-20260430
```

Use `--model-path path/to/generated.glb` when the `modelUrl` artifact cannot be downloaded locally.

Measurement regressor smoke training on a small local dataset:

```bash
python -m vfr_ai_engine.non_runtime.training.measurement_regressor train \
  --dataset data/anthropometry.csv \
  --mapping data/column-mapping.json \
  --output-dir training-artifacts/measurement-regressor-smoke \
  --epochs 5
```

Evaluation against the current heuristic target inference:

```bash
python -m vfr_ai_engine.non_runtime.training.measurement_regressor evaluate \
  --model training-artifacts/measurement-regressor-smoke/measurement-regressor-best.pt \
  --dataset data/anthropometry.csv \
  --mapping data/column-mapping.json \
  --output-dir training-artifacts/measurement-regressor-eval
```

Raw ANSUR/NHANES/CAESAR-derived files should stay under `data/` or another local ignored directory and must not be committed.

## What The Report Means

- `inference`
  Error between the anthropometric auto-targets and the case ground truth.
  This is the best signal for tuning `vfr_ai_engine/runtime/measurements/anthropometry.py`.
- `heuristic`
  Error from the old direct-beta fallback without measurement optimization.
- `auto`
  Error from the new baseline pipeline:
  `infer targets -> optimize SMPL-X -> measure final body`.
- `exact`
  Error when real user measurements are provided.
  This is the practical upper bound of the current optimizer.
- `reachability` assay
  Compares current exact beta fit, unconstrained beta fit with random starts, and strict circumference warp. Use this before training a regressor or widening the dataset so the plateau can be classified as regularization/init, beta-space reachability, loop/tape semantics, or corrective-warp need.
- `measurement_loop_audit`
  Compares configured optimizer vertex loops with independent upper-arm mesh sections on generated GLB artifacts. Use this before changing loop indices, weights, or corrective warps when one measurement has a systematic residual.

## Tuning Strategy

1. Improve `auto_mae` first.
2. Focus on `worst_auto_cases` from the JSON report.
3. Tune only one area at a time in `vfr_ai_engine/runtime/measurements/anthropometry.py`:
   chest, waist, hips, or limb ratios.
4. Re-run the baseline dataset after every change.
5. Keep `exact_mae` low while improving `auto_mae`.

## Practical Targets

- `auto` chest/waist/hips MAE under `4 cm`
- `auto` arm/leg MAE under `2.5 cm`
- `exact` chest/waist/hips MAE under `2 cm`
- `exact` arm/leg MAE under `1.5 cm`
