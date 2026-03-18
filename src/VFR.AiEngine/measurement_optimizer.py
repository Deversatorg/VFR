import logging
from typing import Dict, Optional, Sequence, Tuple

import numpy as np
import smplx
import torch


logger = logging.getLogger("MeasurementOptimizer")

# Vertex loops extracted from the local SMPL-X topology via
# extract_vertex_loops.py.
MEASUREMENT_VERTICES = {
    "chest_circumference": [3573, 3315, 3314, 3897, 5449, 5531, 8183, 6645, 6077, 6078, 6334, 8340, 8339, 8338, 8342, 8341, 6005, 6003, 8179, 8178, 8262, 8263, 6796, 6134, 6133, 6150, 8267, 8216, 6815, 6814, 6813, 6640, 7188, 6623, 6142, 6143, 5487, 3382, 3381, 3872, 4452, 3892, 4069, 4070, 4071, 5482, 5554, 3389, 3372, 3373, 4050, 5550, 5549, 5444, 5445, 3240, 3242, 5647, 5648, 5644, 5645, 5646],
    "waist_circumference": [3335, 3308, 3293, 3550, 3549, 3547, 3546, 4400, 5940, 7136, 6307, 6308, 6310, 6311, 6056, 6071, 6098, 6329, 6070, 6222, 6221, 6236, 6235, 6278, 8240, 8239, 7137, 7138, 5493, 4402, 4401, 5517, 5520, 3517, 3474, 3475, 3460, 3461, 3307, 3568],
    "hips_circumference": [3454, 3562, 4145, 4144, 4084, 3842, 3841, 3495, 3494, 4321, 6255, 6256, 6596, 6597, 6828, 6888, 6889, 6323, 6215, 6202, 6201, 8356, 8363, 8386, 8379, 8378, 6635, 6634, 8389, 5575, 5695, 3884, 3885, 5684, 5685, 5692, 5669, 5662, 3440, 3441],
    "left_bicep_circumference": [3318, 3319, 3826, 3825, 3571, 4392, 3276, 3277, 3910, 3356, 3352, 3523, 3521, 5427, 3399, 3400, 5489, 6161, 6160, 8161, 6282, 6284, 6115, 6117, 6658, 6040, 6039, 7128, 6332, 6582, 6583, 6082, 6081, 6083, 6052, 6319, 6085, 6729, 5534, 3981, 3322, 3558, 3289, 3320],
    "left_thigh_circumference": [3770, 5702, 5701, 3858, 3797, 4131, 4086, 5706, 3794, 3792, 4133, 4134, 4110, 3480, 3477, 3574, 3482, 3465, 3464, 3867, 3501, 3500, 3993, 3773],
}

MEASUREMENT_JOINT_CHAINS = {
    "left_arm": [(16, 18), (18, 20)],
    "right_arm": [(17, 19), (19, 21)],
    "left_leg": [(1, 4), (4, 7)],
    "right_leg": [(2, 5), (5, 8)],
}

SUPPORTED_MEASUREMENTS = {
    "chest_cm",
    "waist_cm",
    "hips_cm",
    "arm_length_cm",
    "leg_length_cm",
}

DEFAULT_MEASUREMENT_WEIGHTS = {
    "chest_cm": 1.0,
    "waist_cm": 1.0,
    "hips_cm": 1.0,
    "arm_length_cm": 1.0,
    "leg_length_cm": 1.0,
}

LOOP_MEASUREMENT_MAP = {
    "chest_cm": "chest_circumference",
    "waist_cm": "waist_circumference",
    "hips_cm": "hips_circumference",
}


def _squeeze_single_sample(tensor: torch.Tensor, name: str) -> torch.Tensor:
    if tensor.ndim == 3:
        if tensor.shape[0] != 1:
            raise ValueError(f"{name} must contain a single sample, got batch size {tensor.shape[0]}.")
        return tensor[0]
    if tensor.ndim != 2:
        raise ValueError(f"{name} must have shape [N, 3] or [1, N, 3], got {tuple(tensor.shape)}.")
    return tensor


