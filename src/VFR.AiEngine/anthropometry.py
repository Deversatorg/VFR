from typing import Dict, Mapping, Tuple


SUPPORTED_MEASUREMENT_TARGETS = (
    "chest_cm",
    "waist_cm",
    "hips_cm",
    "arm_length_cm",
    "leg_length_cm",
)


ANTHROPOMETRIC_PRIORS = {
    "male": {
        "bmi_center": 21.5,
        "chest_ratio": 0.525,
        "waist_ratio": 0.450,
        "hips_ratio": 0.510,
        "arm_ratio": 0.375,
        "leg_ratio": 0.485,
        "bmi_to_chest": 1.6,
        "bmi_to_waist": 2.4,
        "bmi_to_hips": 1.4,
    },
    "female": {
        "bmi_center": 21.0,
        "chest_ratio": 0.530,
        "waist_ratio": 0.420,
        "hips_ratio": 0.540,
        "arm_ratio": 0.372,
        "leg_ratio": 0.482,
        "bmi_to_chest": 1.2,
        "bmi_to_waist": 2.1,
        "bmi_to_hips": 1.9,
    },
    "neutral": {
        "bmi_center": 21.25,
        "chest_ratio": 0.5275,
        "waist_ratio": 0.435,
        "hips_ratio": 0.525,
        "arm_ratio": 0.3735,
        "leg_ratio": 0.4835,
        "bmi_to_chest": 1.4,
        "bmi_to_waist": 2.25,
        "bmi_to_hips": 1.65,
    },
}


BODY_TYPE_ADJUSTMENTS = {
    "male": {
        "regular": {"chest_cm": 0.0, "waist_cm": 0.0, "hips_cm": 0.0, "arm_ratio": 0.0, "leg_ratio": 0.0},
        "slim": {"chest_cm": -1.5, "waist_cm": -3.5, "hips_cm": -1.5, "arm_ratio": 0.002, "leg_ratio": 0.003},
        "athletic": {"chest_cm": 3.5, "waist_cm": -4.0, "hips_cm": 0.5, "arm_ratio": 0.004, "leg_ratio": 0.005},
        "curvy": {"chest_cm": 1.5, "waist_cm": 3.0, "hips_cm": 4.0, "arm_ratio": -0.001, "leg_ratio": -0.0015},
    },
    "female": {
        "regular": {"chest_cm": 0.0, "waist_cm": 0.0, "hips_cm": 0.0, "arm_ratio": 0.0, "leg_ratio": 0.0},
        "slim": {"chest_cm": -1.0, "waist_cm": -2.5, "hips_cm": -0.5, "arm_ratio": 0.001, "leg_ratio": 0.002},
        "athletic": {"chest_cm": 1.0, "waist_cm": -4.0, "hips_cm": 1.0, "arm_ratio": 0.003, "leg_ratio": 0.004},
        "curvy": {"chest_cm": 3.0, "waist_cm": 1.0, "hips_cm": 5.0, "arm_ratio": -0.0005, "leg_ratio": -0.001},
    },
    "neutral": {
        "regular": {"chest_cm": 0.0, "waist_cm": 0.0, "hips_cm": 0.0, "arm_ratio": 0.0, "leg_ratio": 0.0},
        "slim": {"chest_cm": -1.25, "waist_cm": -3.0, "hips_cm": -1.0, "arm_ratio": 0.0015, "leg_ratio": 0.0025},
        "athletic": {"chest_cm": 2.0, "waist_cm": -4.0, "hips_cm": 0.75, "arm_ratio": 0.0035, "leg_ratio": 0.0045},
        "curvy": {"chest_cm": 2.25, "waist_cm": 2.0, "hips_cm": 4.5, "arm_ratio": -0.00075, "leg_ratio": -0.00125},
    },
}


MEASUREMENT_RATIO_BOUNDS = {
    "chest_cm": (0.42, 0.72),
    "waist_cm": (0.34, 0.70),
    "hips_cm": (0.42, 0.74),
    "arm_length_cm": (0.33, 0.42),
    "leg_length_cm": (0.43, 0.53),
}

DEFAULT_INFERRED_WEIGHTS = {
    "chest_cm": 1.2,
    "waist_cm": 1.4,
    "hips_cm": 1.1,
    "arm_length_cm": 0.6,
    "leg_length_cm": 0.7,
}

DEFAULT_USER_WEIGHTS = {
    "chest_cm": 3.0,
    "waist_cm": 3.0,
    "hips_cm": 3.0,
    "arm_length_cm": 2.0,
    "leg_length_cm": 2.0,
}


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def _normalize_gender(gender: str) -> str:
    gender_key = str(gender or "neutral").lower()
    if gender_key not in {"male", "female", "neutral"}:
        gender_key = "neutral"
    return gender_key


