import os
import shutil
import tempfile
from celery import Celery
from ml_pipeline import run_avatar_generation, run_avatar_generation_from_profile

# Redis is used as both the message broker and backend for result storage
# Aspire injects the endpoint as tcp:// but celery requires redis://
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0").replace("tcp://", "redis://")

celery_app = Celery(
    "avatar_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

@celery_app.task(bind=True, name="generate_3d_avatar")
def generate_3d_avatar(self, task_id: str, image_bytes: bytes):
    """
    Celery task that runs the heavy ML prediction on GPU (or simulated via sleep here)
    """
    print(f"[{task_id}] Starting avatar generation task in worker...")
    self.update_state(state='PROGRESS', meta={'progress': 10, 'message': 'Initializing models'})
    
    try:
        # Pass to the pipeline (we update state along the way ideally, but here we just run it)
        output_glb_path = run_avatar_generation(image_bytes)
        
        # Move the generated file to the static avatars folder
        avatars_dir = os.path.join(os.getcwd(), "avatars")
        os.makedirs(avatars_dir, exist_ok=True)
        final_path = os.path.join(avatars_dir, f"{task_id}.glb")
        shutil.move(output_glb_path, final_path)
        
        model_url = f"/models/{task_id}.glb"
        
        return {
            "status": "completed",
            "model_url": model_url,
            "local_path": final_path,
            "message": "Avatar generated successfully."
        }
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise Exception(str(e))

@celery_app.task(bind=True, name="generate_3d_avatar_from_profile")
def generate_3d_avatar_from_profile(self, task_id: str, height: float, weight: float, body_type: str):
    """
    Celery task that runs the ML generation purely using mathematical profile params.
    """
    print(f"[{task_id}] Starting parametric avatar generation in worker...")
    self.update_state(state='PROGRESS', meta={'progress': 10, 'message': 'Mapping profile to SMPL betas...'})
    
    try:
        output_glb_path = run_avatar_generation_from_profile(height, weight, body_type)
        
        # Move the generated file to the static avatars folder
        avatars_dir = os.path.join(os.getcwd(), "avatars")
        os.makedirs(avatars_dir, exist_ok=True)
        final_path = os.path.join(avatars_dir, f"profile_{task_id}.glb")
        shutil.move(output_glb_path, final_path)
        
        model_url = f"/models/profile_{task_id}.glb"
        
        return {
            "status": "completed",
            "model_url": model_url,
            "local_path": final_path,
            "message": "Parametric Avatar generated successfully."
        }
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise Exception(str(e))


@celery_app.task(bind=True, name="generate_garment_3d")
def generate_garment_3d(self, task_id: str, primitive_type: str, input_image_path: str):
    """
    Celery task: removes the background from a clothing photo, processes it
    into a clean texture, and injects it into a base 3D GLB primitive.

    Args:
        task_id:          Unique identifier for this generation job.
        primitive_type:   One of 'tshirt', 'hoodie', 'pants', 'jacket'.
        input_image_path: Path to the uploaded clothing image on disk.
                          We accept a file path (not raw bytes) so Celery's
                          JSON serialiser never has to handle binary data.
    """
    print(f"[{task_id}] Starting garment generation task (primitive: {primitive_type})...")
    self.update_state(state='PROGRESS', meta={'progress': 10, 'message': 'Reading image...'})

    try:
        # Read the image from the path provided by the FastAPI endpoint
        if not os.path.exists(input_image_path):
            raise FileNotFoundError(f"Input image not found at: {input_image_path}")

        with open(input_image_path, "rb") as f:
            image_bytes = f.read()

        from garment_pipeline import GarmentMLPipeline
        pipeline = GarmentMLPipeline()

        self.update_state(state='PROGRESS', meta={'progress': 30, 'message': 'Removing background...'})

        # The pipeline handles rembg + centering + GLB injection internally
        self.update_state(state='PROGRESS', meta={'progress': 60, 'message': 'Applying texture to 3D primitive...'})
        output_glb_path = pipeline.apply_texture_to_primitive(primitive_type, image_bytes)

        # Move the result to the shared garments output directory
        garments_dir = os.path.join(os.path.dirname(__file__), "models", "garments")
        os.makedirs(garments_dir, exist_ok=True)
        final_filename = f"garment_{task_id}.glb"
        final_path = os.path.join(garments_dir, final_filename)
        shutil.move(output_glb_path, final_path)

        self.update_state(state='PROGRESS', meta={'progress': 90, 'message': 'Packaging result...'})

        garment_url = f"/models/garments/{final_filename}"

        return {
            "status": "completed",
            "model_url": garment_url,
            "local_path": final_path,
            "message": f"Garment '{primitive_type}' generated successfully."
        }
    except Exception as e:
        self.update_state(state='FAILURE', meta={'error': str(e)})
        raise Exception(str(e))
    finally:
        # Always clean up the temporary upload file to avoid disk buildup
        try:
            if os.path.exists(input_image_path):
                os.remove(input_image_path)
                print(f"[{task_id}] Cleaned up temp upload: {input_image_path}")
        except OSError as cleanup_error:
            print(f"[{task_id}] Warning: could not delete temp file {input_image_path}: {cleanup_error}")
