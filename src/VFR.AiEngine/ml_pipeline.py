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
        """
        logger.info("Generating 3D body vertices via SMPL-X forward pass...")
        if self.smpl_model:
            # output = self.smpl_model(betas=betas, body_pose=body_pose)
            # vertices = output.vertices.detach().cpu().numpy().squeeze()
            # faces = self.smpl_model.faces
            # return trimesh.Trimesh(vertices, faces, process=False)
            pass
            
        # Mock trimesh creation
        if HAS_ML_DEPS:
            # Box is safer for basic GLTF testing than Capsule
            mesh = trimesh.creation.box(extents=[0.4, 1.6, 0.4])
            return mesh
        return None

    def _virtual_try_on(self, body_mesh: trimesh.Trimesh, garment_path: str = None) -> trimesh.Trimesh:
        """
        3D Virtual Try-On Algorithm:
        1. Load garment mesh.
        2. Align garment roughly using rigid transformation (Translation + Scale).
        3. Transfer Skinning Weights: Find nearest neighbors from body to garment,
           and transfer the bone weights. This allows the garment to animate with the body.
        4. Resolve Collisions: Laplacian smoothing or push garment vertices out of body.
        """
        logger.info("Processing 3D Virtual Try-On (Garment Registration & Skinning Transfer)...")
        if not HAS_ML_DEPS or not body_mesh:
            return None
            
        # Mocking the loaded garment
        garment_mesh = trimesh.creation.cylinder(radius=0.18, height=0.6)
        # Move garment up to 'torso' level
        garment_mesh.apply_translation([0, 0.4, 0])

        # Algorithm Details:
        # A) Spatial Query for Skinning Transfer
        logger.info("Transferring skeletal weights to garment via KDTree...")
        body_kd_tree = cKDTree(body_mesh.vertices)
        distances, nearest_indices = body_kd_tree.query(garment_mesh.vertices, k=1)

        # B) Collision Resolution
        # Push garment vertices outwards if distance < threshold (intersecting body)
        logger.info("Resolving body-garment intersections...")
        collision_mask = distances < 0.015 # 1.5cm threshold
        if np.any(collision_mask):
            # Calculate normals of the nearest body vertices
            body_normals = body_mesh.vertex_normals[nearest_indices]
            # Push intersecting garment vertices out along the body normal
            push_vectors = body_normals[collision_mask] * (0.015 - distances[collision_mask])[:, np.newaxis]
            garment_mesh.vertices[collision_mask] += push_vectors
        
        return garment_mesh

    def process_image(self, image_bytes: bytes) -> str:
        """
        Main Pipeline Entrypoint: Takes image, runs pipelines, exports GLB.
        """
        try:
            # 1. Body Estimation
            betas, body_pose = self._estimate_pose_and_shape(image_bytes)
            
            # 2. SMPL-X Mesh Generation
            body_mesh = self._generate_body_mesh(betas, body_pose)
            
            # 3. Virtual Try On (Assuming a default t-shirt for now)
            garment_mesh = self._virtual_try_on(body_mesh)
            
            # 4. Scene Assembly and Export
            file_id = str(uuid.uuid4())
            output_path = f"/tmp/{file_id}.glb"
            logger.info(f"Assembling Scene and exporting to {output_path}...")
            
            time.sleep(2) # Simulate GPU compute delay for UI testing
            
            if HAS_ML_DEPS and body_mesh:
                # ------------------- PYGLTFLIB EXPORT -------------------
                # Trimesh export often creates invalid GLB for React Three Fiber (context loss).
                # We manually build a compliant GLB using pygltflib.
                
                # Combine meshes for simple export (or just export body if garment missing)
                final_mesh = body_mesh
                if garment_mesh:
                    # In a real app we'd keep them as separate primitives
                    final_mesh = trimesh.util.concatenate([body_mesh, garment_mesh])
                
                vertices = final_mesh.vertices.astype(np.float32)
                indices = final_mesh.faces.astype(np.uint32)
                
                # Pack binary data
                vertices_byte_data = vertices.tobytes()
                indices_byte_data = indices.tobytes()
                blob = vertices_byte_data + indices_byte_data
                
                gltf = GLTF2(
                    scene=0,
                    scenes=[GLTFScene(nodes=[0])],
                    nodes=[Node(mesh=0)],
                    meshes=[
                        Mesh(primitives=[
                            Primitive(
                                attributes=Attributes(POSITION=1),
                                indices=0,
                                material=None
                            )
                        ])
                    ],
                    accessors=[
                        # Indices accessor
                        Accessor(
                            bufferView=0,
                            componentType=5125, # UNSIGNED_INT
                            count=indices.size,
                            type="SCALAR",
                            max=[int(indices.max())],
                            min=[int(indices.min())],
                        ),
                        # Vertices accessor
                        Accessor(
                            bufferView=1,
                            componentType=5126, # FLOAT
                            count=len(vertices),
                            type="VEC3",
                            max=vertices.max(axis=0).tolist(),
                            min=vertices.min(axis=0).tolist(),
                        ),
                    ],
                    bufferViews=[
                        BufferView(
                            buffer=0,
                            byteOffset=len(vertices_byte_data),
                            byteLength=len(indices_byte_data),
                            target=34963, # ELEMENT_ARRAY_BUFFER
                        ),
                        BufferView(
                            buffer=0,
                            byteOffset=0,
                            byteLength=len(vertices_byte_data),
                            target=34962, # ARRAY_BUFFER
                        ),
                    ],
                    buffers=[
                        Buffer(
                            byteLength=len(blob)
                        )
                    ]
                )
                gltf.set_binary_blob(blob)
                gltf.save(output_path)
                logger.info("Successfully exported valid GLB via pygltflib!")

            else:
                # If dependencies aren't installed (dev mode), create a valid minimal empty GLB file
                # This is a generic valid 12-byte GLB header to prevent the frontend from crashing.
                # format: magic (glTF), version (2), length (12)
                minimal_glb = b'glTF\x02\x00\x00\x00\x0c\x00\x00\x00'
                with open(output_path, 'wb') as f:
                    f.write(minimal_glb)
                    
            return output_path
            
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            raise e

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
            # Default T-Pose / A-Pose
            body_pose = torch.eye(3, device=self.device).expand(1, 21, 3, 3) 
            
            # 2. SMPL-X Mesh Generation
            body_mesh = self._generate_body_mesh(betas, body_pose)
            
            # 3. Virtual Try On (Assuming a default t-shirt for now)
            garment_mesh = self._virtual_try_on(body_mesh)
            
            # 4. Scene Assembly and Export
            file_id = str(uuid.uuid4())
            output_path = f"/tmp/profile_{file_id}.glb"
            logger.info(f"Assembling Scene and exporting to {output_path}...")
            
            time.sleep(2) # Simulate CPU/GPU processing
            
            if HAS_ML_DEPS and body_mesh:
                # ------------------- PYGLTFLIB EXPORT -------------------
                final_mesh = body_mesh
                if garment_mesh:
                    final_mesh = trimesh.util.concatenate([body_mesh, garment_mesh])
                
                vertices = final_mesh.vertices.astype(np.float32)
                indices = final_mesh.faces.astype(np.uint32)
                
                vertices_byte_data = vertices.tobytes()
                indices_byte_data = indices.tobytes()
                blob = vertices_byte_data + indices_byte_data
                
                gltf = GLTF2(
                    scene=0,
                    scenes=[GLTFScene(nodes=[0])],
                    nodes=[Node(mesh=0)],
                    meshes=[
                        Mesh(primitives=[
                            Primitive(attributes=Attributes(POSITION=1), indices=0)
                        ])
                    ],
                    accessors=[
                        Accessor(bufferView=0, componentType=5125, count=indices.size, type="SCALAR", max=[int(indices.max())], min=[int(indices.min())]),
                        Accessor(bufferView=1, componentType=5126, count=len(vertices), type="VEC3", max=vertices.max(axis=0).tolist(), min=vertices.min(axis=0).tolist()),
                    ],
                    bufferViews=[
                        BufferView(buffer=0, byteOffset=len(vertices_byte_data), byteLength=len(indices_byte_data), target=34963),
                        BufferView(buffer=0, byteOffset=0, byteLength=len(vertices_byte_data), target=34962),
                    ],
                    buffers=[Buffer(byteLength=len(blob))]
                )
                gltf.set_binary_blob(blob)
                gltf.save(output_path)
            else:
                minimal_glb = b'glTF\x02\x00\x00\x00\x0c\x00\x00\x00'
                with open(output_path, 'wb') as f:
                    f.write(minimal_glb)
                    
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