def _normalize_body_type(body_type: str) -> str:
    body_key = str(body_type or "regular").lower()
    aliases = {
        "average": "regular",
        "normal": "regular",
        "plus": "curvy",
        "stout": "curvy",
    }
    body_key = aliases.get(body_key, body_key)
    if body_key not in {"slim", "regular", "athletic", "curvy"}:
        body_key = "regular"
    return body_key


def infer_measurement_targets(
    *,
    height_cm: float,
    weight_kg: float,
    body_type: str,
    gender: str,
    overrides: Mapping[str, float] | None = None,
    hints: Mapping[str, float] | None = None,
) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, str]]:
    gender_key = _normalize_gender(gender)
    body_key = _normalize_body_type(body_type)
    priors = ANTHROPOMETRIC_PRIORS[gender_key]
    adjustments = BODY_TYPE_ADJUSTMENTS[gender_key][body_key]

    safe_height_cm = max(float(height_cm), 120.0)
    safe_weight_kg = max(float(weight_kg), 35.0)
    height_m = safe_height_cm / 100.0
    bmi = safe_weight_kg / max(height_m * height_m, 1e-6)
    bmi_delta = bmi - priors["bmi_center"]

    targets: Dict[str, float] = {
        "chest_cm": safe_height_cm * priors["chest_ratio"] + priors["bmi_to_chest"] * bmi_delta + adjustments["chest_cm"],
        "waist_cm": safe_height_cm * priors["waist_ratio"] + priors["bmi_to_waist"] * bmi_delta + adjustments["waist_cm"],
        "hips_cm": safe_height_cm * priors["hips_ratio"] + priors["bmi_to_hips"] * bmi_delta + adjustments["hips_cm"],
        "arm_length_cm": safe_height_cm * (priors["arm_ratio"] + adjustments["arm_ratio"]),
        "leg_length_cm": safe_height_cm * (priors["leg_ratio"] + adjustments["leg_ratio"]),
    }

    hint_values = hints or {}
    shoulder_hint = float(hint_values.get("shoulder_cm", 0.0) or 0.0)
    if shoulder_hint > 0:
        expected_shoulder_ratio = {"male": 0.24, "female": 0.23, "neutral": 0.235}[gender_key]
        expected_shoulder = safe_height_cm * expected_shoulder_ratio
        shoulder_delta = _clamp(
            (shoulder_hint - expected_shoulder) / max(expected_shoulder, 1.0),
            -0.15,
            0.15,
        )
        targets["chest_cm"] += shoulder_delta * 10.0
        targets["waist_cm"] -= shoulder_delta * 4.0

    torso_hint = float(hint_values.get("torso_length_cm", 0.0) or 0.0)
    if torso_hint > 0:
        expected_torso_ratio = {"male": 0.31, "female": 0.32, "neutral": 0.315}[gender_key]
        expected_torso = safe_height_cm * expected_torso_ratio
        torso_delta = _clamp(
            (torso_hint - expected_torso) / max(expected_torso, 1.0),
            -0.12,
            0.12,
        )
        targets["leg_length_cm"] -= torso_delta * safe_height_cm * 0.35

    calf_hint = float(hint_values.get("calf_cm", 0.0) or 0.0)
    if calf_hint > 0:
        expected_calf_ratio = {"male": 0.205, "female": 0.210, "neutral": 0.2075}[gender_key]
        expected_calf = safe_height_cm * expected_calf_ratio
        calf_delta = _clamp(
            (calf_hint - expected_calf) / max(expected_calf, 1.0),
            -0.18,
            0.18,
        )
        targets["hips_cm"] += calf_delta * 6.0
        targets["waist_cm"] += calf_delta * 2.0

    for measurement_name, (lower_ratio, upper_ratio) in MEASUREMENT_RATIO_BOUNDS.items():
        lower_bound = safe_height_cm * lower_ratio
        upper_bound = safe_height_cm * upper_ratio
        targets[measurement_name] = round(_clamp(targets[measurement_name], lower_bound, upper_bound), 2)

    weights = dict(DEFAULT_INFERRED_WEIGHTS)
    sources = {measurement_name: "inferred" for measurement_name in targets}

    for measurement_name, raw_value in (overrides or {}).items():
        if measurement_name not in targets:
            continue
        numeric_value = float(raw_value)
        if numeric_value <= 0:
            continue
        targets[measurement_name] = round(numeric_value, 2)
        weights[measurement_name] = DEFAULT_USER_WEIGHTS[measurement_name]
        sources[measurement_name] = "user"

    return targets, weights, sources
