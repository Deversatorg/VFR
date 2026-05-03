"""Static file mounts for generated avatar and garment artifacts."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from vfr_ai_engine.runtime.paths import AVATAR_STORAGE_DIR, GARMENT_STORAGE_DIR

AVATARS_DIR = str(AVATAR_STORAGE_DIR)
GARMENTS_DIR = str(GARMENT_STORAGE_DIR)


def install_static_model_mounts(app: FastAPI) -> None:
    os.makedirs(AVATARS_DIR, exist_ok=True)
    os.makedirs(GARMENTS_DIR, exist_ok=True)

    app.mount("/models/garments", StaticFiles(directory=GARMENTS_DIR), name="garments")
    app.mount("/models", StaticFiles(directory=AVATARS_DIR), name="models")

