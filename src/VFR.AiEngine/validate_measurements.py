import argparse
import json
import os
from typing import Any, Dict, List

import numpy as np
import smplx
import torch

from anthropometry import infer_measurement_targets
from measurement_optimizer import apply_proportion_warp, calculate_measurements, optimize_smplx_betas


SUPPORTED_TARGETS = (
    "chest_cm",
    "waist_cm",
    "hips_cm",
    "arm_length_cm",
    "leg_length_cm",
)

TORSO_TARGETS = (
    "chest_cm",
    "waist_cm",
    "hips_cm",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate SMPL-X measurement fitting against a set of target profiles."
    )
    parser.add_argument(
        "--cases",
        required=True,
        help="Path to a JSON file containing a list of validation cases.",
    )
    parser.add_argument(
        "--model-path",
        default=os.path.join(os.path.dirname(__file__), "models"),
        help="Path to the base SMPL-X models directory.",
    )
    parser.add_argument(
        "--output",
        default=os.path.join(os.path.dirname(__file__), "measurement_validation_report.json"),
        help="Where to save the JSON validation report.",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Torch device to use, for example 'cpu' or 'cuda'.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=160,
        help="Number of optimizer iterations per case.",
    )
    return parser.parse_args()


def _load_cases(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("cases"), list):
        return payload["cases"]
    raise ValueError("Cases JSON must be either a list or an object with a 'cases' array.")


def _simulate_profile_betas(
    *,
    height_cm: float,
    weight_kg: float,
    body_type: str,
    device: torch.device,
    chest: float = 0.0,
    shoulder: float = 0.0,
    waist: float = 0.0,
    hip: float = 0.0,
    arm_length: float = 0.0,
    leg_length: float = 0.0,
) -> torch.Tensor:
    height_m = max(height_cm / 100.0, 1e-6)
    bmi = weight_kg / (height_m ** 2)

    betas = torch.zeros((1, 10), dtype=torch.float32, device=device)
    bmi_offset = (bmi - 21.0) / 3.5
    betas[0, 0] = float(np.clip(bmi_offset, -1.75, 1.75))

    height_offset = (height_cm - 170.0) / 20.0
    betas[0, 1] = float(np.clip(height_offset, -1.0, 1.0)) * 0.15

    normalized_body_type = body_type.lower()
    if normalized_body_type == "slim":
        betas[0, 0] -= 0.25
    elif normalized_body_type == "athletic":
        betas[0, 0] -= 0.35
        betas[0, 1] += 0.05
    elif normalized_body_type in {"curvy", "plus"}:
        betas[0, 0] += 0.5

    bulk_signals = []
    if chest > 0:
        expected_chest = height_cm * 0.52
        bulk_signals.append((chest - expected_chest) / max(expected_chest, 1.0))
    if waist > 0:
        expected_waist = height_cm * 0.45
        bulk_signals.append((waist - expected_waist) / max(expected_waist, 1.0))
    if hip > 0:
        expected_hip = height_cm * 0.53
        bulk_signals.append((hip - expected_hip) / max(expected_hip, 1.0))

    if bulk_signals:
        bulk_bias = float(np.clip(sum(bulk_signals) / len(bulk_signals), -0.4, 0.6))
        betas[0, 0] += bulk_bias * 1.2

    proportion_bias = 0.0
    if arm_length > 0:
        proportion_bias += np.clip((arm_length / max(height_cm, 1.0)) - 0.37, -0.05, 0.05)
    if leg_length > 0:
        proportion_bias += np.clip((leg_length / max(height_cm, 1.0)) - 0.495, -0.06, 0.06)
    if proportion_bias != 0.0:
        betas[0, 1] += float(np.clip(proportion_bias, -0.08, 0.08))

    betas.clamp_(-2.5, 2.5)

    return betas


def _normalize_case(case: Dict[str, Any]) -> Dict[str, Any]:
    measurements = dict(case.get("measurements") or {})

    alias_pairs = {
        "chest": "chest_cm",
        "waist": "waist_cm",
        "hip": "hips_cm",
        "hips": "hips_cm",
        "arm_length": "arm_length_cm",
        "leg_length": "leg_length_cm",
    }
    for alias_key, canonical_key in alias_pairs.items():
        if alias_key in measurements and canonical_key not in measurements:
            measurements[canonical_key] = measurements[alias_key]

    targets = {
        measurement_name: float(measurements[measurement_name])
        for measurement_name in SUPPORTED_TARGETS
        if measurement_name in measurements and float(measurements[measurement_name]) > 0
    }
    if not targets:
        raise ValueError(
            f"Validation case '{case.get('name', 'unnamed_case')}' has no supported target measurements."
        )

    gender = str(case.get("gender", "neutral")).lower()
    if gender not in {"male", "female", "neutral"}:
        gender = "neutral"

    return {
        "name": case.get("name") or "unnamed_case",
        "gender": gender,
        "height_cm": float(case["height_cm"]),
        "weight_kg": float(case["weight_kg"]),
        "body_type": str(case.get("body_type", "average")),
        "shoulder": float(measurements.get("shoulder", 0.0)),
        "calf": float(measurements.get("calf", 0.0)),
        "torso_length": float(measurements.get("torso_length", 0.0)),
        "targets": targets,
    }