def _compute_height_cm(vertices: torch.Tensor) -> torch.Tensor:
    return (vertices[:, 1].max() - vertices[:, 1].min()) * 100.0


def normalize_to_target_height(
    vertices: torch.Tensor,
    joints: Optional[torch.Tensor],
    target_height_cm: Optional[float],
) -> Tuple[torch.Tensor, Optional[torch.Tensor], torch.Tensor, torch.Tensor]:
    normalized_vertices = _squeeze_single_sample(vertices, "vertices")
    normalized_joints = None if joints is None else _squeeze_single_sample(joints, "joints")

    current_height_cm = _compute_height_cm(normalized_vertices)
    scale = torch.ones((), dtype=normalized_vertices.dtype, device=normalized_vertices.device)

    if target_height_cm is not None and target_height_cm > 0:
        target_height_tensor = torch.tensor(
            float(target_height_cm),
            dtype=normalized_vertices.dtype,
            device=normalized_vertices.device,
        )
        scale = target_height_tensor / torch.clamp(current_height_cm, min=1e-6)
        normalized_vertices = normalized_vertices * scale
        if normalized_joints is not None:
            normalized_joints = normalized_joints * scale
        current_height_cm = _compute_height_cm(normalized_vertices)

    return normalized_vertices, normalized_joints, scale, current_height_cm


def _has_valid_loop(loop_name: str) -> bool:
    return len(MEASUREMENT_VERTICES.get(loop_name, [])) >= 3


def _loop_circumference_cm(vertices: torch.Tensor, loop_name: str) -> torch.Tensor:
    loop_indices = MEASUREMENT_VERTICES[loop_name]
    if len(loop_indices) < 3:
        raise RuntimeError(
            f"Vertex loop '{loop_name}' is not configured. "
            "Run extract_vertex_loops.py and paste the resulting indices into MEASUREMENT_VERTICES."
        )

    vertex_index_tensor = torch.tensor(loop_indices, dtype=torch.long, device=vertices.device)
    loop_vertices = vertices[vertex_index_tensor]
    shifted_loop_vertices = torch.roll(loop_vertices, shifts=-1, dims=0)
    edge_lengths = torch.linalg.norm(shifted_loop_vertices - loop_vertices, dim=1)
    return edge_lengths.sum() * 100.0


def _chain_length_cm(joints: torch.Tensor, chain: Sequence[Tuple[int, int]]) -> torch.Tensor:
    total = torch.zeros((), dtype=joints.dtype, device=joints.device)
    for joint_a, joint_b in chain:
        total = total + torch.linalg.norm(joints[joint_b] - joints[joint_a], dim=0)
    return total * 100.0


