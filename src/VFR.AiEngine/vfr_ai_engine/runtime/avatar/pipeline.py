"""Avatar generation orchestration around SMPL-X, target inference, and GLB export."""

import io
# Force OpenMP to use 1 thread to avoid deadlocks in forked Celery processes
import os
os.environ['OMP_NUM_THREADS'] = '1'
import logging
import ipaddress
import socket
from typing import TYPE_CHECKING, Tuple, Any, Optional
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()  # reads .env locally; no-op when env vars are already injected by Aspire

if TYPE_CHECKING:
    import torch
    import trimesh

try:
    import torch
    import smplx
    import trimesh
    import numpy as np
    HAS_ML_DEPS = True
except ImportError:
    HAS_ML_DEPS = False

from vfr_ai_engine.runtime.measurements.anthropometry import infer_measurement_targets as infer_heuristic_measurement_targets
from vfr_ai_engine.runtime.measurements.optimizer import apply_proportion_warp, calculate_measurements, optimize_smplx_betas
from vfr_ai_engine.runtime.measurements.proxy_targets import (
    PROFILE_OPTIMIZATION_WEIGHTS,
    STRICT_EXPLICIT_MEASUREMENT_WEIGHT,
    build_profile_optimizer_targets,
    calculate_proxy_targets,
    convert_shoulder_width_to_circumference_cm,
    normalize_proxy_slider,
)
from vfr_ai_engine.runtime.paths import MODELS_DIR
from vfr_ai_engine.runtime.storage.s3_client import upload_glb

logger = logging.getLogger("AvatarML")


def measurement_target_provider() -> str:
    return os.getenv("MEASUREMENT_TARGET_PROVIDER", "heuristic").strip().lower()


def infer_profile_measurement_targets(
    *,
    height_cm: float,
    weight_kg: float,
    body_type: str,
    gender: str,
    muscularity: float | None,
    body_fat_percentage: float | None,
    overrides: dict[str, float],
    hints: dict[str, float],
) -> tuple[dict[str, float], dict[str, float], dict[str, str]]:
    provider = measurement_target_provider()
    if provider in {"", "heuristic"}:
        return infer_heuristic_measurement_targets(
            height_cm=height_cm,
            weight_kg=weight_kg,
            body_type=body_type,
            gender=gender,
            muscularity=None,
            body_fat_percentage=None,
            overrides=overrides,
            hints=hints,
        )
    if provider == "regressor":
        from vfr_ai_engine.runtime.measurements.regressor import infer_measurement_targets as infer_regressor_measurement_targets

        return infer_regressor_measurement_targets(
            height_cm=height_cm,
            weight_kg=weight_kg,
            body_type=body_type,
            gender=gender,
            muscularity=muscularity,
            body_fat_percentage=body_fat_percentage,
            overrides=overrides,
            hints=hints,
        )
    raise RuntimeError(
        f"Unknown MEASUREMENT_TARGET_PROVIDER='{provider}'. Expected 'heuristic' or 'regressor'."
    )


