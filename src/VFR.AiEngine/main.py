"""
VFR.AiEngine — gRPC Avatar Generation Service
Phase 3 MVP: deterministic avatar URLs based on body measurements.
Phase 4+: replace body of GenerateAvatar with a real ML pipeline.
"""

import grpc
from concurrent import futures
import os
import logging
import threading
import uuid

import tempfile

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

import avatar_pb2
import avatar_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AvatarServiceServicer(avatar_pb2_grpc.AvatarServiceServicer):
    """
    MVP implementation: returns a stable CDN URL based on user_id + body_type.
    TODO Phase 4: call a mesh-generation model (e.g. SMPL-X) to produce a real .glb.
    """

    # Base storage URL — override with AVATAR_STORAGE_BASE env var in production.
    _STORAGE_BASE = os.getenv("AVATAR_STORAGE_BASE", "https://storage.vfr.dev/models")

    def GenerateAvatar(
        self, request: avatar_pb2.AvatarRequest, context: grpc.ServicerContext
    ) -> avatar_pb2.AvatarResponse:
        logger.info(
            "gRPC GenerateAvatar: user=%s body_type=%s h=%.1f w=%.1f",
            request.user_id,
            request.body_type,
            request.height_cm,
            request.weight_kg,
        )

        body_slug = (request.body_type or "regular").lower()
        model_id = f"{request.user_id}_{body_slug}"
        
        # In a real phase 4, we might also push to Celery here,
        # but for now we keep the deterministic URL.
        avatar_url = f"{self._STORAGE_BASE}/{model_id}.glb"

        return avatar_pb2.AvatarResponse(
            avatar_url=avatar_url,
            model_id=model_id,
        )

# ── FastAPI Application ──────────────────────────────────────────────────────────

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(title="VFR AI Engine", description="AI 3D Avatar Generation & Try-On Pipeline")

# Directories for static file serving
_AVATARS_DIR  = os.path.join(os.getcwd(), "avatars")
_GARMENTS_DIR = os.path.join(os.path.dirname(__file__), "models", "garments")
os.makedirs(_AVATARS_DIR,  exist_ok=True)
os.makedirs(_GARMENTS_DIR, exist_ok=True)

# Mount static file directories
app.mount("/models/garments", StaticFiles(directory=_GARMENTS_DIR), name="garments")
app.mount("/models",          StaticFiles(directory=_AVATARS_DIR),  name="models")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict to actual frontend domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AvatarGenerationResponse(BaseModel):
    task_id: str
    status: str
    message: str

class GarmentGenerationResponse(BaseModel):
    task_id: str
    status: str
    message: str

class ProfileAvatarRequest(BaseModel):
    height: float
    weight: float
    body_type: str
    gender: str = 'neutral'  # 'male', 'female', or 'neutral'

