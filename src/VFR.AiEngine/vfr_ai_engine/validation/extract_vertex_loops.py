import argparse
import os
from typing import Dict, List

import numpy as np
import smplx
import torch
import trimesh

from vfr_ai_engine.paths import MODELS_DIR


def _slice_mesh_components(
    mesh: trimesh.Trimesh,
    height_y: float,
    rounding_decimals: int = 6,
) -> List[np.ndarray]:
    """
    Slice the mesh with a horizontal plane and split the resulting line
    segments into disconnected contour components.
    """
    slice_segments = np.asarray(
        trimesh.intersections.mesh_plane(
            mesh,
            plane_origin=[0, height_y, 0],
            plane_normal=[0, 1, 0],
        )
    )

    if slice_segments.size == 0:
        return []

    point_to_segments: Dict[tuple, List[int]] = {}
    point_lookup: Dict[tuple, np.ndarray] = {}
    segment_keys: List[List[tuple]] = []

    for segment_index, segment in enumerate(slice_segments):
        endpoint_keys: List[tuple] = []
        for point in segment:
            key = tuple(np.round(point, rounding_decimals).tolist())
            endpoint_keys.append(key)
            point_lookup.setdefault(key, point)
            point_to_segments.setdefault(key, []).append(segment_index)
        segment_keys.append(endpoint_keys)

    visited_segments = set()
    components: List[np.ndarray] = []

    for start_segment in range(len(slice_segments)):
        if start_segment in visited_segments:
            continue

        stack = [start_segment]
        component_segment_indices = []

        while stack:
            segment_index = stack.pop()
            if segment_index in visited_segments:
                continue

            visited_segments.add(segment_index)
            component_segment_indices.append(segment_index)

            for point_key in segment_keys[segment_index]:
                for neighbor_index in point_to_segments[point_key]:
                    if neighbor_index not in visited_segments:
                        stack.append(neighbor_index)

        component_points = _order_contour_points(
            point_lookup=point_lookup,
            segment_keys=segment_keys,
            component_segment_indices=component_segment_indices,
        )
        if len(component_points) > 0:
            components.append(component_points)

    return components


def _order_contour_points(
    point_lookup: Dict[tuple, np.ndarray],
    segment_keys: List[List[tuple]],
    component_segment_indices: List[int],
) -> np.ndarray:
    """
    Recover an ordered contour walk directly from the slice segments.
    """
    graph: Dict[tuple, List[tuple]] = {}

    for segment_index in component_segment_indices:
        start_key, end_key = segment_keys[segment_index]
        graph.setdefault(start_key, []).append(end_key)
        graph.setdefault(end_key, []).append(start_key)

    if not graph:
        return np.empty((0, 3), dtype=np.float64)

    start_key = next(iter(graph))
    ordered_keys = [start_key]
    previous_key = None
    current_key = start_key

    for _ in range(len(graph) + 1):
        neighbors = graph[current_key]
        if previous_key is None:
            next_key = neighbors[0]
        else:
            next_candidates = [neighbor for neighbor in neighbors if neighbor != previous_key]
            if not next_candidates:
                break
            next_key = next_candidates[0]

        if next_key == start_key:
            break

        ordered_keys.append(next_key)
        previous_key, current_key = current_key, next_key

    if len(ordered_keys) < 3:
        ordered_keys = list(graph.keys())

    return np.array([point_lookup[point_key] for point_key in ordered_keys], dtype=np.float64)


def _contour_points_to_vertex_loop(mesh: trimesh.Trimesh, contour_points: np.ndarray) -> List[int]:
    """
    Map ordered contour points back to original mesh vertex indices while
    preserving the contour walk order and removing duplicates.
    """
    _, vertex_indices = mesh.kdtree.query(contour_points)
    ordered_indices: List[int] = []
    seen = set()

    for vertex_index in np.asarray(vertex_indices, dtype=np.int64).tolist():
        if vertex_index in seen:
            continue
        seen.add(vertex_index)
        ordered_indices.append(int(vertex_index))

    return ordered_indices


def _build_contour_candidates(
    mesh: trimesh.Trimesh,
    contour_components: List[np.ndarray],
) -> List[dict]:
    """
    Convert contour points into candidates that reference the original SMPL-X
    vertex indices, preserving global indexing for copy/paste into the optimizer.
    """
    candidates = []

    for component_index, contour_points in enumerate(contour_components):
        ordered_indices = _contour_points_to_vertex_loop(mesh, contour_points)

        if len(ordered_indices) < 3:
            continue

        centroid = contour_points.mean(axis=0)

        candidates.append(
            {
                "component_index": component_index,
                "centroid": centroid,
                "point_count": int(len(contour_points)),
                "vertex_count": int(len(ordered_indices)),
                "ordered_indices": ordered_indices,
            }
        )

    return candidates


