"""FastAPI route handlers for queueing generation jobs and polling Celery status."""

from __future__ import annotations

import logging
import os
import tempfile
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from vfr_ai_engine.api.schemas import (
    AvatarGenerationResponse,
    GarmentGenerationResponse,
    ProfileAvatarRequest,
)
from vfr_ai_engine.api.status import task_status_response

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
def read_root():
    return {"status": "ok", "service": "VFR AI Engine (HTTP+gRPC)"}


@router.get("/health")
def health_check():
    return {"status": "healthy"}


@router.post("/api/v1/avatar/generate", response_model=AvatarGenerationResponse)
async def generate_avatar(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File provided is not an image.")

    task_id = str(uuid.uuid4())
    image_bytes = await file.read()

    from vfr_ai_engine.tasks.avatar import generate_3d_avatar

    task = generate_3d_avatar.apply_async(args=[task_id, image_bytes], task_id=task_id)

    return AvatarGenerationResponse(
        task_id=task.id,
        status="accepted",
        message="Avatar generation task has been queued successfully.",
    )


@router.post("/api/v1/avatar/generate-from-profile", response_model=AvatarGenerationResponse)
async def generate_avatar_from_profile(request: ProfileAvatarRequest):
    task_id = str(uuid.uuid4())

    from vfr_ai_engine.tasks.avatar import generate_3d_avatar_from_profile

    task = generate_3d_avatar_from_profile.apply_async(
        args=[
            task_id,
            request.user_id,
            request.height,
            request.weight,
            request.body_type,
            request.gender,
            request.muscularity,
            request.body_fat_percentage,
            request.chest,
            request.waist,
            request.hip,
            request.shoulder,
            request.calf,
            request.arm_length,
            request.torso_length,
            request.leg_length,
            request.face_image_url,
        ],
        task_id=task_id,
    )

    return AvatarGenerationResponse(
        task_id=task.id,
        status="accepted",
        message="Parametric avatar generation task queued.",
    )


@router.post("/api/v1/garment/generate", response_model=GarmentGenerationResponse)
async def generate_garment(file: UploadFile = File(...), primitive_type: str = Form(...)):
    """Queue a garment texture job and return a polling task id."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File provided is not an image.")

    valid_primitives = ["tshirt", "hoodie", "pants", "jacket"]
    if primitive_type.lower() not in valid_primitives:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown primitive_type '{primitive_type}'. Valid options: {valid_primitives}",
        )

    task_id = str(uuid.uuid4())
    temp_image_path = os.path.join(tempfile.gettempdir(), f"upload_{task_id}.png")
    image_bytes = await file.read()
    with open(temp_image_path, "wb") as tmp_file:
        tmp_file.write(image_bytes)
    logger.info("Garment upload saved to temp: %s", temp_image_path)

    from vfr_ai_engine.tasks.garments import generate_garment_3d

    task = generate_garment_3d.apply_async(
        args=[task_id, primitive_type.lower(), temp_image_path],
        task_id=task_id,
    )

    return GarmentGenerationResponse(
        task_id=task.id,
        status="accepted",
        message=f"Garment texture generation for '{primitive_type}' has been queued.",
    )


@router.get("/api/v1/garment/status/{task_id}")
async def get_garment_status(task_id: str):
    """Poll the status of a garment generation task. Same shape as avatar status."""
    from celery.result import AsyncResult
    from vfr_ai_engine.tasks.app import celery_app

    try:
        result = AsyncResult(task_id, app=celery_app)
        return task_status_response(task_id, result.state, result.info, result.result)
    except Exception as exc:
        logger.exception("Failed to parse garment task status.", extra={"task_id": task_id})
        return {
            "task_id": task_id,
            "status": "FAILURE",
            "progress": 0,
            "message": f"Worker result parsing error: {str(exc)}",
        }


@router.get("/api/v1/avatar/status/{task_id}")
async def get_avatar_status(task_id: str):
    from celery.result import AsyncResult
    from vfr_ai_engine.tasks.app import celery_app

    try:
        result = AsyncResult(task_id, app=celery_app)
        return task_status_response(task_id, result.state, result.info, result.result)
    except Exception as exc:
        logger.exception("Failed to parse avatar task status.", extra={"task_id": task_id})
        return {
            "task_id": task_id,
            "status": "FAILURE",
            "progress": 0,
            "message": f"Worker result parsing error: {str(exc)}",
        }