@app.get("/")
def read_root():
    return {"status": "ok", "service": "VFR AI Engine (HTTP+gRPC)"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/api/v1/avatar/generate", response_model=AvatarGenerationResponse)
async def generate_avatar(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File provided is not an image.")

    task_id = str(uuid.uuid4())
    image_bytes = await file.read()
    
    from worker import generate_3d_avatar
    task = generate_3d_avatar.apply_async(args=[task_id, image_bytes], task_id=task_id)

    return AvatarGenerationResponse(
        task_id=task.id,
        status="accepted",
        message="Avatar generation task has been queued successfully."
    )

@app.post("/api/v1/avatar/generate-from-profile", response_model=AvatarGenerationResponse)
async def generate_avatar_from_profile(request: ProfileAvatarRequest):
    task_id = str(uuid.uuid4())
    
    from worker import generate_3d_avatar_from_profile
    task = generate_3d_avatar_from_profile.apply_async(
        args=[task_id, request.height, request.weight, request.body_type, request.gender],
        task_id=task_id
    )

    return AvatarGenerationResponse(
        task_id=task.id,
        status="accepted",
        message="Parametric avatar generation task queued."
    )

@app.post("/api/v1/garment/generate", response_model=GarmentGenerationResponse)
async def generate_garment(
    file: UploadFile = File(...),
    primitive_type: str = Form(...)
):
    """
    Accepts a 2D clothing image and a primitive type (e.g. 'tshirt', 'hoodie').
    Dispatches a Celery task to:
      1. Remove the background from the clothing photo.
      2. Process and centre the texture on a 1024x1024 canvas.
      3. Inject it into the matching base GLB primitive.
    Returns a task_id to poll via GET /api/v1/garment/status/{task_id}.

    NOTE: We save the upload to a temporary file and pass the *path* to Celery,
    not raw bytes — Celery's JSON serialiser cannot handle binary payloads.
    The worker cleans up the temp file after processing.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File provided is not an image.")

    valid_primitives = ["tshirt", "hoodie", "pants", "jacket"]
    if primitive_type.lower() not in valid_primitives:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown primitive_type '{primitive_type}'. Valid options: {valid_primitives}"
        )

    task_id = str(uuid.uuid4())

    # Persist the upload to a temp file so the Celery worker can read it.
    # We use a named temp file with delete=False so the path remains valid
    # after this request handler exits (the worker deletes it when done).
    tmp_dir = tempfile.gettempdir()
    temp_image_path = os.path.join(tmp_dir, f"upload_{task_id}.png")
    image_bytes = await file.read()
    with open(temp_image_path, "wb") as tmp_file:
        tmp_file.write(image_bytes)
    logger.info("Garment upload saved to temp: %s", temp_image_path)

    from worker import generate_garment_3d
    task = generate_garment_3d.apply_async(
        args=[task_id, primitive_type.lower(), temp_image_path],
        task_id=task_id
    )

    return GarmentGenerationResponse(
        task_id=task.id,
        status="accepted",
        message=f"Garment texture generation for '{primitive_type}' has been queued."
    )

@app.get("/api/v1/garment/status/{task_id}")
async def get_garment_status(task_id: str):
    """Poll the status of a garment generation task. Same shape as the avatar status endpoint."""
    from worker import celery_app
    from celery.result import AsyncResult

    try:
        res = AsyncResult(task_id, app=celery_app)
        state = res.state

        response = {
            "task_id": task_id,
            "status": state,
            "progress": 0,
            "message": ""
        }

        if state == 'PENDING':
            response['message'] = 'Task is waiting for a worker...'
        elif state == 'PROGRESS':
            if isinstance(res.info, dict):
                response['progress'] = res.info.get('progress', 0)
                response['message'] = res.info.get('message', '')
        elif state == 'SUCCESS':
            response['progress'] = 100
            response['message'] = "Completed"
            response['result'] = res.result
        elif state == 'FAILURE':
            response['message'] = str(res.result)

        return response
    except Exception as e:
        logger.error(f"Error parsing Celery state for garment task {task_id}: {str(e)}")
        return {
            "task_id": task_id,
            "status": "FAILURE",
            "progress": 0,
            "message": f"Worker result parsing error: {str(e)}"
        }

@app.get("/api/v1/avatar/status/{task_id}")
async def get_avatar_status(task_id: str):
    from worker import celery_app
    from celery.result import AsyncResult
    
    try:
        res = AsyncResult(task_id, app=celery_app)
        state = res.state
        
        response = {
            "task_id": task_id,
            "status": state,
            "progress": 0,
            "message": ""
        }

        if state == 'PENDING':
            response['message'] = 'Task is waiting for a worker...'
        elif state == 'PROGRESS':
            if isinstance(res.info, dict):
                response['progress'] = res.info.get('progress', 0)
                response['message'] = res.info.get('message', '')
        elif state == 'SUCCESS':
            response['progress'] = 100
            response['message'] = "Completed"
            response['result'] = res.result
        elif state == 'FAILURE':
            response['message'] = str(res.result)

        return response
    except Exception as e:
        logger.error(f"Error parsing Celery state for {task_id}: {str(e)}")
        return {
            "task_id": task_id,
            "status": "FAILURE",
            "progress": 0,
            "message": f"Worker result parsing error: {str(e)}"
        }

def serve_grpc() -> None:
    port = int(os.getenv("GRPC_PORT", "50051"))
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    avatar_pb2_grpc.add_AvatarServiceServicer_to_server(AvatarServiceServicer(), server)
    listen_addr = f"0.0.0.0:{port}"
    server.add_insecure_port(listen_addr)
    logger.info("VFR.AiEngine gRPC server listening on %s", listen_addr)
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    is_worker = os.getenv("RUN_WORKER", "false").lower() == "true"
    
    if is_worker:
        logger.info("Starting Celery Worker directly (Not Supported Here, Use CELERY CLI)")
    else:
        # Start gRPC in a background thread
        grpc_thread = threading.Thread(target=serve_grpc, daemon=True)
        grpc_thread.start()
        
        # Start FastAPI on the main thread
        http_port = int(os.getenv("PORT", "8000"))
        logger.info("VFR.AiEngine HTTP FastAPI listening on 0.0.0.0:%d", http_port)
        uvicorn.run(app, host="0.0.0.0", port=http_port)
