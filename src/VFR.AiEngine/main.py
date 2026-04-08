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
import time
import uuid

import tempfile

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from pydantic import BaseModel

import avatar_pb2
import avatar_pb2_grpc
from logging_config import configure_logging, generate_request_id, request_context

configure_logging("vfr-aiengine")
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

default_dev_origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
extra_allowed_origins = [
    origin.strip()
    for origin in os.getenv("AI_ENGINE_ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=default_dev_origins + extra_allowed_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _extract_trace_id(request: Request) -> str | None:
    traceparent = request.headers.get("traceparent", "").strip()
    if traceparent:
        parts = traceparent.split("-")
        if len(parts) >= 4 and len(parts[1]) == 32:
            return parts[1]

    return None


@app.middleware("http")
async def add_request_logging(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", "").strip() or generate_request_id()
    trace_id = _extract_trace_id(request) or request_id
    started_at = time.perf_counter()

    with request_context(request_id=request_id, trace_id=trace_id):
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.exception(
                "HTTP request failed.",
                extra={
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "elapsed_ms": elapsed_ms,
                },
            )
            raise

        response.headers["X-Request-ID"] = request_id

        if request.url.path not in {"/", "/health"}:
            elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
            log_fn = logger.warning if response.status_code >= 400 else logger.info
            log_fn(
                "HTTP request completed.",
                extra={
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "status_code": response.status_code,
                    "elapsed_ms": elapsed_ms,
                },
            )

        return response

class AvatarGenerationResponse(BaseModel):
    task_id: str
    status: str
    message: str

class GarmentGenerationResponse(BaseModel):
    task_id: str
    status: str
    message: str

class ProfileAvatarRequest(BaseModel):
    user_id: str
    height: float
    weight: float
    body_type: str
    gender: str = 'neutral'
    muscularity: float = 0
    body_fat_percentage: float = 0
    chest: float = 0
    waist: float = 0
    hip: float = 0
    shoulder: float = 0
    calf: float = 0
    arm_length: float = 0
    torso_length: float = 0
    leg_length: float = 0
    face_image_url: str = ""

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
        args=[
            task_id, request.user_id, request.height, request.weight, request.body_type, request.gender,
            request.muscularity, request.body_fat_percentage,
            request.chest, request.waist, request.hip, request.shoulder, request.calf,
            request.arm_length, request.torso_length, request.leg_length, request.face_image_url
        ],
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
        logger.exception(
            "Failed to parse garment task status.",
            extra={"task_id": task_id},
        )
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
        logger.exception(
            "Failed to parse avatar task status.",
            extra={"task_id": task_id},
        )
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
        uvicorn.run(app, host="0.0.0.0", port=http_port, log_config=None, access_log=False)
