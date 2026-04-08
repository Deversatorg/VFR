import logging
import os
import shutil

from celery import Celery

from logging_config import configure_logging, task_context
from ml_pipeline import run_avatar_generation, run_avatar_generation_from_profile

configure_logging("vfr-aiengine-worker")
logger = logging.getLogger("VFR.AiEngine.Worker")

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
    worker_hijack_root_logger=False,
    worker_redirect_stdouts=False,
)


@celery_app.task(bind=True, name="generate_3d_avatar")
def generate_3d_avatar(self, task_id: str, image_bytes: bytes):
    """Image-based avatar generation (future). Returns S3 URL."""
    with task_context(task_id=task_id):
        logger.info("Image avatar generation task started.")
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': 'Initialising models...'})

        try:
            model_url = run_avatar_generation(image_bytes)

            self.update_state(state='PROGRESS', meta={'progress': 95, 'message': 'Finalising...'})
            logger.info("Image avatar generation task completed successfully.")
            return {
                "status": "completed",
                "model_url": model_url,
                "message": "Avatar generated successfully."
            }
        except Exception:
            self.update_state(state='FAILURE', meta={'error': 'Avatar generation failed.'})
            logger.exception("Image avatar generation task failed.")
            raise


@celery_app.task(bind=True, name="generate_3d_avatar_from_profile")
def generate_3d_avatar_from_profile(
    self, task_id: str, user_id: str, height: float, weight: float, body_type: str, gender: str = 'neutral',
    muscularity: float = 0, body_fat_percentage: float = 0,
    chest: float = 0, waist: float = 0, hip: float = 0, shoulder: float = 0, calf: float = 0,
    arm_length: float = 0, torso_length: float = 0, leg_length: float = 0, face_image_url: str = ""
):
    """Parametric SMPL-X avatar generation. Returns S3 public URL."""
    with task_context(task_id=task_id, user_id=user_id):
        logger.info(
            "Profile avatar generation task started.",
            extra={"gender": gender, "body_type": body_type},
        )
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': f'Running SMPL-X ({gender})...'})

        try:
            generation_result = run_avatar_generation_from_profile(
                user_id, height, weight, body_type, gender,
                muscularity, body_fat_percentage,
                chest, waist, hip, shoulder, calf, arm_length, torso_length, leg_length, face_image_url
            )
            if isinstance(generation_result, str):
                model_url = generation_result
                measurements = {}
                targets = {}
                measurement_sources = {}
            else:
                model_url = generation_result.get("model_url", "")
                measurements = generation_result.get("measurements", {})
                targets = generation_result.get("targets", {})
                measurement_sources = generation_result.get("measurement_sources", {})

            self.update_state(state='PROGRESS', meta={'progress': 95, 'message': 'Finalising...'})
            logger.info("Profile avatar generation task completed successfully.")
            return {
                "status": "completed",
                "model_url": model_url,
                "measurements": measurements,
                "targets": targets,
                "measurement_sources": measurement_sources,
                "message": f"Avatar generated successfully (SMPL-X, gender={gender})."
            }
        except Exception:
            self.update_state(state='FAILURE', meta={'error': 'Profile avatar generation failed.'})
            logger.exception("Profile avatar generation task failed.")
            raise


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
    with task_context(task_id=task_id):
        logger.info(
            "Garment generation task started.",
            extra={"primitive_type": primitive_type},
        )
        self.update_state(state='PROGRESS', meta={'progress': 10, 'message': 'Reading image...'})

        try:
            if not os.path.exists(input_image_path):
                raise FileNotFoundError(f"Input image not found at: {input_image_path}")

            with open(input_image_path, "rb") as f:
                image_bytes = f.read()

            from garment_pipeline import GarmentMLPipeline
            pipeline = GarmentMLPipeline()

            self.update_state(state='PROGRESS', meta={'progress': 30, 'message': 'Removing background...'})
            self.update_state(state='PROGRESS', meta={'progress': 60, 'message': 'Applying texture to 3D primitive...'})
            output_glb_path = pipeline.apply_texture_to_primitive(primitive_type, image_bytes)

            garments_dir = os.path.join(os.path.dirname(__file__), "models", "garments")
            os.makedirs(garments_dir, exist_ok=True)
            final_filename = f"garment_{task_id}.glb"
            final_path = os.path.join(garments_dir, final_filename)
            shutil.move(output_glb_path, final_path)

            self.update_state(state='PROGRESS', meta={'progress': 90, 'message': 'Packaging result...'})
            garment_url = f"/models/garments/{final_filename}"

            logger.info(
                "Garment generation task completed successfully.",
                extra={"primitive_type": primitive_type},
            )
            return {
                "status": "completed",
                "model_url": garment_url,
                "local_path": final_path,
                "message": f"Garment '{primitive_type}' generated successfully."
            }
        except Exception:
            self.update_state(state='FAILURE', meta={'error': 'Garment generation failed.'})
            logger.exception(
                "Garment generation task failed.",
                extra={"primitive_type": primitive_type},
            )
            raise
        finally:
            try:
                if os.path.exists(input_image_path):
                    os.remove(input_image_path)
                    logger.info("Cleaned up temporary garment upload.")
            except OSError:
                logger.exception("Failed to clean up temporary garment upload.")