def calculate_measurements(
    vertices: torch.Tensor,
    joints: Optional[torch.Tensor] = None,
    target_height_cm: Optional[float] = None,
) -> Dict[str, torch.Tensor]:
    normalized_vertices, normalized_joints, scale, height_cm = normalize_to_target_height(
        vertices=vertices,
        joints=joints,
        target_height_cm=target_height_cm,
    )

    measurements: Dict[str, torch.Tensor] = {
        "height_cm": height_cm,
        "applied_scale": scale,
    }

    if _has_valid_loop("chest_circumference"):
        measurements["chest_cm"] = _loop_circumference_cm(normalized_vertices, "chest_circumference")
    if _has_valid_loop("waist_circumference"):
        measurements["waist_cm"] = _loop_circumference_cm(normalized_vertices, "waist_circumference")
    if _has_valid_loop("hips_circumference"):
        measurements["hips_cm"] = _loop_circumference_cm(normalized_vertices, "hips_circumference")
    if _has_valid_loop("left_bicep_circumference"):
        measurements["left_bicep_cm"] = _loop_circumference_cm(normalized_vertices, "left_bicep_circumference")
    if _has_valid_loop("left_thigh_circumference"):
        measurements["left_thigh_cm"] = _loop_circumference_cm(normalized_vertices, "left_thigh_circumference")

    if normalized_joints is not None:
        left_arm_cm = _chain_length_cm(normalized_joints, MEASUREMENT_JOINT_CHAINS["left_arm"])
        right_arm_cm = _chain_length_cm(normalized_joints, MEASUREMENT_JOINT_CHAINS["right_arm"])
        left_leg_cm = _chain_length_cm(normalized_joints, MEASUREMENT_JOINT_CHAINS["left_leg"])
        right_leg_cm = _chain_length_cm(normalized_joints, MEASUREMENT_JOINT_CHAINS["right_leg"])

        measurements["left_arm_length_cm"] = left_arm_cm
        measurements["right_arm_length_cm"] = right_arm_cm
        measurements["left_leg_length_cm"] = left_leg_cm
        measurements["right_leg_length_cm"] = right_leg_cm
        measurements["arm_length_cm"] = 0.5 * (left_arm_cm + right_arm_cm)
        measurements["leg_length_cm"] = 0.5 * (left_leg_cm + right_leg_cm)

    return measurements


def _prepare_initial_betas(
    initial_betas: Optional[np.ndarray],
    device: torch.device,
    dtype: torch.dtype,
) -> torch.nn.Parameter:
    if initial_betas is None:
        beta_values = torch.zeros((1, 10), dtype=dtype, device=device)
        return torch.nn.Parameter(beta_values)

    if torch.is_tensor(initial_betas):
        initial_array = initial_betas.detach().cpu().numpy()
    else:
        initial_array = np.asarray(initial_betas, dtype=np.float32)

    flattened = initial_array.reshape(-1).astype(np.float32)
    if flattened.shape[0] < 10:
        padded = np.zeros((10,), dtype=np.float32)
        padded[: flattened.shape[0]] = flattened
        flattened = padded
    elif flattened.shape[0] > 10:
        flattened = flattened[:10]

    beta_values = torch.tensor(flattened.reshape(1, 10), dtype=dtype, device=device)
    return torch.nn.Parameter(beta_values)