def _extract_predicted_values(
    measured: Dict[str, torch.Tensor],
    measurement_names: List[str],
) -> Dict[str, float]:
    return {
        measurement_name: float(measured[measurement_name].detach().cpu().item())
        for measurement_name in measurement_names
        if measurement_name in measured
    }


def _compute_error_report(
    predicted: Dict[str, float],
    targets: Dict[str, float],
) -> Dict[str, Dict[str, float]]:
    report: Dict[str, Dict[str, float]] = {}
    for measurement_name, target_value in targets.items():
        predicted_value = float(predicted[measurement_name])
        abs_error = abs(predicted_value - target_value)
        rel_error = abs_error / max(abs(target_value), 1.0)
        report[measurement_name] = {
            "target": round(target_value, 4),
            "predicted": round(predicted_value, 4),
            "abs_error": round(abs_error, 4),
            "rel_error": round(rel_error, 6),
        }
    return report


def _summarize_cases(case_results: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    category_errors = {
        "inference": {name: [] for name in SUPPORTED_TARGETS},
        "heuristic": {name: [] for name in SUPPORTED_TARGETS},
        "auto": {name: [] for name in SUPPORTED_TARGETS},
        "exact": {name: [] for name in SUPPORTED_TARGETS},
    }

    for case_result in case_results:
        for category_name in category_errors:
            for measurement_name, details in case_result[category_name].items():
                category_errors[category_name][measurement_name].append(details["abs_error"])

    summary: Dict[str, Dict[str, float]] = {}
    for measurement_name in SUPPORTED_TARGETS:
        if not category_errors["auto"][measurement_name]:
            continue
        summary[measurement_name] = {
            "inference_mae": round(float(np.mean(category_errors["inference"][measurement_name])), 4),
            "heuristic_mae": round(float(np.mean(category_errors["heuristic"][measurement_name])), 4),
            "auto_mae": round(float(np.mean(category_errors["auto"][measurement_name])), 4),
            "exact_mae": round(float(np.mean(category_errors["exact"][measurement_name])), 4),
            "inference_max_abs_error": round(float(np.max(category_errors["inference"][measurement_name])), 4),
            "heuristic_max_abs_error": round(float(np.max(category_errors["heuristic"][measurement_name])), 4),
            "auto_max_abs_error": round(float(np.max(category_errors["auto"][measurement_name])), 4),
            "exact_max_abs_error": round(float(np.max(category_errors["exact"][measurement_name])), 4),
        }
    return summary


def _mean_abs_error(report: Dict[str, Dict[str, float]]) -> float:
    if not report:
        return 0.0
    return float(np.mean([item["abs_error"] for item in report.values()]))


def _build_worst_cases(case_results: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, float]]:
    ranked = sorted(
        case_results,
        key=lambda case_result: _mean_abs_error(case_result["auto"]),
        reverse=True,
    )
    return [
        {
            "name": case_result["name"],
            "auto_mean_abs_error": round(_mean_abs_error(case_result["auto"]), 4),
            "exact_mean_abs_error": round(_mean_abs_error(case_result["exact"]), 4),
            "inference_mean_abs_error": round(_mean_abs_error(case_result["inference"]), 4),
        }
        for case_result in ranked[:limit]
    ]


