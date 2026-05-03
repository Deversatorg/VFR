"""SMPL-X measurement calculation, corrective warping, and beta optimization."""

import logging
from typing import Dict, Optional, Sequence, Tuple

import numpy as np
import smplx
import torch


logger = logging.getLogger("MeasurementOptimizer")

# Vertex loops extracted from the local SMPL-X topology via
# vfr_ai_engine.non_runtime.validation.extract_vertex_loops.
MEASUREMENT_VERTICES = {
    "chest_circumference": [3573, 3315, 3314, 3897, 5449, 5531, 8183, 6645, 6077, 6078, 6334, 8340, 8339, 8338, 8342, 8341, 6005, 6003, 8179, 8178, 8262, 8263, 6796, 6134, 6133, 6150, 8267, 8216, 6815, 6814, 6813, 6640, 7188, 6623, 6142, 6143, 5487, 3382, 3381, 3872, 4452, 3892, 4069, 4070, 4071, 5482, 5554, 3389, 3372, 3373, 4050, 5550, 5549, 5444, 5445, 3240, 3242, 5647, 5648, 5644, 5645, 5646],
    "waist_circumference": [3335, 3308, 3293, 3550, 3549, 3547, 3546, 4400, 5940, 7136, 6307, 6308, 6310, 6311, 6056, 6071, 6098, 6329, 6070, 6222, 6221, 6236, 6235, 6278, 8240, 8239, 7137, 7138, 5493, 4402, 4401, 5517, 5520, 3517, 3474, 3475, 3460, 3461, 3307, 3568],
    "hips_circumference": [3454, 3562, 4145, 4144, 4084, 3842, 3841, 3495, 3494, 4321, 6255, 6256, 6596, 6597, 6828, 6888, 6889, 6323, 6215, 6202, 6201, 8356, 8363, 8386, 8379, 8378, 6635, 6634, 8389, 5575, 5695, 3884, 3885, 5684, 5685, 5692, 5669, 5662, 3440, 3441],
    # Upper-torso slice extracted around 75% standing height. This remains a
    # proxy loop, but it is distinct from the chest contour so shoulder targets
    # can move independently instead of fighting the chest measurement directly.
    "shoulder_circumference": [3313, 3310, 4397, 4169, 3835, 3834, 3979, 3980, 3334, 5439, 5440, 5643, 5641, 5640, 5637, 5636, 3984, 3983, 3895, 3894, 5657, 5938, 8351, 6642, 6643, 6731, 6732, 8330, 8331, 8334, 8335, 8337, 8174, 8173, 6097, 6728, 6727, 6589, 6590, 6913, 7133, 6073, 6076, 6659, 6661, 6146, 7233, 6105, 6880, 7193, 8272, 7189, 7190, 8245, 8243, 8241, 8242, 8327, 5947, 5633, 5522, 5521, 5523, 5525, 4454, 4453, 5560, 4457, 4136, 3342, 4497, 3385, 3913, 3911],
    # Mid-upper-arm contour extracted from an X-normal plane at 48% of the
    # positive arm span. The average proxy currently mirrors the left side.
    "bicep_circumference": [4386, 4387, 4267, 4268, 4373, 4262, 4261, 4303, 4304, 4355, 4356, 4336, 4335, 4351, 4378, 4271, 4272, 4345],
    # Placeholder average proxy loop; currently mirrors the extracted left side.
    "thigh_circumference": [3770, 5702, 5701, 3858, 3797, 4131, 4086, 5706, 3794, 3792, 4133, 4134, 4110, 3480, 3477, 3574, 3482, 3465, 3464, 3867, 3501, 3500, 3993, 3773],
    "left_bicep_circumference": [4386, 4387, 4267, 4268, 4373, 4262, 4261, 4303, 4304, 4355, 4356, 4336, 4335, 4351, 4378, 4271, 4272, 4345],
    "left_thigh_circumference": [3770, 5702, 5701, 3858, 3797, 4131, 4086, 5706, 3794, 3792, 4133, 4134, 4110, 3480, 3477, 3574, 3482, 3465, 3464, 3867, 3501, 3500, 3993, 3773],
}

