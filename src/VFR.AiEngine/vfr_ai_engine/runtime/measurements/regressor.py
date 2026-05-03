"""Optional runtime target inference through a trained measurement regressor."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Mapping

from vfr_ai_engine.runtime.measurements.anthropometry import DEFAULT_INFERRED_WEIGHTS, DEFAULT_USER_WEIGHTS
from vfr_ai_engine.runtime.measurements.proxy_targets import (
    PROFILE_OPTIMIZATION_WEIGHTS,
    convert_shoulder_width_to_circumference_cm,
)
from vfr_ai_engine.runtime.measurements.regressor_model import MeasurementRegressorPredictor
from vfr_ai_engine.runtime.measurements.regressor_schema import OUTPUT_MEASUREMENTS, REQUIRED_RUNTIME_MEASUREMENTS


REGRESSOR_SOURCE = "measurement_regressor"


def infer_measurement_targets(
    *,
    height_cm: float,
    weight_kg: float,
    body_type: str,
    gender: str,
    muscularity: float | None = None,
    body_fat_percentage: float | None = None,
    overrides: Mapping[str, float] | None = None,
    hints: Mapping[str, float] | None = None,
    model_path: str | None = None,
) -> tuple[dict[str, float], dict[str, float], dict[str, str]]:
    checkpoint_path = model_path or os.getenv("MEASUREMENT_REGRESSOR_MODEL_PATH", "")
    if not checkpoint_path:
        raise RuntimeError(
            "MEASUREMENT_TARGET_PROVIDER=regressor requires MEASUREMENT_REGRESSOR_MODEL_PATH."
        )
    predictor = _load_predictor(str(Path(checkpoint_path)))
    profile = {
        "height_cm": height_cm,
        "weight_kg": weight_kg,
        "body_type": body_type,
        "gender": gender,
        "muscularity": muscularity or 0.0,
        "body_fat_percentage": body_fat_percentage or 0.0,
    }
    targets = {
        measurement_name: float(value)
        for measurement_name, value in predictor.predict_profile(profile).items()
        if measurement_name in OUTPUT_MEASUREMENTS
    }
    missing = [measurement_name for measurement_name in REQUIRED_RUNTIME_MEASUREMENTS if measurement_name not in targets]
    if missing:
        raise RuntimeError(
            "Measurement regressor did not produce required targets: " + ", ".join(missing)
        )

    weights = {
        measurement_name: DEFAULT_INFERRED_WEIGHTS.get(measurement_name, 1.0)
        for measurement_name in targets
    }
    sources = {measurement_name: REGRESSOR_SOURCE for measurement_name in targets}

    for measurement_name, raw_value in (overrides or {}).items():
        if measurement_name not in targets:
            continue
        numeric_value = float(raw_value)
        if numeric_value <= 0:
            continue
        targets[measurement_name] = round(numeric_value, 2)
        weights[measurement_name] = DEFAULT_USER_WEIGHTS.get(measurement_name, 3.0)
        sources[measurement_name] = "user"

    hint_values = hints or {}
    for hint_name in ("shoulder_cm", "calf_cm", "torso_length_cm"):
        numeric_value = float(hint_values.get(hint_name, 0.0) or 0.0)
        if numeric_value <= 0:
            continue
        targets[hint_name] = round(numeric_value, 2)
        weights[hint_name] = 1.0
        sources[hint_name] = "user_hint"

    _add_optimizer_compatible_targets(targets, weights, sources)

    return targets, weights, sources


@lru_cache(maxsize=2)
def _load_predictor(model_path: str) -> MeasurementRegressorPredictor:
    return MeasurementRegressorPredictor.from_checkpoint(model_path)


def _add_optimizer_compatible_targets(
    targets: dict[str, float],
    weights: dict[str, float],
    sources: dict[str, str],
) -> None:
    if targets.get("left_bicep_cm", 0.0) > 0:
        targets["bicep_circumference_cm"] = round(float(targets["left_bicep_cm"]), 2)
        weights["bicep_circumference_cm"] = PROFILE_OPTIMIZATION_WEIGHTS["bicep_circumference_cm"]
        sources["bicep_circumference_cm"] = sources.get("left_bicep_cm", REGRESSOR_SOURCE)

    if targets.get("left_thigh_cm", 0.0) > 0:
        targets["thigh_circumference_cm"] = round(float(targets["left_thigh_cm"]), 2)
        weights["thigh_circumference_cm"] = PROFILE_OPTIMIZATION_WEIGHTS["thigh_circumference_cm"]
        sources["thigh_circumference_cm"] = sources.get("left_thigh_cm", REGRESSOR_SOURCE)

    shoulder_width = targets.get("shoulder_cm", 0.0)
    shoulder_circumference = convert_shoulder_width_to_circumference_cm(shoulder_width)
    if shoulder_circumference > 0:
        targets["shoulder_circumference_cm"] = shoulder_circumference
        weights["shoulder_circumference_cm"] = PROFILE_OPTIMIZATION_WEIGHTS["shoulder_circumference_cm"]
        sources["shoulder_circumference_cm"] = sources.get("shoulder_cm", REGRESSOR_SOURCE)
