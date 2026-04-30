"""Celery task for converting a garment image into a served GLB artifact."""

from __future__ import annotations

import logging
import os
import shutil

from vfr_ai_engine.garments.pipeline import GarmentMLPipeline
from vfr_ai_engine.observability.logging import task_context
from vfr_ai_engine.paths import GARMENT_STORAGE_DIR
from vfr_ai_engine.tasks.app import celery_app

logger = logging.getLogger("VFR.AiEngine.Worker")


@celery_app.task(bind=True, name="generate_garment_3d")
def generate_garment_3d(self, task_id: str, primitive_type: str, input_image_path: str):
    """Texture a base garment primitive and move the GLB into the served garment storage."""
    with task_context(task_id=task_id):
        logger.info("Garment generation task started.", extra={"primitive_type": primitive_type})
        self.update_state(state="PROGRESS", meta={"progress": 10, "message": "Reading image..."})

        try:
            if not os.path.exists(input_image_path):
                raise FileNotFoundError(f"Input image not found at: {input_image_path}")

            with open(input_image_path, "rb") as f:
                image_bytes = f.read()

            pipeline = GarmentMLPipeline()
            self.update_state(state="PROGRESS", meta={"progress": 30, "message": "Removing background..."})
            self.update_state(state="PROGRESS", meta={"progress": 60, "message": "Applying texture to 3D primitive..."})
            output_glb_path = pipeline.apply_texture_to_primitive(primitive_type, image_bytes)

            garments_dir = str(GARMENT_STORAGE_DIR)
            os.makedirs(garments_dir, exist_ok=True)
            final_filename = f"garment_{task_id}.glb"
            final_path = os.path.join(garments_dir, final_filename)
            shutil.move(output_glb_path, final_path)

            self.update_state(state="PROGRESS", meta={"progress": 90, "message": "Packaging result..."})
            garment_url = f"/models/garments/{final_filename}"

            logger.info("Garment generation task completed successfully.", extra={"primitive_type": primitive_type})
            return {
                "status": "completed",
                "model_url": garment_url,
                "local_path": final_path,
                "message": f"Garment '{primitive_type}' generated successfully.",
            }
        except Exception:
            logger.exception("Garment generation task failed.", extra={"primitive_type": primitive_type})
            raise
        finally:
            try:
                if os.path.exists(input_image_path):
                    os.remove(input_image_path)
                    logger.info("Cleaned up temporary garment upload.")
            except OSError:
                logger.exception("Failed to clean up temporary garment upload.")