MEASUREMENT_JOINT_CHAINS = {
    # These paths are tuned to the semantics of the UI inputs.
    # "Arm length" is closer to collar -> shoulder -> elbow -> wrist than a
    # full fingertip reach, and "leg length" behaves much closer to
    # pelvis/hip -> knee -> ankle than to a full toe-inclusive path.
    "left_arm": [(13, 16), (16, 18), (18, 20)],
    "right_arm": [(14, 17), (17, 19), (19, 21)],
    "left_leg": [(0, 1), (1, 4), (4, 7)],
    "right_leg": [(0, 2), (2, 5), (5, 8)],
}

MEASUREMENT_JOINT_PATHS = {
    "left_arm": [13, 16, 18, 20],
    "right_arm": [14, 17, 19, 21],
    "left_leg": [0, 1, 4, 7],
    "right_leg": [0, 2, 5, 8],
}

LIMB_WARP_SCALE_LIMITS = {
    "arm_length_cm": (0.90, 1.18),
    "leg_length_cm": (0.90, 1.12),
}

TORSO_HEIGHT_PATH = [0, 3, 6, 9, 12, 15]
TORSO_WARP_SCALE_LIMITS = (0.90, 1.18)

SUPPORTED_MEASUREMENTS = {
    "chest_cm",
    "waist_cm",
    "hips_cm",
    "shoulder_circumference_cm",
    "bicep_circumference_cm",
    "thigh_circumference_cm",
    "left_bicep_cm",
    "left_thigh_cm",
    "arm_length_cm",
    "leg_length_cm",
}

DEFAULT_MEASUREMENT_WEIGHTS = {
    "chest_cm": 1.0,
    "waist_cm": 1.0,
    "hips_cm": 1.0,
    "shoulder_circumference_cm": 0.3,
    "bicep_circumference_cm": 0.5,
    "thigh_circumference_cm": 0.5,
    "left_bicep_cm": 0.9,
    "left_thigh_cm": 0.85,
    "arm_length_cm": 0.35,
    "leg_length_cm": 0.5,
}

SHAPE_PRESERVATION_BETA_WEIGHTS = (
    1.8,  # beta[0]: overall bulk / weight
    3.2,  # beta[1]: muscle taper / V-shape
    3.0,  # beta[2]: roundness / softness
    1.2,
    0.8,
    0.8,
    0.6,
    0.5,
    0.5,
    0.5,
)

LOOP_MEASUREMENT_MAP = {
    "chest_cm": "chest_circumference",
    "waist_cm": "waist_circumference",
    "hips_cm": "hips_circumference",
    "shoulder_circumference_cm": "shoulder_circumference",
    "bicep_circumference_cm": "bicep_circumference",
    "thigh_circumference_cm": "thigh_circumference",
    "left_bicep_cm": "left_bicep_circumference",
    "left_thigh_cm": "left_thigh_circumference",
}
STRICT_EXPLICIT_CIRCUMFERENCE_KEYS = {
    "chest_cm",
    "waist_cm",
    "hips_cm",
    "shoulder_circumference_cm",
    "bicep_circumference_cm",
    "thigh_circumference_cm",
    "left_bicep_cm",
    "left_thigh_cm",
}

CIRCUMFERENCE_WARP_SPECS = {
    "shoulder_circumference_cm": {"loop_name": "shoulder_circumference", "band_ratio": 0.055, "min_scale": 0.55, "max_scale": 3.5},
    "chest_cm": {"loop_name": "chest_circumference", "band_ratio": 0.060, "min_scale": 0.45, "max_scale": 3.0},
    "waist_cm": {"loop_name": "waist_circumference", "band_ratio": 0.065, "min_scale": 0.35, "max_scale": 3.5},
    "hips_cm": {"loop_name": "hips_circumference", "band_ratio": 0.075, "min_scale": 0.40, "max_scale": 3.0},
    "bicep_circumference_cm": {"loop_name": "bicep_circumference", "band_ratio": 0.040, "min_scale": 0.45, "max_scale": 3.0},
    "thigh_circumference_cm": {"loop_name": "thigh_circumference", "band_ratio": 0.050, "min_scale": 0.45, "max_scale": 3.0},
    "left_bicep_cm": {"loop_name": "left_bicep_circumference", "band_ratio": 0.040, "min_scale": 0.45, "max_scale": 3.0},
    "left_thigh_cm": {"loop_name": "left_thigh_circumference", "band_ratio": 0.050, "min_scale": 0.45, "max_scale": 3.0},
}
CIRCUMFERENCE_WARP_ORDER = (
    "shoulder_circumference_cm",
    "chest_cm",
    "waist_cm",
    "hips_cm",
    "bicep_circumference_cm",
    "thigh_circumference_cm",
    "left_bicep_cm",
    "left_thigh_cm",
)


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
            "Run vfr_ai_engine.non_runtime.validation.extract_vertex_loops and paste the resulting indices into MEASUREMENT_VERTICES."
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


