import io
import time
import uuid
import logging
from typing import Tuple

try:
    import torch
    import smplx
    import trimesh
    import numpy as np
    from scipy.spatial import cKDTree
    from pygltflib import GLTF2, Scene as GLTFScene, Node, Mesh, Primitive, Attributes, Buffer, BufferView, Accessor, Asset
    HAS_ML_DEPS = True
except ImportError:
    HAS_ML_DEPS = False

logger = logging.getLogger("AvatarML")

class AvatarMLPipeline:
    def __init__(self):
        logger.info("Initializing ML Pipeline...")
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        if HAS_ML_DEPS:
            logger.info(f"Using device: {self.device}")
            # In a real environment, we'd load the SMPL-X model here:
            # self.smpl_model = smplx.create(model_path='models/smplx', model_type='smplx',
            #                              gender='neutral', use_face_contour=False,
            #                              num_betas=10, num_expression_coeffs=10).to(self.device)
            #
            # self.pose_estimator = CLIFF_Model.load_from_checkpoint('weights/cliff.ckpt').to(self.device)
            self.smpl_model = None
            self.pose_estimator = None
        else:
            logger.warning("ML dependencies (torch, smplx, trimesh) not installed. Using mock mode.")

    def _estimate_pose_and_shape(self, image_bytes: bytes) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Takes an image and uses a CNN/Transformer (like CLIFF or HMR 2.0) to predict:
        - betas: Shape parameters (thickness, height)
        - body_pose: Joint rotations
        """
        logger.info("Predicting SMPL parameters (betas, pose)...")
        if self.pose_estimator:
            # image_tensor = preprocess(image_bytes)
            # pred_rotmat, pred_betas, _ = self.pose_estimator(image_tensor)
            # return pred_betas, pred_rotmat
            pass
            
        # Mock tensors for structural demonstration
        # 1 person, 10 shape params
        mock_betas = torch.zeros([1, 10], dtype=torch.float32, device=self.device) 
        # 1 person, 21 body joints, 3x3 rotation matrices
        mock_body_pose = torch.eye(3, device=self.device).expand(1, 21, 3, 3) 
        return mock_betas, mock_body_pose

    def _generate_body_mesh(self, betas: torch.Tensor, body_pose: torch.Tensor) -> trimesh.Trimesh:
        """
        Passes parameters through the SMPL-X differentiable layer to construct the 3D human mesh.
        If SMPL-X is missing, falls back to the high-poly Xbot GLB mannequin.
        """
        logger.info("Generating 3D body vertices...")
        if self.smpl_model:
            # output = self.smpl_model(betas=betas, body_pose=body_pose)
            # vertices = output.vertices.detach().cpu().numpy().squeeze()
            # faces = self.smpl_model.faces
            # return trimesh.Trimesh(vertices, faces, process=False)
            pass
            
        return None  # We bypass Trimesh generation for the fallback now

    def process_image(self, image_bytes: bytes) -> str:
        """
        Main Pipeline Entrypoint: Takes image, runs pipelines, exports GLB.
        """
        try:
            betas, body_pose = self._estimate_pose_and_shape(image_bytes)
            
            file_id = str(uuid.uuid4())
            output_path = f"/tmp/{file_id}.glb"
            logger.info(f"Assembling Scene and exporting to {output_path}...")
            
            time.sleep(2) # Simulate GPU compute delay
            
            if self.smpl_model:
                pass # Original Trimesh export logic goes here when SMPL-X is active 
                
            # FALLBACK: Use high-poly Xbot mannequin
            self._generate_scaled_mannequin_glb(betas, output_path)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            raise e

    def _generate_scaled_mannequin_glb(self, betas: torch.Tensor, output_path: str):
        """
        Loads the high-poly base mannequin, scales it based on heuristic betas, 
        and saves it using pygltflib to preserve materials and skeletons.
        """
        import os
        base_glb_path = os.path.join(os.path.dirname(__file__), "models", "Xbot.glb")
        
        if not os.path.exists(base_glb_path):
            logger.warning("Xbot.glb not found! Using minimal fallback.")
            minimal_glb = b'glTF\x02\x00\x00\x00\x0c\x00\x00\x00'
            with open(output_path, 'wb') as f:
                f.write(minimal_glb)
            return

        logger.info(f"Loading Base Mannequin from {base_glb_path}...")
        gltf = GLTF2().load(base_glb_path)
        
        # Calculate scale multipliers
        height_factor = float(betas[0, 0].item()) * 0.05
        weight_factor = float(betas[0, 1].item()) * 0.01
        
        y_scale = 1.0 + height_factor  # Height translation
        xz_scale = 1.0 + weight_factor # Girth/Width translation
        
        logger.info(f"Scaling mannequin by: XZ={xz_scale:.2f}, Y={y_scale:.2f}")
        
        # Apply scale strictly to the root nodes of the active scene
        scene = gltf.scenes[gltf.scene]
        for node_idx in scene.nodes:
            node = gltf.nodes[node_idx]
            # Pygltflib node.scale defaults to None if it's [1,1,1] in the file
            if node.scale is None:
                node.scale = [1.0, 1.0, 1.0]
            
            node.scale[0] *= xz_scale
            node.scale[1] *= y_scale
            node.scale[2] *= xz_scale
            
        gltf.save(output_path)
        logger.info(f"Scaled mannequin exported successfully!")

    def _simulate_profile_betas(self, height_cm: float, weight_kg: float, body_type: str) -> torch.Tensor:
        """
        Heuristic mapping of physical metrics to SMPL betas.
        Beta[0] strongly correlates with height/scale.
        Beta[1] strongly correlates with weight/girth.
        Beta[2] correlates with muscle/fat distribution.
        """
        betas = torch.zeros([1, 10], dtype=torch.float32, device=self.device)
        
        # Base approximations
        base_height_cm = 170.0
        base_weight_kg = 70.0

        # Heuristic 1: Height affects beta[0] linearly. 
        # (Usually 1 unit of beta[0] is roughly 5cm difference)
        height_diff = height_cm - base_height_cm
        betas[0, 0] = height_diff / 5.0

        # Heuristic 2: Weight affects beta[1]
        bmi = weight_kg / ((height_cm / 100) ** 2)
        target_bmi = 24.2 # Base BMI
        bmi_diff = bmi - target_bmi
        betas[0, 1] = bmi_diff * 0.4 
        
        # Heuristic 3: Body Type affects local components
        bt_lower = body_type.lower()
        if 'slim' in bt_lower:
            betas[0, 2] -= 1.5 # Less volume overall
        elif 'athletic' in bt_lower:
            betas[0, 2] += 1.0 # More muscle definition
            betas[0, 3] -= 0.5 # Less fat
        elif 'plussize' in bt_lower or 'heavy' in bt_lower:
            betas[0, 2] += 2.0 # More overall volume
            
        logger.info(f"Generated heuristic Betas for {height_cm}cm, {weight_kg}kg, {body_type}: {betas[0,:3].tolist()}...")
        return betas

    def process_profile(self, height_cm: float, weight_kg: float, body_type: str) -> str:
        """
        Main Pipeline Entrypoint for Parametric Generation (No Image)
        """
        try:
            logger.info(f"Processing parametric profile: h={height_cm}, w={weight_kg}, type={body_type}")
            
            # 1. Body Estimation purely from math
            betas = self._simulate_profile_betas(height_cm, weight_kg, body_type)
            
            file_id = str(uuid.uuid4())
            output_path = f"/tmp/profile_{file_id}.glb"
            logger.info(f"Assembling Scene and exporting to {output_path}...")
            
            time.sleep(2) # Simulate CPU/GPU processing
            
            if self.smpl_model:
                pass # Original SMPL-X generation goes here
            
            # FALLBACK: Use high-poly Xbot mannequin 
            self._generate_scaled_mannequin_glb(betas, output_path)
                    
            return output_path
            
        except Exception as e:
            logger.error(f"Profile Pipeline failed: {str(e)}")
            raise e

# Singleton instance for the worker
pipeline_instance = AvatarMLPipeline()

def run_avatar_generation(image_bytes: bytes) -> str:
    return pipeline_instance.process_image(image_bytes)

def run_avatar_generation_from_profile(height: float, weight: float, body_type: str) -> str:
    """Wrapper for generating avatar purely from profile parameters"""
    return pipeline_instance.process_profile(height, weight, body_type)
