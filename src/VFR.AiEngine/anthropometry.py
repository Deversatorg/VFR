from typing import Dict, Mapping, Tuple


SUPPORTED_MEASUREMENT_TARGETS = (
    "chest_cm",
    "waist_cm",
    "hips_cm",
    "arm_length_cm",
    "leg_length_cm",
    "left_bicep_cm",
    "left_thigh_cm",
)


ANTHROPOMETRIC_PRIORS = {
    "male": {
        "bmi_center": 22.0,
        "chest_ratio": 0.540,
        "waist_ratio": 0.440,
        "hips_ratio": 0.525,
        "bicep_ratio": 0.155,
        "thigh_ratio": 0.320,
        # Limb ratios are calibrated to the current measurement definition in
        # measurement_optimizer.py, which includes collar/hand and pelvis/foot
        # segments. These values are intentionally higher than the older
        # shoulder-elbow-wrist proxy.
        "arm_ratio": 0.374,
        "leg_ratio": 0.506,
        "bmi_to_chest": 1.5,
        "bmi_to_waist": 2.0,
        "bmi_to_hips": 1.4,
        "bmi_to_bicep": 0.55,
        "bmi_to_thigh": 0.9,
    },
    "female": {
        "bmi_center": 21.0,
        "chest_ratio": 0.530,
        "waist_ratio": 0.420,
        "hips_ratio": 0.575,
        "bicep_ratio": 0.145,
        "thigh_ratio": 0.335,
        "arm_ratio": 0.368,
        "leg_ratio": 0.487,
        "bmi_to_chest": 1.2,
        "bmi_to_waist": 2.1,
        "bmi_to_hips": 1.9,
        "bmi_to_bicep": 0.45,
        "bmi_to_thigh": 1.0,
    },
    "neutral": {
        "bmi_center": 21.5,
        "chest_ratio": 0.535,
        "waist_ratio": 0.430,
        "hips_ratio": 0.550,
        "bicep_ratio": 0.150,
        "thigh_ratio": 0.3275,
        "arm_ratio": 0.372,
        "leg_ratio": 0.494,
        "bmi_to_chest": 1.35,
        "bmi_to_waist": 2.05,
        "bmi_to_hips": 1.65,
        "bmi_to_bicep": 0.5,
        "bmi_to_thigh": 0.95,
    },
}


BODY_TYPE_ADJUSTMENTS = {
    "male": {
        "regular": {"chest_cm": 0.0, "waist_cm": 0.0, "hips_cm": 0.0, "left_bicep_cm": 0.0, "left_thigh_cm": 0.0, "arm_ratio": 0.0, "leg_ratio": 0.0},
        "slim": {"chest_cm": -3.0, "waist_cm": -5.0, "hips_cm": -4.0, "left_bicep_cm": -2.2, "left_thigh_cm": -3.0, "arm_ratio": 0.0, "leg_ratio": 0.0},
        "athletic": {"chest_cm": 8.0, "waist_cm": -7.0, "hips_cm": -2.5, "left_bicep_cm": 5.5, "left_thigh_cm": 3.5, "arm_ratio": 0.0, "leg_ratio": 0.0},
        "curvy": {"chest_cm": 4.5, "waist_cm": 6.5, "hips_cm": 7.0, "left_bicep_cm": 1.5, "left_thigh_cm": 4.8, "arm_ratio": 0.0, "leg_ratio": 0.0},
    },
    "female": {
        "regular": {"chest_cm": 0.0, "waist_cm": 0.0, "hips_cm": 0.0, "left_bicep_cm": 0.0, "left_thigh_cm": 0.0, "arm_ratio": 0.0, "leg_ratio": 0.0},
        "slim": {"chest_cm": -2.0, "waist_cm": -4.0, "hips_cm": -3.0, "left_bicep_cm": -1.2, "left_thigh_cm": -2.5, "arm_ratio": 0.0, "leg_ratio": 0.0},
        "athletic": {"chest_cm": 2.5, "waist_cm": -4.5, "hips_cm": -0.5, "left_bicep_cm": 2.8, "left_thigh_cm": 1.9, "arm_ratio": 0.0, "leg_ratio": 0.0},
        "curvy": {"chest_cm": 3.5, "waist_cm": 2.5, "hips_cm": 7.0, "left_bicep_cm": 1.0, "left_thigh_cm": 5.2, "arm_ratio": 0.0, "leg_ratio": 0.0},
    },
    "neutral": {
        "regular": {"chest_cm": 0.0, "waist_cm": 0.0, "hips_cm": 0.0, "left_bicep_cm": 0.0, "left_thigh_cm": 0.0, "arm_ratio": 0.0, "leg_ratio": 0.0},
        "slim": {"chest_cm": -2.5, "waist_cm": -4.5, "hips_cm": -3.5, "left_bicep_cm": -1.7, "left_thigh_cm": -2.8, "arm_ratio": 0.0, "leg_ratio": 0.0},
        "athletic": {"chest_cm": 6.0, "waist_cm": -5.75, "hips_cm": -1.5, "left_bicep_cm": 4.2, "left_thigh_cm": 2.8, "arm_ratio": 0.0, "leg_ratio": 0.0},
        "curvy": {"chest_cm": 3.8, "waist_cm": 4.75, "hips_cm": 6.25, "left_bicep_cm": 1.1, "left_thigh_cm": 4.6, "arm_ratio": 0.0, "leg_ratio": 0.0},
    },
}