def _select_contour_candidate(candidates: List[dict], strategy: str) -> dict:
    if not candidates:
        raise ValueError("No contour candidates found for this slice.")

    if strategy == "center":
        return min(
            candidates,
            key=lambda candidate: (
                abs(candidate["centroid"][0]),
                -candidate["vertex_count"],
                -candidate["point_count"],
            ),
        )

    if strategy == "positive_x":
        preferred = [candidate for candidate in candidates if candidate["centroid"][0] > 0]
        pool = preferred or candidates
        return max(
            pool,
            key=lambda candidate: (
                candidate["centroid"][0],
                candidate["vertex_count"],
                candidate["point_count"],
            ),
        )

    if strategy == "negative_x":
        preferred = [candidate for candidate in candidates if candidate["centroid"][0] < 0]
        pool = preferred or candidates
        return min(
            pool,
            key=lambda candidate: (
                candidate["centroid"][0],
                -candidate["vertex_count"],
                -candidate["point_count"],
            ),
        )

    raise ValueError(f"Unknown contour selection strategy: {strategy}")


def _print_contour_diagnostics(label: str, candidates: List[dict], selected: dict) -> None:
    print(f"{label}: found {len(candidates)} contour candidate(s)")
    for candidate in candidates:
        cx, cy, cz = candidate["centroid"]
        marker = "*" if candidate["component_index"] == selected["component_index"] else " "
        print(
            f"  {marker} component={candidate['component_index']} "
            f"centroid=({cx:.4f}, {cy:.4f}, {cz:.4f}) "
            f"points={candidate['point_count']} "
            f"vertices={candidate['vertex_count']}"
        )


def extract_measurement_loop(
    mesh: trimesh.Trimesh,
    height_y: float,
    label: str,
    strategy: str,
) -> List[int]:
    contour_components = _slice_mesh_components(mesh, height_y)
    candidates = _build_contour_candidates(mesh, contour_components)
    selected = _select_contour_candidate(candidates, strategy)
    _print_contour_diagnostics(label, candidates, selected)
    return selected["ordered_indices"]


def extract_loops(smplx_model_path: str) -> None:
    print("Loading SMPL-X model to extract topology...")
    body_model = smplx.create(
        model_path=smplx_model_path,
        model_type="smplx",
        gender="neutral",
        num_betas=10,
        use_pca=False,
        ext="npz",
    )

    output = body_model(betas=torch.zeros(1, 10))
    vertices = output.vertices[0].detach().numpy()
    faces = body_model.faces

    mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)

    min_y = float(np.min(vertices[:, 1]))
    max_y = float(np.max(vertices[:, 1]))
    height = max_y - min_y

    chest_y = min_y + (height * 0.73)
    waist_y = min_y + (height * 0.60)
    hips_y = min_y + (height * 0.52)
    thigh_y = min_y + (height * 0.45)
    bicep_y = min_y + (height * 0.70)

    print("Slicing mesh and resolving contour loops on the original SMPL-X mesh...")
    chest_indices = extract_measurement_loop(mesh, chest_y, "Chest", "center")
    waist_indices = extract_measurement_loop(mesh, waist_y, "Waist", "center")
    hips_indices = extract_measurement_loop(mesh, hips_y, "Hips", "center")
    bicep_indices = extract_measurement_loop(mesh, bicep_y, "Left Bicep", "positive_x")
    thigh_indices = extract_measurement_loop(mesh, thigh_y, "Left Thigh", "positive_x")

    print("\n--- EXTRACTION COMPLETE ---")
    print("Copy and paste this into your MEASUREMENT_VERTICES dictionary:\n")
    print("MEASUREMENT_VERTICES = {")
    print(f"    'chest_circumference': {chest_indices},")
    print(f"    'waist_circumference': {waist_indices},")
    print(f"    'hips_circumference': {hips_indices},")
    print(f"    'left_bicep_circumference': {bicep_indices},")
    print(f"    'left_thigh_circumference': {thigh_indices},")
    print("}")


def _parse_args() -> argparse.Namespace:
    default_model_path = str(MODELS_DIR)
    parser = argparse.ArgumentParser(
        description="Extract SMPL-X vertex loops for anthropometric measurements."
    )
    parser.add_argument(
        "--model-path",
        default=default_model_path,
        help="Path to the base SMPL-X models directory.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    extract_loops(smplx_model_path=args.model_path)
