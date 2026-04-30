# Avatar Batch Analysis 20260429-0002

## Run

- Runtime path: ProfileApi broker -> AiEngine worker.
- Cases: 12 baseline Studio avatar cases.
- Output directory: `tests/artifacts/studio-avatar-batch/full-20260429-0002`
- Measurement report: `agents/reports/avatar-batch-measurement-report.md`
- Status: all 12 cases reached `SUCCESS`.
- Duration: 97.97 seconds.

## Runtime Findings

- No terminal payload completeness issues were found.
- Every terminal broker status has `progress: 100`, a populated `result`, and a `.glb` `modelUrl`.
- Persisted profile snapshots match terminal `modelUrl` in `lastAvatarModelUrl` and `generatedAvatar.modelUrl`.
- `generatedAvatar.isCurrent` is true for every case.
- Intermediate `PROGRESS` responses with `result: null` are expected.

## Measurement Findings

- Overall target MAE: 10.2116 cm.
- Case-truth MAE: 3.3852 cm.
- Source group MAE:
  - user: 3.2175 cm
  - inferred: 20.8263 cm
  - proxy_targets: 20.5792 cm

The generated avatars mostly honor explicit user torso and length inputs. The plateau is dominated by derived limb circumference targets, especially bicep.

## Strongest Signal

- `bicep_circumference_cm` has positive signed error in all 12 cases.
- Mean signed bicep target error: +36.157 cm.
- Worst bicep residuals:
  - `male_tall_curvy_plus`: target 33.51 cm, measured 77.56 cm, signed +44.05 cm.
  - `male_tall_slim_athletic`: target 29.49 cm, measured 72.13 cm, signed +42.64 cm.
  - `male_average_regular`: target 29.24 cm, measured 70.20 cm, signed +40.96 cm.

`left_bicep_cm` and `bicep_circumference_cm` are equal in every case, so this is not a left/proxy bookkeeping mismatch. It is either a loop/tape semantics problem for the bicep loop or a missing local corrective warp for upper arms.

## Secondary Signal

- `leg_length_cm` is consistently high in case-truth residuals, mean signed +6.211 cm.
- Waist and chest are consistently low:
  - waist mean signed -4.819 cm
  - chest mean signed -4.254 cm
- Thighs are much closer than biceps, but female thigh targets overshoot more often than male thigh targets.

## Current Diagnosis

The first blocker was a refactor bug: `STRICT_EXPLICIT_MEASUREMENT_WEIGHT` was not imported in `vfr_ai_engine.avatar.pipeline`. After importing it, smoke and full batch passed.

The current math plateau should not be attacked by retraining or adding more data yet. The batch suggests the product path is healthy and the model can fit explicit torso/length inputs reasonably, while bicep circumference is systematically off by roughly a factor of 2x. That pattern points first to bicep loop semantics and/or missing upper-arm corrective warp, not global beta training.

## Recommended Next Experiment

Run an arm-first local assay:

1. Pick three cases: `male_tall_slim_athletic`, `male_tall_curvy_plus`, `female_tall_slim`.
2. Keep the current global beta fit fixed.
3. Compare current measured bicep loop against a direct geometric upper-arm loop audit.
4. If loop semantics are valid, apply a localized upper-arm circumference warp after the base solve.
5. Success criterion: bicep MAE drops materially without moving chest, waist, hips, arm length, or shoulder circumference.

Only after this should we consider training, new weights, or dataset expansion.