def _prepare_parent_tensor(
    parents: torch.Tensor | np.ndarray | Sequence[int],
    device: torch.device,
) -> torch.Tensor:
    if torch.is_tensor(parents):
        parent_tensor = parents.to(device=device, dtype=torch.long)
    else:
        parent_tensor = torch.tensor(list(parents), dtype=torch.long, device=device)
    return parent_tensor.reshape(-1)


def _prepare_weights_tensor(
    weights: torch.Tensor | np.ndarray,
    device: torch.device,
    dtype: torch.dtype,
) -> torch.Tensor:
    if torch.is_tensor(weights):
        weight_tensor = weights.to(device=device, dtype=dtype)
    else:
        weight_tensor = torch.tensor(weights, device=device, dtype=dtype)
    if weight_tensor.ndim != 2:
        raise ValueError(f"weights must have shape [V, J], got {tuple(weight_tensor.shape)}.")
    return weight_tensor


def _build_descendants(parents: torch.Tensor) -> Dict[int, list[int]]:
    children: Dict[int, list[int]] = {joint_idx: [] for joint_idx in range(int(parents.numel()))}
    for child_idx, parent_idx in enumerate(parents.tolist()):
        if parent_idx >= 0:
            children[parent_idx].append(child_idx)

    descendants: Dict[int, list[int]] = {}

    def collect(node_idx: int) -> list[int]:
        cached = descendants.get(node_idx)
        if cached is not None:
            return cached

        result: list[int] = []
        for child_idx in children[node_idx]:
            result.append(child_idx)
            result.extend(collect(child_idx))
        descendants[node_idx] = result
        return result

    for joint_idx in children:
        collect(joint_idx)

    return descendants


