"""Canonical schema for the measurement regressor training data."""

from __future__ import annotations

import math
from typing import Any


GENDER_VALUES = ("female", "male", "neutral")
BODY_TYPE_VALUES = ("slim", "regular", "athletic", "curvy")

NUMERIC_INPUT_FIELDS = (
    "height_cm",
    "weight_kg",
    "bmi",
    "muscularity",
    "body_fat_percentage",
)

MODEL_INPUT_FIELDS = (
    *NUMERIC_INPUT_FIELDS,
    *(f"gender_{value}" for value in GENDER_VALUES),
    *(f"body_type_{value}" for value in BODY_TYPE_VALUES),
)

OUTPUT_MEASUREMENTS = (
    "chest_cm",
    "waist_cm",
    "hips_cm",
    "left_bicep_cm",
    "left_thigh_cm",
    "arm_length_cm",
    "leg_length_cm",
    "shoulder_cm",
    "calf_cm",
    "torso_length_cm",
)

REQUIRED_RUNTIME_MEASUREMENTS = (
    "chest_cm",
    "waist_cm",
    "hips_cm",
    "left_bicep_cm",
    "left_thigh_cm",
    "arm_length_cm",
    "leg_length_cm",
)

FIELD_ALIASES = {
    "gender": ("gender", "sex"),
    "height_cm": ("height_cm", "height", "stature_cm", "stature"),
    "weight_kg": ("weight_kg", "weight", "mass_kg", "body_weight_kg"),
    "body_type": ("body_type", "bodyType", "build"),
    "muscularity": ("muscularity", "muscle", "muscle_slider"),
    "body_fat_percentage": ("body_fat_percentage", "body_fat", "fat", "fat_percent"),
    "bmi": ("bmi", "BMI"),
    "measurement_mode": ("measurement_mode", "mode"),
}

MEASUREMENT_ALIASES = {
    "chest_cm": ("chest_cm", "chest", "chest_circumference_cm"),
    "waist_cm": ("waist_cm", "waist", "waist_circumference_cm"),
    "hips_cm": ("hips_cm", "hips", "hip", "hip_cm", "buttock_circumference_cm"),
    "left_bicep_cm": (
        "left_bicep_cm",
        "bicep_cm",
        "upper_arm_cm",
        "upperarm_cm",
        "left_upper_arm_cm",
    ),
    "left_thigh_cm": ("left_thigh_cm", "thigh_cm", "left_thigh", "mid_thigh_cm"),
    "arm_length_cm": ("arm_length_cm", "arm_length", "left_arm_length_cm"),
    "leg_length_cm": ("leg_length_cm", "leg_length", "left_leg_length_cm"),
    "shoulder_cm": ("shoulder_cm", "shoulder", "shoulder_width_cm"),
    "calf_cm": ("calf_cm", "calf", "left_calf_cm"),
    "torso_length_cm": ("torso_length_cm", "torso_length", "trunk_length_cm"),
}


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        if not value or value.lower() in {"nan", "null", "none", "na", "n/a"}:
            return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def normalize_gender(value: Any) -> str:
    raw = str(value or "neutral").strip().lower()
    if raw in {"m", "man", "men", "male", "1"}:
        return "male"
    if raw in {"f", "woman", "women", "female", "2"}:
        return "female"
    return "neutral"


def infer_body_type_from_bmi(bmi: float | None) -> str:
    if bmi is None:
        return "regular"
    if bmi < 20.0:
        return "slim"
    if bmi >= 29.0:
        return "curvy"
    return "regular"


def normalize_body_type(value: Any, bmi: float | None = None) -> str:
    raw = str(value or "").strip().lower()
    aliases = {
        "lean": "slim",
        "thin": "slim",
        "average": "regular",
        "normal": "regular",
        "soft": "curvy",
        "plus": "curvy",
        "plus size": "curvy",
        "plus-size": "curvy",
        "plus_size": "curvy",
        "stout": "curvy",
        "stocky": "curvy",
        "muscular": "athletic",
    }
    body_type = aliases.get(raw, raw)
    if body_type in BODY_TYPE_VALUES:
        return body_type
    return infer_body_type_from_bmi(bmi)


def derive_bmi(height_cm: float | None, weight_kg: float | None, bmi: float | None = None) -> float | None:
    if bmi is not None and bmi > 0:
        return bmi
    if height_cm is None or weight_kg is None or height_cm <= 0 or weight_kg <= 0:
        return None
    height_m = height_cm / 100.0
    return weight_kg / max(height_m * height_m, 1e-6)


def bmi_bucket(bmi: float | None) -> str:
    if bmi is None:
        return "unknown"
    if bmi < 18.5:
        return "underweight"
    if bmi < 25.0:
        return "normal"
    if bmi < 30.0:
        return "overweight"
    return "obese"


def encode_profile_features(profile: dict[str, Any]) -> list[float]:
    gender = normalize_gender(profile.get("gender"))
    height_cm = parse_float(profile.get("height_cm"))
    weight_kg = parse_float(profile.get("weight_kg"))
    bmi = derive_bmi(height_cm, weight_kg, parse_float(profile.get("bmi")))
    body_type = normalize_body_type(profile.get("body_type"), bmi)

    values = [
        float(height_cm or 0.0),
        float(weight_kg or 0.0),
        float(bmi or 0.0),
        float(parse_float(profile.get("muscularity")) or 0.0),
        float(parse_float(profile.get("body_fat_percentage")) or 0.0),
    ]
    values.extend(1.0 if gender == value else 0.0 for value in GENDER_VALUES)
    values.extend(1.0 if body_type == value else 0.0 for value in BODY_TYPE_VALUES)
    return values
