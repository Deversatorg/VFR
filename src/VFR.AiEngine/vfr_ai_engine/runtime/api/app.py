"""Application factory for the AI engine FastAPI service."""

from __future__ import annotations

import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from vfr_ai_engine.runtime.api.middleware import install_request_logging
from vfr_ai_engine.runtime.api.routes import router
from vfr_ai_engine.runtime.api.static_files import install_static_model_mounts


def create_app() -> FastAPI:
    app = FastAPI(title="VFR AI Engine", description="AI 3D Avatar Generation & Try-On Pipeline")
    install_static_model_mounts(app)

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
    install_request_logging(app, logging.getLogger(__name__))
    app.include_router(router)
    return app
