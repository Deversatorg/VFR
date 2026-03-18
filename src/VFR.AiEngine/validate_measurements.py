import argparse
import json
import os
from typing import Any, Dict, List

import numpy as np
import smplx
import torch

from measurement_optimizer import calculate_measurements, optimize_smplx_betas


SUPPORTED_TARGETS = (
    "chest_cm",
    "waist_cm",
    "hips_cm",
    "arm_length_cm",
    "leg_length_cm",
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
        default=120,
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
        proportion_bias += np.clip((leg_length / max(height_cm, 1.0)) - 0.48, -0.06, 0.06)
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


def _compute_error_report(
    measured: Dict[str, torch.Tensor],
    targets: Dict[str, float],
) -> Dict[str, Dict[str, float]]:
    report: Dict[str, Dict[str, float]] = {}
    for measurement_name, target_value in targets.items():
        predicted_value = float(measured[measurement_name].detach().cpu().item())
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
    per_measurement_errors: Dict[str, List[float]] = {name: [] for name in SUPPORTED_TARGETS}
    baseline_errors: Dict[str, List[float]] = {name: [] for name in SUPPORTED_TARGETS}

    for case_result in case_results:
        for measurement_name, details in case_result["optimized"].items():
            per_measurement_errors[measurement_name].append(details["abs_error"])
        for measurement_name, details in case_result["heuristic"].items():
            baseline_errors[measurement_name].append(details["abs_error"])

    summary: Dict[str, Dict[str, float]] = {}
    for measurement_name in SUPPORTED_TARGETS:
        optimized_values = per_measurement_errors[measurement_name]
        if not optimized_values:
            continue
        heuristic_values = baseline_errors[measurement_name]
        summary[measurement_name] = {
            "optimized_mae": round(float(np.mean(optimized_values)), 4),
            "optimized_max_abs_error": round(float(np.max(optimized_values)), 4),
            "heuristic_mae": round(float(np.mean(heuristic_values)), 4),
            "heuristic_max_abs_error": round(float(np.max(heuristic_values)), 4),
        }
    return summary


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

        body_model = body_models[gender]
        heuristic_betas = _simulate_profile_betas(
            height_cm=case["height_cm"],
            weight_kg=case["weight_kg"],
            body_type=case["body_type"],
            device=torch_device,
            chest=case["targets"].get("chest_cm", 0.0),
            shoulder=case["shoulder"],
            waist=case["targets"].get("waist_cm", 0.0),
            hip=case["targets"].get("hips_cm", 0.0),
            arm_length=case["targets"].get("arm_length_cm", 0.0),
            leg_length=case["targets"].get("leg_length_cm", 0.0),
        )

        with torch.no_grad():
            heuristic_output = body_model(betas=heuristic_betas, return_verts=True)
        heuristic_measurements = calculate_measurements(
            vertices=heuristic_output.vertices,
            joints=heuristic_output.joints,
            target_height_cm=case["height_cm"],
        )

        optimized_betas = optimize_smplx_betas(
            target_measurements=case["targets"],
            smplx_model_path=args.model_path,
            gender=gender,
            num_iterations=args.iterations,
            device=args.device,
            target_height_cm=case["height_cm"],
            initial_betas=heuristic_betas.detach().cpu().numpy(),
        )
        optimized_betas_tensor = torch.tensor(optimized_betas, dtype=torch.float32, device=torch_device)

        with torch.no_grad():
            optimized_output = body_model(betas=optimized_betas_tensor, return_verts=True)
        optimized_measurements = calculate_measurements(
            vertices=optimized_output.vertices,
            joints=optimized_output.joints,
            target_height_cm=case["height_cm"],
        )

        heuristic_report = _compute_error_report(heuristic_measurements, case["targets"])
        optimized_report = _compute_error_report(optimized_measurements, case["targets"])

        case_results.append(
            {
                "name": case["name"],
                "gender": gender,
                "height_cm": case["height_cm"],
                "weight_kg": case["weight_kg"],
                "body_type": case["body_type"],
                "heuristic": heuristic_report,
                "optimized": optimized_report,
            }
        )

    report = {
        "case_count": len(case_results),
        "summary": _summarize_cases(case_results),
        "cases": case_results,
    }

    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=True, indent=2)

    print(json.dumps(report["summary"], ensure_ascii=True, indent=2))
    print(f"\nSaved full validation report to: {args.output}")


if __name__ == "__main__":
    main()