class AvatarMLPipeline:
    def __init__(self):
        logger.info("Initializing ML Pipeline...")
        self._smpl_models: dict = {}   # cache: gender → smplx model
        self.pose_estimator = None

        if HAS_ML_DEPS:
            import os
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
            logger.info(f"Using device: {self.device}")
            # smplx.create() automatically appends the model_type (e.g., 'smplx')
            # to the provided path, so we only point to the base models folder.
            self.model_path = str(MODELS_DIR)
            # Pre-load neutral to validate the model files exist at startup.
            self._get_smpl_model('neutral')
        else:
            self.device = 'cpu'
            self.model_path = None
            logger.warning("ML dependencies (torch, smplx, trimesh) not installed. Using mock mode.")

    def _get_smpl_model(self, gender: str):
        """Returns a cached SMPL-X model for the given gender, loading it on first use.
        Falls back to 'neutral' if the gender-specific .npz file is not available.
        """
        if not HAS_ML_DEPS:
            return None
        gender = gender.lower()
        # SMPL-X supports 'male', 'female', 'neutral'
        if gender not in ('male', 'female', 'neutral'):
            gender = 'neutral'
        if gender not in self._smpl_models:
            try:
                logger.info(f"Loading SMPL-X model (gender={gender})...")
                model = smplx.create(
                    model_path=self.model_path,
                    model_type='smplx',
                    gender=gender,
                    num_betas=10,
                    use_face_contour=False,
                    ext='npz'
                ).to(self.device)
                self._smpl_models[gender] = model
                logger.info(f"SMPL-X model loaded successfully (gender={gender}).")
            except Exception as e:
                logger.warning(f"SMPL-X model for gender='{gender}' not found: {e}")
                # Fall back to neutral if the gender-specific file is missing
                if gender != 'neutral':
                    logger.info("Falling back to neutral SMPL-X model...")
                    self._smpl_models[gender] = self._get_smpl_model('neutral')
                else:
                    logger.error("Neutral SMPL-X model also unavailable. Will use Xbot fallback.")
                    self._smpl_models[gender] = None
        return self._smpl_models[gender]

    def _simulate_profile_betas(
        self, height_cm: float, weight_kg: float, body_type: str,
        chest: float = 0, waist: float = 0, hip: float = 0, shoulder: float = 0,
        calf: float = 0, arm_length: float = 0, torso_length: float = 0, leg_length: float = 0,
    ) -> Any:
        """
        Conservative heuristic mapping of coarse metrics to SMPL-X shape betas.

        Only body_type contributes semantic warm-start bias. Muscle and fat
        composition are handled later as optimizer proxy targets instead of
        directly perturbing the SMPL-X beta PCA axes.
        """
        def _normalize_body_key(raw_body_type: str) -> str:
            body_key = str(raw_body_type or "regular").lower()
            body_aliases = {
                "lean": "slim",
                "average": "regular",
                "normal": "regular",
                "soft": "curvy",
                "plus": "curvy",
                "plus size": "curvy",
                "plus-size": "curvy",
                "plus_size": "curvy",
                "stout": "curvy",
            }
            body_key = body_aliases.get(body_key, body_key)
            if body_key not in {"slim", "regular", "athletic", "curvy"}:
                body_key = "regular"
            return body_key

        height_m = max(height_cm / 100.0, 1e-6)
        bmi = weight_kg / (height_m ** 2)
        body_key = _normalize_body_key(body_type)

        betas = torch.zeros((1, 10), dtype=torch.float32, device=self.device)

        semantic_beta_basis = torch.tensor(
            [
                [1.20, 0.10, 0.10, 0.22, 0.08, 0.06, 0.00, 0.00, 0.00, 0.00],
                [0.24, -1.25, 0.82, 0.36, 0.16, 0.10, 0.05, 0.02, 0.00, 0.00],
                [1.08, 0.94, -0.32, 0.30, 0.18, 0.12, 0.05, 0.00, 0.00, 0.00],
            ],
            dtype=torch.float32,
            device=self.device,
        )
        body_type_controls = {
            "slim": (-0.65, -0.15, -0.55),
            "regular": (0.00, 0.00, 0.00),
            "athletic": (-0.08, 1.05, -0.30),
            "curvy": (0.45, -0.14, 0.95),
        }

        semantic_controls = torch.tensor(
            [body_type_controls[body_key]],
            dtype=torch.float32,
            device=self.device,
        )
        betas += torch.matmul(semantic_controls, semantic_beta_basis)

        # beta[0]: overall bulk. Keep this as the dominant heuristic signal.
        bmi_offset = (bmi - 21.0) / 3.5
        betas[0, 0] += float(np.clip(bmi_offset, -1.75, 1.75)) * 0.75

        # beta[1]: very mild proportional bias only. Height itself is enforced
        # later during export, so we should not double-count it here.
        height_offset = (height_cm - 170.0) / 20.0
        betas[0, 1] += float(np.clip(height_offset, -1.0, 1.0)) * 0.12

        # Coarse torso measurements mainly refine the weight/roundness axes
        # while leaving the higher-order PCA components conservative.
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
            betas[0, 0] += bulk_bias * 0.9
            betas[0, 1] += bulk_bias * 0.18
            betas[0, 2] -= bulk_bias * 0.10

        # Mild proportion hints only when explicitly provided.
        proportion_bias = 0.0
        if arm_length > 0:
            proportion_bias += np.clip((arm_length / max(height_cm, 1.0)) - 0.37, -0.05, 0.05)
        if leg_length > 0:
            proportion_bias += np.clip((leg_length / max(height_cm, 1.0)) - 0.495, -0.06, 0.06)
        if proportion_bias != 0.0:
            proportion_bias = float(np.clip(proportion_bias, -0.08, 0.08))
            betas[0, 1] += proportion_bias
            betas[0, 4] += proportion_bias * 0.50
            betas[0, 5] -= proportion_bias * 0.30

        if shoulder > 0:
            expected_shoulder = height_cm * 0.235
            shoulder_bias = float(np.clip((shoulder - expected_shoulder) / max(expected_shoulder, 1.0), -0.2, 0.2))
            betas[0, 1] -= shoulder_bias * 0.35
            betas[0, 2] += shoulder_bias * 0.45
            betas[0, 3] += shoulder_bias * 0.18

        if calf > 0:
            expected_calf = height_cm * 0.12
            calf_bias = float(np.clip((calf - expected_calf) / max(expected_calf, 1.0), -0.2, 0.2))
            betas[0, 0] += calf_bias * 0.18
            betas[0, 5] += calf_bias * 0.25

        if torso_length > 0:
            expected_torso = height_cm * 0.315
            torso_bias = float(np.clip((torso_length - expected_torso) / max(expected_torso, 1.0), -0.15, 0.15))
            betas[0, 4] -= torso_bias * 0.18
            betas[0, 5] -= torso_bias * 0.12

        betas.clamp_(-2.5, 2.5)

        logger.info(
            "Profile betas - h=%.1fcm, w=%.1fkg, BMI=%.1f, body=%s: %s",
            height_cm,
            weight_kg,
            bmi,
            body_key,
            betas[0].tolist(),
        )
        return betas

    def _extract_skin_color(self, image_url: str) -> Optional[Tuple[float, float, float]]:
        """Extracts the dominant skin color from an image URL."""
        if not image_url:
            return None
        try:
            import requests
            from PIL import Image
            import numpy as np

            parsed = urlparse(image_url)
            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                raise ValueError("Only absolute http(s) image URLs are allowed.")
            if parsed.username or parsed.password:
                raise ValueError("Credentialed image URLs are not allowed.")

            addresses = {
                addr_info[4][0]
                for addr_info in socket.getaddrinfo(parsed.hostname, parsed.port, proto=socket.IPPROTO_TCP)
            }
            for address in addresses:
                ip = ipaddress.ip_address(address)
                if (
                    ip.is_private
                    or ip.is_loopback
                    or ip.is_link_local
                    or ip.is_multicast
                    or ip.is_reserved
                    or ip.is_unspecified
                ):
                    raise ValueError(f"Blocked non-public image host: {address}")

            logger.info(f"Extracting skin color from {image_url}...")
            response = requests.get(
                image_url,
                timeout=5,
                allow_redirects=False,
                headers={"User-Agent": "VFR-AiEngine/1.0"},
            )
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "")
            if not content_type.startswith("image/"):
                raise ValueError(f"Expected image content type, got '{content_type or 'unknown'}'")
            img = Image.open(io.BytesIO(response.content)).convert("RGB")
            img.thumbnail((100, 100)) # resize for speed
            
            # Simple heuristic: average color of the center region
            data = np.array(img)
            h, w, _ = data.shape
            center = data[h//4:3*h//4, w//4:3*w//4]
            avg_color = center.mean(axis=(0, 1)) / 255.0
            
            logger.info(f"Extracted color: {avg_color}")
            return tuple(avg_color.tolist())
        except Exception as e:
            logger.warning(f"Failed to extract skin color: {e}")
            return None

    def _generate_smplx_glb(
        self,
        betas: Any,
        output_path: str,
        gender: str = 'neutral',
        target_height_m: float = 1.70,
        skin_color: Optional[Tuple[float, float, float]] = None,
        target_measurements: Optional[dict[str, float]] = None,
        strict_circumference_keys: Optional[list[str]] = None,
    ) -> str:
        """
        Runs the SMPL-X forward pass, exports the mesh as GLB, uploads to S3.
        Returns the public S3 URL (or local path when S3 is unavailable).
        """
        import os
        smpl_model = self._get_smpl_model(gender)
        if smpl_model is None:
            raise RuntimeError(f"SMPL-X model for gender='{gender}' is not available.")

        logger.info(f"Running SMPL-X forward pass (gender={gender})...")

        if torch.is_tensor(betas):
            betas = betas.clone().detach().to(dtype=torch.float32, device=self.device)
        else:
            betas = torch.tensor(betas, dtype=torch.float32, device=self.device)

        with torch.no_grad():
            output = smpl_model(betas=betas, return_verts=True)

        warped_vertices, warped_joints, warp_scales = apply_proportion_warp(
            vertices=output.vertices,
            joints=output.joints,
            parents=smpl_model.parents,
            weights=smpl_model.lbs_weights,
            target_measurements=target_measurements,
            target_height_cm=target_height_m * 100.0,
            strict_circumference_keys=strict_circumference_keys,
        )
        if warp_scales:
            logger.info("Applied post-generation limb warp: %s", warp_scales)

        verts = warped_vertices.detach().cpu().numpy()   # (N, 3)
        faces = smpl_model.faces                            # (F, 3)

        # Scale mesh to precise target height
        current_height = verts[:, 1].max() - verts[:, 1].min()
        scale = target_height_m / current_height
        verts = verts * scale

        mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)

        import numpy as np
        import trimesh.transformations as tf
        
        # Rotate 180 degrees around Y-axis so it faces the camera
        matrix = tf.rotation_matrix(np.pi, [0, 1, 0])
        mesh.apply_transform(matrix)
        
        # Center the mesh
        min_y = mesh.vertices[:, 1].min()
        mesh.apply_translation([0, -min_y, 0])

        # Get rigging data
        if warped_joints is not None:
            joints = warped_joints.detach().cpu().numpy() * scale
        else:
            joints = output.joints[0].detach().cpu().numpy() * scale
        # Apply same transformations to joints
        joints = (np.hstack([joints, np.ones((joints.shape[0], 1))]) @ matrix.T)[:, :3]
        joints[:, 1] -= min_y

        parents = smpl_model.parents.detach().cpu().numpy()
        weights = smpl_model.lbs_weights.detach().cpu().numpy() # (V, J)

        # Truncate joints to only include the actual skeletal bones
        num_bones = len(parents)
        joints = joints[:num_bones]

        # Handle vertex colors (skin tone)
        vertex_colors = None
        if skin_color:
            # Create RGBA vertex colors
            rgba = list(skin_color) + [1.0]
            vertex_colors = np.tile(rgba, (len(verts), 1))

        # Export rigged GLB using pygltflib
        self._write_rigged_glb(
            output_path, 
            mesh.vertices.astype(np.float32), 
            mesh.faces.astype(np.uint32), 
            joints.astype(np.float32), 
            parents.astype(np.int32), 
            weights.astype(np.float32),
            colors=vertex_colors
        )
        
        logger.info(f"SMPL-X rigged GLB exported to {output_path}")

        # Upload to S3 and return public URL
        s3_key = f"avatars/{os.path.basename(output_path)}"
        public_url = upload_glb(output_path, s3_key)
        
        return public_url

    # SMPL-X standard joint names (first 54)
    SMPLX_JOINT_NAMES = [
        "pelvis", "left_hip", "right_hip", "spine_1", "left_knee", "right_knee", "spine_2", "left_ankle", "right_ankle",
        "spine_3", "left_foot", "right_foot", "neck", "left_collar", "right_collar", "head", "left_shoulder",
        "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist", "jaw", "left_eye_smplhf",
        "right_eye_smplhf", "left_index_1", "left_index_2", "left_index_3", "left_middle_1", "left_middle_2",
        "left_middle_3", "left_pinky_1", "left_pinky_2", "left_pinky_3", "left_ring_1", "left_ring_2", "left_ring_3",
        "left_thumb_1", "left_thumb_2", "left_thumb_3", "right_index_1", "right_index_2", "right_index_3",
        "right_middle_1", "right_middle_2", "right_middle_3", "right_pinky_1", "right_pinky_2", "right_pinky_3",
        "right_ring_1", "right_ring_2", "right_ring_3", "right_thumb_1", "right_thumb_2", "right_thumb_3"
    ]

    def _write_rigged_glb(self, path, vertices, faces, joints, parents, weights, colors=None):
        """
        Constructs a GLB with a static body mesh plus a skeleton node hierarchy.

        The current frontend only needs a clean body mesh and named skeleton
        anchors (for example spine/chest) for wardrobe attachment. A previous
        custom skin export produced visibly collapsed avatars in Three.js, so
        the body mesh is intentionally exported without binding it to the skin
        until proper bind-matrix validation is in place.
        """
        from pygltflib import GLTF2, Buffer, BufferView, Accessor, Mesh, Primitive, Attributes, Node, Skin, Scene
        import numpy as np
        import os

        gltf = GLTF2()
        
        num_verts = vertices.shape[0]
        num_joints = joints.shape[0]
        
        # 1. Защита от лишних весов: обрезаем матрицу весов под количество реальных костей
        if weights.shape[1] > num_joints:
            weights = weights[:, :num_joints]
            
        v_indices = np.zeros((num_verts, 4), dtype=np.uint16)
        v_weights = np.zeros((num_verts, 4), dtype=np.float32)
        
        # 2. Безопасная обработка весов с геометрической привязкой "осиротевших" вершин
        for i in range(num_verts):
            w = weights[i]
            
            # Если вершина потеряла свои кости (например, отрезали кости лица)
            if w.sum() < 1e-5:
                # Находим физически ближайшую кость в 3D пространстве
                dist = np.linalg.norm(joints - vertices[i], axis=1)
                closest_j = np.argmin(dist)
                w = np.zeros(num_joints, dtype=np.float32)
                w[closest_j] = 1.0
                
            # Берем топ-4 веса
            top_4_idx = np.argsort(w)[-4:][::-1]
            top_4_w = w[top_4_idx]
            
            # Ре-нормализация (чтобы сумма всегда была ровно 1.0)
            sum_w = top_4_w.sum()
            if sum_w > 1e-5:
                top_4_w /= sum_w
            else:
                top_4_w = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)
                top_4_idx = np.array([0, 0, 0, 0], dtype=np.uint16)
                
            v_indices[i] = top_4_idx.astype(np.uint16)
            v_weights[i] = top_4_w

        # 3. Упаковка байтов
        pos_bin = vertices.tobytes()
        ind_bin = faces.tobytes()
        j_ind_bin = v_indices.tobytes()
        j_w_bin = v_weights.tobytes()
        
        full_bin = pos_bin + ind_bin + j_ind_bin + j_w_bin
        if colors is not None:
            col_bin = colors.astype(np.float32).tobytes()
            full_bin += col_bin
        else:
            col_bin = b""

        offset = 0
        accessors_info = [
            (pos_bin, 5126, "VEC3", 34962),
            (ind_bin, 5125, "SCALAR", 34963),
            (j_ind_bin, 5123, "VEC4", 34962),
            (j_w_bin, 5126, "VEC4", 34962)
        ]
        if colors is not None:
            accessors_info.append((col_bin, 5126, "VEC4", 34962))

        for i, (data, comp_type, data_type, target) in enumerate(accessors_info):
            view = BufferView(buffer=0, byteOffset=offset, byteLength=len(data), target=target)
            gltf.bufferViews.append(view)
            acc = Accessor(bufferView=i, componentType=comp_type, count=0, type=data_type)
            if data_type == "VEC3": acc.count = num_verts
            elif data_type == "SCALAR": acc.count = faces.size
            elif data_type == "VEC4": acc.count = num_verts
            
            if i == 0:
                acc.min = vertices.min(axis=0).tolist()
                acc.max = vertices.max(axis=0).tolist()
            gltf.accessors.append(acc)
            offset += len(data)

        # 4. Сборка Меша
        attr = Attributes(POSITION=0, JOINTS_0=2, WEIGHTS_0=3)
        if colors is not None:
            attr.COLOR_0 = 4
            
        prim = Primitive(attributes=attr, indices=1)
        gltf.meshes.append(Mesh(primitives=[prim]))
        
        # 5. Сборка Скелета
        joint_nodes = []
        rel_translations = np.zeros_like(joints)
        for i in range(num_joints):
            p = parents[i]
            if p >= 0:
                rel_translations[i] = joints[i] - joints[p]
            else:
                rel_translations[i] = joints[i]
                
        for i in range(num_joints):
            name = self.SMPLX_JOINT_NAMES[i] if i < len(self.SMPLX_JOINT_NAMES) else f"joint_{i}"
            node = Node(name=name, translation=rel_translations[i].tolist())
            joint_nodes.append(len(gltf.nodes))
            gltf.nodes.append(node)
            
        for i, p in enumerate(parents):
            if p >= 0:
                if gltf.nodes[joint_nodes[p]].children is None: 
                    gltf.nodes[joint_nodes[p]].children = []
                gltf.nodes[joint_nodes[p]].children.append(joint_nodes[i])
                
        # 6. Skin (Привязка)
        ibms = []
        for i in range(num_joints):
            m = np.eye(4, dtype=np.float32)
            m[:3, 3] = joints[i]
            ibms.append(np.linalg.inv(m))
            
        ibm_data = np.array(ibms, dtype=np.float32).tobytes()
        
        # Аккуратно добавляем IBM в конец бинарного буфера
        final_blob_data = full_bin + ibm_data
        
        gltf.bufferViews.append(BufferView(buffer=0, byteOffset=offset, byteLength=len(ibm_data)))
        gltf.accessors.append(Accessor(bufferView=len(gltf.bufferViews)-1, componentType=5126, count=num_joints, type="MAT4"))
        
        skin = Skin(joints=joint_nodes, inverseBindMatrices=len(gltf.accessors)-1)
        gltf.skins.append(skin)
        
        # 7. Финальная сцена
        mesh_node = Node(mesh=0, name="Body")
        skeleton_root = joint_nodes[0]
        gltf.nodes.append(mesh_node)
        gltf.scenes.append(Scene(nodes=[skeleton_root, len(gltf.nodes)-1]))
        gltf.scene = 0
        
        # 8. СОХРАНЕНИЕ БИНАРНИКА (без падений)
        buffer = Buffer(byteLength=len(final_blob_data))
        gltf.buffers.append(buffer)
        gltf.set_binary_blob(final_blob_data)
        
        os.makedirs(os.path.dirname(path) or '/tmp', exist_ok=True)
        gltf.save(path)

    def process_profile(
        self, user_id: str, height_cm: float, weight_kg: float, body_type: str, gender: str = 'neutral',
        muscularity: float = 0, body_fat_percentage: float = 0,
        chest: float = 0, waist: float = 0, hip: float = 0, shoulder: float = 0, calf: float = 0,
        arm_length: float = 0, torso_length: float = 0, leg_length: float = 0, face_image_url: str = ""
    ) -> dict[str, Any]:
        """
        Main Pipeline Entrypoint for Parametric Generation.
        Returns the generated public URL plus body measurements for Studio refinement.
        """
        try:
            logger.info(
                f"Processing parametric profile: user={user_id}, h={height_cm}, w={weight_kg}, "
                f"type={body_type}, gender={gender}"
            )

            user_measurement_overrides = {}
            if waist > 0:
                user_measurement_overrides["waist_cm"] = waist
            if chest > 0:
                user_measurement_overrides["chest_cm"] = chest
            if hip > 0:
                user_measurement_overrides["hips_cm"] = hip
            if leg_length > 0:
                user_measurement_overrides["leg_length_cm"] = leg_length
            if arm_length > 0:
                user_measurement_overrides["arm_length_cm"] = arm_length

            target_measurements, measurement_weights, measurement_sources = infer_profile_measurement_targets(
                height_cm=height_cm,
                weight_kg=weight_kg,
                body_type=body_type,
                gender=gender,
                muscularity=muscularity,
                body_fat_percentage=body_fat_percentage,
                overrides=user_measurement_overrides,
                hints={
                    "shoulder_cm": shoulder,
                    "calf_cm": calf,
                    "torso_length_cm": torso_length,
                },
            )
            explicit_manual_measurement_keys = {
                measurement_name
                for measurement_name, source in measurement_sources.items()
                if source == "user"
            }
            if explicit_manual_measurement_keys:
                measurement_weights = {
                    **measurement_weights,
                    **{
                        measurement_name: STRICT_EXPLICIT_MEASUREMENT_WEIGHT
                        for measurement_name in explicit_manual_measurement_keys
                    },
                }
            explicit_shoulder_circumference_cm = convert_shoulder_width_to_circumference_cm(shoulder)
            if explicit_shoulder_circumference_cm > 0:
                target_measurements = {
                    **target_measurements,
                    "shoulder_circumference_cm": explicit_shoulder_circumference_cm,
                }
                measurement_weights = {
                    **measurement_weights,
                    "shoulder_circumference_cm": STRICT_EXPLICIT_MEASUREMENT_WEIGHT,
                }
                measurement_sources = {
                    **measurement_sources,
                    "shoulder_circumference_cm": "user",
                }

            normalized_muscle_slider = normalize_proxy_slider(muscularity)
            normalized_fat_slider = normalize_proxy_slider(body_fat_percentage)
            if measurement_target_provider() == "regressor":
                proxy_targets = {}
            else:
                proxy_targets = calculate_proxy_targets(
                    exact_measurements=target_measurements,
                    muscle_slider=normalized_muscle_slider,
                    fat_slider=normalized_fat_slider,
                    gender=gender,
                )
            if proxy_targets:
                if measurement_sources.get("shoulder_circumference_cm") == "user":
                    proxy_targets = {
                        measurement_name: target_value
                        for measurement_name, target_value in proxy_targets.items()
                        if measurement_name != "shoulder_circumference_cm"
                    }
                target_measurements = {
                    **target_measurements,
                    **proxy_targets,
                }
                measurement_weights = {
                    **measurement_weights,
                    **{
                        measurement_name: PROFILE_OPTIMIZATION_WEIGHTS[measurement_name]
                        for measurement_name in proxy_targets
                        if measurement_name in PROFILE_OPTIMIZATION_WEIGHTS
                    },
                }
                measurement_sources = {
                    **measurement_sources,
                    **{
                        measurement_name: (
                            f"proxy_targets(muscle={normalized_muscle_slider:.3f},fat={normalized_fat_slider:.3f})"
                        )
                        for measurement_name in proxy_targets
                    },
                }

            shape_hint_shoulder = shoulder if shoulder > 0 else target_measurements.get("shoulder_cm", 0.0)
            shape_hint_calf = calf if calf > 0 else target_measurements.get("calf_cm", 0.0)
            shape_hint_torso = torso_length if torso_length > 0 else target_measurements.get("torso_length_cm", 0.0)

            heuristic_betas = self._simulate_profile_betas(
                height_cm,
                weight_kg,
                body_type,
                target_measurements.get("chest_cm", 0.0),
                target_measurements.get("waist_cm", 0.0),
                target_measurements.get("hips_cm", 0.0),
                shape_hint_shoulder,
                shape_hint_calf,
                target_measurements.get("arm_length_cm", 0.0),
                shape_hint_torso,
                target_measurements.get("leg_length_cm", 0.0),
            )

            logger.info(
                "Anthropometric targets for optimization: %s (sources=%s)",
                target_measurements,
                measurement_sources,
            )

            manual_hint_values = {
                "shoulder_cm": shoulder,
                "calf_cm": calf,
                "torso_length_cm": torso_length,
            }
            optimization_targets, optimization_weights, explicit_manual_keys = build_profile_optimizer_targets(
                target_measurements=target_measurements,
                measurement_weights=measurement_weights,
                measurement_sources=measurement_sources,
                manual_hint_values=manual_hint_values,
            )
            logger.info(
                "Optimization loss weights: %s (explicit_manual_keys=%s)",
                optimization_weights,
                explicit_manual_keys,
            )

            approximate_hint_fields = []
            if shoulder > 0:
                approximate_hint_fields.append("shoulder")
            if calf > 0:
                approximate_hint_fields.append("calf")
            if torso_length > 0:
                approximate_hint_fields.append("torso_length")
            if approximate_hint_fields:
                logger.info(
                    "Approximate shape hints applied before optimization: %s",
                    approximate_hint_fields,
                )

            try:
                optimizer_iterations = 180 if user_measurement_overrides else 120
                optimized_betas = optimize_smplx_betas(
                    target_measurements=optimization_targets,
                    smplx_model_path=self.model_path,
                    gender=gender,
                    num_iterations=optimizer_iterations,
                    target_height_cm=height_cm,
                    initial_betas=heuristic_betas.detach().cpu().numpy(),
                    shape_preservation_weight=0.05,
                    measurement_weights=optimization_weights,
                    explicit_keys=explicit_manual_keys,
                    device=str(self.device)
                )
                betas = torch.tensor(optimized_betas, dtype=torch.float32, device=self.device)
            except Exception as e:
                logger.warning(f"Measurement optimization failed ({e}), falling back to heuristic betas.")
                betas = heuristic_betas

            measured_summary: dict[str, float] = {}
            smpl_model = self._get_smpl_model(gender)
            if smpl_model is not None:
                with torch.no_grad():
                    measured_output = smpl_model(betas=betas, return_verts=True)
                measured_vertices, measured_joints, warp_scales = apply_proportion_warp(
                    vertices=measured_output.vertices,
                    joints=measured_output.joints,
                    parents=smpl_model.parents,
                    weights=smpl_model.lbs_weights,
                    target_measurements=target_measurements,
                    target_height_cm=height_cm,
                    strict_circumference_keys=explicit_manual_keys,
                )
                measured = calculate_measurements(
                    vertices=measured_vertices,
                    joints=measured_joints,
                    target_height_cm=height_cm,
                )
                measured_summary = {
                    measurement_name: round(
                        float(measured[measurement_name].detach().cpu().item()),
                        2,
                    )
                    for measurement_name in target_measurements
                    if measurement_name in measured
                }
                if "height_cm" in measured:
                    measured_summary["height_cm"] = round(
                        float(measured["height_cm"].detach().cpu().item()),
                        2,
                    )
                if warp_scales:
                    logger.info("Applied debug proportion warp: %s", warp_scales)
                logger.info(
                    "Post-optimization height-normalized measurements: %s",
                    measured_summary,
                )

            # Extract skin color if face image provided
            skin_color = self._extract_skin_color(face_image_url)

            import re
            import time
            from vfr_ai_engine.runtime.storage.s3_client import delete_old_user_avatars
            
            safe_user_id = re.sub(r'[^a-zA-Z0-9_\-]', '', user_id)
            timestamp = int(time.time())
            tmp_path = f"/tmp/profile_{safe_user_id}_{timestamp}.glb"

            # Delete the previous unique file(s) for this user to save space
            delete_old_user_avatars(safe_user_id)

            if smpl_model is not None:
                logger.info(f"Using real SMPL-X pipeline (gender={gender})...")
                target_height_m = height_cm / 100.0
                public_url = self._generate_smplx_glb(
                    betas,
                    tmp_path,
                    gender=gender,
                    target_height_m=target_height_m,
                    skin_color=skin_color,
                    target_measurements=target_measurements,
                    strict_circumference_keys=explicit_manual_keys,
                )
            else:
                raise RuntimeError(f"SMPL-X unavailable for gender='{gender}' and neutral fallback also failed.")

            logger.info(f"Avatar available at: {public_url}")
            return {
                "model_url": public_url,
                "measurements": measured_summary,
                "targets": {
                    measurement_name: round(float(target_value), 2)
                    for measurement_name, target_value in target_measurements.items()
                },
                "measurement_sources": measurement_sources,
            }

        except Exception as e:
            logger.error(f"Profile Pipeline failed: {str(e)}")
            raise

    def process_image(self, image_bytes: bytes) -> str:
        """
        Image-based Pipeline Entrypoint (Phase 4+).
        Currently a stub that falls back to the scaled mannequin.
        Replace with CLIFF / HMR 2.0 pose estimator in production.
        """
        try:
            logger.info("Image pipeline called — returning invalid URL since HMR not implemented yet.")
            return "error://image_pipeline_not_implemented"

        except Exception as e:
            logger.error(f"Image Pipeline failed: {str(e)}")
            raise


# Singleton instance for the worker
pipeline_instance = AvatarMLPipeline()

def run_avatar_generation(image_bytes: bytes) -> str:
    return pipeline_instance.process_image(image_bytes)

def run_avatar_generation_from_profile(
    user_id: str, height: float, weight: float, body_type: str, gender: str = 'neutral',
    muscularity: float = 0, body_fat_percentage: float = 0,
    chest: float = 0, waist: float = 0, hip: float = 0, shoulder: float = 0, calf: float = 0,
    arm_length: float = 0, torso_length: float = 0, leg_length: float = 0, face_image_url: str = ""
) -> dict[str, Any]:
    """Wrapper for generating avatar purely from profile parameters"""
    return pipeline_instance.process_profile(
        user_id, height, weight, body_type, gender,
        muscularity, body_fat_percentage,
        chest, waist, hip, shoulder, calf, arm_length, torso_length, leg_length, face_image_url
    )
