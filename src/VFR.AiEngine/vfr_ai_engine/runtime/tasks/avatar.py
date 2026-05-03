"""Celery tasks for image-based and profile-based avatar generation."""

from __future__ import annotations

import logging

from vfr_ai_engine.runtime.avatar.pipeline import run_avatar_generation, run_avatar_generation_from_profile
from vfr_ai_engine.runtime.observability.logging import task_context
from vfr_ai_engine.runtime.tasks.app import celery_app

logger = logging.getLogger("VFR.AiEngine.Worker")


@celery_app.task(bind=True, name="generate_3d_avatar")
def generate_3d_avatar(self, task_id: str, image_bytes: bytes):
    """Image-based avatar generation placeholder. Returns a fetchable model URL."""
    with task_context(task_id=task_id):
        logger.info("Image avatar generation task started.")
        self.update_state(state="PROGRESS", meta={"progress": 10, "message": "Initialising models..."})

        try:
            model_url = run_avatar_generation(image_bytes)
            self.update_state(state="PROGRESS", meta={"progress": 95, "message": "Finalising..."})
            logger.info("Image avatar generation task completed successfully.")
            return {
                "status": "completed",
                "model_url": model_url,
                "message": "Avatar generated successfully.",
            }
        except Exception:
            logger.exception("Image avatar generation task failed.")
            raise


@celery_app.task(bind=True, name="generate_3d_avatar_from_profile")
def generate_3d_avatar_from_profile(
    self,
    task_id: str,
    user_id: str,
    height: float,
    weight: float,
    body_type: str,
    gender: str = "neutral",
    muscularity: float = 0,
    body_fat_percentage: float = 0,
    chest: float = 0,
    waist: float = 0,
    hip: float = 0,
    shoulder: float = 0,
    calf: float = 0,
    arm_length: float = 0,
    torso_length: float = 0,
    leg_length: float = 0,
    face_image_url: str = "",
):
    """Parametric SMPL-X avatar generation from persisted Studio profile data."""
    with task_context(task_id=task_id, user_id=user_id):
        logger.info(
            "Profile avatar generation task started.",
            extra={"gender": gender, "body_type": body_type},
        )
        self.update_state(state="PROGRESS", meta={"progress": 10, "message": f"Running SMPL-X ({gender})..."})

        try:
            generation_result = run_avatar_generation_from_profile(
                user_id,
                height,
                weight,
                body_type,
                gender,
                muscularity,
                body_fat_percentage,
                chest,
                waist,
                hip,
                shoulder,
                calf,
                arm_length,
                torso_length,
                leg_length,
                face_image_url,
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

            self.update_state(state="PROGRESS", meta={"progress": 95, "message": "Finalising..."})
            logger.info("Profile avatar generation task completed successfully.")
            return {
                "status": "completed",
                "model_url": model_url,
                "measurements": measurements,
                "targets": targets,
                "measurement_sources": measurement_sources,
                "message": f"Avatar generated successfully (SMPL-X, gender={gender}).",
            }
        except RuntimeError as exc:
            logger.exception("Profile avatar generation task failed.")
            raise
        except Exception:
            logger.exception("Profile avatar generation task failed.")
            raise