def main() -> None:
    args = _parse_args()
    torch_device = torch.device(args.device)
    cases = [_normalize_case(case) for case in _load_cases(args.cases)]

    body_models: Dict[str, Any] = {}
    case_results: List[Dict[str, Any]] = []

    for case in cases:
        gender = case["gender"]
        if gender not in body_models:
            body_models[gender] = smplx.create(
                model_path=args.model_path,
                model_type="smplx",
                gender=gender,
                num_betas=10,
                use_face_contour=False,
                ext="npz",
            ).to(torch_device)

        inferred_targets, inferred_weights, inferred_sources = infer_measurement_targets(
            height_cm=case["height_cm"],
            weight_kg=case["weight_kg"],
            body_type=case["body_type"],
            gender=gender,
            overrides={},
            hints={
                "shoulder_cm": case["shoulder"],
                "calf_cm": case["calf"],
                "torso_length_cm": case["torso_length"],
            },
        )

        body_model = body_models[gender]
        heuristic_betas = _simulate_profile_betas(
            height_cm=case["height_cm"],
            weight_kg=case["weight_kg"],
            body_type=case["body_type"],
            device=torch_device,
            chest=inferred_targets.get("chest_cm", 0.0),
            shoulder=case["shoulder"],
            waist=inferred_targets.get("waist_cm", 0.0),
            hip=inferred_targets.get("hips_cm", 0.0),
            arm_length=inferred_targets.get("arm_length_cm", 0.0),
            leg_length=inferred_targets.get("leg_length_cm", 0.0),
        )

        with torch.no_grad():
            heuristic_output = body_model(betas=heuristic_betas, return_verts=True)
        heuristic_vertices, heuristic_joints, _ = apply_proportion_warp(
            vertices=heuristic_output.vertices,
            joints=heuristic_output.joints,
            parents=body_model.parents,
            weights=body_model.lbs_weights,
            target_measurements=inferred_targets,
            target_height_cm=case["height_cm"],
        )
        heuristic_measurements = calculate_measurements(
            vertices=heuristic_vertices,
            joints=heuristic_joints,
            target_height_cm=case["height_cm"],
        )

        inferred_shape_targets = {
            measurement_name: inferred_targets[measurement_name]
            for measurement_name in TORSO_TARGETS
            if measurement_name in inferred_targets
        }
        inferred_shape_weights = {
            measurement_name: inferred_weights[measurement_name]
            for measurement_name in inferred_shape_targets
            if measurement_name in inferred_weights
        }

        auto_betas = optimize_smplx_betas(
            target_measurements=inferred_shape_targets,
            smplx_model_path=args.model_path,
            gender=gender,
            num_iterations=max(100, min(args.iterations, 140)),
            device=args.device,
            target_height_cm=case["height_cm"],
            initial_betas=heuristic_betas.detach().cpu().numpy(),
            measurement_weights=inferred_shape_weights,
        )
        auto_betas_tensor = torch.tensor(auto_betas, dtype=torch.float32, device=torch_device)

        with torch.no_grad():
            auto_output = body_model(betas=auto_betas_tensor, return_verts=True)
        auto_vertices, auto_joints, _ = apply_proportion_warp(
            vertices=auto_output.vertices,
            joints=auto_output.joints,
            parents=body_model.parents,
            weights=body_model.lbs_weights,
            target_measurements=inferred_targets,
            target_height_cm=case["height_cm"],
        )
        auto_measurements = calculate_measurements(
            vertices=auto_vertices,
            joints=auto_joints,
            target_height_cm=case["height_cm"],
        )

        exact_shape_targets = {
            measurement_name: case["targets"][measurement_name]
            for measurement_name in TORSO_TARGETS
            if measurement_name in case["targets"]
        }
        exact_betas = optimize_smplx_betas(
            target_measurements=exact_shape_targets,
            smplx_model_path=args.model_path,
            gender=gender,
            num_iterations=args.iterations,
            device=args.device,
            target_height_cm=case["height_cm"],
            initial_betas=auto_betas,
        )
        exact_betas_tensor = torch.tensor(exact_betas, dtype=torch.float32, device=torch_device)

        with torch.no_grad():
            exact_output = body_model(betas=exact_betas_tensor, return_verts=True)
        exact_vertices, exact_joints, _ = apply_proportion_warp(
            vertices=exact_output.vertices,
            joints=exact_output.joints,
            parents=body_model.parents,
            weights=body_model.lbs_weights,
            target_measurements=case["targets"],
            target_height_cm=case["height_cm"],
        )
        exact_measurements = calculate_measurements(
            vertices=exact_vertices,
            joints=exact_joints,
            target_height_cm=case["height_cm"],
        )

        target_measurement_names = list(case["targets"].keys())
        inference_report = _compute_error_report(inferred_targets, case["targets"])
        heuristic_report = _compute_error_report(
            _extract_predicted_values(heuristic_measurements, target_measurement_names),
            case["targets"],
        )
        auto_report = _compute_error_report(
            _extract_predicted_values(auto_measurements, target_measurement_names),
            case["targets"],
        )
        exact_report = _compute_error_report(
            _extract_predicted_values(exact_measurements, target_measurement_names),
            case["targets"],
        )

        case_results.append(
            {
                "name": case["name"],
                "gender": gender,
                "height_cm": case["height_cm"],
                "weight_kg": case["weight_kg"],
                "body_type": case["body_type"],
                "target_sources": inferred_sources,
                "inferred_targets": inferred_targets,
                "inference": inference_report,
                "heuristic": heuristic_report,
                "auto": auto_report,
                "exact": exact_report,
            }
        )

    report = {
        "case_count": len(case_results),
        "summary": _summarize_cases(case_results),
        "worst_auto_cases": _build_worst_cases(case_results),
        "cases": case_results,
    }

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=True, indent=2)

    print(json.dumps(report["summary"], ensure_ascii=True, indent=2))
    print("\nWorst auto-generation cases:")
    print(json.dumps(report["worst_auto_cases"], ensure_ascii=True, indent=2))
    print(f"\nSaved full validation report to: {args.output}")


if __name__ == "__main__":
    main()
