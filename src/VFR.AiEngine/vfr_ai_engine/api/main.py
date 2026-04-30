"""FastAPI process entrypoint; starts gRPC in-process for legacy compatibility."""

from __future__ import annotations

import logging
import os
import threading

import uvicorn

from vfr_ai_engine.api.app import create_app
from vfr_ai_engine.api.routes import (
    generate_avatar,
    generate_avatar_from_profile,
    generate_garment,
    get_avatar_status,
    get_garment_status,
    health_check,
    read_root,
)
from vfr_ai_engine.api.schemas import AvatarGenerationResponse, GarmentGenerationResponse, ProfileAvatarRequest
from vfr_ai_engine.api.static_files import AVATARS_DIR as _AVATARS_DIR, GARMENTS_DIR as _GARMENTS_DIR
from vfr_ai_engine.api.status import task_status_response as _task_status_response
from vfr_ai_engine.grpc.server import serve_grpc
from vfr_ai_engine.observability.logging import configure_logging

configure_logging("vfr-aiengine")
logger = logging.getLogger(__name__)
app = create_app()


def main() -> None:
    is_worker = os.getenv("RUN_WORKER", "false").lower() == "true"
    if is_worker:
        logger.info("Starting Celery Worker directly is not supported here; use the Celery CLI.")
        return

    grpc_thread = threading.Thread(target=serve_grpc, daemon=True)
    grpc_thread.start()

    http_port = int(os.getenv("PORT", "8000"))
    logger.info("VFR.AiEngine HTTP FastAPI listening on 0.0.0.0:%d", http_port)
    uvicorn.run(app, host="0.0.0.0", port=http_port, log_config=None, access_log=False)


if __name__ == "__main__":
    main()