def optimize_smplx_betas(
    target_measurements: Dict[str, float],
    smplx_model_path: str,
    gender: str = "neutral",
    num_iterations: int = 120,
    learning_rate: float = 0.05,
    device: str = "cpu",
    regularization_weight: float = 0.01,
    target_height_cm: Optional[float] = None,
    initial_betas: Optional[np.ndarray] = None,
    measurement_weights: Optional[Dict[str, float]] = None,
    patience: int = 20,
    min_delta: float = 1e-5,
) -> np.ndarray:
    if not target_measurements:
        raise ValueError("target_measurements must not be empty.")

    unknown_measurements = sorted(set(target_measurements) - SUPPORTED_MEASUREMENTS)
    if unknown_measurements:
        raise ValueError(f"Unsupported measurement(s) for optimization: {unknown_measurements}")

    active_targets = {
        key: float(value)
        for key, value in target_measurements.items()
        if value is not None and float(value) > 0
    }
    if not active_targets:
        raise ValueError("No positive target measurements were provided.")

    for measurement_name in active_targets:
        loop_name = LOOP_MEASUREMENT_MAP.get(measurement_name)
        if loop_name and not _has_valid_loop(loop_name):
            raise RuntimeError(
                f"Cannot optimize '{measurement_name}' because '{loop_name}' is still a placeholder. "
                "Run extract_vertex_loops.py and paste the results into MEASUREMENT_VERTICES."
            )

    torch_device = torch.device(device)
    dtype = torch.float32
    body_model = smplx.create(
        model_path=smplx_model_path,
        model_type="smplx",
        gender=gender,
        num_betas=10,
        use_face_contour=False,
        ext="npz",
    ).to(torch_device)

    betas = _prepare_initial_betas(initial_betas=initial_betas, device=torch_device, dtype=dtype)
    optimizer = torch.optim.Adam([betas], lr=learning_rate)

    effective_weights = dict(DEFAULT_MEASUREMENT_WEIGHTS)
    if measurement_weights:
        effective_weights.update(measurement_weights)

    best_loss = float("inf")
    best_iteration = -1
    best_betas = betas.detach().clone()
    stale_iterations = 0

    logger.info(
        "Starting SMPL-X measurement optimization for %s with targets=%s, target_height_cm=%s",
        gender,
        active_targets,
        target_height_cm,
    )

    for iteration in range(num_iterations):
        optimizer.zero_grad()

        output = body_model(betas=betas, return_verts=True)
        current_measurements = calculate_measurements(
            vertices=output.vertices,
            joints=output.joints,
            target_height_cm=target_height_cm,
        )

        missing_measurements = [
            measurement_name
            for measurement_name in active_targets
            if measurement_name not in current_measurements
        ]
        if missing_measurements:
            raise RuntimeError(
                f"Optimizer could not compute required measurements: {missing_measurements}"
            )

        measurement_losses = []
        for measurement_name, target_value in active_targets.items():
            current_value = current_measurements[measurement_name]
            target_tensor = torch.tensor(target_value, dtype=dtype, device=torch_device)
            relative_error = (current_value - target_tensor) / torch.clamp(target_tensor.abs(), min=1.0)
            weight = float(effective_weights.get(measurement_name, 1.0))
            measurement_losses.append(weight * relative_error.pow(2))

        loss = torch.stack(measurement_losses).mean()
        if regularization_weight > 0:
            loss = loss + regularization_weight * betas.pow(2).mean()

        if not torch.isfinite(loss):
            raise RuntimeError("Optimization diverged: loss became non-finite.")

        loss.backward()
        optimizer.step()

        with torch.no_grad():
            betas.clamp_(-5.0, 5.0)

        current_loss = float(loss.detach().cpu().item())
        if current_loss + min_delta < best_loss:
            best_loss = current_loss
            best_iteration = iteration
            best_betas = betas.detach().clone()
            stale_iterations = 0
        else:
            stale_iterations += 1

        if iteration == 0 or (iteration + 1) % 10 == 0:
            current_values = {
                measurement_name: round(float(current_measurements[measurement_name].detach().cpu().item()), 3)
                for measurement_name in active_targets
            }
            logger.info(
                "Iteration %s/%s: loss=%.6f, measurements=%s",
                iteration + 1,
                num_iterations,
                current_loss,
                current_values,
            )

        if stale_iterations >= patience:
            logger.info(
                "Early stopping after %s iterations without meaningful improvement.",
                stale_iterations,
            )
            break

    with torch.no_grad():
        final_output = body_model(betas=best_betas, return_verts=True)
        final_measurements = calculate_measurements(
            vertices=final_output.vertices,
            joints=final_output.joints,
            target_height_cm=target_height_cm,
        )

    final_abs_errors = {
        measurement_name: round(
            abs(float(final_measurements[measurement_name].detach().cpu().item()) - target_value),
            3,
        )
        for measurement_name, target_value in active_targets.items()
    }

    logger.info(
        "Optimization finished at iteration %s with best_loss=%.6f and abs_errors=%s",
        best_iteration + 1,
        best_loss,
        final_abs_errors,
    )

    return best_betas.detach().cpu().numpy()


if __name__ == "__main__":
    example_targets = {
        "chest_cm": 100.0,
        "waist_cm": 82.0,
        "hips_cm": 98.0,
        "arm_length_cm": 64.0,
        "leg_length_cm": 92.0,
    }

    optimized = optimize_smplx_betas(
        target_measurements=example_targets,
        smplx_model_path="models",
        gender="neutral",
        target_height_cm=175.0,
        device="cpu",
    )
    print("Optimized betas:", optimized)