BASE_MUSCULARITY = {
    "slim": 35.0,
    "regular": 50.0,
    "athletic": 72.0,
    "curvy": 45.0,
}

BASE_BODY_FAT_PERCENT = {
    "male": {
        "slim": 12.0,
        "regular": 18.0,
        "athletic": 14.0,
        "curvy": 24.0,
    },
    "female": {
        "slim": 20.0,
        "regular": 28.0,
        "athletic": 23.0,
        "curvy": 34.0,
    },
    "neutral": {
        "slim": 16.0,
        "regular": 23.0,
        "athletic": 18.0,
        "curvy": 29.0,
    },
}


MEASUREMENT_RATIO_BOUNDS = {
    "chest_cm": (0.42, 0.72),
    "waist_cm": (0.34, 0.70),
    "hips_cm": (0.42, 0.74),
    "left_bicep_cm": (0.11, 0.21),
    "left_thigh_cm": (0.24, 0.42),
    # These bounds should cover realistic anthropometric ranges for the
    # current limb-length definition. The old upper bound (0.35) clipped
    # normal adult arms into systematically short values.
    "arm_length_cm": (0.34, 0.40),
    "leg_length_cm": (0.43, 0.53),
}

DEFAULT_INFERRED_WEIGHTS = {
    "chest_cm": 1.3,
    "waist_cm": 1.5,
    "hips_cm": 1.2,
    "left_bicep_cm": 0.9,
    "left_thigh_cm": 0.85,
    "arm_length_cm": 0.2,
    "leg_length_cm": 0.35,
}

DEFAULT_USER_WEIGHTS = {
    "chest_cm": 3.0,
    "waist_cm": 3.0,
    "hips_cm": 3.0,
    "left_bicep_cm": 1.2,
    "left_thigh_cm": 1.1,
    "arm_length_cm": 0.9,
    "leg_length_cm": 1.1,
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
        "lean": "slim",
        "average": "regular",
        "normal": "regular",
        "soft": "curvy",
        "plus": "curvy",
        "stout": "curvy",
    }
    body_key = aliases.get(body_key, body_key)
    if body_key not in {"slim", "regular", "athletic", "curvy"}:
        body_key = "regular"
    return body_key


def _apply_bmi_shape_refinement(
    *,
    targets: Dict[str, float],
    gender_key: str,
    body_key: str,
    bmi: float,
) -> None:
    # The base priors already fit the validation set fairly well on average,
    # so this refinement only nudges the edge cases that still look visually
    # off: especially very lean male slim/athletic bodies, which otherwise
    # keep too much torso and hip volume.
    if gender_key == "male":
        lean_factor = _clamp((21.0 - bmi) / 4.0, 0.0, 1.0)
        if body_key == "athletic" and lean_factor > 0:
            targets["chest_cm"] += 1.5 * lean_factor
            targets["waist_cm"] -= 2.0 * lean_factor
            targets["hips_cm"] -= 1.5 * lean_factor
            targets["left_bicep_cm"] += 1.2 * lean_factor
            targets["left_thigh_cm"] += 0.8 * lean_factor
        elif body_key == "slim" and lean_factor > 0:
            targets["chest_cm"] -= 2.0 * lean_factor
            targets["waist_cm"] -= 1.8 * lean_factor
            targets["hips_cm"] -= 1.5 * lean_factor
            targets["left_bicep_cm"] -= 0.8 * lean_factor
            targets["left_thigh_cm"] -= 1.0 * lean_factor

    if gender_key == "female":
        lean_factor = _clamp((20.5 - bmi) / 4.0, 0.0, 1.0)
        if body_key == "slim" and lean_factor > 0:
            targets["chest_cm"] -= 1.0 * lean_factor
            targets["waist_cm"] -= 1.5 * lean_factor
            targets["hips_cm"] -= 1.5 * lean_factor
            targets["left_bicep_cm"] -= 0.5 * lean_factor
            targets["left_thigh_cm"] -= 0.7 * lean_factor
        elif body_key == "athletic" and lean_factor > 0:
            targets["chest_cm"] += 0.5 * lean_factor
            targets["waist_cm"] -= 1.5 * lean_factor
            targets["hips_cm"] -= 0.75 * lean_factor
            targets["left_bicep_cm"] += 0.7 * lean_factor
            targets["left_thigh_cm"] += 0.5 * lean_factor


