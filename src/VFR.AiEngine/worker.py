import os
import shutil
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
