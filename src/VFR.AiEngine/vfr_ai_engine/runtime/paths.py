"""Shared filesystem locations for runtime code and validation tooling."""

from __future__ import annotations

import os
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = RUNTIME_DIR.parent
APP_ROOT = PACKAGE_DIR.parent

MODELS_DIR = Path(os.getenv("SMPLX_MODEL_DIR", str(APP_ROOT / "models")))
AVATAR_STORAGE_DIR = Path(os.getenv("AVATAR_STORAGE_DIR", str(APP_ROOT / "avatars")))
GARMENT_STORAGE_DIR = Path(os.getenv("GARMENT_STORAGE_DIR", str(APP_ROOT / "models" / "garments")))
GARMENT_PRIMITIVES_DIR = Path(os.getenv("GARMENT_PRIMITIVES_DIR", str(MODELS_DIR / "primitives")))