def _apply_body_composition_refinement(
    *,
    targets: Dict[str, float],
    gender_key: str,
    body_key: str,
    muscularity: float | None,
    body_fat_percentage: float | None,
) -> None:
    if muscularity is not None and muscularity > 0:
        base_muscularity = BASE_MUSCULARITY[body_key]
        muscularity_delta = _clamp((float(muscularity) - base_muscularity) / 35.0, -1.25, 1.25)
        chest_gain = {"male": 9.0, "female": 4.0, "neutral": 6.5}[gender_key]
        waist_gain = {"male": -5.5, "female": -3.0, "neutral": -4.25}[gender_key]
        hips_gain = {"male": -2.5, "female": -1.0, "neutral": -1.75}[gender_key]
        bicep_gain = {"male": 6.0, "female": 2.8, "neutral": 4.2}[gender_key]
        thigh_gain = {"male": 4.0, "female": 2.4, "neutral": 3.2}[gender_key]
        targets["chest_cm"] += muscularity_delta * chest_gain
        targets["waist_cm"] += muscularity_delta * waist_gain
        targets["hips_cm"] += muscularity_delta * hips_gain
        targets["left_bicep_cm"] += muscularity_delta * bicep_gain
        targets["left_thigh_cm"] += muscularity_delta * thigh_gain

    if body_fat_percentage is not None and body_fat_percentage > 0:
        base_body_fat = BASE_BODY_FAT_PERCENT[gender_key][body_key]
        body_fat_delta = _clamp((float(body_fat_percentage) - base_body_fat) / 10.0, -1.25, 1.25)
        chest_gain = {"male": 3.0, "female": 3.5, "neutral": 3.25}[gender_key]
        waist_gain = {"male": 8.5, "female": 6.5, "neutral": 7.5}[gender_key]
        hips_gain = {"male": 6.0, "female": 7.5, "neutral": 6.75}[gender_key]
        bicep_gain = {"male": 1.8, "female": 1.2, "neutral": 1.5}[gender_key]
        thigh_gain = {"male": 5.0, "female": 4.8, "neutral": 4.9}[gender_key]
        targets["chest_cm"] += body_fat_delta * chest_gain
        targets["waist_cm"] += body_fat_delta * waist_gain
        targets["hips_cm"] += body_fat_delta * hips_gain
        targets["left_bicep_cm"] += body_fat_delta * bicep_gain
        targets["left_thigh_cm"] += body_fat_delta * thigh_gain


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
        "left_bicep_cm": safe_height_cm * priors["bicep_ratio"] + priors["bmi_to_bicep"] * bmi_delta + adjustments["left_bicep_cm"],
        "left_thigh_cm": safe_height_cm * priors["thigh_ratio"] + priors["bmi_to_thigh"] * bmi_delta + adjustments["left_thigh_cm"],
        "arm_length_cm": safe_height_cm * (priors["arm_ratio"] + adjustments["arm_ratio"]),
        "leg_length_cm": safe_height_cm * (priors["leg_ratio"] + adjustments["leg_ratio"]),
    }

    _apply_bmi_shape_refinement(
        targets=targets,
        gender_key=gender_key,
        body_key=body_key,
        bmi=bmi,
    )
    _apply_body_composition_refinement(
        targets=targets,
        gender_key=gender_key,
        body_key=body_key,
        muscularity=muscularity,
        body_fat_percentage=body_fat_percentage,
    )

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
