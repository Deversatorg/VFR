"""Proxy measurement targets derived from Studio muscle/fat controls."""

from __future__ import annotations

from typing import Optional

PROFILE_OPTIMIZATION_WEIGHTS = {
    "chest_cm": 1.0,
    "waist_cm": 1.0,
    "hips_cm": 1.0,
    "shoulder_circumference_cm": 0.3,
    "bicep_circumference_cm": 0.5,
    "thigh_circumference_cm": 0.5,
}
STRICT_EXPLICIT_MEASUREMENT_WEIGHT = 20.0
PROFILE_OPTIMIZATION_TARGET_KEYS = {
    "chest_cm",
    "waist_cm",
    "hips_cm",
    "shoulder_circumference_cm",
    "bicep_circumference_cm",
    "thigh_circumference_cm",
}
SHOULDER_WIDTH_TO_CIRCUMFERENCE_RATIO = 2.6


def _clamp_float(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def normalize_proxy_slider(raw_value: Optional[float]) -> float:
    if raw_value is None:
        return 0.0

    value = float(raw_value)
    if value <= 0:
        return 0.0
    if value <= 1.0:
        return _clamp_float(value, 0.0, 1.0)
    return _clamp_float(value / 100.0, 0.0, 1.0)


def calculate_proxy_targets(
    exact_measurements: dict[str, float],
    muscle_slider: Optional[float],
    fat_slider: Optional[float],
    gender: str,
) -> dict[str, float]:
    chest_cm = float(exact_measurements.get("chest_cm", 0.0) or 0.0)
    hips_cm = float(exact_measurements.get("hips_cm", 0.0) or 0.0)
    if chest_cm <= 0 or hips_cm <= 0:
        return {}

    gender_key = str(gender or "neutral").lower()
    if gender_key not in {"male", "female", "neutral"}:
        gender_key = "neutral"

    muscle = normalize_proxy_slider(muscle_slider)
    fat = normalize_proxy_slider(fat_slider)

    if gender_key == "male":
        base_shoulder = chest_cm * 1.15
        target_shoulder = base_shoulder + muscle * chest_cm * 0.10 + fat * chest_cm * 0.03
        target_bicep = chest_cm * (0.25 + muscle * 0.08 + fat * 0.02)
        target_thigh = hips_cm * (0.54 + muscle * 0.05 + fat * 0.08)
    elif gender_key == "female":
        base_shoulder = chest_cm * 1.10
        target_shoulder = base_shoulder + muscle * chest_cm * 0.07 + fat * chest_cm * 0.04
        target_bicep = chest_cm * (0.21 + muscle * 0.05 + fat * 0.02)
        target_thigh = hips_cm * (0.58 + muscle * 0.03 + fat * 0.10)
    else:
        base_shoulder = chest_cm * 1.125
        target_shoulder = base_shoulder + muscle * chest_cm * 0.085 + fat * chest_cm * 0.035
        target_bicep = chest_cm * (0.23 + muscle * 0.065 + fat * 0.02)
        target_thigh = hips_cm * (0.56 + muscle * 0.04 + fat * 0.09)

    return {
        "shoulder_circumference_cm": target_shoulder,
        "bicep_circumference_cm": target_bicep,
        "thigh_circumference_cm": target_thigh,
    }


def build_profile_optimizer_targets(
    target_measurements: dict[str, float],
    measurement_weights: dict[str, float],
    measurement_sources: dict[str, str],
    manual_hint_values: Optional[dict[str, float]] = None,
) -> tuple[dict[str, float], dict[str, float], list[str]]:
    optimization_targets = {
        measurement_name: target_value
        for measurement_name, target_value in target_measurements.items()
        if measurement_name in PROFILE_OPTIMIZATION_TARGET_KEYS
    }

    explicit_manual_measurement_keys = {
        measurement_name
        for measurement_name, source in measurement_sources.items()
        if source == "user"
    }
    explicit_manual_hint_keys = {
        hint_name
        for hint_name, hint_value in (manual_hint_values or {}).items()
        if hint_value is not None and float(hint_value) > 0
    }
    explicit_keys = sorted(explicit_manual_measurement_keys | explicit_manual_hint_keys)

    optimization_weights = {}
    for measurement_name in optimization_targets:
        if measurement_name in explicit_manual_measurement_keys:
            optimization_weights[measurement_name] = STRICT_EXPLICIT_MEASUREMENT_WEIGHT
        else:
            optimization_weights[measurement_name] = PROFILE_OPTIMIZATION_WEIGHTS.get(
                measurement_name,
                measurement_weights.get(measurement_name, 1.0),
            )

    return optimization_targets, optimization_weights, explicit_keys


def convert_shoulder_width_to_circumference_cm(shoulder_width_cm: Optional[float]) -> float:
    if shoulder_width_cm is None:
        return 0.0
    value = float(shoulder_width_cm)
    if value <= 0:
        return 0.0
    return round(value * SHOULDER_WIDTH_TO_CIRCUMFERENCE_RATIO, 2)