def _scale_joint_path(
    joints: torch.Tensor,
    descendants: Dict[int, list[int]],
    path: Sequence[int],
    scale_factor: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    if len(path) < 2:
        return joints, torch.zeros_like(joints)

    old_joints = joints.clone()
    new_joints = joints.clone()
    joint_deltas = torch.zeros_like(joints)
    moved_joints = set(path)

    for segment_idx in range(1, len(path)):
        parent_idx = path[segment_idx - 1]
        child_idx = path[segment_idx]
        new_joints[child_idx] = new_joints[parent_idx] + scale_factor * (
            old_joints[child_idx] - old_joints[parent_idx]
        )
        joint_deltas[child_idx] = new_joints[child_idx] - old_joints[child_idx]

    for joint_idx in path[1:]:
        delta = joint_deltas[joint_idx]
        if float(torch.linalg.norm(delta).detach().cpu().item()) <= 1e-8:
            continue

        for descendant_idx in descendants.get(joint_idx, []):
            if descendant_idx in moved_joints:
                continue
            new_joints[descendant_idx] = old_joints[descendant_idx] + delta
            joint_deltas[descendant_idx] = delta

    return new_joints, joint_deltas


def _apply_joint_deltas_to_vertices(
    vertices: torch.Tensor,
    joint_deltas: torch.Tensor,
    weights: torch.Tensor,
) -> torch.Tensor:
    usable_joint_count = min(joint_deltas.shape[0], weights.shape[1])
    if usable_joint_count <= 0:
        return vertices

    vertex_offsets = weights[:, :usable_joint_count] @ joint_deltas[:usable_joint_count]
    return vertices + vertex_offsets


def _warp_limb_pair(
    vertices: torch.Tensor,
    joints: torch.Tensor,
    parents: torch.Tensor,
    weights: torch.Tensor,
    measurement_name: str,
    target_length_cm: float,
) -> tuple[torch.Tensor, torch.Tensor, float]:
    if measurement_name == "arm_length_cm":
        left_key, right_key = "left_arm", "right_arm"
    elif measurement_name == "leg_length_cm":
        left_key, right_key = "left_leg", "right_leg"
    else:
        return vertices, joints, 1.0

    left_current = _chain_length_cm(joints, MEASUREMENT_JOINT_CHAINS[left_key])
    right_current = _chain_length_cm(joints, MEASUREMENT_JOINT_CHAINS[right_key])
    current_average = 0.5 * (left_current + right_current)
    current_average_value = float(current_average.detach().cpu().item())
    if current_average_value <= 1e-6 or target_length_cm <= 0:
        return vertices, joints, 1.0

    min_scale, max_scale = LIMB_WARP_SCALE_LIMITS[measurement_name]
    scale_factor = max(min(float(target_length_cm) / current_average_value, max_scale), min_scale)
    if abs(scale_factor - 1.0) <= 1e-3:
        return vertices, joints, 1.0

    descendants = _build_descendants(parents)
    warped_joints = joints
    accumulated_deltas = torch.zeros_like(joints)

    for side_key in (left_key, right_key):
        path = MEASUREMENT_JOINT_PATHS[side_key]
        warped_joints, side_deltas = _scale_joint_path(
            joints=warped_joints,
            descendants=descendants,
            path=path,
            scale_factor=scale_factor,
        )
        accumulated_deltas = accumulated_deltas + side_deltas

    warped_vertices = _apply_joint_deltas_to_vertices(
        vertices=vertices,
        joint_deltas=accumulated_deltas,
        weights=weights,
    )

    return warped_vertices, warped_joints, scale_factor


def _apply_height_compensation(
    vertices: torch.Tensor,
    joints: torch.Tensor,
    parents: torch.Tensor,
    weights: torch.Tensor,
    target_height_cm: float,
) -> tuple[torch.Tensor, torch.Tensor, float]:
    current_height_cm = float(_compute_height_cm(vertices).detach().cpu().item())
    if current_height_cm <= 1e-6 or target_height_cm <= 0:
        return vertices, joints, 1.0

    min_scale, max_scale = TORSO_WARP_SCALE_LIMITS
    scale_factor = max(min(float(target_height_cm) / current_height_cm, max_scale), min_scale)
    if abs(scale_factor - 1.0) <= 1e-3:
        return vertices, joints, 1.0

    descendants = _build_descendants(parents)
    warped_joints, joint_deltas = _scale_joint_path(
        joints=joints,
        descendants=descendants,
        path=TORSO_HEIGHT_PATH,
        scale_factor=scale_factor,
    )
    warped_vertices = _apply_joint_deltas_to_vertices(
        vertices=vertices,
        joint_deltas=joint_deltas,
        weights=weights,
    )
    return warped_vertices, warped_joints, scale_factor


def _warp_circumference_band(
    vertices: torch.Tensor,
    measurement_name: str,
    target_circumference_cm: float,
) -> tuple[torch.Tensor, float]:
    warp_spec = CIRCUMFERENCE_WARP_SPECS.get(measurement_name)
    if warp_spec is None or target_circumference_cm <= 0:
        return vertices, 1.0

    loop_name = warp_spec["loop_name"]
    if not _has_valid_loop(loop_name):
        return vertices, 1.0

    current_circumference_cm = _loop_circumference_cm(vertices, loop_name)
    current_circumference_value = float(current_circumference_cm.detach().cpu().item())
    if current_circumference_value <= 1e-6:
        return vertices, 1.0

    min_scale = float(warp_spec["min_scale"])
    max_scale = float(warp_spec["max_scale"])
    scale_factor = torch.clamp(
        torch.tensor(float(target_circumference_cm), dtype=vertices.dtype, device=vertices.device)
        / torch.clamp(current_circumference_cm, min=1e-6),
        min=min_scale,
        max=max_scale,
    )
    scale_factor_value = float(scale_factor.detach().cpu().item())
    if abs(scale_factor_value - 1.0) <= 1e-3:
        return vertices, 1.0

    loop_indices = torch.tensor(
        MEASUREMENT_VERTICES[loop_name],
        dtype=torch.long,
        device=vertices.device,
    )
    loop_vertices = vertices[loop_indices]
    loop_center = loop_vertices.mean(dim=0)
    body_height_m = torch.clamp(_compute_height_cm(vertices) / 100.0, min=1e-3)
    half_height = torch.clamp(
        body_height_m * float(warp_spec["band_ratio"]),
        min=0.02,
    )

    vertical_distance = torch.abs(vertices[:, 1] - loop_center[1])
    band_weight = torch.clamp(1.0 - (vertical_distance / half_height), min=0.0).pow(2).unsqueeze(1)

    radial_xz = vertices[:, [0, 2]] - loop_center[[0, 2]]
    scaled_xz = loop_center[[0, 2]] + radial_xz * (1.0 + band_weight * (scale_factor - 1.0))

    warped_vertices = vertices.clone()
    warped_vertices[:, 0] = scaled_xz[:, 0]
    warped_vertices[:, 2] = scaled_xz[:, 1]
    return warped_vertices, scale_factor_value


def apply_proportion_warp(
    vertices: torch.Tensor,
    joints: Optional[torch.Tensor],
    parents: torch.Tensor | np.ndarray | Sequence[int],
    weights: torch.Tensor | np.ndarray,
    target_measurements: Optional[Dict[str, float]] = None,
    target_height_cm: Optional[float] = None,
    strict_circumference_keys: Optional[Sequence[str]] = None,
) -> tuple[torch.Tensor, Optional[torch.Tensor], Dict[str, float]]:
    normalized_vertices, normalized_joints, _, _ = normalize_to_target_height(
        vertices=vertices,
        joints=joints,
        target_height_cm=target_height_cm,
    )
    if normalized_joints is None or not target_measurements:
        return normalized_vertices, normalized_joints, {}

    parent_tensor = _prepare_parent_tensor(parents, device=normalized_vertices.device)
    weight_tensor = _prepare_weights_tensor(
        weights=weights,
        device=normalized_vertices.device,
        dtype=normalized_vertices.dtype,
    )

    warped_vertices = normalized_vertices
    warped_joints = normalized_joints
    applied_scales: Dict[str, float] = {}
    strict_circumference_key_set = {
        key
        for key in (strict_circumference_keys or ())
        if key in CIRCUMFERENCE_WARP_SPECS
    }

    leg_target = float(target_measurements.get("leg_length_cm", 0.0) or 0.0)
    if leg_target > 0:
        warped_vertices, warped_joints, leg_scale = _warp_limb_pair(
            vertices=warped_vertices,
            joints=warped_joints,
            parents=parent_tensor,
            weights=weight_tensor,
            measurement_name="leg_length_cm",
            target_length_cm=leg_target,
        )
        if abs(leg_scale - 1.0) > 1e-3:
            applied_scales["leg_length_cm"] = round(leg_scale, 4)
            if target_height_cm is not None and target_height_cm > 0:
                warped_vertices, warped_joints, torso_scale = _apply_height_compensation(
                    vertices=warped_vertices,
                    joints=warped_joints,
                    parents=parent_tensor,
                    weights=weight_tensor,
                    target_height_cm=float(target_height_cm),
                )
                if abs(torso_scale - 1.0) > 1e-3:
                    applied_scales["torso_height_cm"] = round(torso_scale, 4)
                current_height_after_comp = float(_compute_height_cm(warped_vertices).detach().cpu().item())
                if abs(current_height_after_comp - float(target_height_cm)) > 0.5:
                    warped_vertices, warped_joints, _, _ = normalize_to_target_height(
                        vertices=warped_vertices,
                        joints=warped_joints,
                        target_height_cm=target_height_cm,
                    )

    arm_target = float(target_measurements.get("arm_length_cm", 0.0) or 0.0)
    if arm_target > 0:
        warped_vertices, warped_joints, arm_scale = _warp_limb_pair(
            vertices=warped_vertices,
            joints=warped_joints,
            parents=parent_tensor,
            weights=weight_tensor,
            measurement_name="arm_length_cm",
            target_length_cm=arm_target,
        )
        if abs(arm_scale - 1.0) > 1e-3:
            applied_scales["arm_length_cm"] = round(arm_scale, 4)

    for measurement_name in CIRCUMFERENCE_WARP_ORDER:
        if measurement_name not in strict_circumference_key_set:
            continue
        circumference_target = float(target_measurements.get(measurement_name, 0.0) or 0.0)
        if circumference_target <= 0:
            continue
        warped_vertices, circumference_scale = _warp_circumference_band(
            vertices=warped_vertices,
            measurement_name=measurement_name,
            target_circumference_cm=circumference_target,
        )
        if abs(circumference_scale - 1.0) > 1e-3:
            applied_scales[measurement_name] = round(circumference_scale, 4)

    return warped_vertices, warped_joints, applied_scales


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
    if _has_valid_loop("shoulder_circumference"):
        measurements["shoulder_circumference_cm"] = _loop_circumference_cm(normalized_vertices, "shoulder_circumference")
    if _has_valid_loop("bicep_circumference"):
        measurements["bicep_circumference_cm"] = _loop_circumference_cm(normalized_vertices, "bicep_circumference")
    if _has_valid_loop("thigh_circumference"):
        measurements["thigh_circumference_cm"] = _loop_circumference_cm(normalized_vertices, "thigh_circumference")
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


def _resolve_constraint_weights(
    *,
    active_targets: Dict[str, float],
    explicit_keys: Optional[Sequence[str]],
    shape_preservation_weight: float,
    regularization_weight: float,
) -> tuple[float, float, list[str]]:
    explicit_key_set = {
        str(key)
        for key in (explicit_keys or ())
        if key is not None and str(key).strip()
    }
    active_explicit_measurements = sorted(explicit_key_set & set(active_targets))

    effective_shape_preservation_weight = float(shape_preservation_weight)
    effective_regularization_weight = float(regularization_weight)

    if explicit_key_set:
        has_explicit_circumference_targets = bool(explicit_key_set & STRICT_EXPLICIT_CIRCUMFERENCE_KEYS)
        if has_explicit_circumference_targets:
            effective_shape_preservation_weight = min(effective_shape_preservation_weight, 0.002)
            effective_regularization_weight = min(effective_regularization_weight, 0.0001)
        else:
            effective_shape_preservation_weight = min(effective_shape_preservation_weight, 0.005)
            effective_regularization_weight = min(effective_regularization_weight, 0.0005)

    return (
        effective_shape_preservation_weight,
        effective_regularization_weight,
        active_explicit_measurements,
    )


def optimize_smplx_betas(
    target_measurements: Dict[str, float],
    smplx_model_path: str,
    gender: str = "neutral",
    num_iterations: int = 120,
    learning_rate: float = 0.05,
    device: str = "cpu",
    regularization_weight: float = 0.003,
    target_height_cm: Optional[float] = None,
    initial_betas: Optional[np.ndarray] = None,
    shape_preservation_weight: float = 0.2,
    measurement_weights: Optional[Dict[str, float]] = None,
    explicit_keys: Optional[Sequence[str]] = None,
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
                "Run vfr_ai_engine.non_runtime.validation.extract_vertex_loops and paste the results into MEASUREMENT_VERTICES."
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
    initial_beta_anchor = betas.detach().clone() if initial_betas is not None else None
    beta_preservation_weights = torch.tensor(
        SHAPE_PRESERVATION_BETA_WEIGHTS,
        dtype=dtype,
        device=torch_device,
    ).reshape(1, -1)
    optimizer = torch.optim.Adam([betas], lr=learning_rate)

    effective_weights = dict(DEFAULT_MEASUREMENT_WEIGHTS)
    if measurement_weights:
        effective_weights.update(measurement_weights)
    (
        effective_shape_preservation_weight,
        effective_regularization_weight,
        active_explicit_measurements,
    ) = _resolve_constraint_weights(
        active_targets=active_targets,
        explicit_keys=explicit_keys,
        shape_preservation_weight=shape_preservation_weight,
        regularization_weight=regularization_weight,
    )

    best_measurement_loss = float("inf")
    best_objective_loss = float("inf")
    best_iteration = -1
    best_betas = betas.detach().clone()
    stale_iterations = 0

    logger.info(
        "Starting SMPL-X measurement optimization for %s with targets=%s, target_height_cm=%s, "
        "shape_preservation_weight=%.3f->%.3f, regularization_weight=%.6f->%.6f, explicit_keys=%s",
        gender,
        active_targets,
        target_height_cm,
        shape_preservation_weight,
        effective_shape_preservation_weight,
        regularization_weight,
        effective_regularization_weight,
        active_explicit_measurements,
    )

    for iteration in range(num_iterations):
        optimizer.zero_grad()

        output = body_model(betas=betas, return_verts=True)
        warped_vertices, warped_joints, _ = apply_proportion_warp(
            vertices=output.vertices,
            joints=output.joints,
            parents=body_model.parents,
            weights=body_model.lbs_weights,
            target_measurements=active_targets,
            target_height_cm=target_height_cm,
            strict_circumference_keys=active_explicit_measurements,
        )
        current_measurements = calculate_measurements(
            vertices=warped_vertices,
            joints=warped_joints,
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

        measurement_loss = torch.stack(measurement_losses).mean()
        loss = measurement_loss
        shape_preservation_loss = torch.zeros((), dtype=dtype, device=torch_device)
        if initial_beta_anchor is not None and effective_shape_preservation_weight > 0:
            beta_drift = (betas - initial_beta_anchor).pow(2)
            shape_preservation_loss = (beta_drift * beta_preservation_weights).mean()
            loss = loss + effective_shape_preservation_weight * shape_preservation_loss

        beta_regularization_loss = torch.zeros((), dtype=dtype, device=torch_device)
        if effective_regularization_weight > 0:
            beta_regularization_loss = betas.pow(2).mean()
            loss = loss + effective_regularization_weight * beta_regularization_loss

        if not torch.isfinite(loss):
            raise RuntimeError("Optimization diverged: loss became non-finite.")

        loss.backward()
        optimizer.step()

        with torch.no_grad():
            betas.clamp_(-4.0, 4.0)

        current_total_loss = float(loss.detach().cpu().item())
        current_measurement_loss = float(measurement_loss.detach().cpu().item())
        current_shape_preservation_loss = float(shape_preservation_loss.detach().cpu().item())
        current_beta_regularization_loss = float(beta_regularization_loss.detach().cpu().item())
        if (
            current_total_loss + min_delta < best_objective_loss
            or (
                abs(current_total_loss - best_objective_loss) <= min_delta
                and current_measurement_loss + min_delta < best_measurement_loss
            )
        ):
            best_objective_loss = current_total_loss
            best_measurement_loss = current_measurement_loss
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
                "Iteration %s/%s: measurement_loss=%.6f, shape_preservation_loss=%.6f, "
                "beta_regularization_loss=%.6f, total_loss=%.6f, measurements=%s",
                iteration + 1,
                num_iterations,
                current_measurement_loss,
                current_shape_preservation_loss,
                current_beta_regularization_loss,
                current_total_loss,
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
        final_vertices, final_joints, _ = apply_proportion_warp(
            vertices=final_output.vertices,
            joints=final_output.joints,
            parents=body_model.parents,
            weights=body_model.lbs_weights,
            target_measurements=active_targets,
            target_height_cm=target_height_cm,
            strict_circumference_keys=active_explicit_measurements,
        )
        final_measurements = calculate_measurements(
            vertices=final_vertices,
            joints=final_joints,
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
        "Optimization finished at iteration %s with best_objective_loss=%.6f, best_measurement_loss=%.6f and abs_errors=%s",
        best_iteration + 1,
        best_objective_loss,
        best_measurement_loss,
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
