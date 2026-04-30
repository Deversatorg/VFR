# VFR AI Engine Validation

This folder includes a baseline anthropometry validation loop for tuning
`height + weight + body_type + gender -> plausible avatar shape`.

## Files

- `vfr_ai_engine/validation/measurements.py`
  Runs heuristic, auto-inferred, exact-fit validation, and the reachability/calibration assay against a case set.
- `validation_cases.baseline.json`
  Starter archetype dataset for daily tuning.
- `vfr_ai_engine/measurements/anthropometry.py`
  Main place to tune body priors and body-type adjustments.

## Run

```bash
python -m vfr_ai_engine.validation.measurements --cases validation_cases.baseline.json
```

Optional flags:

```bash
python -m vfr_ai_engine.validation.measurements \
  --cases validation_cases.baseline.json \
  --model-path models \
  --device cpu \
  --iterations 140 \
  --output measurement_validation_report.json
```

Reachability/calibration assay for plateau diagnosis:

```bash
python -m vfr_ai_engine.validation.measurements \
  --cases validation_cases.baseline.json \
  --assay reachability \
  --random-starts 3 \
  --output measurement_reachability_assay.json
```

## What The Report Means

- `inference`
  Error between the anthropometric auto-targets and the case ground truth.
  This is the best signal for tuning `vfr_ai_engine/measurements/anthropometry.py`.
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

## Tuning Strategy

1. Improve `auto_mae` first.
2. Focus on `worst_auto_cases` from the JSON report.
3. Tune only one area at a time in `vfr_ai_engine/measurements/anthropometry.py`:
   chest, waist, hips, or limb ratios.
4. Re-run the baseline dataset after every change.
5. Keep `exact_mae` low while improving `auto_mae`.

## Practical Targets

- `auto` chest/waist/hips MAE under `4 cm`
- `auto` arm/leg MAE under `2.5 cm`
- `exact` chest/waist/hips MAE under `2 cm`
- `exact` arm/leg MAE under `1.5 cm`
