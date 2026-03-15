import io
# Force OpenMP to use 1 thread to avoid deadlocks in forked Celery processes
import os
os.environ['OMP_NUM_THREADS'] = '1'
import time
import uuid
import logging
from typing import TYPE_CHECKING, Tuple, Any, Optional
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
    from pygltflib import GLTF2
    HAS_ML_DEPS = True
except ImportError:
    HAS_ML_DEPS = False

from s3_client import upload_glb  # S3 upload helper

logger = logging.getLogger("AvatarML")

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
            self.model_path = os.path.join(os.path.dirname(__file__), 'models')
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

    def _simulate_profile_betas(self, height_cm: float, weight_kg: float, body_type: str) -> Any:
        """
        BMI-based mapping of physical metrics to SMPL-X shape betas.
        """
        # Calculate standard BMI
        height_m = height_cm / 100.0
        bmi = weight_kg / (height_m ** 2)

        betas = torch.zeros((1, 10), dtype=torch.float32)

        # betas[0] controls overall weight/thickness. Normal BMI is ~22.
        # Scale proportional to (BMI - 22)
        betas[0, 0] = (bmi - 22.0) * 0.4

        # betas[1] controls weight distribution (waist-to-hip / chest).
        b_type = body_type.lower()
        if b_type == 'slim':
            betas[0, 1] = -1.5
            betas[0, 2] = 0.0
        elif b_type == 'curvy':
            betas[0, 1] = 1.5
            betas[0, 2] = 1.0
        elif b_type == 'athletic':
            betas[0, 1] = 0.5
            betas[0, 2] = -1.5
        else: # average
            betas[0, 1] = 0.0
            betas[0, 2] = 0.0

        logger.info(
            f"Profile betas — h={height_cm}cm, w={weight_kg}kg, BMI={bmi:.1f}, "
            f"type={body_type}: {betas[0, :3].tolist()}"
        )
        return torch.tensor(betas, dtype=torch.float32).to(self.device)

    def _generate_smplx_glb(self, betas: Any, output_path: str, gender: str = 'neutral') -> str:
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

        verts = output.vertices[0].detach().cpu().numpy()   # (N, 3)
        faces = smpl_model.faces                             # (F, 3)

        mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)

        # Rotate 180 degrees around X-axis
        import numpy as np
        import trimesh.transformations as tf
        matrix = tf.rotation_matrix(np.pi, [1, 0, 0])
        # Note: if it was upside down due to this very rotation being applied previously,
        # we still apply it exactly as requested (which mirrors the old rotation).
        # We also rotate 180 degrees around Z-axis so it faces the camera if it's currently facing away.
        # But per the exact request:
        mesh.apply_transform(matrix)

        os.makedirs(os.path.dirname(output_path) or '/tmp', exist_ok=True)
        mesh.export(output_path, file_type='glb')
        logger.info(f"SMPL-X mesh exported to {output_path} "
                    f"({len(verts)} verts, {len(faces)} faces)")

        # Upload to S3 and return public URL
        s3_key = f"avatars/{os.path.basename(output_path)}"
        return upload_glb(output_path, s3_key)



    def process_profile(self, height_cm: float, weight_kg: float, body_type: str, gender: str = 'neutral') -> str:
        """
        Main Pipeline Entrypoint for Parametric Generation.
        Returns a public S3 URL (or local path when S3 is unavailable).
        """
        try:
            logger.info(
                f"Processing parametric profile: h={height_cm}, w={weight_kg}, "
                f"type={body_type}, gender={gender}"
            )

            betas = self._simulate_profile_betas(height_cm, weight_kg, body_type)

            file_id = str(uuid.uuid4())
            tmp_path = f"/tmp/profile_{file_id}.glb"

            smpl_model = self._get_smpl_model(gender)
            if smpl_model is not None:
                logger.info(f"Using real SMPL-X pipeline (gender={gender})...")
                public_url = self._generate_smplx_glb(betas, tmp_path, gender=gender)
            else:
                raise RuntimeError(f"SMPL-X unavailable for gender='{gender}' and neutral fallback also failed.")

            logger.info(f"Avatar available at: {public_url}")
            return public_url

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

def run_avatar_generation_from_profile(height: float, weight: float, body_type: str, gender: str = 'neutral') -> str:
    """Wrapper for generating avatar purely from profile parameters"""
    return pipeline_instance.process_profile(height, weight, body_type, gender)
